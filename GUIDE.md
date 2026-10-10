# iLO 5 Firefox Auto Power-On — Complete Setup Guide
### For Air-Gapped Ubuntu PCs (No Internet)

---

## What This Does

This script automates the entire iLO 5 server power-on workflow:

1. 🦊 Opens **Firefox** and navigates to your iLO 5 web interface
2. 🔐 **Logs in** with your iLO credentials
3. ⚡ Clicks the **Power On** button
4. 🟢 **Waits** until the yellow power indicator turns **green** (server is ON)
5. 🖥️ Opens the **HTML5 Remote Console** (bottom-left preview area)
6. ⌨️ **Waits** for the OS to boot, then presses Enter and **types your password**
7. 🚪 **Closes** the browser after the boot process completes

Everything runs in the **foreground** — you can watch every step happen on screen.

---

## Prerequisites

| Component | Version | Purpose |
|-----------|---------|---------|
| Ubuntu | 20.04+ (Desktop) | Must have a graphical desktop (GNOME, XFCE, etc.) |
| Firefox | Any recent version | Browser for automation |
| geckodriver | 0.33+ | WebDriver for Firefox |
| Python 3 | 3.8+ | Script runtime |
| selenium | 4.0+ | Python browser automation library |

---

## Step 1: Download Everything on an Internet-Connected PC

On a PC **with internet**, run these commands to download all required files:

### 1a. Download geckodriver

```bash
# Find your geckodriver version at: https://github.com/mozilla/geckodriver/releases
# Download the linux64 version
wget https://github.com/mozilla/geckodriver/releases/download/v0.35.0/geckodriver-v0.35.0-linux64.tar.gz

# Extract it
tar -xzf geckodriver-v0.35.0-linux64.tar.gz
# This gives you a single file: geckodriver
```

### 1b. Download Python selenium wheels

```bash
# Create a directory for wheels
mkdir wheels

# Download selenium and all its dependencies
pip3 download selenium -d ./wheels/
```

### 1c. Download Firefox .deb (if not already installed on the target PC)

```bash
# On a matching Ubuntu version:
mkdir debs
cd debs
apt download firefox
# Or for Firefox ESR:
apt download firefox-esr
cd ..
```

> **Note**: If Firefox is already installed on your air-gapped PC, you can skip this step.

### 1d. Organize the USB drive

Create this folder structure on your USB drive:

```
USB_DRIVE/
├── ilo_poweron/
│   ├── ilo_browser_poweron.py      ← main script
│   ├── install.sh                  ← installer
│   ├── ilo-browser-poweron.service ← systemd service
│   └── packages/
│       ├── geckodriver              ← extracted geckodriver binary
│       ├── wheels/
│       │   ├── selenium-4.x.x-py3-none-any.whl
│       │   ├── urllib3-x.x.x-py3-none-any.whl
│       │   ├── certifi-x.x.x-py3-none-any.whl
│       │   └── ... (other dependency wheels)
│       └── debs/                    ← only if Firefox needs installing
│           └── firefox_xxx.deb
```

---

## Step 2: Transfer to the Air-Gapped PC

1. Plug the USB drive into the air-gapped Ubuntu PC
2. Mount it (usually auto-mounts to `/media/yourusername/USB_NAME/`)
3. Copy the files:

```bash
# Copy to a working directory
cp -r /media/$USER/USB_NAME/ilo_poweron ~/ilo_poweron
cd ~/ilo_poweron
```

---

## Step 3: Configure the Script

Edit the configuration section at the top of the Python script:

```bash
nano ilo_browser_poweron.py
```

Find these lines near the top and set your values:

```python
# ─────────────────────────────────────────────
#  CONFIGURATION — Edit these values
# ─────────────────────────────────────────────
ILO_HOST         = "192.168.1.100"        # ← Your iLO IP address
ILO_USER         = "admin"                # ← Your iLO username
ILO_PASSWORD     = "your_password"        # ← Your iLO password
CONSOLE_PASSWORD = "Console_password"     # ← Password for the OS console

BOOT_WAIT_SECONDS = 120   # ← How long to wait for OS to boot (adjust as needed)
```

