#!/usr/bin/env python3
"""
iLO 5 Firefox Auto Power-On + Console Login
=============================================
Opens Firefox, logs into iLO 5, powers on the server, waits for the
power indicator to turn green, opens the HTML5 console, waits for boot,
types the console password, and closes the browser.

Designed for air-gapped Ubuntu PCs with no internet.
All steps run in the FOREGROUND so you can watch them happen.
"""

import time
import sys
import logging
from datetime import datetime

from selenium import webdriver
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.firefox.service import Service as GeckoService
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import (
    TimeoutException, NoSuchElementException, WebDriverException,
    StaleElementReferenceException,
)

# ─────────────────────────────────────────────
#  CONFIGURATION — Edit these values
# ─────────────────────────────────────────────
ILO_HOST         = "ILO_IP_PLACEHOLDER"       # iLO IP address or hostname
ILO_USER         = "admin"                     # iLO login username
ILO_PASSWORD     = "your_password"             # iLO login password
CONSOLE_PASSWORD = "Console_password"          # Password to type in the HTML5 console

# How long (seconds) to wait for page elements before giving up
PAGE_TIMEOUT     = 30

# How many times to retry reaching iLO if network isn't up yet
MAX_RETRIES      = 10
RETRY_DELAY      = 15   # seconds between retries

# How long (seconds) to wait after server is ON for OS to boot to login screen
BOOT_WAIT_SECONDS = 120

# How long (seconds) to poll for power indicator to turn green
POWER_ON_TIMEOUT  = 300   # 5 minutes

# Poll interval for power status checks (seconds)
POWER_POLL_INTERVAL = 5

# How long (seconds) to wait after typing password for the boot process to finish
POST_PASSWORD_WAIT = 60

# Path to geckodriver — leave empty "" to auto-detect from PATH
GECKODRIVER_PATH = ""
# ─────────────────────────────────────────────

ILO_URL = f"https://{ILO_HOST}"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[
        logging.FileHandler("/var/log/ilo_browser_poweron.log"),
        logging.StreamHandler(sys.stdout),
    ],
)
log = logging.getLogger(__name__)


# ── Selector maps for iLO 5 ──────────────────────────────────────────────────

LOGIN_USER_SELECTORS = [
    (By.ID,    "username"),
    (By.ID,    "login_name"),
    (By.NAME,  "username"),
    (By.NAME,  "login_name"),
    (By.CSS_SELECTOR, "input[type='text']"),
]

LOGIN_PASS_SELECTORS = [
    (By.ID,    "password"),
    (By.NAME,  "password"),
    (By.CSS_SELECTOR, "input[type='password']"),
]

LOGIN_BTN_SELECTORS = [
    (By.ID,    "btn_login"),
    (By.ID,    "login-form-submit"),
    (By.CSS_SELECTOR, "button[type='submit']"),
    (By.CSS_SELECTOR, "input[type='submit']"),
    (By.XPATH, "//button[contains(translate(text(),'LOGIN','login'),'log')]"),
]

# Power button / power switch selectors for iLO 5
POWER_BTN_SELECTORS = [
    (By.XPATH, "//*[contains(@id,'power') and (contains(@id,'btn') or contains(@id,'Btn') or contains(@id,'button') or contains(@id,'Button'))]"),
    (By.XPATH, "//*[@id='btnPowerSwitch']"),
    (By.XPATH, "//*[@id='power-button']"),
    (By.XPATH, "//*[@id='powerButton']"),
    (By.XPATH, "//button[contains(translate(text(),'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'),'power on')]"),
    (By.XPATH, "//*[contains(translate(@title,'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'),'power on')]"),
    # Momentary press option in power dropdown
    (By.XPATH, "//*[contains(translate(text(),'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'),'momentary press')]"),
]

# Confirm dialog selectors (iLO may ask "Are you sure?")
CONFIRM_BTN_SELECTORS = [
    (By.XPATH, "//button[contains(translate(text(),'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'),'ok')]"),
    (By.XPATH, "//button[contains(translate(text(),'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'),'yes')]"),
    (By.XPATH, "//button[contains(translate(text(),'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'),'confirm')]"),
    (By.ID,    "btnOK"),
    (By.ID,    "confirmBtn"),
]

