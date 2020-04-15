#!/usr/bin/python3
# signal2json.py: Signal backup dumping script designed for dumping sqlite output
# of signal-backup-dump as JSON.
#
# JSON is used rather than the conventional CSV to facilitate JavaScript import,
# search indexing, and to save space by not having to include optional fields,
# of which because of left joins there are many.
#
# Produced by the Bibliotheca Anonoma under the direction of Chief Archivist Antonizoon Overtwater.
# The GPLv3 License is chosen for consistency with Signal community development. 

'''
This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU eneral Public License
along with this program.  If not, see <https://www.gnu.org/licenses/>.
'''

import os
import sys
import json
import sqlite3
from collections import OrderedDict

# import personal constant values from your config 
from config import * 

SIGNAL_GROUP_HEADER = "__textsecure_group__!"

def mkdirs(path):
    """Make directory, if it doesn't exist."""
    if not os.path.exists(path):
        os.makedirs(path)

# create the folder to output to
mkdirs(OUTPUT_PATH)

# generate a dict from a SQL query
def dict_factory(cursor, row):
    d = OrderedDict()
    for idx, col in enumerate(cursor.description):
        if row[idx] != None:
            d[col[0]] = row[idx]
    return d

conn = sqlite3.connect(SQLITE_DB)
conn.row_factory = dict_factory
cursor = conn.cursor()

# dict holding all signal backup data
backups = {}

def query(query):
    # 0. get all contact info (not all are signal contacts, only those with profile_key)
    cursor.execute(query)
    
    return cursor.fetchall()

def write(data, fname, sort_keys=False):
    with open(os.path.join(OUTPUT_PATH, '%s.json' % fname), 'w') as f:
        json.dump(data, f, indent=2, sort_keys=sort_keys)

''' Get the primary information '''

## 00. create homepage
# get all thread message info, which is primary definition of how 
# messages are grouped. it's what you see on the first screen
try:
    backups['threads'] = query(
        """SELECT thread._id AS thread_id, thread.date, thread.message_count, thread.recipient_ids, recipient.phone, recipient.group_id, coalesce(recipient.system_display_name,  groups.title) AS title, thread.snippet, thread.snippet_type, thread.delivery_receipt_count, thread.last_seen, groups.avatar_id, groups.avatar_content_type, thread.snippet_uri, thread.snippet_content_type, thread.snippet_extras FROM thread 
        LEFT JOIN recipient ON  thread.recipient_ids  = recipient._id 
        LEFT JOIN groups ON recipient.group_id = groups.group_id
        ORDER BY date DESC;"""
    )
except sqlite3.OperationalError as e: # no such table: recipient
    print("Possible old format: Unable to find the `recipient` table in this sql dump. Use signal2json.py instead.")
    print(e)
    sys.exit(1)

# create a dict of recipient_ids to titles for use with threads with no corresponding contact name
titles = {}
for item in backups['threads']:
    # try to use thread title first
    try:
        titles[item['recipient_ids']] = item['title']
    except KeyError:
        # otherwise try to use phone number as title
        try:
            titles[item['recipient_ids']] = item['phone']
        except KeyError:
            titles[item['recipient_ids']] = item['group_id']

write(backups['threads'], 'threads')

# 0. get all contact info (not all are signal contacts, only those with profile_key)
# includes contacts with user assigned name, contacts with only signal profile name
# does not include contacts not found in `recipient_preferences` (maybe they quit signal?) but found in `thread`. 
backups['contacts'] = query(
    """SELECT thread._id AS thread_id, thread.recipient_ids, recipient.phone, recipient.color, recipient.message_expiration_time, recipient.registered, recipient.system_display_name, recipient.system_photo_uri, recipient.system_contact_uri, recipient.profile_key, recipient.signal_profile_name, recipient.signal_profile_avatar, recipient.profile_family_name, recipient.profile_joined_name, thread.date, thread.message_count, thread.delivery_receipt_count, thread.last_seen 
    FROM recipient
    LEFT JOIN thread ON thread.recipient_ids  = recipient._id
    WHERE profile_key IS NOT NULL
    AND thread.recipient_ids NOT LIKE '__textsecure_group__!%';""" # don't include groups
)

