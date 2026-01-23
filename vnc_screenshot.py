#!/usr/bin/env python3
"""
VNC Screenshot Tool - Subprocess version with hard timeouts
Uses vncdo CLI in subprocess which can be forcefully killed on timeout
"""

import os
import sys
import time
import argparse
import subprocess
from concurrent.futures import ProcessPoolExecutor, as_completed, TimeoutError

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
    return {"ip": ip, "port": port, "password": password, "hostname": hostname}

def vnc_worker(server_info, index, total, timeout, screenshot_dir, force):
    """Uses vncdo CLI via subprocess - can be killed on timeout"""
    ip = server_info["ip"]
    port = server_info["port"]
    password = server_info["password"]
    prefix = f"[{index}/{total}]"

    pass_str = password if password else "null"
    filename = f"{ip}_{port}-{pass_str}.png"
    filepath = os.path.join(screenshot_dir, filename)

    # Check if screenshot already exists (skip if not forcing)
    if not force and os.path.exists(filepath):
        print(f"{prefix} SKIPPED: {ip}:{port} - Screenshot already exists", flush=True)
        return (True, server_info, "skipped")

    connection_string = f"{ip}::{port}"

    cmd = ["vncdo"]
    if password:
        cmd.extend(["--password", password])
    cmd.extend([
        "--server", connection_string,
        "key", "space",
        "pause", "1",
        "capture", filepath
    ])

    print(f"{prefix} Connecting to {ip}:{port}...", flush=True)

    try:
        # subprocess.run with timeout KILLS the process if it exceeds timeout
        result = subprocess.run(
            cmd,
            timeout=timeout,
            capture_output=True,
            text=True,
            start_new_session=True  # Allows killing entire process group
        )

        if result.returncode == 0 and os.path.exists(filepath):
            print(f"{prefix} SUCCESS: {ip}:{port} -> {filename}", flush=True)
            return (True, server_info, None)
        else:
            err = result.stderr.strip()[:80] or f"Exit code {result.returncode}"
            print(f"{prefix} FAILED: {ip}:{port} - {err}", flush=True)
            return (False, server_info, err)

    except subprocess.TimeoutExpired:
        print(f"{prefix} FAILED: {ip}:{port} - KILLED (timeout {timeout}s)", flush=True)
        return (False, server_info, f"Killed after {timeout}s")
    except FileNotFoundError:
        print(f"{prefix} FAILED: vncdo not found - install with: pip install vncdotool", flush=True)
        return (False, server_info, "vncdo not installed")
    except Exception as e:
        print(f"{prefix} FAILED: {ip}:{port} - {str(e)[:80]}", flush=True)
        return (False, server_info, str(e)[:80])

def main():
    parser = argparse.ArgumentParser(description='VNC Screenshot Tool - Hard Timeout Version')
    parser.add_argument('-w', '--workers', type=int, default=DEFAULT_WORKERS,
                        help=f'Number of parallel workers (default: {DEFAULT_WORKERS})')
    parser.add_argument('-f', '--file', type=str, default=VNC_FILE,
                        help=f'VNC server list file (default: {VNC_FILE})')
    parser.add_argument('-t', '--timeout', type=int, default=CONNECTION_TIMEOUT,
                        help=f'Connection timeout in seconds (default: {CONNECTION_TIMEOUT})')
    parser.add_argument('--no-parallel', action='store_true',
                        help='Disable parallel processing (sequential mode)')
    parser.add_argument('--force', action='store_true',
                        help='Force re-capture of screenshots even if they already exist')
    args = parser.parse_args()

    print("VNC Screenshot Tool - Hard Timeout Version")
    print("=" * 60)

    if not os.path.exists(args.file):
        print(f"Error: {args.file} not found!")
        print(f"Create a {args.file} file with format:")
        print("ip:port-password-hostname")
        print("Example: 192.168.1.100:5900-mypass-server1")
        sys.exit(1)

    create_screenshot_dir()

    with open(args.file) as f:
        servers = [s for s in (parse_vnc_line(l) for l in f) if s]

    if not servers:
        print("No valid servers found")
        sys.exit(1)

    total = len(servers)
    workers = 1 if args.no_parallel else min(args.workers, total)
    force = args.force

    print(f"Total servers: {total}")
    print(f"Parallel workers: {workers}")
    print(f"Connection timeout: {args.timeout}s")
    print(f"Force re-capture: {'Yes' if force else 'No'}")
    print(f"Screenshot directory: {SCREENSHOT_DIR}/")
    print("=" * 60)
    print()

    start_time = time.time()
    successful = 0
    skipped = 0
    failed = 0
    failed_list = []

    if args.no_parallel:
        for i, server in enumerate(servers, 1):
            result = vnc_worker(server, i, total, args.timeout, SCREENSHOT_DIR, force)
            if result[0]:
                if result[2] == "skipped":
                    skipped += 1
                else:
                    successful += 1
            else:
                failed += 1
                failed_list.append((result[1], result[2]))
    else:
        with ProcessPoolExecutor(max_workers=workers) as executor:
            futures = {
                executor.submit(vnc_worker, server, i, total, args.timeout, SCREENSHOT_DIR, force): (server, i)
                for i, server in enumerate(servers, 1)
            }

            for future in as_completed(futures):
                server, index = futures[future]
                try:
                    # Extra timeout at executor level as safety net
                    result = future.result(timeout=args.timeout + 10)
                    if result[0]:
                        if result[2] == "skipped":
                            skipped += 1
                        else:
                            successful += 1
                    else:
                        failed += 1
                        failed_list.append((result[1], result[2]))
                except TimeoutError:
                    print(f"[{index}/{total}] EXECUTOR TIMEOUT: {server['ip']}:{server['port']}", flush=True)
                    failed += 1
                    failed_list.append((server, "Executor timeout"))
                except Exception as e:
                    print(f"[{index}/{total}] ERROR: {server['ip']}:{server['port']} - {e}", flush=True)
                    failed += 1
                    failed_list.append((server, str(e)[:50]))

    elapsed = time.time() - start_time

    print()
    print("=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print(f"Total servers: {total}")
    print(f"Successful: {successful}")
    print(f"Skipped: {skipped}")
    print(f"Failed: {failed}")
    print(f"Time elapsed: {elapsed:.2f} seconds")
    print(f"Average time per server: {elapsed/total:.2f} seconds")
    print(f"Screenshots saved in: {SCREENSHOT_DIR}/")

    if failed_list:
        print()
        print("FAILED SERVERS:")
        for server, error in failed_list:
            print(f"  - {server['ip']}:{server['port']} - {error}")

    print("=" * 60)

if __name__ == "__main__":
    main()