# Power status indicators — text that means the server is ON
POWER_ON_INDICATORS = [
    "server power: on",
    "power state: on",
    "server is on",
    "powered on",
    "power: on",
]

# Power status indicators — text that means the server is OFF
POWER_OFF_INDICATORS = [
    "server power: off",
    "power state: off",
    "server is off",
    "powered off",
    "power: off",
]

# HTML5 console link/button selectors (bottom-left area in iLO 5)
CONSOLE_PREVIEW_SELECTORS = [
    # The small console preview thumbnail / link at the bottom-left
    (By.XPATH, "//*[contains(@id,'console') or contains(@id,'Console')]//canvas"),
    (By.XPATH, "//*[contains(@class,'console-preview')]"),
    (By.XPATH, "//*[contains(@class,'remote-console')]"),
    (By.XPATH, "//a[contains(translate(text(),'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'),'console')]"),
    (By.XPATH, "//*[contains(@id,'consolePreview')]"),
    (By.XPATH, "//*[contains(@id,'remote-console')]"),
    (By.XPATH, "//div[contains(@class,'thumbnail')]//canvas"),
    (By.XPATH, "//canvas"),
]

# HTML5 Console option in the dropdown/menu
HTML5_CONSOLE_SELECTORS = [
    (By.XPATH, "//*[contains(translate(text(),'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'),'html5 console')]"),
    (By.XPATH, "//*[contains(translate(text(),'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'),'html5')]"),
    (By.XPATH, "//a[contains(translate(@href,'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'),'html5')]"),
    (By.XPATH, "//*[contains(@id,'html5') or contains(@id,'HTML5')]"),
    (By.XPATH, "//a[contains(translate(text(),'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'),'integrated remote console')]"),
]


def make_driver() -> webdriver.Firefox:
    """Create a Firefox WebDriver instance (visible, foreground)."""
    opts = Options()
    # Accept iLO self-signed certificates automatically
    opts.accept_insecure_certs = True
    # Do NOT run headless — user wants to see everything
    # opts.add_argument("--headless")
    opts.set_preference("security.tls.insecure_fallback_hosts", ILO_HOST)

    if GECKODRIVER_PATH:
        service = GeckoService(executable_path=GECKODRIVER_PATH)
    else:
        service = GeckoService()   # auto-detect from PATH

    driver = webdriver.Firefox(service=service, options=opts)
    driver.set_page_load_timeout(PAGE_TIMEOUT)
    driver.maximize_window()
    return driver


def find_element(driver, selectors, timeout=PAGE_TIMEOUT):
    """Try multiple selectors in order, return first visible match."""
    for by, value in selectors:
        try:
            wait = WebDriverWait(driver, min(timeout, 5),
                                 ignored_exceptions=[StaleElementReferenceException])
            el = wait.until(EC.presence_of_element_located((by, value)))
            if el.is_displayed():
                log.debug(f"  Found element: ({by}, {value})")
                return el
        except (TimeoutException, NoSuchElementException):
            continue
    return None


def click_element(driver, selectors, label="element", timeout=PAGE_TIMEOUT):
    """Find and click an element using multiple selector strategies."""
    el = find_element(driver, selectors, timeout)
    if el:
        driver.execute_script("arguments[0].scrollIntoView(true);", el)
        time.sleep(0.3)
        try:
            el.click()
        except Exception:
            driver.execute_script("arguments[0].click();", el)
        log.info(f"  ✅  Clicked: {label}")
        return True
    log.warning(f"  ⚠️  Could not find: {label}")
    return False


def save_screenshot(driver, name):
    """Save a debug screenshot to /tmp/."""
    path = f"/tmp/ilo_{name}.png"
    try:
        driver.save_screenshot(path)
        log.info(f"  📸  Screenshot saved: {path}")
    except Exception as e:
        log.warning(f"  Could not save screenshot: {e}")


# ── STEP 1: Reach iLO ─────────────────────────────────────────────────────────

