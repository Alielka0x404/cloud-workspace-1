# VNC Screenshot Tool

Automated tool to connect to multiple VNC servers and capture screenshots.

## Features

- Parallel processing for fast bulk screenshot capture
- Connect to multiple VNC servers from a list (supports 1000+ servers)
- Configurable number of parallel workers
- Automatically wake screens with key press
- Capture and save screenshots with organized naming
- Support for password-protected and open VNC servers
- Thread-safe processing with real-time progress tracking
- Comprehensive error handling and detailed summary reports
- Sequential mode option for compatibility

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

### Basic Usage (Parallel Mode - Default)

Run with 10 parallel workers (default):

```bash
python3 vnc_screenshot.py
```

### Custom Number of Workers

For 1000+ servers, increase the number of parallel workers:

```bash
python3 vnc_screenshot.py -w 50
```

Recommended worker counts:
- 10-100 servers: 10-20 workers
- 100-500 servers: 20-50 workers
- 500-1000 servers: 50-100 workers
- 1000+ servers: 100-200 workers

### Sequential Mode

Disable parallel processing (one server at a time):

```bash
python3 vnc_screenshot.py --no-parallel
```

### Custom VNC File

Use a different server list file:

```bash
python3 vnc_screenshot.py -f my_servers.txt -w 100
```

### Command Line Options

```
-w, --workers NUM      Number of parallel workers (default: 10)
-f, --file FILE        VNC server list file (default: vnc.txt)
--no-parallel          Disable parallel processing
-h, --help             Show help message
```

### How It Works

The tool will:
1. Read all servers from vnc.txt
2. Connect to multiple servers in parallel (based on worker count)
3. Send a space key press to wake each screen
4. Capture screenshots simultaneously
5. Save them to the screenshots/ directory
6. Display real-time progress and final summary

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

## Performance

Parallel processing dramatically reduces total execution time:

- Sequential mode: ~3-4 seconds per server
  - 100 servers: ~6-7 minutes
  - 1000 servers: ~60-70 minutes

- Parallel mode (50 workers): ~3-4 seconds total for 50 servers
  - 100 servers: ~6-8 seconds
  - 1000 servers: ~60-80 seconds

Performance tips:
- Start with 10-20 workers and increase gradually
- Too many workers may cause network congestion
- Monitor your network bandwidth
- Failed connections are retried automatically

## Notes

- Each connection takes ~3 seconds (2s stabilization + 1s screen wake)
- Connection timeout is handled by vncdotool defaults
- Comments in vnc.txt start with # and are ignored
- Thread-safe output ensures readable progress logs
- Failed servers are listed at the end for easy retry

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
