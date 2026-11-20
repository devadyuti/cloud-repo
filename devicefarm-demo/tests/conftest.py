"""Appium driver fixture.

On Device Farm the test host injects DEVICEFARM_* env vars and the testspec
starts an Appium server on 127.0.0.1:4723 with default capabilities. Locally,
set APP_PATH (and optionally DEVICE_UDID) and run `appium` yourself.
"""

import os
import time
from pathlib import Path

import pytest
from appium import webdriver
from appium.options.android import UiAutomator2Options
from appium.webdriver.common.appiumby import AppiumBy

APPIUM_URL = os.environ.get("APPIUM_URL", "http://127.0.0.1:4723/wd/hub")
APP_PACKAGE = "com.amazonaws.devicefarm.android.referenceapp"
APP_ACTIVITY = f"{APP_PACKAGE}.Activities.MainActivity"


def _screenshot_dir() -> Path:
    # Files written to DEVICEFARM_SCREENSHOT_PATH show up under "Screenshots"
    # in the Device Farm console. Locally they go to ./screenshots.
    path = Path(os.environ.get("DEVICEFARM_SCREENSHOT_PATH", "screenshots"))
    path.mkdir(parents=True, exist_ok=True)
    return path


def _options() -> UiAutomator2Options:
    opts = UiAutomator2Options()
    opts.platform_name = "Android"
    opts.automation_name = "UiAutomator2"
    opts.app_package = APP_PACKAGE
    opts.app_activity = APP_ACTIVITY
    opts.new_command_timeout = 120
    # targetSdk >= 23 means runtime permission prompts; grant them up front.
    opts.auto_grant_permissions = True

    on_device_farm = "DEVICEFARM_DEVICE_UDID" in os.environ
    if on_device_farm:
        opts.udid = os.environ["DEVICEFARM_DEVICE_UDID"]
        opts.device_name = os.environ.get("DEVICEFARM_DEVICE_NAME", "Android")
        opts.app = os.environ["DEVICEFARM_APP_PATH"]
        if os.environ.get("DEVICEFARM_DEVICE_OS_VERSION"):
            opts.platform_version = os.environ["DEVICEFARM_DEVICE_OS_VERSION"]
    else:
        opts.device_name = os.environ.get("DEVICE_NAME", "Android Emulator")
        if os.environ.get("DEVICE_UDID"):
            opts.udid = os.environ["DEVICE_UDID"]
        if os.environ.get("APP_PATH"):
            opts.app = os.environ["APP_PATH"]
    return opts


def _dismiss_compat_dialog(drv) -> None:
    """Android 14+ shows "This app was built for an older version of Android"
    over the sample app (targetSdk 24). Tap OK if it is there; no-op otherwise."""
    drv.implicitly_wait(0)
    try:
        for _ in range(5):  # dialog can appear a moment after launch
            buttons = drv.find_elements(
                AppiumBy.ANDROID_UIAUTOMATOR,
                'new UiSelector().resourceId("android:id/button1").text("OK")',
            )
            if buttons:
                buttons[0].click()
                return
            time.sleep(1)
    finally:
        drv.implicitly_wait(10)


@pytest.fixture
def driver():
    drv = webdriver.Remote(APPIUM_URL, options=_options())
    _dismiss_compat_dialog(drv)
    drv.implicitly_wait(10)
    yield drv
    drv.quit()


@pytest.fixture
def screenshot(driver, request):
    """Call screenshot("step-name") to capture the current screen."""
    out = _screenshot_dir()

    def _take(step: str) -> Path:
        path = out / f"{request.node.name}-{step}.png"
        driver.get_screenshot_as_file(str(path))
        return path

    return _take
