#!/usr/bin/env python3

import os
import re
import subprocess
import threading
import time
import hashlib
import atexit
from flask import Flask, render_template, jsonify, send_from_directory, request, Response
from pathlib import Path
from PIL import Image
import io

app = Flask(__name__)

SCREENSHOT_DIR = "screenshots"
THUMBNAIL_DIR = "thumbnails"
WEBSOCKIFY_BASE_PORT = 6080
MAX_WEBSOCKIFY_PROCESSES = 50

# Thumbnail settings
THUMB_SIZES = {
    'small': (200, 150),    # For grid view
    'medium': (400, 300),   # For larger cards
    'large': (800, 600),    # For preview
}
JPEG_QUALITY = 75  # Compression quality (1-100)

active_proxies = {}
proxy_lock = threading.Lock()
next_port = WEBSOCKIFY_BASE_PORT
thumbnail_cache = {}
thumb_lock = threading.Lock()

def ensure_dirs():
    """Create necessary directories"""
    for d in [SCREENSHOT_DIR, THUMBNAIL_DIR]:
        if not os.path.exists(d):
            os.makedirs(d)
    for size in THUMB_SIZES:
        size_dir = os.path.join(THUMBNAIL_DIR, size)
        if not os.path.exists(size_dir):
            os.makedirs(size_dir)

def get_file_hash(filepath):
    """Get hash of file for cache invalidation"""
    stat = os.stat(filepath)
    return hashlib.md5(f"{filepath}{stat.st_mtime}{stat.st_size}".encode()).hexdigest()[:12]

def generate_thumbnail(src_path, size_name='small'):
    """Generate compressed thumbnail"""
    if size_name not in THUMB_SIZES:
        size_name = 'small'
    
    filename = os.path.basename(src_path)
    thumb_filename = filename.rsplit('.', 1)[0] + '.jpg'  # Convert to JPEG
    thumb_dir = os.path.join(THUMBNAIL_DIR, size_name)
    thumb_path = os.path.join(thumb_dir, thumb_filename)
    
    # Check cache
    cache_key = f"{src_path}:{size_name}"
    file_hash = get_file_hash(src_path)
    
    with thumb_lock:
        if cache_key in thumbnail_cache and thumbnail_cache[cache_key] == file_hash:
            if os.path.exists(thumb_path):
                return thumb_path
    
    try:
        with Image.open(src_path) as img:
            # Convert to RGB if necessary (for PNG with transparency)
            if img.mode in ('RGBA', 'P'):
                img = img.convert('RGB')
            
            # Resize with high-quality resampling
            img.thumbnail(THUMB_SIZES[size_name], Image.Resampling.LANCZOS)
            
            # Save as JPEG with compression
            img.save(thumb_path, 'JPEG', quality=JPEG_QUALITY, optimize=True)
        
        with thumb_lock:
            thumbnail_cache[cache_key] = file_hash
        
        return thumb_path
    except Exception as e:
        print(f"Error generating thumbnail for {src_path}: {e}")
        return None

def generate_all_thumbnails():
    """Background task to pre-generate all thumbnails"""
    if not os.path.exists(SCREENSHOT_DIR):
        return
    
    count = 0
    for filename in os.listdir(SCREENSHOT_DIR):
        if filename.endswith('.png'):
            src_path = os.path.join(SCREENSHOT_DIR, filename)
            for size in ['small', 'medium']:
                generate_thumbnail(src_path, size)
            count += 1
    
    print(f"Generated thumbnails for {count} screenshots")

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
            'display_password': password,
            'thumb_small': f"/thumb/small/{filename.rsplit('.', 1)[0]}.jpg",
            'thumb_medium': f"/thumb/medium/{filename.rsplit('.', 1)[0]}.jpg",
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

@app.route('/api/screenshots/paginated')
def get_screenshots_paginated():
    """Paginated endpoint for better performance"""
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 50, type=int)
    search = request.args.get('search', '').lower()
    
    screenshots = []
    
    if not os.path.exists(SCREENSHOT_DIR):
        return jsonify({'screenshots': [], 'total': 0, 'page': page, 'pages': 0})
    
    for filename in os.listdir(SCREENSHOT_DIR):
        if filename.endswith('.png'):
            info = parse_screenshot_filename(filename)
            if info:
                # Apply search filter
                if search:
                    if not (search in info['ip'].lower() or 
                            search in info['port'] or 
                            search in info['display_password'].lower()):
                        continue
                screenshots.append(info)
    
    screenshots.sort(key=lambda x: (x['ip'], int(x['port'])))
    
    total = len(screenshots)
    pages = (total + per_page - 1) // per_page
    start = (page - 1) * per_page
    end = start + per_page
    
    return jsonify({
        'screenshots': screenshots[start:end],
        'total': total,
        'page': page,
        'pages': pages,
        'per_page': per_page
    })

