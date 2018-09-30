import praw
import re
import requests
import subprocess

#Reddit authentication
reddit = praw.Reddit(client_id='iLgrLcssI69Y6g',
                     client_secret='RmkVJrA97Os4XJ2XrLHBKq0Rye8',
                     password='BeP339ZJxEZYQ4PL',
                     user_agent='ProtonStatusBot by /u/Rafficer',
                     username='ProtonStatusBot')

#Regular Expressions to check if the message contains a servername
vpnstatus_regex1 = re.compile(r'vpn ((\w\w)(-|#| )(\d{1,3}))', re.IGNORECASE) # For uk-03 format (UK = Group 2, 03 = Group 4)
vpnstatus_regex2 = re.compile(r'vpn (((\w\w)(-|#| )\w\w)(-|#| )(\d{1,3}))', re.IGNORECASE) # For is-de-01 format (is-de = Group2, 01 = Group 6)


def main():
    for message in reddit.inbox.stream(skip_existing=True):
        print(message.body)
        print("---------------")
        servername = None
        if vpnstatus_regex1.match(message.body):
            servername = (vpnstatus_regex1.match(message.body).group(2) + "#" + vpnstatus_regex1.match(message.body).group(4)).upper()
        elif vpnstatus_regex2.match(message.body):
            servername = (vpnstatus_regex2.match(message.body).group(2) + "#" + vpnstatus_regex2.match(message.body).group(6)).upper()

        ServerID = getVPNID(servername)
        if ServerID != None:
            pass
            #TODO connect to VPN etc
        else:
            continue
        


#TODO Search for the ID in for the server name

def getVPNID(servername):
    serverlist = requests.get("https://api.protonmail.ch/vpn/logicals").json()
    for server in serverlist["LogicalServers"]:
        if servername == server["Name"]:
            return server["ID"]

#TODO pass to connect script