backups['user_ids'] = {} # dict of user_id keys with str value title
for item in backups['contacts']:
    # try to find the user id defined as yourself in config.py from phone number
    try:
        if item['phone'] == PHONE_NUMBER and OWNER_RECIPIENT_ID is None:
            OWNER_RECIPIENT_ID = item['recipient_ids']
    except KeyError:
        # skip checking if there is no phone number
        pass
    
    try: # contact has a user assigned name
        backups['user_ids'][item['recipient_ids']] = item['system_display_name']
    
    except KeyError:
        try: # contact does not have a user assigned name, but has a signal profile name
            backups['user_ids'][item['recipient_ids']] = item['signal_profile_name']
            print(item['signal_profile_name'])
        
        except KeyError:
            try: # if there is no signal_profile_name, title, or phone, but there is a profile_joined_name, use that
                    backups['user_ids'][item['recipient_ids']] = item['profile_joined_name']
            
            except KeyError:
                try: 
                # contact has no name other than the thread name, phone number, or group id (probably because it is a group)
                    backups['user_ids'][item['recipient_ids']] = titles[item['recipient_ids']]
                    item['signal_profile_name'] = titles[item['recipient_ids']] # use title as profile name
                    print(item['signal_profile_name'])
                except KeyError: # last resort: set name to None object (rare)
                    backups['user_ids'][item['recipient_ids']] = None

write(backups['contacts'], 'contacts')

def index_user(c, thread, user_id, name=None):
    c["meta"]["userindex"].append(user_id)
    c["meta"]["users"][user_id] = {}
    
    # set name if provided, or try to find it in contacts, but set it to user_id if not found
    if name != None:
        c["meta"]["users"][user_id]["name"] = name
    else:
        try:
            c["meta"]["users"][user_id]["name"] = backups['user_ids'][user_id]
        except KeyError: # user_id does not exist in contacts
            try: # find a thread with a matching address
                c["meta"]["users"][user_id]["name"] = titles[user_id]
            except KeyError: # no matching thread with the title
                c["meta"]["users"][user_id]["name"] = user_id
                print("Couldn't find username for", user_id)

    return c["meta"]["userindex"].index(user_id) # get and store user ID number

def init_dict(address, title):
    # basic template for chat dict
    c = {}
    c["meta"] = {
        "channels": {},
        "servers": [{}],
        "userindex": [],
        "users": {}
    }
    c["data"] = {} # chats will have to be reordered when dumping with key sorting

    # populate chat dict with metadata
    c["meta"]["channels"][address] = {}
    c["meta"]["channels"][address]["name"] = title # thread title
    c["meta"]["channels"][address]["server"] = 0 # first server ID, always 0 in the case of a signal dump since there is only one dump source and one thread per file.

    c["meta"]["servers"][0]["name"] = SQLITE_DB # set the "server" to the dump name
    c["meta"]["servers"][0]["service"] = "signal" # service name, can be detected by the viewer to make use of a service's additional fields
    c["meta"]["servers"][0]["type"] = "SERVER" # set the type to "SERVER" representing group chat not pm

    # add your own user as the first (index 0) in the userindex
    index_user(c, address, PHONE_NUMBER, name=DISPLAY_NAME)
    
    return c

# log can be used to store to a single sequence csv-style chat log
def get_sms(c, thread_id, address, log=None, pm=False):
    # get group messages FROM sms where thread_id = <tid>
    # match all addresses (phone numbers) to contact name (use simple join)
    sms = query(
        """SELECT sms._id AS sid, sms.address, recipient.system_display_name, sms.reply_path_present, sms.date, sms.date_sent, sms.body, sms.reactions, sms.reactions_last_seen
        FROM sms
        LEFT JOIN recipient  ON sms.address = recipient._id
        WHERE thread_id = %d
        ORDER BY date ASC;
        """ % thread_id
    )
    
    # populate group chat with sms using date as id
    c["data"][address] = {}
    for text in sms:
        # Groups: address == group_id means its your own message
        if pm:
            try:
                # reply_path_present == None means its your own message, otherwise its the other persons
                if text['reply_path_present'] == 1:
                    del text['reply_path_present']
            except KeyError:
                text['address'] = PHONE_NUMBER
                text['system_display_name'] = DISPLAY_NAME
        else: # group chat detection method only
            # Groups: address == group_id means its your own message
            if (text['address'] == address): 
                text['address'] = PHONE_NUMBER
                text['system_display_name'] = DISPLAY_NAME
            
            try: # remove extraneous field
                del text['reply_path_present']
            except KeyError:
                pass
        
        # date_sent used as message ID, as it is constant, will always be the same without duplicates on every dump, sorts automatically by date in json.
        # FIXME: not known if quote_id uses date_sent as primary key
        sid = str(text['date_sent'])
        c["data"][address][sid] = {}
        c["data"][address][sid]['t'] = text['date_sent'] # date_sent is what the signal app displays to you
        
        try: # message body is missing for some reason
            c["data"][address][sid]['m'] = text['body']
        except:
            c["data"][address][sid]['m'] = ""
        
        try:
            c["data"][address][sid]['u'] = c["meta"]["userindex"].index(text['address']) # get and store user ID number
        
        except ValueError: # user not found in current group membership, but might just be a removed user, so add them to the list
            # get and store user ID number
            c["data"][address][sid]['u'] = index_user(c, address, text['address']) 
        
        # additional fields not processed by the viewer at the moment
        c["data"][address][sid]['date_received'] = text['date'] # date the other person received
        
        if log != None: # store to log if provided
            log[text['date_sent']] = text