def wait_for_ilo(driver) -> bool:
    """Retry opening the iLO URL until it loads."""
    log.info("=" * 55)
    log.info("STEP 1: Reaching iLO web interface")
    log.info("=" * 55)
    log.info(f"  Target: {ILO_URL}")

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            driver.get(ILO_URL)
            log.info(f"  ✅  iLO page loaded (attempt {attempt})")
            return True
        except WebDriverException as e:
            msg = str(e)[:80] if hasattr(e, 'msg') else str(e)[:80]
            log.warning(f"  Attempt {attempt}/{MAX_RETRIES} failed: {msg}")
            if attempt < MAX_RETRIES:
                log.info(f"  Waiting {RETRY_DELAY}s before retrying ...")
                time.sleep(RETRY_DELAY)
    return False


# ── STEP 2: Login ─────────────────────────────────────────────────────────────

def login(driver) -> bool:
    """Fill in iLO login credentials and submit."""
    log.info("")
    log.info("=" * 55)
    log.info("STEP 2: Logging into iLO")
    log.info("=" * 55)

    time.sleep(3)  # let the login page fully render

    user_field = find_element(driver, LOGIN_USER_SELECTORS)
    if not user_field:
        log.error("  ❌  Could not find username field.")
        save_screenshot(driver, "login_no_user_field")
        return False
    user_field.clear()
    user_field.send_keys(ILO_USER)
    log.info(f"  Entered username: {ILO_USER}")

    pass_field = find_element(driver, LOGIN_PASS_SELECTORS)
    if not pass_field:
        log.error("  ❌  Could not find password field.")
        save_screenshot(driver, "login_no_pass_field")
        return False
    pass_field.clear()
    pass_field.send_keys(ILO_PASSWORD)
    log.info("  Entered password: ****")

    if not click_element(driver, LOGIN_BTN_SELECTORS, "Login button"):
        # Fallback: submit via Enter key
        pass_field.submit()
        log.info("  Submitted login form via Enter key.")

    time.sleep(5)  # wait for dashboard to load
    log.info("  ✅  Login submitted — dashboard should be loading.")
    return True


# ── STEP 3: Power On ─────────────────────────────────────────────────────────

def get_page_text(driver) -> str:
    """Get all visible text on the page (lowercase)."""
    try:
        return driver.find_element(By.TAG_NAME, "body").text.lower()
    except Exception:
        return ""


def is_server_on(driver) -> bool:
    """Check if the server is currently powered on."""
    text = get_page_text(driver)
    return any(indicator in text for indicator in POWER_ON_INDICATORS)


def is_server_off(driver) -> bool:
    """Check if the server is currently powered off."""
    text = get_page_text(driver)
    return any(indicator in text for indicator in POWER_OFF_INDICATORS)


def power_on(driver) -> bool:
    """Click the power-on button and handle confirmation."""
    log.info("")
    log.info("=" * 55)
    log.info("STEP 3: Powering on the server")
    log.info("=" * 55)

    if is_server_on(driver):
        log.info("  ✅  Server is ALREADY powered on — skipping power-on.")
        return True

    log.info("  Server is OFF. Clicking power-on button ...")

    if not click_element(driver, POWER_BTN_SELECTORS, "Power button"):
        log.error("  ❌  Power button not found.")
        log.info(f"  Current URL: {driver.current_url}")
        save_screenshot(driver, "power_btn_not_found")
        return False

    time.sleep(2)

    # Handle confirmation dialog if it appears
    confirm = find_element(driver, CONFIRM_BTN_SELECTORS, timeout=5)
    if confirm:
        log.info("  Confirmation dialog detected — clicking OK ...")
        try:
            confirm.click()
        except Exception:
            driver.execute_script("arguments[0].click();", confirm)
        log.info("  ✅  Confirmed power-on.")

    time.sleep(1)
    log.info("  ✅  Power On command sent.")
    return True


# ── STEP 4: Wait for green indicator ─────────────────────────────────────────