### Tuning Tips

| Setting | Default | When to Change |
|---------|---------|---------------|
| `BOOT_WAIT_SECONDS` | 120 | Increase if your server takes long to boot to login screen |
| `POST_PASSWORD_WAIT` | 60 | Increase if the OS takes long to process after password |
| `POWER_ON_TIMEOUT` | 300 | Increase if iLO takes long to show green power indicator |
| `MAX_RETRIES` | 10 | Increase if iLO takes long to become reachable on boot |
| `RETRY_DELAY` | 15 | Seconds between iLO reachability retries |

---

## Step 4: Run the Installer

```bash
cd ~/ilo_poweron
sudo bash install.sh
```

The installer will:
- ✅ Install geckodriver from `./packages/geckodriver`
- ✅ Install selenium from `./packages/wheels/`
- ✅ Install Firefox .deb from `./packages/debs/` (if present)
- ✅ Copy the script to `/opt/ilo_poweron/`
- ✅ Set up the systemd service to run on boot

### What if the installer reports missing packages?

The installer will tell you exactly what's missing and how to get it. Follow the instructions, download what's needed on another PC, and re-run.

---

## Step 5: Test Manually (IMPORTANT!)

Before enabling the auto-boot service, **test the script manually** first:

```bash
sudo python3 /opt/ilo_poweron/ilo_browser_poweron.py
```

You should see:
1. Firefox opens in the foreground
2. The iLO login page loads
3. Credentials are typed in automatically
4. The dashboard loads
5. The Power On button is clicked
6. Logs show polling for the green power indicator
7. Once green, the HTML5 console opens
8. After the boot wait, the password is typed
9. The browser closes

### Watch the terminal output

The script logs every step clearly:

```
╔═══════════════════════════════════════════════════════╗
║   iLO 5 Firefox Auto Power-On + Console Login        ║
║   2025-01-15 08:30:00                                ║
╚═══════════════════════════════════════════════════════╝

Starting Firefox browser (foreground mode) ...
=======================================================
STEP 1: Reaching iLO web interface
=======================================================
  Target: https://192.168.1.100
  ✅  iLO page loaded (attempt 1)

=======================================================
STEP 2: Logging into iLO
=======================================================
  Entered username: admin
  Entered password: ****
  ✅  Clicked: Login button
  ✅  Login submitted — dashboard should be loading.

=======================================================
STEP 3: Powering on the server
=======================================================
  Server is OFF. Clicking power-on button ...
  ✅  Clicked: Power button
  ✅  Power On command sent.

=======================================================
STEP 4: Waiting for power indicator to turn GREEN
=======================================================
  ⏳  Still waiting ... [0m 5s elapsed] (poll #1)
  ⏳  Still waiting ... [0m 10s elapsed] (poll #2)
  ✅  Power indicator is GREEN — server is ON! (after 15s, 3 polls)

=======================================================
STEP 5: Opening HTML5 Remote Console
=======================================================
  Looking for console preview area (bottom-left) ...
  ✅  Clicked: Console preview
  Looking for 'HTML5 Console' option ...
  ✅  HTML5 Console option clicked.

=======================================================
STEP 6: Waiting for server to boot, then typing password
=======================================================
  Waiting 120 seconds for OS to reach login screen ...
  ⏳  90s remaining before typing password ...
  ⏳  60s remaining before typing password ...
  ⏳  30s remaining before typing password ...
  Boot wait complete. Now sending keystrokes to console ...
  Pressing Enter to activate password prompt ...
  Typing console password ...
  Pressing Enter to submit password ...
  ✅  Password sent to console.

=======================================================
STEP 7: Waiting for boot process to complete, then closing
=======================================================
  Waiting 60 seconds for boot to finish ...
  ✅  Boot process should be complete.

╔═══════════════════════════════════════════════════════╗
║   ✅  ALL STEPS COMPLETED SUCCESSFULLY               ║
╚═══════════════════════════════════════════════════════╝
Closing browser ...
Browser closed.
```

