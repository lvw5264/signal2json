**Signal2JSON.py** converts signal backups decrypted and dumped in SQLite from [signal-backup-decode](https://github.com/pajowu/signal-backup-decode) into human readable, pretty printed JSON, which can be read as is or imported into other databases/viewers (ideally on encrypted storage of course), of which the [Discord History Viewer](https://dht.chylex.com/build/viewer.html) is utilized for reference. 

We will make a modified version of the discord history viewer to add additional functionality and possibly even make it a universal chat log viewer. It's chat log format is very elegant and makes a perfect universal standard for all other chat logs to be converted to.

Due to the amount of media being shared over the course of three years, the Signal app data grew to be 5gb in size for some users, which became almost impractical to back up, search, or even maintain in the app safely (where one malformed message made the app crash before a backup could complete). Most of all having the full chat history on a portable device is a security and privacy risk no matter what encryption or passwords are on the device, as it could possibly be caught unlocked, and the risk grows as more data retained on device. 

This script allows chats to be dumped to backup and a retention period set where chats are deleted after each backup, yet still accessible and searchable on a less often accessed (ideally encrypted) device.

Signal encrypted backups can be dumped to sqlite, but require the use of complex SQL joins to obtain the data in the expected series. Instead, this script was made to allow the Signal app to have chat history cleared after each successful backup, which can be done periodically.


## Usage

### Step 1: Extract SQLite

```
# install signal-backup-decode from rust repositories
$ cargo install signal-backup-decode

# for a backup file called: signal-2018-11-01-00-00-00.backup and a password file with 30 char password no spaces or newlines
$ ~/.cargo/bin/signal-backup-decode signal-2018-11-01-00-00-00.backup --password_file passwords.txt --sqlite-path signal-2018-11-01-00-00-00.sqlite
```

### Step 2: Run Signal2JSON.py

Signal-backup-decode gives you a sqlite file that we can convert to a JSON format compatible with the Discord History Viewer. Copy that sqlite over to the same directory as `signal2json.py`.

First, create a file called `config.py` (using the config.py.example file included in this repository), and fill out the information with your relevant information. In particular, you will need to put your own personal contact name to label your own messages, as this information is not stored in Signal. Since this makes `config.py` personal information, this file is ignored in `.gitignore` in this repository.

```
# paths of source database files and output directories
SQLITE_DB = "signal-2018-11-01-00-00-00.sqlite"
OUTPUT_PATH = "signal-2018-11-01-00-00-00"

# your own personal display name
DISPLAY_NAME = "Your Name"
PHONE_NUMBER = "+19999999999"
```

Then just run the following command (python3 is strongly recommended for superior unicode support, but the default python 2 might work):


> **Note:** If an older signal dump is used (prior to ~2020, such as 20190130), it will have an older SQL schema where the `recipient` table is named `recipients_preferences`, and the phone number was used as the `recipient_ids`, rather than a user id. Use the prior git tag 20190130 instead. https://github.com/lvw5264/signal2json/releases/tag/20190130

```
python3 signal2json.py
```

Your chat logs will then be output to `OUTPUT_PATH` as specified in `config.py`, with the filenames (group id/phone number, full name):

```
+19999999999-Your_Name.json
tExTs3cur3gr0up1d-Cryptocurrency_AI_Trader
```

There are also lists of your contacts, groups, and thread view (what you see in the main screen of the signal UI) in the following files:

```
contacts.json
groups.json
threads.json
```

### Step 3: Import into Discord History Viewer

As seen in `example.json.py`, a lightly augmented version of Discord History Viewer's refreshingly simple format is used in a modified version of its HTML code to allow it to view images locally.

Because of security restrictions on reading files from disk in browser HTML/JS code, if you want to view images you will need to serve the images directory using python's simpleHTTPserver, available on any Linux or Mac OS X system.

https://dht.chylex.com/build/viewer.html

First, cd into the folder created by `signal-backup-decode` in Step 3. It should have an `attachments/` folder inside. We will download the viewer next to that folder and serve it with python's simple HTTP server, so we can view the attachments embedded.

```
$ cd signal-2018-11-01-00-00-00  # the folder where `signal-backup-decode` put your attachments/ folder
$ wget https://dht.chylex.com/build/viewer.html  # download the discord history viewer
$ ls                                             # ensure that you see the following folders & files at least (extra files are OK)
attachments  avatars    config     viewer.html
$ python -m SimpleHTTPServer 8000                # run the python webserver in there to make the attachments viewable
```

Then, open up the url [`http://localhost:8000/viewer.html`](http://localhost:8000/viewer.html) . Then click "Load File" at the top right and select a chat log json. You will be able to see chat logs, and the images will be embedded. Non-image files will appear as downloadable attachments instead.

We will make a modified edition of Discord History Viewer able to view embedded images and guess the correct file extension from MIMEtype for downloadable attachments, because currently it is just saved without a file extension (unacceptable in Windows).

## Formats

Two output formats are used, one which closely matches the full output of Signal to csv or plain text, and a second which matches that of discord. (csv format is pending work)

### Universal Chat Log Format

Based on the Discord JSON message output of Discord History Tracker (under the open source MIT License), this format is chosen as our universal chat file format due to various factors:

1. **Simplicity** - The log format provides the very basics, yet elements universally applicable to any modern group chat system and even older ones such as IRC. There's a chat log with  message ids for hashes, message body, and optional e external link objects and a attachment objects which have a URL associated which works for both local and remote paths. These elements are applicable in some form to almost every modern group chat. Most of all, unlike XML it is decently readable by a human when indented.
2.  **Elegance of Design** - The Discord log format has a very elegant structure with an initial Meta object describing each user in the conversation. It scales effortlessly from a private message to a massive group, with members able to be added at anyt time. And it can easily be expanded as need be without affecting the ability for the Discord History Tracker to view it, though it may be good to modify the viewer to expand all the extra key value pairs as needed.
3. **Existing Open Source Viewer** - Discord History Tracker provides a nice client-side browser based viewer that can be retrofitted for use with any other group chat logs that can be converted to this format. It can be run offline or online wherever Javascript is available.
  * One issue might be the lack of the ability to simply embed files due to browser security restrictions, but this might be resolved by running a simple python HTTP server on the attachments to make them visible.
  * We make all Signal attachments with "image" MIMEtype embeds `"e"`, and all other MIME types attachments `a`. This way, images can be viewed if an HTTP server is utilized, and attachments can be downloaded.
4. **Use in a Popular Group Chat** - Given that our Discord chat logs are already in the format, it was convenient to simply match this format rather than build yet another standard that few people would use.

Dump path/filename format: `service_name/20181224/chat_id-chat_name.json`

### Future Possibilities

We will attempt to convert various other log formats to match this standard, particularly our Signal dumps. For example:

* Signal encrypted backups are stored in their own special scheme and its up to other developers like me to make them readable. The table fields seem reminiscent of its SMS/MMS past, with an annoying split between messages that typically go over SMS and messages that typically go over MMS. Also many fields were added over time and not available previously.
* Google Hangouts/GChat - The predecessor to our use of Signal is this cloud chat provider, which gives logs in the convenient JSON format despite being XMPP at its core.
* Facebook Chat - Another XMPP chat from the past. It's time to delete and exit.
* Matrix/Riot.im - The wildly popular open source self hostable alternative to IRC is a major goal for us. We need to be able to dump encrypted messages though.
* SMS/MMS - Generic text message groups can be transformed from XML to this format used by a popular Android sms backup app. This can also be used for past Signal backups and the Silence app too.
  * One user is stuck by vendor lock in to Textra, we have little choice but to break in a titaniumbackup dump to retrieve the data.
* IRCCloud, Quassel - Two IRC chat systems that I have plain text logs for. These can get difficult to parse, they have discord bridging for the most part, and they were designed to be read as they are so I might let them pass. But it is a major goal.
* GroupMe: Does JSON backups as well.
* WhatsApp: Much like Signal but it aint.
* Telegram: Piloted for a while, not really what we needed.
* Other platforms not relevant to us but still worthy might be Slack, RocketChat, 

## Key Design Considerations

See the Signal-Android code to review the SQL Schema for Signal on Android. We refer to SQL fields in the format `table.field`. There is no iOS support since currently there is no way to backup from Signal for iOS.

* Due to the use of SQL LEFT JOINs, many records had fields that are NULL, lacking a corresponding value. We elected to remove them from the JSON object to represent the lack of data, as well as in cases where no useful information exists (equals 0 or ""), as the alternative would be to have extraneous data take up space and be left with a None object.
* The variable date in Signal represents a Unix timestamp plus 3 additional digits for milliseconds. To convert unix time to local time, drop the last 3 digits and run it through `date -d @YOUR_TIMESTAMP`
* Your user ID (the phone number) is never recorded in chat backups, unless you specifically made a contact for yourself and chatted to yourself, pushbullet style. Instead, messages that came from you are implied.
* Attachment filenames are `part.unique_id` + "_" + `part.part_id`. Unique ID appears to be equivalent to a Unix timestamp + milliseconds.
* `sms.date_sent` in the table `sms` was used to represent the true date that the message was sent, and so it is indexed by this in JSON.
* `mms.date` in the table `mms` was used in lieu of `mms.date_received` to represent the true date that the message was sent.
    * This matters since Signal messages sometimes take a while to be recieved by the recipient, perhaps due to a device being offline or other lag issues. The date we chose is also what Signal shows to the user as the true date, and `date_received` is used as the primary reference of mms.quote_id.

## Issues

* Not all information from the sqlite database was deemed to be worthy of archival (such as read receipts, etc). And other new items may possibly be overlooked. Please make a pull request to add them in and justify their addition.
* Stickers are not yet supported, though signal-backup-decode does dump them.
* Reactions are not yet supported, they rely on some sort of blob.
* Avatars are not yet supported.
* Quotes use the message `mms.date` (when message was sent) as the `mms.quote_id`, which differs from `mms.date_received` as that is merely the date your device received it.
    * It is likely that this is to keep compatibility with messages quoted from the `sms` table, but it is unknown whether `sms.date_sent` (which we use as the timestamp in our log formats) is used as it should be the equivalent of `mms.date`, rather than `sms.date` which is the date it was recorded to be received.
    * Therefore, someone will need to experiment and raise an issue if they cannot find a quoted message originating from the table `sms`, so it could possibly be rectified.
* The `mms` table defines a `quote_attachment` field indicating that the quoted message has an associated attachment with it. As the sample dump used had no examples of such a message and it is of low priority, it is up to someone else to implement it.
    * If you do want to implement this, follow the format and set it as a nested attachment "a" in the "q" object, with the variable "url".
* `mms.shared_contacts` indicates a contact vcf file being shared, but it is unknown how we should handle it.
* It is unclear what the purpose of "part.digest" is, which is a byte blob. It appears only in files sent by your own user. Maybe it represents a hash of some kind?
* We do not have any messages where `part.caption` is not null in the entire history of our use of Signal, as its purpose seems to be overtaken by `mms.body`. If someone has another opinion just tell us.
* The meaning of `mms.m_type` is uncertain. We thought it indicated text with `128` and media attachments with `132`, but this is not really the case so we watch for fname instead. It would be great if we could figure out what it means consistently.

### Viewer Modifications

* Detect whether the json is from a Signal dump
* (DONE) Run a python simplehttpserver to make the attachments available at localhost:8000/uniqueid_partid
* Detect the correct mimetype of the file and serve it to the browser. Probably need to use python_magic: https://github.com/sjkingo/python-parrot/blob/master/parrot/parrot.py
  * Alternatively, propose a mod to signal rust dump to autodetect and place file extensions

## SQL Schema Changes

### Breaking Changes to `signal2json-2.py`

As a result of some key SQL Schema changes, a second version of the signal2json script had to be made (the old one is retained for recovery of previous dumps).

Around the time when Avatars and Stickers were introduced, perhaps in the aim of supporting a future email username, a new `recipient._id` field was created to replace the phone number and move it to `recipient.phone` instead. 

`thread.recipient_ids` and `sms.address` therefore stores this new `recipient._id` instead of what is now `recipient.phone`.

```
recipient._id = # New primary key replacing phone, which is demoted
thread.recipient_ids = recipient._id
recipient_preferences.recipient_ids = recipient.phone
```

New columns with significant values are as follows. Apparently they represent the first detected Signal profile name? Also there's a new UUID field, but not all users have a UUID?

```
recipient.uuid
recipient.profile_joined_name
recipient.profile_family_name
sms.reactions
sms.reactions_unread
sms.reactions_last_seen
mms.previews
mms.reveal_duration
mms.reveal_start_time
mms.reactions
mms.reactions_unread
mms.reactions_last_seen
```

For the thread feature for viewing snippet images, three fields were added:

```
thread.snippet_uri
thread.snippet_content_type
thread.snippet_extras
```

Additional minor renames were as follows:

```
recipient_preferences.expire_messages = recipient.message_expiration_time
recipient_preferences.system_contact_photo = recipient.system_photo_uri
```

Unused columns (at least in my experience) apparently include the following:

```
recipient.username
recipient.email
```

### Migrations Necessary

* [x] OWNER_RECIPIENT_ID - store into this variable
* [ ] PHONE_NUMBER conversion to recipient_id
* [ ] Have a map of recipient ID to phone number, for use in filenames and lookups (used near the last parts of the script)

## Forerunners

### SignalTextBackupViewer

Unfortunately this doesn't support anything except the old .xml format used by Silence, which is no longer used.

https://github.com/baumschubser/SignalTextBackupViewer

### View-signal-backup

Someone had made this "CLI and UI to view contents of decrypted Signal backup files", but it seems overly complicated in terms of go and javascript. I simply outsource the hard part of decryption to signal-backup-decode


https://github.com/nthurow/view-signal-backup
