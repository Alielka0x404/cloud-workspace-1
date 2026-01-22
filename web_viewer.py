#!/usr/bin/env python3

import os
import re
import subprocess
import threading
import time
import signal
import atexit
from flask import Flask, render_template, jsonify, send_from_directory, request, session, redirect, url_for
from pathlib import Path
from functools import wraps

app = Flask(__name__)
app.secret_key = 'vnc_screenshot_secret_key_2024'

# Authentication credentials
AUTH_USERNAME = 'amin'
AUTH_PASSWORD = '@Amin123'

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'logged_in' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

SCREENSHOT_DIR = "screenshots"
VNC_FILE = "vnc.txt"
WEBSOCKIFY_BASE_PORT = 6080
MAX_WEBSOCKIFY_PROCESSES = 50

active_proxies = {}
proxy_lock = threading.Lock()
next_port = WEBSOCKIFY_BASE_PORT

# Cache for VNC server info (ip:port -> hostname)
vnc_servers_cache = {}

def load_vnc_servers():
    """Load VNC servers from vnc.txt and cache hostname info"""
    global vnc_servers_cache
    vnc_servers_cache = {}

    if not os.path.exists(VNC_FILE):
        return

    try:
        with open(VNC_FILE, 'r') as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith('#'):
                    continue

                parts = line.split('-')
                if len(parts) >= 2:
                    ip_port = parts[0].strip()
                    password = parts[1].strip() if len(parts) > 1 else ''
                    hostname = parts[2].strip() if len(parts) > 2 else ''

                    ip_port_parts = ip_port.split(':')
                    if len(ip_port_parts) == 2:
                        ip = ip_port_parts[0]
                        port = ip_port_parts[1]
                        key = f"{ip}:{port}"
                        vnc_servers_cache[key] = hostname
    except Exception as e:
        print(f"Error loading vnc.txt: {e}")

def parse_screenshot_filename(filename):
    pattern = r'^(.+?)_(\d+)-(.+?)\.png$'
    match = re.match(pattern, filename)

    if match:
        ip = match.group(1)
        port = match.group(2)
        password = match.group(3)

        # Get hostname from cache
        key = f"{ip}:{port}"
        hostname = vnc_servers_cache.get(key, '')

        return {
            'filename': filename,
            'ip': ip,
            'port': port,
            'password': password if password != 'null' else None,
            'display_password': password,
            'hostname': hostname
        }
    return None

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')

        if username == AUTH_USERNAME and password == AUTH_PASSWORD:
            session['logged_in'] = True
            return redirect(url_for('index'))
        else:
            return render_template('login.html', error='Invalid credentials')

    return render_template('login.html')

@app.route('/logout')
def logout():
    session.pop('logged_in', None)
    return redirect(url_for('login'))

@app.route('/')
@login_required
def index():
    return render_template('gallery.html')

@app.route('/api/screenshots')
@login_required
def get_screenshots():
    # Reload VNC servers to get latest hostname info
    load_vnc_servers()

    screenshots = []

    if not os.path.exists(SCREENSHOT_DIR):
        return jsonify({'screenshots': [], 'total': 0})

    for filename in os.listdir(SCREENSHOT_DIR):
        if filename.endswith('.png'):
            info = parse_screenshot_filename(filename)
            if info:
                filepath = os.path.join(SCREENSHOT_DIR, filename)
                info['mtime'] = os.path.getmtime(filepath)
                screenshots.append(info)

    # Sort by modification time (newest first)
    screenshots.sort(key=lambda x: x['mtime'], reverse=True)

    return jsonify({
        'screenshots': screenshots,
        'total': len(screenshots)
    })

@app.route('/screenshots/<path:filename>')
@login_required
def serve_screenshot(filename):
    return send_from_directory(SCREENSHOT_DIR, filename)

@app.route('/vnc/<ip>/<port>')
@login_required
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
            ['websockify', str(ws_port), target],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            start_new_session=True
        )

        time.sleep(1.0)

        if process.poll() is not None:
            stdout, stderr = process.communicate()
            error_msg = stderr.decode() if stderr else stdout.decode()
            print(f"Failed to start websockify on port {ws_port}")
            print(f"Error: {error_msg}")
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
@login_required
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
@login_required
def stop_vnc_proxy(port):
    cleanup_proxy(port)
    return jsonify({'success': True, 'message': f'Stopped proxy on port {port}'})

@app.route('/api/vnc/active')
@login_required
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
