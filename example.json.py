# discord style json chat format
discord_chat = {
	"data": {
		"CHANNEL_ID": {
			"1": {
				"a": [ # attachment file, anything not an embeddable image and must be downloaded instead
					{
						"url": "1521174341954_3107",
						"type": "application",
						"mime": "application/pdf",
						"size": 67297,
						"w": 0,
						"h": 0
					}
				],
				"m": "Hello world",
				"t": 1462239120922,
				"u": 1
			},
			"2": {
				"e": [ # signal rendition of an embeddable image file
					{
						"url": "1543696028484_5566",
						"type": "image",  # discord history viewer checks for the embed type
						"mime": "image/jpeg", # actual mime type used to give the file an extension
						"size": 478169,
						"w": 2080,
						"h": 1560
					}
				]
				"m": "Good day to you as well",
				"t": 1462239123893,
				"u": 0
			},
			"3": {
				"e": [ # external images, not used in signal
					{
						"type": "image",
						"url": "https://i.redd.it/hur4wm20qp521.gif"
					}
				],
				"m": "What a dumpster fire of a year",
				"t": 1462239129832,
				"u": 1
			}
			"4": {
				"e": [ # external article urls, not used in signal
					{
						"type": "article",
						"url": "https://www.reddit.com/r/technology/comments/6z2cnd/lawsuit_filed_in_atlanta_us_district_court_faults/dms9nof/"
					}
				],
				"q": [
					{
						"type": "quote",
						"id": "2",
						"m": "Good day to you as well",
						"u": 0
						"a": [ # quotes can also have nested attachments, but not implemented yet
							{
								"url": "1543696028484_5566",
								"type": "image/jpeg",
								"size": 478169,
								"w": 2080,
								"h": 1560
							}
						]
					}
				],
				"m": "Goodbye world",
				"t": 1462239130000,
				"u": 1
			}
		}
	},
	"meta": {
		"channels": {
			"CHANNEL_ID": { # textsecure group ID or DM phone number
				"name": "CHANNEL_NAME", # group name or username
				"server": 0
			}
		},
		"servers": [ # corresponds to our backup dump name
			{
				"name": "SERVER_NAME",
				"service": "signal", # can be either signal or discord at the moment, unlocks different decoding options
				"type": "DM" # either DM or SERVER much like
			}
		],
		"userindex": [ # list of users
			"USER_0",
			"USER_1"
		],
		"users": {
			"USER_0": { # user 0 should always be you
				"name": "USER_0_NAME"
			},
			"USER_1": { # in a DM, user 1 is the person you are talking to
				"name": "USER_1_NAME"
			} # in groups there can be more than two users
		}
	}
}