---

## Step 6: Enable Auto-Start on Boot

The installer already enabled the systemd service. On next boot, the script runs automatically after the graphical desktop loads.

### Useful systemd commands

```bash
# Check if the service is enabled
sudo systemctl is-enabled ilo-browser-poweron

# Manually start the service (same as running the script)
sudo systemctl start ilo-browser-poweron

# Check service status
sudo systemctl status ilo-browser-poweron

# View live logs
sudo journalctl -u ilo-browser-poweron -f

# Disable auto-start on boot
sudo systemctl disable ilo-browser-poweron

# Re-enable auto-start on boot
sudo systemctl enable ilo-browser-poweron
```

---

## Troubleshooting

### Debug Screenshots

The script saves screenshots at `/tmp/` whenever something goes wrong:

| File | When it's saved |
|------|----------------|
| `/tmp/ilo_login_no_user_field.png` | Username field not found on login page |
| `/tmp/ilo_login_no_pass_field.png` | Password field not found on login page |
| `/tmp/ilo_login_fail.png` | Login failed |
| `/tmp/ilo_power_btn_not_found.png` | Power button not found on dashboard |
| `/tmp/ilo_power_timeout.png` | Server didn't power on within 5 minutes |
| `/tmp/ilo_console_opened.png` | HTML5 console opened (for verification) |
| `/tmp/ilo_console_fail.png` | Could not open HTML5 console |
| `/tmp/ilo_password_fail.png` | Failed to type password |
| `/tmp/ilo_final_state.png` | Final state before closing browser |
| `/tmp/ilo_error.png` | Any unexpected error |

### Log File

Full logs are written to:
```bash
cat /var/log/ilo_browser_poweron.log
```

### Common Issues

| Problem | Solution |
|---------|----------|
| Firefox doesn't open | Make sure you're running on the desktop (not SSH). Check `DISPLAY=:0` is set. |
| "geckodriver not found" | Make sure geckodriver is in `/usr/local/bin/` and executable: `chmod +x /usr/local/bin/geckodriver` |
| iLO certificate error | The script handles this with `accept_insecure_certs = True`. If it still fails, try navigating to the iLO URL manually in Firefox first and accepting the cert. |
| Login fields not found | Your iLO UI may use different element IDs. Check the screenshot, then update the selectors in the script. |
| Power button not found | Check the dashboard screenshot. The power button selector may need updating for your specific iLO 5 firmware version. |
| Console doesn't open | Navigate manually to `https://YOUR_ILO_IP/#/remote_console` — the script tries this as a fallback. |
| Password typed too early | Increase `BOOT_WAIT_SECONDS` in the configuration. |
| Password typed too late | Decrease `BOOT_WAIT_SECONDS`. |
| Service doesn't run on boot | Check `systemctl status ilo-browser-poweron` and `journalctl -u ilo-browser-poweron` for errors. |

### Testing geckodriver manually

```bash
# Verify geckodriver works
geckodriver --version

# Verify selenium can import
python3 -c "from selenium import webdriver; print('OK')"

# Quick test: open Firefox via selenium
python3 -c "
from selenium import webdriver
from selenium.webdriver.firefox.options import Options
opts = Options()
driver = webdriver.Firefox(options=opts)
driver.get('about:blank')
print('Firefox opened successfully!')
driver.quit()
"
```

---

## File Reference

| File | Location | Purpose |
|------|----------|---------|
| `ilo_browser_poweron.py` | `/opt/ilo_poweron/` | Main automation script |
| `ilo-browser-poweron.service` | `/etc/systemd/system/` | Systemd service for auto-start |
| `install.sh` | (your USB/working dir) | One-time installer |
| Log file | `/var/log/ilo_browser_poweron.log` | Runtime logs |
| Screenshots | `/tmp/ilo_*.png` | Debug screenshots |
