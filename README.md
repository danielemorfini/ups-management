# UPS Monitor Service

A systemd daemon that monitors a CyberPower UPS and automatically manages Proxmox VM shutdowns when power is lost.

> **Note:** this is a personal project, built and tuned for my own Proxmox/PBS homelab setup rather than as a general-purpose tool.
>
> Feel free to read, fork, or adapt it, but don't expect it to cover cases outside what I actually needed.

## Overview

This service monitors your UPS battery status and responds to power events in three stages:

1. **Normal Operation (ONLINE)**
   - System runs on main power

2. **Power Loss (ON BATTERY)**
   - When power fails, the daemon:
     - Sends an alert email with battery status
     - Gracefully shuts down running Proxmox VMs/LXCs if charge drops below threshold or runtime is too low

3. **Critical Battery (ON LOWBATT)**
   - When battery hits critical level, the host shuts down immediately

## How It Works

```
# UPS Monitor Daemon (runs every 5s)
- Query UPS status (charge %, runtime)
- Detect state changes (Online → Battery → LowBatt)
- Send email alerts (via Proxmox)
- Manage shutdowns (stop VMs/LXCs → shutdown host)
```

## Requirements

- **NUT (Network UPS Tools)** for communicating with the UPS:
  - UPS must be configured in `/etc/nut/ups.conf`
  - `upsc` command must be available

- **Proxmox Host** running Proxmox VE
  - Python 3.7+
  - SSH access to Proxmox Backup Server

- **Email** - Configured Proxmox mail system for alerts

## Configuration

### 1. Copy and Configure Environment File

```sh
cp config/ups-management.example.env config/ups-management.env
```

Edit `config/ups-management.env` with your settings:

### 2. Verify NUT Configuration

```sh
# Check UPS is accessible
upsc cyberpower@localhost ups.status

# Should return something like:
# - OL (online) or
# - OB (on battery) or
# - LB (low battery)
```

## Installation & Integration

### Step 1: Install Files

```sh
# Copy project to installation directory
sudo cp -r ./* /opt/ups-management/

# Make main script executable
sudo chmod +x /opt/ups-management/main.py

# Create data directory for state tracking
sudo mkdir -p /opt/ups-management/data
```

### Step 2: Create Systemd Service

```sh
# Copy service file to systemd
sudo cp config/custom-ups-monitor.service /etc/systemd/system/

# Or manually create /etc/systemd/system/custom-ups-monitor.service:
# (see config/custom-ups-monitor.service in repo for content)
```

### Step 3: Enable and Start Service

```sh
# Reload systemd configuration
sudo systemctl daemon-reload

# Enable service to auto-start on boot
sudo systemctl enable custom-ups-monitor.service

# Start the service
sudo systemctl start custom-ups-monitor.service

# Verify it's running
sudo systemctl status custom-ups-monitor.service
```

### Step 4: Monitor Logs

```sh
# View real-time logs
sudo journalctl -u custom-ups-monitor.service -f

# View last 50 lines
sudo journalctl -u custom-ups-monitor.service -n 50
```

## Testing

### Test 1: Verify Service is Running

```sh
sudo systemctl status custom-ups-monitor.service
# Should show: active (running)
```

### Test 2: Check UPS Detection

```sh
# Service should detect UPS immediately
sudo journalctl -u custom-ups-monitor.service -n 20 | grep "Starting"
```

### Test 3: Trigger Manual Test Cycle

Use the included test script (run as a module from the project root so it can resolve the `core`/`config` packages):

```sh
# This simulates different UPS states for testing
python3 -m tests.test_cycle
```

### Test 4: Verify Logging

```sh
# Check application logs
tail -f /var/log/ups-monitor.log

# You should see periodic status checks
```

### Test 5: Email Notification Test (Optional)

Manually trigger an email by simulating a power event in the test cycle script.

## Troubleshooting

### Service won't start

- Check if `/opt/ups-management/main.py` is executable
- Verify `config/ups-management.env` exists and is readable
- Check systemd status: `sudo systemctl status custom-ups-monitor.service`

### UPS not detected

- Verify NUT service is running: `sudo systemctl status nut-server`
- Test UPS connection: `upsc cyberpower@localhost ups.status`
- Check UPS name in config matches `/etc/nut/ups.conf`

### No email alerts

- Verify Proxmox mail is configured: `proxmox-mail-forward`
- Check TARGET_EMAIL user exists in Proxmox
- Review logs for email errors: `journalctl -u custom-ups-monitor.service`

### Service stops unexpectedly

- Check logs for exceptions: `journalctl -u custom-ups-monitor.service -n 100`
- Increase restart delay in service file if needed: `RestartSec=10`

## Files Overview

| File      | Description                           |
| --------- | ------------------------------------- |
| `main.py` | Entry point, handles daemon lifecycle |

| File                                | Description               |
| ----------------------------------- | ------------------------- |
| `config/settings.py`                | Configuration management  |
| `config/custom-ups-monitor.service` | Systemd unit file         |
| `config/ups-management.example.env` | Environment file template |

| File                      | Description                     |
| ------------------------- | ------------------------------- |
| `core/monitor.py`         | Main UPS state evaluation logic |
| `core/ups_client.py`      | Communicates with NUT           |
| `core/notifier.py`        | Email notifications             |
| `core/service_manager.py` | VM and host shutdown management |
| `core/logger.py`          | Structured logging              |

| File                  | Description         |
| --------------------- | ------------------- |
| `tests/test_cycle.py` | Manual testing tool |
