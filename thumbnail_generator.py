#!/usr/bin/env python3

import argparse
import asyncio
import os
import time
from pathlib import Path
import logging

from pyppeteer import launch

ENCODE_IN = "utf-8"
ENCODE_OUT = "utf-8"
TEMPLATE_DIR = os.path.dirname(os.path.abspath(__file__))


def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("-i", "--input-url", type=str, required=True, help="Web Url")
    parser.add_argument(
        "-o", "--output-file-path", type=str, required=True, help="Output file path"
    )
    parser.add_argument(
        "-w",
        "--wait-in-secs-before-capture",
        type=int,
        default=5,
        help="Wait (in secs) before capturing screenshot",
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


async def main():
    args = parse_args()
    website_url = args.input_url
    screen_shot_path = Path(args.output_file_path)
    wait_in_secs_before_capture = args.wait_in_secs_before_capture

    screenshots_dir = screen_shot_path.parent
    screenshots_dir.mkdir(exist_ok=True)

    browser = await launch(headless=False, defaultViewport=None)
    print("Processing {}".format(website_url))
    try:
        browser, page = await open_site(
            browser, website_url, screenshots_dir.as_posix()
        )
        # gives us some time to dismiss cookie dialog etc. Also good for throttling requests
        time.sleep(wait_in_secs_before_capture)
        await page.screenshot({"path": screen_shot_path.as_posix()})
        await page.close()
        print(f"📸 Thumbnail saved {screen_shot_path}")
    except Exception as e:
        print("Error processing: {} - {}".format(website_url, str(e)))


if __name__ == "__main__":
    asyncio.get_event_loop().run_until_complete(main())
