#!/bin/bash

ADDR="$1"

generate_keys() {
    local ADDR="$1"
    ssh root@$ADDR "wg genkey > ~/private_key"
    ssh root@$ADDR "wg pubkey < ~/private_key > ~/public_key"
}

if ssh root@$ADDR "ip link show wg0" &> /dev/null; then
  echo "Interface already on -- keys active ?"
else
  generate_keys "$ADDR"
fi


