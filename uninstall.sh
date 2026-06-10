#!/bin/bash
# ShackDash Uninstall Script
# Removes all ShackDash services, files and configuration

set -e

SHACK_DIR="$HOME/shack"
SERVICE_DIR="$HOME/.config/systemd/user"
AUTOSTART_DIR="$HOME/.config/autostart"

echo "╔══════════════════════════════════════╗"
echo "║   ShackDash Uninstaller              ║"
echo "╚══════════════════════════════════════╝"
echo ""
echo "⚠️  This will remove all ShackDash files and services."
read -p "Continue? [y/N] " confirm
if [[ ! "$confirm" =~ ^[Yy]$ ]]; then
    echo "Aborted."
    exit 0
fi

# Stop and disable systemd service
echo "→ Stopping ShackDash server service..."
systemctl --user stop shackdash-server.service 2>/dev/null && echo "✓ Service stopped" || echo "  (service not running)"
systemctl --user disable shackdash-server.service 2>/dev/null && echo "✓ Service disabled" || echo "  (service not enabled)"
rm -f "$SERVICE_DIR/shackdash-server.service"
systemctl --user daemon-reload
echo "✓ Service removed"

# Remove cron job
echo "→ Removing cron job..."
crontab -l 2>/dev/null | grep -v shackdash_fetch | crontab - 2>/dev/null
echo "✓ Cron job removed"

# Remove autostart entry
echo "→ Removing autostart entry..."
rm -f "$AUTOSTART_DIR/shackdash.desktop"
echo "✓ Autostart removed"

# Ask about shack directory
echo ""
read -p "Remove ~/shack/ directory and all station data? [y/N] " remove_data
if [[ "$remove_data" =~ ^[Yy]$ ]]; then
    rm -rf "$SHACK_DIR"
    echo "✓ ~/shack/ removed"
else
    # Remove only ShackDash program files, keep shack.json and solar.json
    rm -f "$SHACK_DIR/shackdash.py"
    rm -f "$SHACK_DIR/shackdash_server.py"
    rm -f "$SHACK_DIR/shackdash_fetch.py"
    rm -f "$SHACK_DIR/shackdash_setup.py"
    rm -f "$SHACK_DIR/shackdash_widget.html"
    rm -f "$SHACK_DIR/shackdash_icon.png"
    rm -f "$SHACK_DIR/shackdash_icon.svg"
    echo "✓ ShackDash program files removed (shack.json and solar.json kept)"
fi

echo ""
echo "╔══════════════════════════════════════╗"
echo "║   ShackDash uninstalled              ║"
echo "╚══════════════════════════════════════╝"
