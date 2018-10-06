import praw
import re
import requests
import os
import time
import logging
import json
import subprocess

if os.geteuid() != 0:
    exit("Please run as root!")

logging.basicConfig(level=logging.CRITICAL, format=' %(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

#Reddit authentication
reddit = praw.Reddit(client_id='iLgrLcssI69Y6g',
                     client_secret='RmkVJrA97Os4XJ2XrLHBKq0Rye8',
                     password='BeP339ZJxEZYQ4PL',
                     user_agent='ProtonStatusBot by /u/Rafficer',
                     username='ProtonStatusBot')

# Check if the network namespace "vpnsb" exists, if not, create it.
if not os.path.isfile("/var/run/netns/vpnsb"):
    logger.debug("Creating network namespace...")
    os.system("setup/create_namespace.sh")
else:
    logger.debug("Network namespace exists")

#Regular Expressions to check if the message contains a servername
re_vpncheck_short = re.compile(r'vpn ((\w\w)(-|#| ?)(\d{1,3}))( tcp| udp)?', re.IGNORECASE) # For uk-03 format (UK = Group 2, 03 = Group 4, tcp/udp = Group 5)
re_vpncheck_long = re.compile(r'vpn (((\w\w)(-|#| ?)(\w\w))(-|#| ?)(\d{1,3}))( tcp| udp)?', re.IGNORECASE) # For is-de-01 format (is = group 3,de = Group5, 01 = Group 7, tcp/udp = Group 8)


def main():
    is_vpn_running(True)
    logger.debug("Message Loop started")
    for message in reddit.inbox.stream(skip_existing=True):
        if is_vpn_running():
            is_vpn_running(True)
        logger.debug("")
        logger.debug('New Message')
        logger.debug("Message Author: " + str(message.author))
        logger.debug('Message Body:')
        logger.debug(message.body)
        logger.debug("---------------")
        servername = None
        protocol = None
        if re_vpncheck_short.search(message.body):
            servername = (re_vpncheck_short.search(message.body).group(2) + "#" + re_vpncheck_short.search(message.body).group(4).lstrip("0")).upper()
            if re_vpncheck_short.search(message.body).group(5) != None:
                protocol = re_vpncheck_short.search(message.body).group(5).strip().lower()
            else:
                protocol = "udp"
        elif re_vpncheck_long.search(message.body):
            servername = (re_vpncheck_long.search(message.body).group(3) + "-" + re_vpncheck_long.search(message.body).group(5) + "#" + re_vpncheck_long.search(message.body).group(7).lstrip("0")).upper()
            if re_vpncheck_long.search(message.body).group(8) != None:
                protocol = re_vpncheck_long.search(message.body).group(8).strip().lower()
            else:
                protocol = "udp"
        logger.debug(servername)
        ServerID = getVPNID(servername)
        if ServerID != None:
            logger.debug("Starting connection")
            download_ovpn_file(ServerID, protocol)
            oldip = json.loads(subprocess.check_output('ip netns exec vpnsb wget -qO- "https://api.protonmail.ch/vpn/location"', stderr=subprocess.STDOUT, shell=True))['IP']
            if connectvpn():
                inet, dns, ip = errorchecks(oldip)
                logger.debug("Replying...")
                if inet:
                    inetworking = "✔"
                else:
                    inetworking = "❌"
                if dns:
                    dnsworking = "✔"
                else:
                    dnsworking = "❌"
                if ip:
                    AppendMessageFooter(message, ("**Tested Server:** " + servername + " via " + protocol.upper() + "\n\n**Connection successful.** \n\n**DNS Test:** " + dnsworking + "\n\n**Internet Test:** " + inetworking))
                else:
                    AppendMessageFooter(message, "The connection seemed to be successful, however the IP didn't change. Something went wrong")
            else:
                AppendMessageFooter(message, ("Connection to " + servername + " via " + protocol.upper() + " failed"))
            is_vpn_running(True)
        else:
            if servername != None:
                AppendMessageFooter(message, ("Server " + servername + " not found."))
                logger.debug("Server not found")
            else:
                logger.debug('Message not useful')
            continue
        
def getVPNID(servername):
    serverlist = requests.get("https://api.protonmail.ch/vpn/logicals").json()
    for server in serverlist["LogicalServers"]:
        if servername == server["Name"]:
            return server["ID"]

def download_ovpn_file(ServerID, protocol):
    res = requests.get("https://api.protonmail.ch/vpn/config?Platform=Linux&LogicalID={}&Protocol={}".format(ServerID, protocol))
    with open("config.ovpn", "wb") as f:
        for chunk in res.iter_content(10000):
            f.write(chunk)
    logger.debug("OpenVPN Config File downloaded")

def is_vpn_running(disconnect=False):
    if os.system('pgrep openvpn > /dev/null') == 0:
        if disconnect:
            os.system('kill $(pgrep openvpn)')
            time.sleep(8)
            if is_vpn_running():
                os.system('kill -9 $(pgrep openvpn)')
            else:
                logger.debug("Disconnected after 1st try")
                return False
            time.sleep(5)
            if is_vpn_running():
                logger.debug("Disconnected after 2nd try")
                return True
            else:
                logger.debug("Disconnecting failed")
                return False
        return True
    else:
        return False

def connectvpn():
    if os.path.isfile("ovpn.log"):
        os.unlink("ovpn.log")

    os.system('ip netns exec vpnsb ./connectvpn.sh')

    max_tries = 30
    counter = 0
    while counter < max_tries:
        time.sleep(1)
        if os.path.isfile("ovpn.log"):
            with open("ovpn.log") as f:
                if "Initialization Sequence Completed" in f.read():
                    logger.debug("Initialization Sequence Completed")
                    return True
        counter += 1
        if counter >= max_tries:
            logger.debug("Initialization Sequence not completed after {} tries".format(max_tries))
            return

def errorchecks(oldip):
    if os.system("ip netns exec vpnsb ping -c 1 1.1.1.1 > /dev/null") == 0:
        inetcheck = True
    else:
        inetcheck = False

    if os.system("ip netns exec vpnsb nslookup protonvpn.com 10.8.8.1 > /dev/null") == 0:
        dnscheck = True
    else:
        dnscheck = False

    newip = json.loads(subprocess.check_output('ip netns exec vpnsb wget -qO- "https://api.protonmail.ch/vpn/location"', stderr=subprocess.STDOUT, shell=True))['IP']
    if newip == oldip:
        ipcheck = False
    else:
        ipcheck = True

    logger.debug("INET: " + str(inetcheck) + " DNS: " + str(dnscheck) + " Current IP: " + newip + " Previous IP: " + oldip)
    return inetcheck, dnscheck, ipcheck

"""Adds Footer to any message an replies"""
def AppendMessageFooter(msg, messagebody):
    footer = "\n\n_____________________\n\n^^I ^^am ^^a ^^Bot. ^^| [^^How ^^to ^^use](https://example.com) ^^| ^^Made ^^with ^^🖤 ^^by ^^/u/Rafficer"
    full_message = messagebody + footer
    msg.reply(full_message)
    logger.debug("Replied!")
main()