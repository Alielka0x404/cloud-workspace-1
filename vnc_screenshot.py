#!/usr/bin/env python3
"""
VNC Screenshot Tool - Process-per-connection version
Each VNC connection runs in a completely isolated subprocess to avoid
Twisted reactor threading issues.
"""

import os
import sys
import time
import argparse
import json
from multiprocessing import Pool
from datetime import datetime

SCREENSHOT_DIR = "screenshots"
VNC_FILE = "vnc.txt"
DEFAULT_WORKERS = 10
CONNECTION_TIMEOUT = 15

def create_screenshot_dir():
    if not os.path.exists(SCREENSHOT_DIR):
        os.makedirs(SCREENSHOT_DIR)

def parse_vnc_line(line):
    line = line.strip()
    if not line or line.startswith("#"):
        return None

    parts = line.split("-")
    if len(parts) < 2:
        return None

    ip_port = parts[0].strip()
    password = parts[1].strip() if parts[1].strip().lower() != "null" else None
    hostname = parts[2].strip() if len(parts) > 2 else ""

    if ":" not in ip_port:
        return None

    ip, port = ip_port.split(":", 1)

    return {
        "ip": ip,
        "port": port,
        "password": password,
        "hostname": hostname
    }

def single_vnc_connection(args):
    """
    This function runs in a SEPARATE PROCESS.
    Each process gets its own Twisted reactor, avoiding all threading issues.
    """
    server_info, index, total, timeout, screenshot_dir = args
    
    ip = server_info["ip"]
    port = server_info["port"]
    password = server_info["password"]
    
    prefix = f"[{index}/{total}]"
    
    # Import inside the function so each process gets fresh imports
    import socket
    
    try:
        from vncdotool import api
    except ImportError:
        return (False, server_info, "vncdotool not installed")
    
    client = None
    old_timeout = socket.getdefaulttimeout()
    
    try:
        connection_string = f"{ip}::{port}"
        pass_str = password if password else "null"
        filename = f"{ip}_{port}-{pass_str}.png"
        filepath = os.path.join(screenshot_dir, filename)
        
        print(f"{prefix} Connecting to {ip}:{port}...", flush=True)
        
        socket.setdefaulttimeout(timeout)
        
        client = api.connect(connection_string, password=password)
        
        time.sleep(2)
        client.keyPress("space")
        time.sleep(1)
        
        client.captureScreen(filepath)
        
        print(f"{prefix} SUCCESS: {ip}:{port} -> {filename}", flush=True)
        return (True, server_info, None)
        
    except socket.timeout:
        print(f"{prefix} FAILED: {ip}:{port} - Timeout ({timeout}s)", flush=True)
        return (False, server_info, f"Timeout ({timeout}s)")
    except Exception as e:
        error_msg = str(e)
        if len(error_msg) > 100:
            error_msg = error_msg[:100] + "..."
        print(f"{prefix} FAILED: {ip}:{port} - {error_msg}", flush=True)
        return (False, server_info, error_msg)
    finally:
        if client:
            try:
                client.disconnect()
            except:
                pass
        socket.setdefaulttimeout(old_timeout)

def main():
    parser = argparse.ArgumentParser(description='VNC Screenshot Tool - Process Isolation Version')
    parser.add_argument('-w', '--workers', type=int, default=DEFAULT_WORKERS,
                        help=f'Number of parallel workers (default: {DEFAULT_WORKERS})')
    parser.add_argument('-f', '--file', type=str, default=VNC_FILE,
                        help=f'VNC server list file (default: {VNC_FILE})')
    parser.add_argument('-t', '--timeout', type=int, default=CONNECTION_TIMEOUT,
                        help=f'Connection timeout in seconds (default: {CONNECTION_TIMEOUT})')
    parser.add_argument('--no-parallel', action='store_true',
                        help='Disable parallel processing')
    parser.add_argument('--maxtasksperchild', type=int, default=5,
                        help='Restart worker after N tasks (prevents memory leaks)')
    args = parser.parse_args()

    print("VNC Screenshot Tool - Process Isolation Version")
    print("=" * 60)

    if not os.path.exists(args.file):
        print(f"Error: {args.file} not found!")
        sys.exit(1)

    create_screenshot_dir()

    with open(args.file, "r") as f:
        lines = f.readlines()

    servers = [s for s in (parse_vnc_line(l) for l in lines) if s]

    if not servers:
        print("No valid servers found")
        sys.exit(1)

    total_servers = len(servers)
    workers = 1 if args.no_parallel else min(args.workers, total_servers)

    print(f"Total servers: {total_servers}")
    print(f"Parallel workers: {workers}")
    print(f"Connection timeout: {args.timeout}s")
    print(f"Max tasks per child: {args.maxtasksperchild}")
    print(f"Screenshot directory: {SCREENSHOT_DIR}/")
    print("=" * 60)
    print()

    start_time = time.time()

    work_items = [
        (server, i, total_servers, args.timeout, SCREENSHOT_DIR)
        for i, server in enumerate(servers, 1)
    ]

    successful = 0
    failed = 0
    failed_servers = []

    if args.no_parallel:
        for item in work_items:
            result = single_vnc_connection(item)
            if result[0]:
                successful += 1
            else:
                failed += 1
                failed_servers.append((result[1], result[2]))
    else:
        # maxtasksperchild restarts workers periodically to prevent memory/resource leaks
        with Pool(processes=workers, maxtasksperchild=args.maxtasksperchild) as pool:
            for result in pool.imap_unordered(single_vnc_connection, work_items):
                if result[0]:
                    successful += 1
                else:
                    failed += 1
                    failed_servers.append((result[1], result[2]))

    elapsed_time = time.time() - start_time

    print()
    print("=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print(f"Total: {total_servers} | Success: {successful} | Failed: {failed}")
    print(f"Time: {elapsed_time:.2f}s | Avg: {elapsed_time/total_servers:.2f}s per server")
    print(f"Screenshots: {SCREENSHOT_DIR}/")
    print("=" * 60)

if __name__ == "__main__":
    # Required for multiprocessing on some platforms
    import multiprocessing
    multiprocessing.set_start_method('spawn', force=True)
    main()
