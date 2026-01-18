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

## 4. View in Web Browser

```bash
python3 web_viewer.py
```

Open: http://localhost:5000

## 5. Connect to VNC (Optional)

To use the web VNC client, run websockify in another terminal:

```bash
websockify 6080 192.168.1.100:5900
```

Then click "Connect VNC" in the web interface.

## Tips

- Screenshots are saved in `screenshots/` directory
- Increase workers (-w) for faster bulk processing
- Search screenshots by IP, port, or password in web UI
- Click screenshots to view full size
- Use "Copy Info" to copy server details