def wait_for_power_on(driver) -> bool:
    """Poll the iLO dashboard until the power indicator turns green (ON)."""
    log.info("")
    log.info("=" * 55)
    log.info("STEP 4: Waiting for power indicator to turn GREEN")
    log.info("=" * 55)

    if is_server_on(driver):
        log.info("  ✅  Server is already ON (green).")
        return True

    start = time.time()
    elapsed = 0
    poll_count = 0

    while elapsed < POWER_ON_TIMEOUT:
        poll_count += 1
        time.sleep(POWER_POLL_INTERVAL)
        elapsed = time.time() - start

        # Refresh the page to get updated status
        try:
            driver.refresh()
            time.sleep(3)  # let page re-render
        except Exception:
            pass

        if is_server_on(driver):
            log.info(f"  ✅  Power indicator is GREEN — server is ON! "
                     f"(after {int(elapsed)}s, {poll_count} polls)")
            return True

        minutes = int(elapsed) // 60
        seconds = int(elapsed) % 60
        log.info(f"  ⏳  Still waiting ... [{minutes}m {seconds}s elapsed] "
                 f"(poll #{poll_count})")

    log.error(f"  ❌  Timed out after {POWER_ON_TIMEOUT}s — server power "
              f"indicator did not turn green.")
    save_screenshot(driver, "power_timeout")
    return False


# ── STEP 5: Open HTML5 Console ────────────────────────────────────────────────

def open_html5_console(driver) -> bool:
    """Click the console preview (bottom-left), then select HTML5 Console."""
    log.info("")
    log.info("=" * 55)
    log.info("STEP 5: Opening HTML5 Remote Console")
    log.info("=" * 55)

    # Step 5a: Click the console preview area (bottom-left)
    log.info("  Looking for console preview area (bottom-left) ...")
    if not click_element(driver, CONSOLE_PREVIEW_SELECTORS, "Console preview", timeout=15):
        log.warning("  Could not find console preview. Trying Remote Console menu ...")
        # Fallback: try navigating to the Remote Console page directly
        try:
            driver.get(f"{ILO_URL}/#/remote_console")
            time.sleep(3)
        except Exception:
            pass

    time.sleep(2)

    # Step 5b: Click "HTML5 Console" option
    log.info("  Looking for 'HTML5 Console' option ...")
    if click_element(driver, HTML5_CONSOLE_SELECTORS, "HTML5 Console", timeout=15):
        log.info("  ✅  HTML5 Console option clicked.")
    else:
        log.warning("  Could not find HTML5 Console link directly.")
        # Try navigating to it
        try:
            driver.get(f"{ILO_URL}/html5_console.html")
            time.sleep(3)
        except Exception:
            pass
        log.info("  Attempted direct navigation to HTML5 console.")

    time.sleep(5)

    # Check if a new window/tab opened
    windows = driver.window_handles
    if len(windows) > 1:
        driver.switch_to.window(windows[-1])
        log.info(f"  Switched to new console window (total windows: {len(windows)})")
    else:
        log.info("  Console opened in the same window.")

    log.info("  ✅  HTML5 Console should be open.")
    save_screenshot(driver, "console_opened")
    return True


# ── STEP 6: Wait for boot and type password ───────────────────────────────────

def type_console_password(driver) -> bool:
    """Wait for the server to boot, then type the console password."""
    log.info("")
    log.info("=" * 55)
    log.info("STEP 6: Waiting for server to boot, then typing password")
    log.info("=" * 55)
    log.info(f"  Waiting {BOOT_WAIT_SECONDS} seconds for OS to reach login screen ...")

    # Countdown with periodic log messages
    waited = 0
    while waited < BOOT_WAIT_SECONDS:
        chunk = min(10, BOOT_WAIT_SECONDS - waited)
        time.sleep(chunk)
        waited += chunk
        remaining = BOOT_WAIT_SECONDS - waited
        if remaining > 0 and waited % 30 == 0:
            log.info(f"  ⏳  {remaining}s remaining before typing password ...")

    log.info("  Boot wait complete. Now sending keystrokes to console ...")

    # Find the console canvas element to send keystrokes to
    canvas = None
    canvas_selectors = [
        (By.TAG_NAME, "canvas"),
        (By.CSS_SELECTOR, "canvas"),
        (By.XPATH, "//canvas"),
    ]

    for by, value in canvas_selectors:
        try:
            elements = driver.find_elements(by, value)
            if elements:
                canvas = elements[0]
                log.info(f"  Found canvas element for keystroke input.")
                break
        except Exception:
            continue

    if not canvas:
        log.warning("  No canvas element found — sending keys to body instead.")
        canvas = driver.find_element(By.TAG_NAME, "body")

    # Click on the canvas to make sure it has focus
    try:
        canvas.click()
        time.sleep(1)
    except Exception:
        try:
            driver.execute_script("arguments[0].click();", canvas)
            time.sleep(1)
        except Exception:
            log.warning("  Could not click canvas — proceeding anyway.")

    actions = ActionChains(driver)

    # Press Enter first (user mentioned this is needed)
    log.info("  Pressing Enter to activate password prompt ...")
    actions.send_keys(Keys.RETURN)
    actions.perform()
    time.sleep(3)

    # Type the console password
    log.info("  Typing console password ...")
    actions = ActionChains(driver)
    actions.send_keys(CONSOLE_PASSWORD)
    actions.perform()
    time.sleep(1)

    # Press Enter to submit
    log.info("  Pressing Enter to submit password ...")
    actions = ActionChains(driver)
    actions.send_keys(Keys.RETURN)
    actions.perform()

    log.info("  ✅  Password sent to console.")
    return True


