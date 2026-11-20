"""Three short smoke tests against the AWS Device Farm Android reference app.

Credentials below are the sample app's built-in synthetic demo values.
"""

from appium.webdriver.common.appiumby import AppiumBy

APP_PACKAGE = "com.amazonaws.devicefarm.android.referenceapp"
NAV_TOGGLE = "ReferenceApp"  # content-desc of the drawer toggle (app title)
LOGIN_MENU_ITEM = "Login Page"
USERNAME_FIELD = "Username Input Field"
PASSWORD_FIELD = "Password Input Field"
LOGIN_BUTTON = "Login Button"
ALT_MESSAGE = "Alt Message"


def _open_menu_item(driver, label: str) -> None:
    driver.find_element(AppiumBy.ACCESSIBILITY_ID, NAV_TOGGLE).click()
    # UiScrollable scrolls the drawer until the item is visible.
    driver.find_element(
        AppiumBy.ANDROID_UIAUTOMATOR,
        "new UiScrollable(new UiSelector().scrollable(true))"
        f'.scrollIntoView(new UiSelector().text("{label}"))',
    ).click()


def test_app_launches(driver, screenshot):
    screenshot("launched")
    assert driver.current_package == APP_PACKAGE
    assert driver.find_element(AppiumBy.ACCESSIBILITY_ID, NAV_TOGGLE).is_displayed()


def test_navigate_to_login_page(driver, screenshot):
    _open_menu_item(driver, LOGIN_MENU_ITEM)
    screenshot("login-page")
    assert driver.find_element(AppiumBy.ACCESSIBILITY_ID, LOGIN_BUTTON).is_displayed()


def test_login_form_shows_result(driver, screenshot):
    _open_menu_item(driver, LOGIN_MENU_ITEM)
    driver.find_element(AppiumBy.ACCESSIBILITY_ID, USERNAME_FIELD).send_keys("admin")
    driver.find_element(AppiumBy.ACCESSIBILITY_ID, PASSWORD_FIELD).send_keys("password")
    screenshot("form-filled")
    driver.find_element(AppiumBy.ACCESSIBILITY_ID, LOGIN_BUTTON).click()
    message = driver.find_element(AppiumBy.ACCESSIBILITY_ID, ALT_MESSAGE).text
    screenshot("result")
    assert message == "You are logged on as admin"