# log can be used to store to a single sequence csv-style chat log
def get_mms(c, thread_id, address, log=None, pm=False):
    # if address is equal to the group id, that's your own message
    # get all attachments FROM part to add to group messages, null if nonexistent
    mms = query(
        """SELECT mms._id AS mid, mms.date, mms.date_received, mms.body, mms.address, recipient.system_display_name , mms.m_type, part.unique_id, part._id AS part_id, part.file_name AS orig_fname, part.ct, part.data_size, part.aspect_ratio, part.width, part.height, part.quote, part.voice_note, part.caption, mms.quote_id, mms.quote_author, mms.quote_body
        FROM mms
        INNER JOIN recipient  ON mms.address = recipient._id
        LEFT JOIN part ON part.mid = mms._id
        WHERE thread_id = %d
        ORDER BY date ASC;
        """ % thread_id
    )

    # populate group chat with mms
    for text in mms:
        if not pm: # group chat detection method only
            # Groups: address == group_id means its your own message
            if (text['address'] == address): 
                text['address'] = PHONE_NUMBER
                text['system_display_name'] = DISPLAY_NAME

        # private messages: where the address is the other person's, so st differentiates
        try:
            # st is whether you sent it (null) or the other person sent it (1)
            if (text['st'] == 1):
                del text['st'] # remove unnecessary field
        except KeyError:
            text['address'] = PHONE_NUMBER
            text['system_display_name'] = DISPLAY_NAME
        
        # str(date) used as message ID, as it is constant, will always be the same without duplicates on every dump, sorts automatically by date in json. quote_id uses date as primary key
        mid = str(text['date'])
        c["data"][address][mid] = {}
        c["data"][address][mid]['t'] = text['date'] # equivalent to date_sent, not date_received
        c["data"][address][mid]['date_received'] = text['date_received'] # date your device received the message

        try: # remove empty body variable from those with no attachment
            if text['body'] != "" and text['body'] != None:
                c["data"][address][mid]['m'] = text['body'] # set body
            else:
                c["data"][address][mid]['m'] = "" # special case: body of the message should always exist
        except KeyError:
            c["data"][address][mid]['m'] = "" # special case: body of the message should always exist
        
        try:
            c["data"][address][mid]['u'] = c["meta"]["userindex"].index(text['address']) # get and store user ID number
        
        except ValueError: # user not found in current group membership, but might just be a removed user, so add them to the list
            # get and store user ID number
            c["data"][address][mid]['u'] = index_user(c, address, text['address'])

        ## mms attachment objects
        try:
            if text['quote_id'] == 0: # eliminate existing empty quote
                del text['quote']
                del text['quote_id']
            else: # quote exists and has content
                # process the quote into a quote object
                c["data"][address][mid]['q'] = {}
                # quote_id actually references `mms.date` of the post, when it was sent
                # TODO: Figure out if it represents either `sms.date_sent` as would be logical, or `sms.date` which is when your device recorded it.
                c["data"][address][mid]['q']['t'] = text['quote_id']
                c["data"][address][mid]['q']['m'] = text['quote_body']
                
                try:
                    c["data"][address][mid]['q']['u'] = c["meta"]["userindex"].index(text['quote_author'])
                except ValueError: # quote_author not found, maybe their messages were deleted or are in a different thread
                    # get and store user ID number
                    c["data"][address][mid]['u'] = index_user(c, address, text['quote_author'])
                
                # quote attachments can be processed later when we start having them
                # you will need to check mms.quote_attachment != -1 for any posts
                # then get the attachment data from those with part.quote = 1
                #c["data"][address][mid]['q']['a'] = {}
                #c["data"][address][mid]['q']['a']['url'] = ""
    
        except KeyError:
            pass
        
        # m_type = 128 is text, 132 is media?. But not always, so we can't rely on this. Does it mean sms vs gcm? It appears to be a mandatory column.
        
        # attachment `a` found by filename and expected to be included in the file. embeds `e` are for images to be previewed.
        try: # generate filename by putting together unique_id (timestamp) and part_id together
            text['fname'] = str(text['unique_id']) + "_" + str(text['part_id'])
        
            try:
                if text['voice_note'] == 0: # eliminate unnecessary variables
                    del text['voice_note']
            except KeyError: # variable does not exist so skip
                pass

            # if the MIME type is an image, use embed object to allow preview.
            if 'image' in text['ct']:
                o = 'e'
            else: # Otherwise, use discord attachment object for files
                o = 'a'

            # instantiate the list of dictionary attachments (allows multiple in one message, but Signal doesn't do this so it is always index 0)
            c["data"][address][mid][o] = [{}]

            # Notice that in older messages width, height, and aspect ratio were not stored
            # just set url to bare fname, which the viewer should convert when it detects a signal message to the correct uri
            c["data"][address][mid][o][0]['url'] = "attachments/" + text['fname'] # url for discord history viewer, where it is served using simpleHTTPviewer
            c["data"][address][mid][o][0]['type'] = text['ct'].split('/')[0] # file type, without full MIME
            
            # additional fields not used by the viewer at the moment
            c["data"][address][mid][o][0]['fname'] = text['fname'] # true filename stored
            c["data"][address][mid][o][0]['mime'] = text['ct'] # MIME Type (takes the place of file extensions)
            c["data"][address][mid][o][0]['size'] = text['data_size'] # file size in bytes
            
            try: # set width and height of images
                c["data"][address][mid][o][0]['w'] = text['width'] # image height
                c["data"][address][mid][o][0]['h'] = text['height'] # image height
                
            except KeyError:
                pass
        
        except KeyError: # no attachment found
            pass

        if log != None: # store to log if provided
            log[text['date']] = text

