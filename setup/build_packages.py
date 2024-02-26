import os
import sys
import subprocess


# Define a dictionary with package names names and corresponding commands
my_dict = {
    "wireguard-go": [
        "GOOS=linux GOARCH=arm CGO_ENABLED=0 go build -v -o wireguard-go",
        "git@github.com:WireGuard/wireguard-go.git",
    ]
}

dst = "~"


def do(ssh, scp):

    ADDR = ssh.get_transport().getpeername()[0]
    for package in my_dict:

        name = package
        build_cmd = my_dict[name][0]
        git_dir = my_dict[name][1]
        if check_remote_file(ADDR, name):

            if os.path.isdir(name):
                print(f"{name} directory exists.")
            else:
                print(f"{name} directory does not exist")
                subprocess.run(
                    f"git clone {git_dir}", shell=True, executable="/bin/bash"
                )

            binary_path = os.path.join(name, name)
            if os.path.exists(binary_path) and os.access(binary_path, os.X_OK):
                print(f"{name} binary exists")

            else:
                print(f"{name} binary does not exist. Compiling with {build_cmd}")
                subprocess.run(
                    f"cd {name} && {build_cmd}", shell=True, executable="/bin/bash"
                )

            scp.put(binary_path, dst)

        else:
            print(f"{ADDR} device already has {name} in {dst}")


def check_remote_file(host, file):
    status = subprocess.call(["ssh", f"root@{host}", f"test -f {dst}/{file}"])
    return status
