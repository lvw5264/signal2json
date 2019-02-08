#!/usr/bin/python3
# signal2json.py: Signal backup dumping script designed for dumping sqlite output
# of signal-backup-dump as JSON.
#
# JSON is used rather than the conventional CSV to facilitate JavaScript import,
# search indexing, and to save space by not having to include optional fields,
# of which because of left joins there are many.
#
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

# dict holding all signal backup keys
backups = OrderedDict()

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
backups['threads'] = query(
	"""SELECT thread._id, date, message_count, thread.recipient_ids, coalesce(recipient_preferences.system_display_name,  groups.title) AS title, snippet, snippet_type, delivery_receipt_count, last_seen, groups.avatar_id, groups.avatar_content_type FROM thread 
	LEFT JOIN groups ON thread.recipient_ids = groups.group_id
	LEFT JOIN recipient_preferences ON  thread.recipient_ids  = recipient_preferences.recipient_ids 
	ORDER BY date DESC;"""
)
write(backups['threads'], 'threads')

# 0. get all contact info (not all are signal contacts, only those with profile_key)
backups['contacts'] = query(
	"""SELECT thread._id AS thread_id, thread.recipient_ids, color, expire_messages, system_display_name, system_contact_photo, system_contact_uri , profile_key, signal_profile_name, signal_profile_avatar, thread.date, thread.message_count, thread.delivery_receipt_count, thread.last_seen 
	FROM recipient_preferences
	INNER JOIN thread ON thread.recipient_ids  = recipient_preferences.recipient_ids
	WHERE profile_key IS NOT NULL;"""
)

backups['user_ids'] = {} # dict of user_id keys with str value title
for item in backups['contacts']:
	try:
		backups['user_ids'][item['recipient_ids']] = item['system_display_name']
	except KeyError:
		backups['user_ids'][item['recipient_ids']] = item['signal_profile_name']

write(backups['contacts'], 'contacts')

## Get all user chat messages
# loop on every id
backups['chat'] = OrderedDict()
for thread in backups['contacts']:
	# set address to recipient_ids
	address = thread['recipient_ids']
	
	# get messages FROM mms where thread_id = <tid>
	# match all addresses (phone numbers) to contact name (use simple join)
	sms = query(
		"""SELECT sms._id AS sid, address, recipient_preferences.system_display_name,  reply_path_present, date, date_sent, body 
		FROM sms
		LEFT JOIN recipient_preferences  ON sms.address = recipient_preferences.recipient_ids
		WHERE thread_id = %d
		ORDER BY date ASC;
		""" % thread['thread_id']
	)
	
	# populate chat with sms using date as id
	backups['chat'][address] = {}
	for text in sms:
		try:
			# reply_path_present == None means its your own message, otherwise its the other persons
			reply_message = text['reply_path_present'] != None
			if reply_message:
				del text['reply_path_present'] # remove unnecessary field
		except KeyError:
			text['address'] = PHONE_NUMBER
			text['system_display_name'] = DISPLAY_NAME
			

		backups['chat'][address][text['date']] = text
	
	# if address is equal to the thread name, that's your own message
	# get all attachments FROM part to add to messages, null if nonexistent
	mms = query(
		"""SELECT mms._id AS mid, mms.date, mms.date_received, mms.body, mms.address, recipient_preferences.system_display_name , mms.m_type, part.unique_id, part._id AS part_id, part.file_name AS orig_fname, part.ct, part.data_size, part.aspect_ratio, part.width, part.height, part.quote, part.voice_note, part.caption, mms.quote_id, mms.quote_author, mms.quote_body, mms.st
		FROM mms
		INNER JOIN recipient_preferences  ON mms.address = recipient_preferences.recipient_ids
		LEFT JOIN part ON part.mid = mms._id
		WHERE thread_id = %d
		ORDER BY date ASC;
		""" % thread['thread_id']
	)

	# populate  chat with mms
	for text in mms:
		try:
			# STATUS st is whether you sent it (null) or the other person sent it (1)
			reply_mms = text['st'] != None
			if reply_mms:
				del text['st'] # remove unnecessary field
		except KeyError:
			text['address'] = PHONE_NUMBER
			text['system_display_name'] = DISPLAY_NAME
		
		try:
			if text['body'] == "":
				del text['body']
		except KeyError:
			pass
		
		# Notice that in older messages width, height, and aspect ratio were not stored
		
		try:
			if text['voice_note'] == 0: # eliminate unnecessary variables
				del text['voice_note']
		except KeyError: # variable does not exist so skip
			pass

		try:
			if text['quote_id'] == 0:
				del text['quote']
				del text['quote_id']
		except KeyError:
			pass
		
		try: # generate filename by putting together unique_id (timestamp) and part_id together
			text['fname'] = str(text['unique_id']) + "_" + str(text['part_id'])
		except KeyError: # key doesn't exist since no attachment, move on
			pass
		
		# we need to somehow obtain the files, which may be found in the digest but its doubtful
		# maybe it was overlooked by this dumper. don't wipe signal until you are sure
		#try:
		#	text['digest']
		
		backups['chat'][address][text['date']] = text

	# write unique filename with phone number (without +) as first word, contact name without spaces
	write(
		backups['chat'][address],
		"%s-%s" % (
			address.replace("+", ""),
			thread['system_display_name'].replace(" ", "_")
		),
		sort_keys=True
	)



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

