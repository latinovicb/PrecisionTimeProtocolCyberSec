# SSH connection for setup
ssh_conns = {
    "master": ["192.168.88.101"],
    "slave": ["192.168.88.102"],
}

# Interfaces used for setup & measurment
ptp_sec_cons = {
    "eth1": "192.0.2.",
    "wg0": "198.51.100.",
    "macsec0": "203.0.113.",
}

# commands will be selected iterativelly, first cmd ise
# extra logging info for master so that generators wouldn't bug -- maybe fix generators later
ptp_sec_cmds = {
    "no_enc_multicast": {
        "master": "ptp4l -m -i eth1 -l 7",
        "slave": "ptp4l -m -i eth1 -s",
    },
    "no_enc_unicast": {
        "master": "ptp4l -m -i eth1 -l 7 -f settings.cfg",
        "slave": "ptp4l -m -i eth1 -f settings.cfg -s",
    },
}