@app.route('/screenshots/<path:filename>')
def serve_screenshot(filename):
    """Serve original screenshot with caching headers"""
    response = send_from_directory(SCREENSHOT_DIR, filename)
    response.headers['Cache-Control'] = 'public, max-age=3600'
    return response

@app.route('/thumb/<size>/<path:filename>')
def serve_thumbnail(size, filename):
    """Serve compressed thumbnail"""
    if size not in THUMB_SIZES:
        size = 'small'
    
    # Find original PNG file
    png_filename = filename.rsplit('.', 1)[0] + '.png'
    src_path = os.path.join(SCREENSHOT_DIR, png_filename)
    
    if not os.path.exists(src_path):
        return "Not found", 404
    
    thumb_path = generate_thumbnail(src_path, size)
    
    if thumb_path and os.path.exists(thumb_path):
        response = send_from_directory(os.path.dirname(thumb_path), os.path.basename(thumb_path))
        response.headers['Cache-Control'] = 'public, max-age=86400'  # Cache for 24h
        return response
    
    # Fallback to original
    return send_from_directory(SCREENSHOT_DIR, png_filename)

@app.route('/thumb/blur/<path:filename>')
def serve_blur_placeholder(filename):
    """Serve tiny blurred placeholder (LQIP - Low Quality Image Placeholder)"""
    png_filename = filename.rsplit('.', 1)[0] + '.png'
    src_path = os.path.join(SCREENSHOT_DIR, png_filename)
    
    if not os.path.exists(src_path):
        return "Not found", 404
    
    try:
        with Image.open(src_path) as img:
            if img.mode in ('RGBA', 'P'):
                img = img.convert('RGB')
            
            # Create tiny 20x15 placeholder
            img.thumbnail((20, 15), Image.Resampling.LANCZOS)
            
            buffer = io.BytesIO()
            img.save(buffer, 'JPEG', quality=30)
            buffer.seek(0)
            
            response = Response(buffer.getvalue(), mimetype='image/jpeg')
            response.headers['Cache-Control'] = 'public, max-age=604800'  # 1 week
            return response
    except:
        return "Error", 500

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
            ['websockify', str(ws_port), target],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            start_new_session=True
        )
        
        time.sleep(1.0)
        
        if process.poll() is not None:
            stdout, stderr = process.communicate()
            error_msg = stderr.decode() if stderr else stdout.decode()
            print(f"Failed to start websockify: {error_msg}")
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
        print("Error: websockify not found")
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
    print("\nCleaning up websockify processes...")
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
            'target': f"{ip}:{port}"
        })
    else:
        return jsonify({
            'success': False,
            'error': 'Failed to start websockify'
        }), 500

@app.route('/api/vnc/stop/<int:port>', methods=['POST'])
def stop_vnc_proxy(port):
    cleanup_proxy(port)
    return jsonify({'success': True})

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

@app.route('/api/regenerate-thumbnails', methods=['POST'])
def regenerate_thumbnails():
    """Force regenerate all thumbnails"""
    with thumb_lock:
        thumbnail_cache.clear()
    
    # Clear thumbnail directories
    for size in THUMB_SIZES:
        size_dir = os.path.join(THUMBNAIL_DIR, size)
        if os.path.exists(size_dir):
            for f in os.listdir(size_dir):
                os.remove(os.path.join(size_dir, f))
    
    # Regenerate in background
    threading.Thread(target=generate_all_thumbnails, daemon=True).start()
    
    return jsonify({'success': True, 'message': 'Regenerating thumbnails in background'})

if __name__ == '__main__':
    ensure_dirs()
    
    print("=" * 60)
    print("VNC Screenshot Web Viewer (Optimized)")
    print("=" * 60)
    print("http://localhost:5000")
    print()
    print("Features:")
    print("  - Compressed thumbnails (75% smaller)")
    print("  - Lazy loading images")
    print("  - Automatic websockify proxy")
    print("=" * 60)
    
    # Pre-generate thumbnails in background
    threading.Thread(target=generate_all_thumbnails, daemon=True).start()
    
    try:
        app.run(host='0.0.0.0', port=5000, debug=False, threaded=True)
    except KeyboardInterrupt:
        cleanup_all_proxies()
