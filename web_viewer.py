#!/usr/bin/env python3

import os
import re
import subprocess
import threading
import time
import signal
import atexit
from flask import Flask, render_template, jsonify, send_from_directory, request
from pathlib import Path

app = Flask(__name__)

SCREENSHOT_DIR = "screenshots"
WEBSOCKIFY_BASE_PORT = 6080
MAX_WEBSOCKIFY_PROCESSES = 50

active_proxies = {}
proxy_lock = threading.Lock()
next_port = WEBSOCKIFY_BASE_PORT

def parse_screenshot_filename(filename):
    pattern = r'^(.+?)_(\d+)-(.+?)\.png$'
    match = re.match(pattern, filename)

    if match:
        ip = match.group(1)
        port = match.group(2)
        password = match.group(3)

        return {
            'filename': filename,
            'ip': ip,
            'port': port,
            'password': password if password != 'null' else None,
            'display_password': password
        }
    return None

@app.route('/')
def index():
    return render_template('gallery.html')

@app.route('/api/screenshots')
def get_screenshots():
    screenshots = []

    if not os.path.exists(SCREENSHOT_DIR):
        return jsonify({'screenshots': [], 'total': 0})

    for filename in os.listdir(SCREENSHOT_DIR):
        if filename.endswith('.png'):
            info = parse_screenshot_filename(filename)
            if info:
                screenshots.append(info)

    screenshots.sort(key=lambda x: (x['ip'], int(x['port'])))

    return jsonify({
        'screenshots': screenshots,
        'total': len(screenshots)
    })

@app.route('/screenshots/<path:filename>')
def serve_screenshot(filename):
    return send_from_directory(SCREENSHOT_DIR, filename)

@app.route('/vnc/<ip>/<port>')
def vnc_viewer(ip, port):
    password = request.args.get('password', '')
    return render_template('vnc_viewer.html', ip=ip, port=port, password=password)

def find_available_port():
    global next_port
    with proxy_lock:
        while next_port in active_proxies:
            next_port += 1
            if next_port > WEBSOCKIFY_BASE_PORT + MAX_WEBSOCKIFY_PROCESSES:
                next_port = WEBSOCKIFY_BASE_PORT
        port = next_port
        next_port += 1
        return port

def start_websockify(target_ip, target_port, password=None):
    try:
        ws_port = find_available_port()
        target = f"{target_ip}:{target_port}"

        print(f"Starting websockify on port {ws_port} -> {target}")

        process = subprocess.Popen(
            ['websockify', '--web=/usr/share/novnc', str(ws_port), target],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True
        )

        time.sleep(0.5)

        if process.poll() is not None:
            print(f"Failed to start websockify on port {ws_port}")
            return None

        proxy_info = {
            'process': process,
            'port': ws_port,
            'target': target,
            'started': time.time()
        }

        with proxy_lock:
            active_proxies[ws_port] = proxy_info

        threading.Timer(300, lambda: cleanup_proxy(ws_port)).start()

        return ws_port

    except FileNotFoundError:
        print("Error: websockify not found. Install with: pip install websockify")
        return None
    except Exception as e:
        print(f"Error starting websockify: {e}")
        return None

def cleanup_proxy(port):
    with proxy_lock:
        if port in active_proxies:
            proxy = active_proxies[port]
            try:
                proxy['process'].terminate()
                proxy['process'].wait(timeout=2)
            except:
                try:
                    proxy['process'].kill()
                except:
                    pass
            del active_proxies[port]
            print(f"Cleaned up websockify on port {port}")

def cleanup_all_proxies():
    print("\nCleaning up all websockify processes...")
    with proxy_lock:
        for port, proxy in list(active_proxies.items()):
            try:
                proxy['process'].terminate()
                proxy['process'].wait(timeout=2)
            except:
                try:
                    proxy['process'].kill()
                except:
                    pass
        active_proxies.clear()
    print("All websockify processes terminated")

atexit.register(cleanup_all_proxies)

@app.route('/api/vnc/start', methods=['POST'])
def start_vnc_proxy():
    data = request.json
    ip = data.get('ip')
    port = data.get('port')
    password = data.get('password')

    if not ip or not port:
        return jsonify({'error': 'IP and port required'}), 400

    ws_port = start_websockify(ip, port, password)

    if ws_port:
        return jsonify({
            'success': True,
            'websockify_port': ws_port,
            'target': f"{ip}:{port}",
            'message': f'Websockify started on port {ws_port}'
        })
    else:
        return jsonify({
            'success': False,
            'error': 'Failed to start websockify. Make sure it is installed.'
        }), 500

@app.route('/api/vnc/stop/<int:port>', methods=['POST'])
def stop_vnc_proxy(port):
    cleanup_proxy(port)
    return jsonify({'success': True, 'message': f'Stopped proxy on port {port}'})

@app.route('/api/vnc/active')
def get_active_proxies():
    with proxy_lock:
        proxies = {
            port: {
                'target': info['target'],
                'uptime': int(time.time() - info['started'])
            }
            for port, info in active_proxies.items()
        }
    return jsonify({'proxies': proxies, 'count': len(proxies)})

if __name__ == '__main__':
    if not os.path.exists(SCREENSHOT_DIR):
        os.makedirs(SCREENSHOT_DIR)
        print(f"Created {SCREENSHOT_DIR} directory")

    print("=" * 60)
    print("VNC Screenshot Web Viewer")
    print("=" * 60)
    print("Starting web server on http://localhost:5000")
    print()
    print("Features:")
    print("  - Automatic websockify proxy management")
    print("  - Click 'Connect VNC' to auto-start connection")
    print("  - No manual websockify setup required")
    print()
    print("Make sure websockify is installed:")
    print("  pip install websockify")
    print("=" * 60)

    try:
        app.run(host='0.0.0.0', port=5000, debug=False, use_reloader=False)
    except KeyboardInterrupt:
        print("\n\nShutting down...")
        cleanup_all_proxies()
