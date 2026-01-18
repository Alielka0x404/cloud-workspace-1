#!/usr/bin/env python3

import os
import sys
import signal
import subprocess
from pathlib import Path

WEBSOCKIFY_PORT = 6080

def check_websockify():
    try:
        result = subprocess.run(['websockify', '--version'],
                              capture_output=True, text=True)
        return True
    except FileNotFoundError:
        return False

def start_proxy():
    if not check_websockify():
        print("Error: websockify not found!")
        print()
        print("Install websockify:")
        print("  pip install websockify")
        print()
        print("Or using apt (Linux):")
        print("  sudo apt-get install websockify")
        sys.exit(1)

    print("=" * 60)
    print("VNC WebSocket Proxy (websockify)")
    print("=" * 60)
    print(f"Starting websockify on port {WEBSOCKIFY_PORT}")
    print()
    print("This proxy allows noVNC web client to connect to VNC servers")
    print()
    print("Note: You need to manually connect to each VNC server")
    print("Use the web interface to click 'Connect VNC' button")
    print()
    print("Press Ctrl+C to stop")
    print("=" * 60)
    print()

    try:
        subprocess.run(['websockify', '--web=/usr/share/novnc',
                       str(WEBSOCKIFY_PORT), '--target-config=/dev/null'])
    except KeyboardInterrupt:
        print("\nShutting down proxy...")
    except Exception as e:
        print(f"Error: {e}")
        print()
        print("You can manually start websockify for a specific server:")
        print(f"  websockify {WEBSOCKIFY_PORT} <VNC_IP>:<VNC_PORT>")
        print()
        print("Example:")
        print(f"  websockify {WEBSOCKIFY_PORT} 192.168.1.100:5900")

if __name__ == '__main__':
    start_proxy()
