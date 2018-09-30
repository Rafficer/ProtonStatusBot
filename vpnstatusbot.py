import praw
import re

reddit = praw.Reddit(client_id='iLgrLcssI69Y6g',
                     client_secret='RmkVJrA97Os4XJ2XrLHBKq0Rye8',
                     password='BeP339ZJxEZYQ4PL',
                     user_agent='ProtonStatusBot by /u/Rafficer',
                     username='ProtonStatusBot')


vpnstatus1_regex = re.compile(r'vpn ((\w\w)(-|#| |)(\d{1,3}))', re.IGNORECASE)

for message in reddit.inbox.stream(skip_existing=True):
    print(message.body)
    if message.body.lower() == "/u/ProtonBlogger test".lower():
        message.reply("hey")