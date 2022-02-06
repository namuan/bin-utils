#!/usr/bin/env python3
"""
Setup a Firefox browser session with Selenium.
Prerequisites:
- Download latest version of geckodriver and place it in your PATH (eg. ~/local/bin)
```
https://github.com/mozilla/geckodriver/releases/
```
- Create symlink for firefox profile
```
ln -s "~/Library/Application Support/Firefox/Profiles/65h6sl1r.default-release" $(pwd)/fireprofile
```
"""
import fire
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait


class FirefoxBrowserSession:
    def __init__(self):
        self.session = None

    def start(self, browser_profile=None):
        if browser_profile:
            self.session = webdriver.Firefox(browser_profile)
        else:
            self.session = webdriver.Firefox()

    def stop(self):
        self.session.close()

    def current(self):
        return self.session


session = FirefoxBrowserSession()


def main(browser_profile: str = None):
    session.start(browser_profile)
    current_session = session.current()
    current_session.get("http://www.google.com")

    # find the element and click it
    current_session.find_element(By.XPATH, "//*[text()='I agree']").click()
    query_input = current_session.find_element(By.NAME, "q")
    query_input.send_keys("deskriders")
    query_input.send_keys(Keys.RETURN)

    # wait for an element to present
    wait = WebDriverWait(current_session, 10)
    wait.until(EC.visibility_of_element_located((By.XPATH, "//*[text()='https://www.deskriders.dev']")))

    current_session.find_element(By.XPATH, "//*[text()='https://www.deskriders.dev']").click()
    session.stop()


if __name__ == "__main__":
    fire.Fire(main)
