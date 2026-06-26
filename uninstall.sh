#!/bin/bash
# ShackDash Uninstall Script
# Removes all ShackDash services, files and configuration

set -e

SHACK_DIR="$HOME/.local/share/shackdash"
SERVICE_DIR="$HOME/.config/systemd/user"
AUTOSTART_DIR="$HOME/.config/autostart"

# Non-interactive flags, used when launched from the tray menu (no terminal
# to prompt in). Manual `bash uninstall.sh` runs interactively as before.
ASSUME_YES=0
DATA_MODE=""  # "keep" or "remove"
for arg in "$@"; do
    case "$arg" in
        -y|--yes)       ASSUME_YES=1 ;;
        --keep-data)    DATA_MODE="keep" ;;
        --remove-data)  DATA_MODE="remove" ;;
    esac
done

echo "╔══════════════════════════════════════╗"
echo "║   ShackDash Uninstaller              ║"
echo "╚══════════════════════════════════════╝"
echo ""
if [ "$ASSUME_YES" -ne 1 ]; then
    echo "⚠️  This will remove all ShackDash files and services."
    read -p "Continue? [y/N] " confirm
    if [[ ! "$confirm" =~ ^[Yy]$ ]]; then
        echo "Aborted."
        exit 0
    fi
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
if [ -z "$DATA_MODE" ]; then
    read -p "Remove $SHACK_DIR and all station data? [y/N] " remove_data
    if [[ "$remove_data" =~ ^[Yy]$ ]]; then
        DATA_MODE="remove"
    else
        DATA_MODE="keep"
    fi
fi

if [ "$DATA_MODE" = "remove" ]; then
    rm -rf "$SHACK_DIR"
    echo "✓ $SHACK_DIR removed"
else
    # Remove only ShackDash program files, keep shack.json and solar.json
    rm -f "$SHACK_DIR/shackdash.py"
    rm -f "$SHACK_DIR/shackdash_server.py"
    rm -f "$SHACK_DIR/shackdash_fetch.py"
    rm -f "$SHACK_DIR/shackdash_setup.py"
    rm -f "$SHACK_DIR/shackdash_widget.html"
    rm -f "$SHACK_DIR/shackdash_icon.png"
    rm -f "$SHACK_DIR/shackdash_icon.svg"
    rm -f "$SHACK_DIR/uninstall.sh"
    echo "✓ ShackDash program files removed (shack.json and solar.json kept)"
fi

echo ""
echo "╔══════════════════════════════════════╗"
echo "║   ShackDash uninstalled              ║"
echo "╚══════════════════════════════════════╝"
