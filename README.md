# ProtonStatusBot

A Reddit Status Bot for ProtonVPN and ProtonMail

## How to use

The Bot reacts to private messages, either directly via Reddit PM or by mentioning it in comments with /u/ProtonStatusBot.

### Checking a VPN Server

Checking a VPN Server requires the command **!vpn** followed by the Server name or `random` for a random server. Tor Servers are not supported.

Adding either TCP or UDP after the Server name will specify the Protocol that's used to connect, defaulting to UDP.

#### Examples:

`/u/ProtonStatusBot !vpn IS-06`

`/u/ProtonStatusBot !vpn US-TX#3`

`/u/ProtonStatusBot !vpn CH-US-1 TCP`

`/u/ProtonStatusBot !vpn random udp`

### Checking ProtonMail Login Status

Checking whether or not the ProtonMail login works can be achieved with the command `!pm login`.

#### Example:

`/u/ProtonStatusBot !pm login`

## Getting Started

These instructions will get you a copy of the project up and running on your local environment for development and testing purposes.

### Prerequisites

Only tested on Ubuntu 18.04.

* Python 3.6.5+
* wget
* ip
* openvpn
* chromium-browser

Python Packages:

* requests
* praw
* selenium

`pip3 install -r requirements.txt`

### Installing

You need your ProtonVPN OpenVPN Username and Password, you can get them on https://account.protonvpn.com

Replace them with `Username` and `Password` in the file `openvpncredentials`

Create a new application on your or a new reddit account by going to https://old.reddit.com/prefs/apps/

Use "personal use script" and give it a name. Then copy the ClientID and the ClientSecret in the respective fields in the `reddit_authentication.py` file. Add the Username of the Account and the Password of the Account as well.

### Running

The program needs to run as root to be allowed to create network namespaces and openvpn sessions.

`sudo python3 protonstatusbot.py`

## Why?

Mainly for me to learn Python. Fairly new to it but always open for improvements.

And because I thought it might be a useful tool. Maybe.

## License

This project is licensed under the MIT License - see the [LICENSE.md](LICENSE.md) file for details