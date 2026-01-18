# VNC Screenshot Tool

Automated tool to connect to multiple VNC servers and capture screenshots.

## Features

- Connect to multiple VNC servers from a list
- Automatically wake screens with key press
- Capture and save screenshots
- Support for password-protected and open VNC servers
- Batch processing with error handling

## Installation

### Method 1: Install from requirements.txt

```bash
pip install -r requirements.txt
```

### Method 2: Install packages individually

If you encounter build errors, try installing packages one by one:

```bash
pip install Pillow
pip install twisted
pip install zope.interface
pip install vncdotool
```

### Method 3: Use pre-built wheels (Windows)

If installation fails on Windows, try:

```bash
pip install --upgrade pip setuptools wheel
pip install --no-cache-dir vncdotool
```

### Method 4: Install from GitHub (latest version)

```bash
pip install Pillow twisted zope.interface
pip install git+https://github.com/sibson/vncdotool.git
```

## Configuration

Create a `vnc.txt` file with your VNC servers in the following format:

```
ip:port-password-hostname
```

### Format Details

- **ip:port**: VNC server IP and port
- **password**: VNC password (use "null" for no password)
- **hostname**: Optional server hostname or description

### Example vnc.txt

```
192.168.1.100:5900-mypassword-server1
192.168.1.101:5900-null-server2
10.0.0.50:5901-secretpass-workstation
172.16.0.10:5900-null-
```

You can use the provided `vnc.txt.example` as a template:

```bash
cp vnc.txt.example vnc.txt
```

## Usage

Run the tool:

```bash
python3 vnc_screenshot.py
```

The tool will:
1. Read all servers from vnc.txt
2. Connect to each server sequentially
3. Send a space key press to wake the screen
4. Capture a screenshot
5. Save it to the screenshots/ directory

## Screenshot Naming

Screenshots are saved with the format: `ip_port-password.png`

Examples:
- `192.168.1.100_5900-mypass.png`
- `10.0.0.50_5901-null.png`

## Output Directory

All screenshots are saved in the `screenshots/` directory, which is automatically created if it doesn't exist.

## Error Handling

The tool handles connection errors gracefully and continues with the next server if one fails. A summary is displayed at the end showing successful and failed connections.

## Requirements

- Python 3.6+
- vncdotool
- Pillow

## Notes

- The tool waits 2 seconds between servers to avoid overwhelming the network
- Connection timeout is handled by vncdotool defaults
- Comments in vnc.txt start with # and are ignored

## Troubleshooting

### Installation Issues on Windows

If you get "subprocess-exited-with-error" or "KeyError: '__version__'" errors:

1. Upgrade pip and build tools:
```bash
python -m pip install --upgrade pip setuptools wheel
```

2. Install Microsoft C++ Build Tools (if needed):
   - Download from: https://visualstudio.microsoft.com/visual-cpp-build-tools/
   - Install "Desktop development with C++" workload

3. Try installing without cache:
```bash
pip install --no-cache-dir --upgrade Pillow twisted zope.interface vncdotool
```

4. Use the latest vncdotool from GitHub:
```bash
pip install git+https://github.com/sibson/vncdotool.git
```

### Connection Issues

- Ensure VNC server is running and accessible
- Check firewall settings allow VNC port
- Verify credentials are correct
- Try connecting with a VNC client first to confirm server works
