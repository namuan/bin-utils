"""
Setup a Firefox browser session with Selenium.
Prerequisites:
- Download latest version of geckodriver and place it in your PATH (eg. ~/local/bin)
```
https://github.com/mozilla/geckodriver/releases/
```
- Create symlink for firefox profile
```
ln -s ~/Library/Application\ Support/Firefox/Profiles/65h6sl1r.default-release $(pwd)/fireprofile
```
"""
import fire
from selenium import webdriver


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


def main(browser_profile: str):
    session.start(browser_profile)
    session.current().get("http://www.google.com")
    session.stop()


if __name__ == '__main__':
    fire.Fire(main)
