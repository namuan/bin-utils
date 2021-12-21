#!/usr/bin/env python

import argparse
import asyncio
import os
import time
from pathlib import Path

from pyppeteer import launch

ENCODE_IN = "utf-8"
ENCODE_OUT = "utf-8"
TEMPLATE_DIR = os.path.dirname(os.path.abspath(__file__))


def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("-i", "--input-url", type=str, required=True, help="Web Url")
    parser.add_argument(
        "-t", "--target-dir", type=str, required=True, help="Target directory"
    )
    parser.add_argument(
        "-o", "--output-file-name", type=str, required=True, help="Output file name"
    )
    return parser.parse_args()


async def open_site(browser, website_url, screenshot_dir):
    page = await browser.newPage()
    await page._client.send(
        "Page.setDownloadBehavior",
        {"behavior": "allow", "downloadPath": screenshot_dir},
    )
    await page.goto(website_url)
    return browser, page


def is_github_page(website_url):
    return "github" in website_url


github_signup_dismissed = False


async def dismiss_signup(page):
    global github_signup_dismissed
    selector = "signup-prompt > div > div > button"
    dismiss_button = await page.querySelector(selector)
    await dismiss_button.click()
    github_signup_dismissed = True


async def main():
    args = parse_args()
    website_url = args.input_url
    target_dir = args.target_dir
    output_file_name = args.output_file_name

    screenshots_dir = Path(target_dir)
    screenshots_dir.mkdir(exist_ok=True)
    browser = await launch(headless=False, defaultViewport=None)
    screen_shot_path = screenshots_dir.joinpath(output_file_name)

    if not screen_shot_path.exists():
        print("Processing {}".format(website_url))
        try:
            browser, page = await open_site(
                browser, website_url, screenshots_dir.as_posix()
            )
            if not github_signup_dismissed and is_github_page(website_url):
                await dismiss_signup(page)
            time.sleep(
                5
            )  # gives us some time to dismiss cookie dialog etc. Also good for throttling requests
            await page.screenshot({"path": screen_shot_path.as_posix()})
            await page.close()
            print(f"📸 Thumbnail saved {screen_shot_path}")
        except Exception as e:
            print("Error processing: {} - {}".format(website_url, str(e)))


if __name__ == "__main__":
    asyncio.get_event_loop().run_until_complete(main())