## obtain all group messages
# get group unique info by thread._id FROM groups
backups['groups'] = query(
    """SELECT thread._id AS thread_id, groups.group_id, groups.title, groups.members, groups.timestamp, groups.active,  groups.avatar_id, groups.avatar_content_type, thread.date, thread.message_count, thread.delivery_receipt_count, thread.last_seen 
    FROM groups
    INNER JOIN thread ON thread.recipient_ids  = groups.group_id;"""
)
# turn members into a list of member jsons
backups['group_ids'] = {} # dict of group_id keys with str value title
for item in backups['groups']:
    backups['group_ids'][item['group_id']] = item['title']
    item['members'] = item['members'].split(",")

write(backups['groups'], 'groups')

# writes chat to json compatible with discord and sorted with meta on top
def write_chat(c, thread, address, title):
    if sys.version_info >= (3, 7): # (Python 3.7 only) sort chats and ensure that meta is on top
        chat = {}
        chat['meta'] = c['meta']
        chat['data'] = {}
        for channel in c['data']: # for each channel in data
            # https://stackoverflow.com/questions/11089655/sorting-dictionary-python-3
            chat['data'][channel] = {k: c['data'][channel][k] for k in sorted(c['data'][channel])}
        
        write(
            chat,
            "%s-%s" % ( # write unique filename with phone number (without __textsecure_group++!) as first word, contact name without spaces
                address,
                title.replace(" ", "_")
            )
        )
    else: # Python versions below 3.7 have to just rely on json.dumps to sort for you
        write(
            c,
            "%s-%s" % (
                address,
                title.replace(" ", "_")
            ),
            sort_keys=True
        )
    # write to csv and plain test logging... but i are tired

# loop on every group id
backups['group_chat'] = {}
for thread in backups['groups']:
    c = init_dict(thread['group_id'], thread['title']) # create the dictionary to dump data to for this thread

    # add the rest of the users by user_id (phone number) to the user index, basic info only
    for user_id in thread['members']:
        # get and store user ID number
        index_user(c, thread['group_id'], user_id)
    
    # stores to c in standard format, still log sms in standard manner though
    backups['group_chat'][thread['group_id']] = {}
    get_sms(c, thread['thread_id'], thread['group_id'], log=backups['group_chat'][thread['group_id']])
    get_mms(c, thread['thread_id'], thread['group_id'], log=backups['group_chat'][thread['group_id']])
    
    write_chat(c, thread, thread['group_id'].replace(SIGNAL_GROUP_HEADER, ""), thread['title'])

    #write(
        #backups['group_chat'][thread['group_id']],
        #"%s-%s" % (
            #thread['group_id'].replace(SIGNAL_GROUP_HEADER, ""),
            #thread['title'].replace(" ", "_")
        #),
        #sort_keys=True
    #)

## Get all user chat messages
# loop on every id
backups['chat'] = {}
for thread in backups['contacts']:
    try: # try to use the contact's system set name
        title = thread['system_display_name']
    except KeyError:
        try: # try to use the contact's signal profile name
            title = thread['signal_profile_name']
        except KeyError: # last resort, use recipient_ids
            title = thread['recipient_ids']
    
    c = init_dict(thread['recipient_ids'], title) # create the dictionary to dump data to for this thread
    
    # stores to c in standard format, still log sms in standard manner though
    backups['chat'][thread['recipient_ids']] = {}
    get_sms(c, thread['thread_id'], thread['recipient_ids'], log=backups['chat'][thread['recipient_ids']], pm=True)
    get_mms(c, thread['thread_id'], thread['recipient_ids'], log=backups['chat'][thread['recipient_ids']], pm=True)
    
    write_chat(c, thread, thread['recipient_ids'], title)

conn.close()
