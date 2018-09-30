#!/usr/bin/env bash

set  -x

if [[ $EUID != 0 ]]; then
  echo "[!] Error: The program requires root access."
  exit 1
fi


NS="vpnsb"
INTRFCE=$(ip addr show | awk '/inet.*brd/{print $NF; exit}')
VETH="veth1"
VPEER="vpeer1"
VETH_ADDR="10.200.1.1"
VPEER_ADDR="10.200.1.2"

mkdir -p /etc/netns/$NS

echo "nameserver 1.1.1.1" > /etc/netns/$NS/resolv.conf
echo "nameserver 1.0.0.1" >> /etc/netns/$NS/resolv.conf

ip netns add $NS

ip link add ${VETH} type veth peer name ${VPEER}

ip link set ${VPEER} netns $NS

ip addr add ${VETH_ADDR}/24 dev ${VETH}

ip link set ${VETH} up

ip netns exec $NS ip addr add ${VPEER_ADDR}/24 dev ${VPEER}
ip netns exec $NS ip link set ${VPEER} up
ip netns exec $NS ip link set lo up
ip netns exec $NS ip route add default via ${VETH_ADDR}

echo "1" > /proc/sys/net/ipv4/ip_forward

iptables -P FORWARD DROP
iptables -F FORWARD

iptables -t nat -F

iptables -t nat -A POSTROUTING -s ${VPEER_ADDR}/24 -o "$INTRFCE" -j MASQUERADE

iptables -A FORWARD -i "$INTRFCE" -o ${VETH} -j ACCEPT
iptables -A FORWARD -o "$INTRFCE" -i ${VETH} -j ACCEPT