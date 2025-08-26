# Conversation Search - Deployment Guide

This directory contains systemd service files and deployment scripts for the Conversation Search Flask application.

## Files

- `conversation-search.service` - Systemd service unit file
- `deploy.sh` - Deployment helper script
- `app-production.py` - Production wrapper for the Flask app
- `README.md` - This file

## Quick Start

### 1. Install the Service

```bash
sudo ./deploy.sh install
```

### 2. Start the Service

```bash
sudo ./deploy.sh start
```

### 3. Check Status

```bash
./deploy.sh status
```

## Manual Installation

If you prefer to install manually or the script doesn't work:

### Step 1: Copy Service File

```bash
sudo cp conversation-search.service /etc/systemd/system/
```

### Step 2: Create Log File

```bash
sudo touch /var/log/conversation-search.log
sudo chown crathmene:crathmene /var/log/conversation-search.log
```

### Step 3: Reload Systemd

```bash
sudo systemctl daemon-reload
```

### Step 4: Enable and Start Service

```bash
sudo systemctl enable conversation-search.service
sudo systemctl start conversation-search.service
```

## Service Management Commands

### Start Service
```bash
sudo systemctl start conversation-search.service
```

### Stop Service
```bash
sudo systemctl stop conversation-search.service
```

### Restart Service
```bash
sudo systemctl restart conversation-search.service
```

### Check Status
```bash
systemctl status conversation-search.service
```

### View Logs
```bash
# Using journalctl
sudo journalctl -u conversation-search.service -f

# Or directly from log file
tail -f /var/log/conversation-search.log
```

### Enable Auto-start on Boot
```bash
sudo systemctl enable conversation-search.service
```

### Disable Auto-start
```bash
sudo systemctl disable conversation-search.service
```

## Deployment Script Usage

The `deploy.sh` script provides convenient commands:

```bash
# Install the service
sudo ./deploy.sh install

# Uninstall the service
sudo ./deploy.sh uninstall

# Start the service
sudo ./deploy.sh start

# Stop the service
sudo ./deploy.sh stop

# Restart the service
sudo ./deploy.sh restart

# Check service status
./deploy.sh status

# View logs (tail -f)
./deploy.sh logs

# Show help
./deploy.sh help
```

## Configuration Details

- **User**: Runs as `crathmene` (non-root)
- **Port**: 5000
- **Working Directory**: `/home/crathmene/git/json-lite/web`
- **Virtual Environment**: `/home/crathmene/git/json-lite/venv`
- **Log File**: `/var/log/conversation-search.log`
- **Restart Policy**: Automatic restart on failure with 10-second delay
- **Security**: 
  - No new privileges
  - Private /tmp
  - Read-only home directory
  - Protected system directories

## Troubleshooting

### Service Won't Start

1. Check the logs:
   ```bash
   sudo journalctl -u conversation-search.service -n 50
   ```

2. Verify Python virtual environment:
   ```bash
   /home/crathmene/git/json-lite/venv/bin/python --version
   ```

3. Check Flask dependencies:
   ```bash
   /home/crathmene/git/json-lite/venv/bin/pip list | grep Flask
   ```

### Port Already in Use

If port 5000 is already in use:

1. Find the process:
   ```bash
   sudo lsof -i :5000
   ```

2. Kill the process or change the port in `app-production.py`

### Permission Denied

Ensure the log file has correct permissions:
```bash
sudo chown crathmene:crathmene /var/log/conversation-search.log
sudo chmod 644 /var/log/conversation-search.log
```

### Database Connection Issues

Verify database file exists and is accessible:
```bash
ls -la /home/crathmene/data/unified_conversations.db
```

## Production Considerations

For production deployment, consider:

1. **Use a Production WSGI Server**: Replace Flask's built-in server with Gunicorn or uWSGI
2. **Add Nginx Reverse Proxy**: For better performance and SSL termination
3. **Configure Firewall**: Only allow necessary ports
4. **Set Up Monitoring**: Use tools like Prometheus or Datadog
5. **Implement Rate Limiting**: Protect against abuse
6. **Add SSL Certificate**: Use Let's Encrypt for HTTPS
7. **Database Backups**: Regular backups of the SQLite database
8. **Log Rotation**: Configure logrotate for the application logs

## Example Gunicorn Configuration

To use Gunicorn instead of Flask's built-in server:

1. Install Gunicorn:
   ```bash
   /home/crathmene/git/json-lite/venv/bin/pip install gunicorn
   ```

2. Update the ExecStart in the service file:
   ```
   ExecStart=/home/crathmene/git/json-lite/venv/bin/gunicorn -w 4 -b 0.0.0.0:5000 app:app
   ```

## Support

For issues or questions about deployment, check:
- Application logs: `/var/log/conversation-search.log`
- System logs: `sudo journalctl -u conversation-search.service`
- Service status: `systemctl status conversation-search.service`