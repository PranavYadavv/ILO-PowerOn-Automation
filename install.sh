#!/bin/bash
# ─────────────────────────────────────────────────────────
#  install.sh — Sets up iLO Firefox Auto Power-On service
#  For AIR-GAPPED Ubuntu PCs (no internet required)
#
#  Run as root:  sudo bash install.sh
# ─────────────────────────────────────────────────────────
set -e

SCRIPT_DIR="/opt/ilo_poweron"
SERVICE_FILE="/etc/systemd/system/ilo-browser-poweron.service"
PACKAGES_DIR="./packages"

echo "╔═══════════════════════════════════════════════════════╗"
echo "║   iLO Firefox Auto Power-On — Offline Installer       ║"
echo "╚═══════════════════════════════════════════════════════╝"
echo ""

# ── 1. Install .deb packages from local directory ──────────────────────
if [ -d "$PACKAGES_DIR/debs" ] && ls "$PACKAGES_DIR/debs"/*.deb 1>/dev/null 2>&1; then
    echo "📦  Installing .deb packages from $PACKAGES_DIR/debs/ ..."
    dpkg -i "$PACKAGES_DIR/debs"/*.deb 2>/dev/null || true
    # Fix any dependency issues
    apt-get -f install -y 2>/dev/null || true
    echo "   ✅  .deb packages installed"
else
    echo "⚠️   No .deb packages found in $PACKAGES_DIR/debs/"
    echo "   Checking if Firefox and geckodriver are already installed ..."
fi

echo ""

# ── 2. Check for Firefox ───────────────────────────────────────────────
echo "🌐  Checking for Firefox ..."
if command -v firefox &>/dev/null; then
    FIREFOX_VERSION=$(firefox --version 2>/dev/null || echo "unknown")
    echo "   ✅  Firefox found: $FIREFOX_VERSION"
elif command -v firefox-esr &>/dev/null; then
    FIREFOX_VERSION=$(firefox-esr --version 2>/dev/null || echo "unknown")
    echo "   ✅  Firefox ESR found: $FIREFOX_VERSION"
else
    echo "   ❌  Firefox NOT found!"
    echo ""
    echo "   You need to install Firefox. Download the .deb from another PC:"
    echo "     apt download firefox firefox-esr"
    echo "   Then copy it to $PACKAGES_DIR/debs/ and re-run this script."
    exit 1
fi

echo ""

# ── 3. Check for geckodriver ───────────────────────────────────────────
echo "🔧  Checking for geckodriver ..."
if command -v geckodriver &>/dev/null; then
    GECKO_VERSION=$(geckodriver --version 2>/dev/null | head -1 || echo "unknown")
    echo "   ✅  geckodriver found: $GECKO_VERSION"
elif [ -f "$PACKAGES_DIR/geckodriver" ]; then
    echo "   Installing geckodriver from $PACKAGES_DIR/ ..."
    cp "$PACKAGES_DIR/geckodriver" /usr/local/bin/geckodriver
    chmod +x /usr/local/bin/geckodriver
    echo "   ✅  geckodriver installed to /usr/local/bin/"
else
    echo "   ❌  geckodriver NOT found!"
    echo ""
    echo "   Download geckodriver from another PC:"
    echo "     https://github.com/mozilla/geckodriver/releases"
    echo "   Download the linux64 .tar.gz, extract, and place the"
    echo "   'geckodriver' binary in $PACKAGES_DIR/ then re-run."
    exit 1
fi

echo ""

# ── 4. Install Python selenium ────────────────────────────────────────
echo "🐍  Checking for Python selenium ..."
if python3 -c "import selenium" 2>/dev/null; then
    SELENIUM_VERSION=$(python3 -c "import selenium; print(selenium.__version__)" 2>/dev/null)
    echo "   ✅  selenium found: $SELENIUM_VERSION"
elif [ -d "$PACKAGES_DIR/wheels" ] && ls "$PACKAGES_DIR/wheels"/*.whl 1>/dev/null 2>&1; then
    echo "   Installing selenium from local wheels ..."
    pip3 install --no-index --find-links="$PACKAGES_DIR/wheels" selenium
    echo "   ✅  selenium installed from local wheels"
else
    echo "   ❌  Python selenium NOT found!"
    echo ""
    echo "   Download selenium wheel from another PC:"
    echo "     pip3 download selenium -d ./wheels/"
    echo "   Then copy the ./wheels/ folder to $PACKAGES_DIR/wheels/"
    echo "   and re-run this script."
    exit 1
fi

echo ""

# ── 5. Install the script ─────────────────────────────────────────────
echo "📁  Installing script to $SCRIPT_DIR ..."
mkdir -p "$SCRIPT_DIR"
cp ilo_browser_poweron.py "$SCRIPT_DIR/"
chmod 755 "$SCRIPT_DIR/ilo_browser_poweron.py"
echo "   ✅  Script installed"

# Create log file if it doesn't exist
touch /var/log/ilo_browser_poweron.log
chmod 666 /var/log/ilo_browser_poweron.log

echo ""

# ── 6. Install systemd service ────────────────────────────────────────
echo "⚙️   Installing systemd service ..."

# Auto-detect current logged-in username
CURRENT_USER="${SUDO_USER:-$USER}"
CURRENT_UID=$(id -u "$CURRENT_USER")

# Patch the service file with the real username and UID
sed "s/yourusername/$CURRENT_USER/g; s|/run/user/1000|/run/user/$CURRENT_UID|g" \
    ilo-browser-poweron.service > "$SERVICE_FILE"

chmod 644 "$SERVICE_FILE"

systemctl daemon-reload
systemctl enable ilo-browser-poweron.service

echo "   ✅  Systemd service installed and enabled"

echo ""
echo "╔═══════════════════════════════════════════════════════╗"
echo "║   ✅  Installation complete!                          ║"
echo "╚═══════════════════════════════════════════════════════╝"
echo ""
echo "⚠️   IMPORTANT: Edit the configuration before first run!"
echo "   sudo nano $SCRIPT_DIR/ilo_browser_poweron.py"
echo ""
echo "   Set these values:"
echo "     ILO_HOST         = \"your_ilo_ip\""
echo "     ILO_USER         = \"your_username\""
echo "     ILO_PASSWORD     = \"your_password\""
echo "     CONSOLE_PASSWORD = \"your_console_password\""
echo ""
echo "Useful commands:"
echo "  sudo python3 $SCRIPT_DIR/ilo_browser_poweron.py     # test manually"
echo "  sudo systemctl start ilo-browser-poweron             # run via service"
echo "  sudo systemctl status ilo-browser-poweron            # check status"
echo "  sudo journalctl -u ilo-browser-poweron -f            # live logs"
echo "  cat /var/log/ilo_browser_poweron.log                 # full log file"
echo ""
echo "Debug screenshots saved to /tmp/ on errors:"
echo "  /tmp/ilo_*.png"
echo ""
