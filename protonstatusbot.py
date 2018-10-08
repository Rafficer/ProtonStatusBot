import praw, prawcore
import re
import requests
import os
import time
import logging
import json
import subprocess
import random
from reddit_authentication import client_id, client_secret, password, username

if os.geteuid() != 0:
    exit("Please run as root!")

logging.basicConfig(level=logging.CRITICAL, format=' %(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

# Reddit authentication
reddit = praw.Reddit(client_id=client_id,
                     client_secret=client_secret,
                     password=password,
                     user_agent='ProtonStatusBot by /u/Rafficer',
                     username=username)

# Check if the network namespace "vpnsb" exists, if not, create it.
if not os.path.isfile("/var/run/netns/vpnsb"):
    logger.debug("Creating network namespace...")
    os.system("setup/create_namespace.sh")
else:
    logger.debug("Network namespace exists")

# Regular Expressions to check if the message contains a servername
re_vpncheck_short = re.compile(r'!vpn ((\w\w)(-|#| ?)(\d{1,3}))( tcp| udp)?', re.IGNORECASE)  # For uk-03 format (UK = Group 2, 03 = Group 4, tcp/udp = Group 5)
re_vpncheck_long = re.compile(r'!vpn (((\w\w)(-|#| ?)(\w\w))(-|#| ?)(\d{1,3}))( tcp| udp)?', re.IGNORECASE)  # For is-de-01 format (is = group 3,de = Group5, 01 = Group 7, tcp/udp = Group 8)
re_vpncheck_random = re.compile(r'!vpn random', re.IGNORECASE)


def main():
    is_vpn_running(True)
    logger.debug("Message Loop started")
    for message in reddit.inbox.stream(skip_existing=True):
        logger.debug('New Message')
        if message.was_comment:
            logger.debug("Message Link: https://reddit.com{}".format(message.context))
        logger.debug("Message Author: " + str(message.author))
        logger.debug('Message Body:')
        logger.debug(message.body)
        try:
            res = handle_message(message)
        except requests.exceptions.ConnectionError as err:
            logger.critical("First requests.exceptions.ConnectionError")
            logger.critical(err)
            connectivity_check()
            try:
                logger.debug("Trying to handle the message again.")
                res = handle_message(message)
            except requests.exceptions.ConnectionError as err:
                logger.critical("Second requests.exceptions.ConnectionError")
                logger.critical(err)
                continue


        if res == None:
            logger.debug("Message not useful")
        else:
            append_message_footer(message, res)

        logger.debug("Message completed!")
        logger.debug("#################")


def handle_message(message):
    """Handles every message and creates the reply"""
    if re_vpncheck_short.search(message.body) or re_vpncheck_long.search(message.body):
        """Checks for VPN Connectivity"""
        servername = None
        protocol = None

        if re_vpncheck_short.search(message.body):
            servername = (re_vpncheck_short.search(message.body).group(2) + "#" + re_vpncheck_short.search(
                message.body).group(4).lstrip("0")).upper()
            if re_vpncheck_short.search(message.body).group(5) != None:
                protocol = re_vpncheck_short.search(message.body).group(5).strip().lower()
            else:
                protocol = "udp"
        elif re_vpncheck_long.search(message.body):
            servername = (re_vpncheck_long.search(message.body).group(3) + "-" + re_vpncheck_long.search(
                message.body).group(5) + "#" + re_vpncheck_long.search(message.body).group(7).lstrip("0")).upper()
            if re_vpncheck_long.search(message.body).group(8) != None:
                protocol = re_vpncheck_long.search(message.body).group(8).strip().lower()
            else:
                protocol = "udp"
        ServerID = get_vpnserver_id(servername)

        if ServerID != None:
            res = test_vpn(servername, ServerID, protocol)
            return res
        else:
            if servername != None:
                logger.debug("Server {} not found".format(servername))
                return "Server {} not found".format(servername)
            else:
                return

    if re_vpncheck_random.search(message.body):
        return test_vpn("FillerServername", "FillerServerID", rand=True)


def test_vpn(servername, ServerID, protocol="udp", rand=False):
    logger.debug("VPN Test requested")
    if is_vpn_running():
        is_vpn_running(True)

    if rand == True:
        serverlist = requests.get("https://api.protonmail.ch/vpn/logicals").json()
        servercount = len(serverlist["LogicalServers"]) - 1
        random_number = random.randint(0, servercount)
        servername = serverlist["LogicalServers"][random_number]["Name"]
        ServerID = get_vpnserver_id(servername)
        protocol = random.choice(["udp", "tcp"])
    logger.debug("Servername: {}".format(servername))
    logger.debug("Starting connection")
    download_ovpn_file(ServerID, protocol)
    try:
        oldip = json.loads(subprocess.check_output('ip netns exec vpnsb wget -T 20 -qO- "https://api.protonmail.ch/vpn/location"',stderr=subprocess.STDOUT, shell=True))['IP']
    except subprocess.CalledProcessError as err:
        logger.critical("Getting oldIP failed")
        logger.critical(err)
        oldip = "OldIPFail"
    if connect_vpn():
        inet, dns, ip = error_checks(oldip)
        if inet:
            inetworking = "✔"
        else:
            inetworking = "❌"
        if dns:
            dnsworking = "✔"
        else:
            dnsworking = "❌"
        if ip:
            is_vpn_running(True)
            return "**Tested Server:** {} via {}\n\n**Connection successful.** \n\n**DNS Test:** {}\n\n**Internet Test:** {}".format(servername, protocol.upper(), dnsworking, inetworking)
        else:
            is_vpn_running(True)
            return "The connection to {} seemed to be successful, however the IP didn't change. Something went wrong".format(servername)
    else:
        is_vpn_running(True)
        return "Connection to {} via {} failed".format(servername, protocol.upper() )
    is_vpn_running(True)


def get_vpnserver_id(servername):
    serverlist = requests.get("https://api.protonmail.ch/vpn/logicals").json()
    for server in serverlist["LogicalServers"]:
        if servername == server["Name"]:
            return server["ID"]


def download_ovpn_file(ServerID, protocol):
    res = requests.get(
        "https://api.protonmail.ch/vpn/config?Platform=Linux&LogicalID={}&Protocol={}".format(ServerID, protocol))
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


def connect_vpn():
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


def error_checks(oldip):
    if os.system("ip netns exec vpnsb ping -c 1 1.0.0.1 > /dev/null") == 0:
        inetcheck = True
    else:
        inetcheck = False

    if os.system("ip netns exec vpnsb nslookup protonvpn.com 10.8.8.1 > /dev/null") == 0:
        dnscheck = True
    else:
        dnscheck = False
    try:
        newip = json.loads(subprocess.check_output('ip netns exec vpnsb wget -T 20 -qO- "https://api.protonmail.ch/vpn/location"',
                                               stderr=subprocess.STDOUT, shell=True))['IP']
    except subprocess.CalledProcessError as err:
        logger.critical("Getting NewIP failed")
        logger.critical(err)
        newip = "NewIPFail"
    if newip == oldip:
        ipcheck = False
    else:
        ipcheck = True

    logger.debug(
        "INET: " + str(inetcheck) + " DNS: " + str(dnscheck) + " Current IP: " + newip + " Previous IP: " + oldip)
    return inetcheck, dnscheck, ipcheck


def append_message_footer(msg, messagebody):
    """Adds Footer to any message an replies"""
    footer = "\n\n_____________________\n\n^^I ^^am ^^a ^^Bot. ^^| [^^How ^^to ^^use](https://github.com/Rafficer/ProtonStatusBot/tree/master#how-to-use) ^^| ^^Made ^^with ^^🖤 ^^by ^^/u/Rafficer"
    full_message = messagebody + footer
    logger.debug("Replying...")
    try:
        msg.reply(full_message)
    except prawcore.exceptions.RequestException:
        logger.debug("Replying failed. Checking for connectivity and trying again.")
        connectivity_check()
        msg.reply(full_message)
    logger.debug("Replied!")


def is_network_down():
    try:
        requests.get("https://wikipedia.org")
        return False
    except requests.exceptions.ConnectionError:
        return True


def connectivity_check():
    internet_down = True
    logger.debug("Connectivity Check requested")
    logged_already = False
    while internet_down:
        if is_network_down():
            if logged_already == False:
                logger.debug("Connection is down. Waiting for it to come back up")
                logged_already = True
            time.sleep(3)
        else:
            internet_down = False
    logger.debug("Connection is up")


while True:
    try:
        main()
    except prawcore.exceptions.RequestException as err:
        logger.critical("prawcore.exceptions.RequestException:")
        logger.critical(err)
        logger.debug("Network seems to be down.")
        connectivity_check()
    except KeyboardInterrupt:
        logger.debug("KeyboardInterrupt detected, Program will shut down")
        exit()

    except Exception as err:
        #logger.critical(err.__name__)
        logger.critical(err)
        logger.critical("Program will shut down.")
        exit("Failure.")