# loop on every group id
backups['group_chat'] = OrderedDict()
for thread in backups['groups']:
	# set address to group_id
	address = thread['group_id']
	
	# get group messages FROM mms where thread_id = <tid>
	# match all addresses (phone numbers) to contact name (use simple join)
	sms = query(
		"""SELECT sms._id AS sid, address, recipient_preferences.system_display_name, date, date_sent, body 
		FROM sms
		LEFT JOIN recipient_preferences  ON sms.address = recipient_preferences.recipient_ids
		WHERE thread_id = %d
		ORDER BY date ASC;
		""" % thread['thread_id']
	)
	
	# populate group chat with sms using date as id
	backups['group_chat'][address] = {}
	for text in sms:
		backups['group_chat'][address][text['date_sent']] = text
	
	# if address is equal to the group id, that's your own message
	# get all attachments FROM part to add to group messages, null if nonexistent
	mms = query(
		"""SELECT mms._id AS mid, mms.date, mms.date_received, mms.body, mms.address, recipient_preferences.system_display_name , mms.m_type, part.unique_id, part._id AS part_id, part.file_name AS orig_fname, part.ct, part.data_size, part.aspect_ratio, part.width, part.height, part.quote, part.voice_note, part.caption, mms.quote_id, mms.quote_author, mms.quote_body
		FROM mms
		INNER JOIN recipient_preferences  ON mms.address = recipient_preferences.recipient_ids
		LEFT JOIN part ON part.mid = mms._id
		WHERE thread_id = %d
		ORDER BY date ASC;
		""" % thread['thread_id']
	)

	# populate group chat with mms
	for text in mms:
		if text['address'] == address: # address == group_id means its your own message
			text['address'] = PHONE_NUMBER
			text['system_display_name'] = DISPLAY_NAME
		
		try:
			if text['voice_note'] == 0: # eliminate unnecessary variables
				del text['voice_note']
		except KeyError: # variable does not exist so skip
			pass
		
		# Notice that in older messages width, height, and aspect ratio were not stored

		try:
			if text['quote_id'] == 0:
				del text['quote']
				del text['quote_id']
		except KeyError:
			pass
		
		try: # generate filename by putting together unique_id (timestamp) and part_id together
			text['fname'] = str(text['unique_id']) + "_" + str(text['part_id'])
			
			try: # remove empty body variable from those with no attachment
				if text['body'] == "":
					del text['body']
			except KeyError:
				pass
		except KeyError: # key doesn't exist since no attachment, move on
			pass
		
		backups['group_chat'][address][text['date']] = text
		
	# write unique filename with phone number (without __textsecure_group++!) as first word, contact name without spaces
	write(
		backups['group_chat'][address],
		"%s-%s" % (
			address.replace("__textsecure_group__!", ""),
			thread['title'].replace(" ", "_")
		),
		sort_keys=True
	)

conn.close()
