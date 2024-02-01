#!/bin/bash

ADDR="$1"

# yes | ssh-keygen -f "~/.ssh/known_hosts" -R "$ADDR"

last_digit="${ADDR: -1}"
echo "Last char: $last_digit"

ssh root@$ADDR "ip a a 192.0.2.$last_digit/24 dev eth1" # eth1 will be used for testing

# ADD NTP CHRONYC CONFIGURATION!!!
