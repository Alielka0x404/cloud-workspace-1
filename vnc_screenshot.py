#!/usr/bin/env python3

import os
import sys
import time
from vncdotool import api
from datetime import datetime

SCREENSHOT_DIR = "screenshots"
VNC_FILE = "vnc.txt"

def create_screenshot_dir():
    if not os.path.exists(SCREENSHOT_DIR):
        os.makedirs(SCREENSHOT_DIR)
        print(f"Created directory: {SCREENSHOT_DIR}")

def parse_vnc_line(line):
    line = line.strip()
    if not line or line.startswith("#"):
        return None

    parts = line.split("-")
    if len(parts) < 2:
        print(f"Invalid format: {line}")
        return None

    ip_port = parts[0].strip()
    password = parts[1].strip() if parts[1].strip().lower() != "null" else None
    hostname = parts[2].strip() if len(parts) > 2 else ""

    if ":" not in ip_port:
        print(f"Invalid IP:PORT format: {ip_port}")
        return None

    ip, port = ip_port.split(":", 1)

    return {
        "ip": ip,
        "port": port,
        "password": password,
        "hostname": hostname
    }

def connect_and_screenshot(server_info):
    ip = server_info["ip"]
    port = server_info["port"]
    password = server_info["password"]
    hostname = server_info["hostname"]

    print(f"\n{'='*60}")
    print(f"Connecting to: {ip}:{port}")
    if hostname:
        print(f"Hostname: {hostname}")
    print(f"{'='*60}")

    try:
        connection_string = f"{ip}::{port}"

        client = api.connect(connection_string, password=password)

        print("Connected successfully!")
        print("Waiting 2 seconds for connection to stabilize...")
        time.sleep(2)

        print("Sending key press to wake screen...")
        client.keyPress("space")

        print("Waiting 1 second for screen to update...")
        time.sleep(1)

        pass_str = password if password else "null"
        filename = f"{ip}_{port}-{pass_str}.png"
        filepath = os.path.join(SCREENSHOT_DIR, filename)

        print(f"Taking screenshot...")
        client.captureScreen(filepath)

        print(f"Screenshot saved: {filepath}")

        client.disconnect()
        print("Disconnected")

        return True

    except Exception as e:
        print(f"Error: {str(e)}")
        return False

def main():
    print("VNC Screenshot Tool")
    print("=" * 60)

    if not os.path.exists(VNC_FILE):
        print(f"Error: {VNC_FILE} not found!")
        print(f"Create a {VNC_FILE} file with format:")
        print("ip:port-password-hostname")
        print("Example: 192.168.1.100:5900-mypass-server1")
        print("Use 'null' for no password: 192.168.1.100:5900-null-server2")
        sys.exit(1)

    create_screenshot_dir()

    with open(VNC_FILE, "r") as f:
        lines = f.readlines()

    servers = []
    for line in lines:
        server_info = parse_vnc_line(line)
        if server_info:
            servers.append(server_info)

    if not servers:
        print("No valid servers found in vnc.txt")
        sys.exit(1)

    print(f"\nFound {len(servers)} server(s) to process\n")

    successful = 0
    failed = 0

    for i, server in enumerate(servers, 1):
        print(f"\nProcessing server {i}/{len(servers)}")
        if connect_and_screenshot(server):
            successful += 1
        else:
            failed += 1

        if i < len(servers):
            print("\nWaiting 2 seconds before next server...")
            time.sleep(2)

    print(f"\n{'='*60}")
    print("Summary")
    print(f"{'='*60}")
    print(f"Total servers: {len(servers)}")
    print(f"Successful: {successful}")
    print(f"Failed: {failed}")
    print(f"Screenshots saved in: {SCREENSHOT_DIR}/")
    print(f"{'='*60}")

if __name__ == "__main__":
    main()
