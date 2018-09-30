#!/usr/bin/env bash

ovpn_options=(
    --config config.ovpn
    --auth-user-pass openvpncredentials
    --auth-retry nointeract
    --log ovpn.log
)

openvpn --daemon "${ovpn_options[@]}"