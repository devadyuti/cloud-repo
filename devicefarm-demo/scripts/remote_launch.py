"""Bring the sample app to the foreground in a running remote access session.

Usage: APPIUM_URL=<remoteDriverEndpoint> python scripts/remote_launch.py
Connects via the session's Appium endpoint, reports whether the app is
installed, launches it, and leaves it open for manual interaction.
"""

import os
import sys

from appium import webdriver
from appium.options.android import UiAutomator2Options

APP_PACKAGE = "com.amazonaws.devicefarm.android.referenceapp"
APP_ACTIVITY = f"{APP_PACKAGE}.Activities.MainActivity"

opts = UiAutomator2Options()
opts.platform_name = "Android"
opts.automation_name = "UiAutomator2"
# No appPackage here: if the app is missing, session creation must still succeed
# so we can report it rather than fail with a launch error.
opts.no_reset = True
opts.new_command_timeout = 300

drv = webdriver.Remote(os.environ["APPIUM_URL"], options=opts)
try:
    installed = drv.is_app_installed(APP_PACKAGE)
    print(f"Installed: {installed}")
    if not installed:
        sys.exit(1)
    drv.execute_script(
        "mobile: startActivity", {"component": f"{APP_PACKAGE}/{APP_ACTIVITY}"}
    )
    print(f"Foreground package: {drv.current_package}")
finally:
    # Ends only the Appium session; the remote access session stays up.
    drv.quit()
