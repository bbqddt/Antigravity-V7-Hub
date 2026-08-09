#!/bin/bash
# deploy_monitor_service.sh - Deploy monitor dashboard as systemd service
# Usage: On cloud server, in /home/admin/antigravity dir: bash deploy_monitor_service.sh

set -euo pipefail

SERVICE_FILE="antigravity-monitor.service"
TARGET_DIR="/etc/systemd/system"

echo "=== Deploy Antigravity Monitor systemd service ==="
echo "Current dir: $(pwd)"
echo "User: $(whoami)"

# 1. Check service file exists
if [[ ! -f "$SERVICE_FILE" ]]; then
    echo "ERROR: $SERVICE_FILE not found. Run from project root."
    exit 1
fi

# 2. Copy to systemd directory (needs sudo)
echo "Copying service file to $TARGET_DIR ..."
sudo cp "$SERVICE_FILE" "$TARGET_DIR/"

# 3. Reload systemd
echo "Reloading systemd config..."
sudo systemctl daemon-reload

# 4. Enable and start service
echo "Enabling and starting antigravity-monitor service..."
sudo systemctl enable --now antigravity-monitor

# 5. Wait for service to start
sleep 3

# 6. Check status
echo "Service status:"
sudo systemctl status antigravity-monitor --no-pager

# 7. Verify HTTP endpoint
echo "Verifying HTTP endpoint (http://localhost:8080)..."
if curl -sf http://localhost:8080 > /dev/null; then
    echo "SUCCESS: Monitor dashboard is responding"
else
    echo "WARNING: Endpoint not responding yet. Check logs: sudo journalctl -u antigravity-monitor -f"
fi

echo "=== Deployment complete ==="