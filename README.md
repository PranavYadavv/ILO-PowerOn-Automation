# iLO 5 Firefox Auto Power-On

Automate an HPE iLO 5 power-on sequence from an Ubuntu desktop, including browser login, power-on, console access, and automatic console password entry.

This project is designed for air-gapped or offline Ubuntu machines where Firefox and geckodriver must be installed from local files rather than downloading from the internet.

## What it does

- Opens Firefox and loads the iLO 5 web interface
- Logs in using the configured iLO credentials
- Clicks the power-on control for the server
- Waits until the server power indicator shows green
- Opens the HTML5 remote console
- Waits for the OS to reach the login screen
- Presses Enter and types the console password
- Closes the browser after the login flow completes

## Files in this project

- `ilo_browser_poweron.py` — main Python automation script
- `install.sh` — offline installer for Firefox, geckodriver, Selenium, and the systemd service
- `ilo-browser-poweron.service` — systemd unit for auto-starting the automation
- `GUIDE.md` — longer step-by-step setup guide

## Requirements

- Ubuntu 20.04+ with a graphical desktop session
- Firefox
- geckodriver
- Python 3.8+
- Selenium

## Supported use case

This is intended for iLO 5 environments where:

- the server is powered off or needs to be brought online remotely
- the management machine is running Ubuntu without internet access
- a local USB drive or transferred package bundle provides the required dependencies

## Quick setup

1. Copy the project folder to the target Ubuntu machine.
2. Edit the configuration at the top of `ilo_browser_poweron.py`:

```python
ILO_HOST         = "192.168.1.100"
ILO_USER         = "admin"
ILO_PASSWORD     = "your_password"
CONSOLE_PASSWORD = "Console_password"
BOOT_WAIT_SECONDS = 120
```

3. Place required local packages in the expected folder layout:

```text
~/ilo_poweron/
├── ilo_browser_poweron.py
├── install.sh
├── ilo-browser-poweron.service
├── packages/
│   ├── geckodriver
│   ├── wheels/
│   │   └── selenium ... .whl
│   └── debs/
│       └── firefox*.deb
```

4. Run the installer:

```bash
cd ~/ilo_poweron
sudo bash install.sh
```

5. Test it manually before enabling the service:

```bash
sudo python3 /opt/ilo_poweron/ilo_browser_poweron.py
```

## Service behavior

The installer installs a systemd service so the script can run automatically when the machine boots.

Useful commands:

```bash
sudo systemctl start ilo-browser-poweron
sudo systemctl status ilo-browser-poweron
sudo journalctl -u ilo-browser-poweron -f
```

## Important notes

- The browser runs in the foreground; it is not headless by default.
- iLO uses a self-signed certificate, and the script is configured to accept insecure certs automatically.
- The script writes logs to `/var/log/ilo_browser_poweron.log` and saves screenshots to `/tmp/ilo_*.png` if an error occurs.
- You should test manually first to verify your exact iLO layout and timing.

## Troubleshooting

### Firefox missing

Install it from a local `.deb` package or copy it from another machine and rerun `install.sh`.

### geckodriver missing

Download the Linux 64-bit release from Mozilla, extract it, and place the binary in `./packages/geckodriver`.

### Selenium missing

Download the Python wheel set from another machine and place them into `./packages/wheels/`.

### Login or power button not found

Adjust the selectors in `ilo_browser_poweron.py` if your iLO firmware layout differs from the expected UI.

## Security warning

This script stores login credentials and console passwords in plain text inside the Python configuration section. Use it only in a trusted environment and keep access to the machine limited.

## License

This project is provided as-is for local automation and infrastructure maintenance tasks.
