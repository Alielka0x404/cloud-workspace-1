#!/usr/bin/env python3

import os
import re
from flask import Flask, render_template, jsonify, send_from_directory, request
from pathlib import Path

app = Flask(__name__)

SCREENSHOT_DIR = "screenshots"

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

@app.route('/api/vnc/proxy')
def vnc_proxy_info():
    return jsonify({
        'websockify_port': 6080,
        'message': 'Make sure websockify is running on port 6080'
    })

if __name__ == '__main__':
    if not os.path.exists(SCREENSHOT_DIR):
        os.makedirs(SCREENSHOT_DIR)
        print(f"Created {SCREENSHOT_DIR} directory")

    print("=" * 60)
    print("VNC Screenshot Web Viewer")
    print("=" * 60)
    print("Starting web server on http://localhost:5000")
    print()
    print("To enable VNC web client, run websockify in another terminal:")
    print("  websockify 6080 localhost:5900")
    print()
    print("Or for dynamic proxy mode:")
    print("  python3 vnc_proxy.py")
    print("=" * 60)

    app.run(host='0.0.0.0', port=5000, debug=True)
