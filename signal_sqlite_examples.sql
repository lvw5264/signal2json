-- get all messages in one single stream (add WHERE thread_id = certain number to get those threads)
-- reply_path_present designates the other person's message as opposed to yours
SELECT _id, thread_id, address, reply_path_present, date, date_sent, body FROM sms ORDER BY date DESC;

-- get all contact info (not all are signal contacts, only those with profile_key)
SELECT _id, recipient_ids, color, expire_messages, system_display_name, system_contact_photo, system_contact_uri , profile_key, signal_profile_name, signal_profile_avatar FROM recipient_preferences  WHERE profile_key IS NOT NULL;

-- get all thread message info, which is primary definition of how 
-- messages are grouped. it's what you see on the first screen
SELECT _id, date, message_count, recipient_ids, snippet, snippet_type, delivery_receipt_count, last_seen FROM thread ORDER BY date DESC;

-- Get all group info, as opposed to identities
SELECT _id, grou_pid, title, members, timestamp, active, avatar, avatar_id, avatar_content_type, avatar_digest FROM groups;

-- get all group message info, named by date.
-- Also includes all non-text data in a single person thread
-- st is whether you sent it (null) or the other person sent it (1)
SELECT _id, thread_id, date, date_received, msg_box, body, address, st, m_type, quote_id, quote_author, quote_body  FROM mms ORDER BY date DESC;

-- get all attachments
-- match to mms table using mid
SELECT _id, unique_id, mid, ct, data_size, aspect_ratio, height, width, quote, voice_note, caption FROM part ORDER BY unique_id DESC;



-- 00. create homepage
-- get all thread message info, which is primary definition of how 
-- messages are grouped. it's what you see on the first screen
SELECT _id, date, message_count, recipient_ids, snippet, snippet_type, delivery_receipt_count, last_seen FROM thread ORDER BY date DESC;

-- 0. get all contact info (not all are signal contacts, only those with profile_key)
SELECT _id, recipient_ids, color, expire_messages, system_display_name, system_contact_photo, system_contact_uri , profile_key, signal_profile_name, signal_profile_avatar FROM recipient_preferences  WHERE profile_key IS NOT NULL;

-- 1. obtain all group messages
-- get group unique info by thread._id FROM groups
SELECT thread._id AS thread_id, groups.group_id, groups.title, groups.members, groups.timestamp, groups.active, groups.avatar, groups.avatar_id, groups.avatar_content_type, groups.avatar_digest , thread.date, thread.message_count, thread.snippet, thread.snippet_type, thread.delivery_receipt_count, thread.last_seen 
FROM groups 
INNER JOIN thread ON thread.recipient_ids  = groups.group_id;

-- using a script on every thread id:

-- get group messages FROM mms where thread_id = <tid>
-- match all addresses (phone numbers) to contact name (use simple join)
-- if address is equal to the group id, that's your own message

-- get all attachments FROM part to add to group messages, null if nonexistent
SELECT mms._id AS mid, mms.thread_id, mms.date, mms.date_received, mms.body, mms.address, recipient_preferences.system_display_name , mms.m_type, part.unique_id, part.ct, part.data_size, part.aspect_ratio, part.width, part.height, part.quote, part.voice_note, part.caption, mms.quote_id, mms.quote_author, mms.quote_body
FROM mms
INNER JOIN recipient_preferences  ON mms.address = recipient_preferences.recipient_ids
LEFT JOIN part ON part.mid = mms._id
WHERE thread_id = 40
ORDER BY date DESC;

-- 2. obtain all user messages
-- for loop: use the contact info that is not groups FROM recipient_preferences to get address to search for recipient_id, then match them to thread id

-- get thread message info FROM thread
SELECT _id, date, message_count, recipient_ids, snippet, snippet_type, delivery_receipt_count, last_seen FROM thread WHERE _id = 1;

-- - match all addresses (phone numbers) to contact name (use simple join)
SELECT _id, thread_id, address, reply_path_present, date, date_sent, body FROM sms WHERE thread_id = 1 ORDER BY date DESC;

-- get group messages FROM mms where thread_id = <tid>
-- get all attachments FROM part to add to group messages
-- st is whether you sent it (null) or the other person sent it (1)
SELECT mms._id AS mid, mms.thread_id, mms.date, mms.date_received, mms_st, mms.body, mms.address, recipient_preferences.system_display_name , mms.m_type, part.unique_id, part.ct, part.data_size, part.aspect_ratio, part.width, part.height, part.quote, part.voice_note, part.caption, mms.quote_id, mms.quote_author, mms.quote_body
FROM mms
INNER JOIN recipient_preferences  ON mms.address = recipient_preferences.recipient_ids
LEFT JOIN part ON part.mid = mms._id
WHERE thread_id = 1
ORDER BY date DESC;

-- join both sms and mms messages with date as primary key into a single json

-- convert json into markdown, then to tufte css html
