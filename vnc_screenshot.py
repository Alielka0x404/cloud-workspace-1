#!/usr/bin/env python3

import os
import sys
import time
import argparse
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from vncdotool import api
from datetime import datetime

SCREENSHOT_DIR = "screenshots"
VNC_FILE = "vnc.txt"
DEFAULT_WORKERS = 10

print_lock = threading.Lock()

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

def safe_print(*args, **kwargs):
    with print_lock:
        print(*args, **kwargs)

def connect_and_screenshot(server_info, index=None, total=None):
    ip = server_info["ip"]
    port = server_info["port"]
    password = server_info["password"]
    hostname = server_info["hostname"]

    prefix = f"[{index}/{total}]" if index and total else ""

    try:
        connection_string = f"{ip}::{port}"

        safe_print(f"{prefix} Connecting to {ip}:{port}...")

        client = api.connect(connection_string, password=password)

        time.sleep(2)

        client.keyPress("space")

        time.sleep(1)

        pass_str = password if password else "null"
        filename = f"{ip}_{port}-{pass_str}.png"
        filepath = os.path.join(SCREENSHOT_DIR, filename)

        client.captureScreen(filepath)

        client.disconnect()

        safe_print(f"{prefix} SUCCESS: {ip}:{port} -> {filename}")

        return (True, server_info, None)

    except Exception as e:
        safe_print(f"{prefix} FAILED: {ip}:{port} - {str(e)}")
        return (False, server_info, str(e))

def main():
    parser = argparse.ArgumentParser(description='VNC Screenshot Tool with Parallel Processing')
    parser.add_argument('-w', '--workers', type=int, default=DEFAULT_WORKERS,
                        help=f'Number of parallel workers (default: {DEFAULT_WORKERS})')
    parser.add_argument('-f', '--file', type=str, default=VNC_FILE,
                        help=f'VNC server list file (default: {VNC_FILE})')
    parser.add_argument('--no-parallel', action='store_true',
                        help='Disable parallel processing (sequential mode)')
    args = parser.parse_args()

    print("VNC Screenshot Tool - Parallel Mode")
    print("=" * 60)

    vnc_file = args.file

    if not os.path.exists(vnc_file):
        print(f"Error: {vnc_file} not found!")
        print(f"Create a {vnc_file} file with format:")
        print("ip:port-password-hostname")
        print("Example: 192.168.1.100:5900-mypass-server1")
        print("Use 'null' for no password: 192.168.1.100:5900-null-server2")
        sys.exit(1)

    create_screenshot_dir()

    with open(vnc_file, "r") as f:
        lines = f.readlines()

    servers = []
    for line in lines:
        server_info = parse_vnc_line(line)
        if server_info:
            servers.append(server_info)

    if not servers:
        print("No valid servers found in vnc.txt")
        sys.exit(1)

    total_servers = len(servers)
    workers = 1 if args.no_parallel else args.workers

    print(f"Total servers: {total_servers}")
    print(f"Parallel workers: {workers}")
    print(f"Screenshot directory: {SCREENSHOT_DIR}/")
    print("=" * 60)
    print()

    start_time = time.time()

    successful = 0
    failed = 0
    failed_servers = []

    if args.no_parallel:
        for i, server in enumerate(servers, 1):
            result = connect_and_screenshot(server, i, total_servers)
            if result[0]:
                successful += 1
            else:
                failed += 1
                failed_servers.append((server, result[2]))
    else:
        with ThreadPoolExecutor(max_workers=workers) as executor:
            future_to_server = {
                executor.submit(connect_and_screenshot, server, i, total_servers): (server, i)
                for i, server in enumerate(servers, 1)
            }

            for future in as_completed(future_to_server):
                server, index = future_to_server[future]
                try:
                    result = future.result()
                    if result[0]:
                        successful += 1
                    else:
                        failed += 1
                        failed_servers.append((result[1], result[2]))
                except Exception as exc:
                    failed += 1
                    safe_print(f"[{index}/{total_servers}] ERROR: {server['ip']}:{server['port']} - {exc}")
                    failed_servers.append((server, str(exc)))

    elapsed_time = time.time() - start_time

    print()
    print("=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print(f"Total servers: {total_servers}")
    print(f"Successful: {successful}")
    print(f"Failed: {failed}")
    print(f"Time elapsed: {elapsed_time:.2f} seconds")
    print(f"Average time per server: {elapsed_time/total_servers:.2f} seconds")
    print(f"Screenshots saved in: {SCREENSHOT_DIR}/")

    if failed_servers:
        print()
        print("FAILED SERVERS:")
        for server, error in failed_servers:
            print(f"  - {server['ip']}:{server['port']} - {error}")

    print("=" * 60)

if __name__ == "__main__":
    main()