# ── STEP 7: Wait and close ────────────────────────────────────────────────────

def wait_and_close(driver):
    """Wait for the boot process to finish, then close the browser."""
    log.info("")
    log.info("=" * 55)
    log.info("STEP 7: Waiting for boot process to complete, then closing")
    log.info("=" * 55)
    log.info(f"  Waiting {POST_PASSWORD_WAIT} seconds for boot to finish ...")

    waited = 0
    while waited < POST_PASSWORD_WAIT:
        chunk = min(10, POST_PASSWORD_WAIT - waited)
        time.sleep(chunk)
        waited += chunk
        remaining = POST_PASSWORD_WAIT - waited
        if remaining > 0 and waited % 30 == 0:
            log.info(f"  ⏳  {remaining}s remaining ...")

    save_screenshot(driver, "final_state")
    log.info("  ✅  Boot process should be complete.")


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    log.info("")
    log.info("╔═══════════════════════════════════════════════════════╗")
    log.info("║   iLO 5 Firefox Auto Power-On + Console Login        ║")
    log.info("║   " + datetime.now().strftime("%Y-%m-%d %H:%M:%S") + "                                  ║")
    log.info("╚═══════════════════════════════════════════════════════╝")
    log.info("")

    driver = None
    try:
        log.info("Starting Firefox browser (foreground mode) ...")
        driver = make_driver()

        # Step 1: Reach iLO
        if not wait_for_ilo(driver):
            log.error("❌  iLO never became reachable. Giving up.")
            sys.exit(1)

        time.sleep(2)

        # Step 2: Login
        if not login(driver):
            log.error("❌  Login failed.")
            save_screenshot(driver, "login_fail")
            sys.exit(1)

        # Step 3: Power On
        if not power_on(driver):
            log.error("❌  Power-on failed.")
            sys.exit(1)

        # Step 4: Wait for green indicator
        if not wait_for_power_on(driver):
            log.error("❌  Server did not power on within timeout.")
            sys.exit(1)

        # Step 5: Open HTML5 Console
        if not open_html5_console(driver):
            log.error("❌  Could not open HTML5 Console.")
            save_screenshot(driver, "console_fail")
            sys.exit(1)

        # Step 6: Wait for boot + type password
        if not type_console_password(driver):
            log.error("❌  Failed to type console password.")
            save_screenshot(driver, "password_fail")
            sys.exit(1)

        # Step 7: Wait and close
        wait_and_close(driver)

        log.info("")
        log.info("╔═══════════════════════════════════════════════════════╗")
        log.info("║   ✅  ALL STEPS COMPLETED SUCCESSFULLY               ║")
        log.info("╚═══════════════════════════════════════════════════════╝")
        sys.exit(0)

    except Exception as e:
        log.exception(f"Unexpected error: {e}")
        if driver:
            save_screenshot(driver, "error")
        sys.exit(1)

    finally:
        if driver:
            log.info("Closing browser ...")
            driver.quit()
            log.info("Browser closed.")


if __name__ == "__main__":
    main()
