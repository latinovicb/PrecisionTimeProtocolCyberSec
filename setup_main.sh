#!/bin/bash
#
# change list to suit your needs
ADDR_LIST=(
"192.168.88.102"
"192.168.88.101"
)

# possibly two for loops
for ADDR in "${ADDR_LIST[@]}"; do
  ssh root@$ADDR "mount -o rw,remount /"
 ./setup_networking.sh $ADDR
 ./setup_build_packages.py $ADDR
 ./setup_wg_keys.sh $ADDR

done
