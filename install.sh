#!/bin/bash
# ShackDash Install Script
# Installs ShackDash amateur radio desktop widget on Ubuntu/Debian

set -e

SHACK_DIR="$HOME/shack"
SERVICE_DIR="$HOME/.config/systemd/user"
AUTOSTART_DIR="$HOME/.config/autostart"

echo "╔══════════════════════════════════════╗"
echo "║   ShackDash Installer                ║"
echo "╚══════════════════════════════════════╝"
echo ""

# Must not run as root
if [ "$EUID" -eq 0 ]; then
    echo "❌ Do not run this script as root or with sudo."
    echo "   Run as your normal user: bash install.sh"
    exit 1
fi

# Check DBus session is available for systemd --user
if [ -z "$DBUS_SESSION_BUS_ADDRESS" ] && [ -z "$XDG_RUNTIME_DIR" ]; then
    echo "❌ No user session bus detected."
    echo "   Please run this script from a desktop terminal, not an SSH session."
    echo "   If using SSH, try: export XDG_RUNTIME_DIR=/run/user/\$(id -u)"
    exit 1
fi

# Check OS
if ! command -v apt-get &> /dev/null; then
    echo "⚠️  Warning: This installer is designed for Ubuntu/Debian."
    echo "   You may need to install dependencies manually."
fi

# Install dependencies
echo "→ Installing dependencies..."
sudo apt-get install -y \
    python3 \
    python3-gi \
    gir1.2-gtk-3.0 \
    gir1.2-webkit2-4.1 \
    gir1.2-appindicator3-0.1 \
    libayatana-appindicator3-1 2>/dev/null || \
sudo apt-get install -y \
    python3 \
    python3-gi \
    gir1.2-gtk-3.0 \
    gir1.2-webkit2-4.0 \
    gir1.2-appindicator3-0.1
echo "✓ Dependencies installed"

# Create shack directory
echo "→ Creating $SHACK_DIR..."
mkdir -p "$SHACK_DIR"

# Copy files
echo "→ Copying ShackDash files..."
cp shackdash.py "$SHACK_DIR/"
cp shackdash_server.py "$SHACK_DIR/"
cp shackdash_fetch.py "$SHACK_DIR/"
cp shackdash_setup.py "$SHACK_DIR/"
cp shackdash_widget.html "$SHACK_DIR/"
cp shackdash_icon.png "$SHACK_DIR/"
cp shackdash_icon.svg "$SHACK_DIR/"

# Preserve existing config if present
if [ -f "$SHACK_DIR/shack.json" ]; then
    echo "✓ Existing shack.json preserved"
else
    echo "✓ No shack.json found — Setup Wizard will run on first launch"
fi
echo "✓ Files copied to $SHACK_DIR"

# Install systemd service
echo "→ Installing systemd service..."
mkdir -p "$SERVICE_DIR"
sed "s|%h|$HOME|g" shackdash-server.service > "$SERVICE_DIR/shackdash-server.service"
systemctl --user daemon-reload
systemctl --user enable shackdash-server.service
systemctl --user start shackdash-server.service
echo "✓ ShackDash server service installed and started"

# Install cron job for solar data refresh
echo "→ Setting up solar data refresh (every 3 hours)..."
(crontab -l 2>/dev/null | grep -v shackdash_fetch; \
 echo "0 */3 * * * /usr/bin/python3 $SHACK_DIR/shackdash_fetch.py") | crontab -
echo "✓ Cron job installed"

# Autostart
echo "→ Setting up autostart..."
mkdir -p "$AUTOSTART_DIR"
cat > "$AUTOSTART_DIR/shackdash.desktop" << DESKTOP
[Desktop Entry]
Type=Application
Name=ShackDash
Exec=python3 $SHACK_DIR/shackdash.py
Icon=$SHACK_DIR/shackdash_icon.png
Comment=Amateur Radio Station Widget
X-GNOME-Autostart-enabled=true
DESKTOP
echo "✓ Autostart entry created"

echo ""
echo "╔══════════════════════════════════════╗"
echo "║   Installation complete! 🎙️          ║"
echo "╚══════════════════════════════════════╝"
echo ""
echo "Run ShackDash now with:"
echo "  python3 ~/shack/shackdash.py"
echo ""
echo "On first launch, the Setup Wizard will guide you"
echo "through entering your callsign and location details."
