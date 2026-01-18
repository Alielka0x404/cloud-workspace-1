# Quick Start Guide

## 1. Install Dependencies

```bash
pip install -r requirements.txt
```

## 2. Create VNC Server List

Create `vnc.txt` with your servers:

```
192.168.1.100:5900-password123-server1
192.168.1.101:5900-null-server2
10.0.0.50:5901-mypass-workstation
```

Format: `ip:port-password-hostname`
Use "null" for no password

## 3. Capture Screenshots

Basic (10 parallel workers):
```bash
python3 vnc_screenshot.py
```

For 1000+ servers (100 workers):
```bash
python3 vnc_screenshot.py -w 100
```

If servers are hanging (not responding):
```bash
python3 vnc_screenshot.py -w 100 -t 10
```
This sets a 10-second timeout per server.

## 4. View in Web Browser

```bash
python3 web_viewer.py
```

Open: http://localhost:5000

## 5. Connect to VNC

Just click "Connect VNC" in the web interface!

The system automatically:
- Starts websockify proxy for that server
- Opens VNC viewer in new window
- Connects with the saved password
- Auto-connects within 1-2 seconds

No manual setup required!

## Tips

- Screenshots are saved in `screenshots/` directory
- Increase workers (-w) for faster bulk processing
- Lower timeout (-t) if servers are hanging (default: 15s)
- Tool automatically skips unresponsive servers after timeout
- Search screenshots by IP, port, or password in web UI
- Click screenshots to view full size
- Use "Copy Info" to copy server details
- VNC connections auto-cleanup after 5 minutes
- websockify must be installed (included in requirements.txt)

## Troubleshooting Crashes

If the tool crashes after ~250 servers:

**Solution 1: Reduce workers**
```bash
python3 vnc_screenshot.py -w 20  # Use fewer workers
```

**Solution 2: Process in batches**
```bash
head -500 vnc.txt > batch1.txt
python3 vnc_screenshot.py -f batch1.txt -w 50
```

The tool now auto-cleans resources every 50 connections to prevent crashes.
