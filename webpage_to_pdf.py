#!/usr/bin/env python3

import argparse
import asyncio
import logging
import os
import platform
import random
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
    parser.add_argument("-o", "--output-file-path", type=Path, required=True, help="Full output file path for PDF")
    parser.add_argument(
        "-w",
        "--wait-in-secs-before-capture",
        type=int,
        default=5,
        help="Wait (in secs) before capturing screenshot",
    )
    return parser.parse_args()


async def open_site(browser, website_url, output_dir):
    page = await browser.newPage()
    await page._client.send(
        "Page.setDownloadBehavior",
        {"behavior": "allow", "downloadPath": output_dir},
    )
    await page.goto(website_url, {"waitUntil": "networkidle2"})
    await page.emulateMedia("screen")
    return browser, page


def scroll_speed():
    return random.randint(300, 500)


async def scroll_to_end(page):
    current_scroll_position, new_height = 0, 1
    while current_scroll_position <= new_height:
        await page.evaluate(f"""() => {{ window.scrollTo(0, {current_scroll_position}); }} """)
        new_height = await page.evaluate("""() => { return document.body.scrollHeight; } """)
        current_scroll_position += scroll_speed()
        logging.info(f"current_scroll_position: {current_scroll_position}, new_height: {new_height}")
        # Wait to any dynamic elements to load
        time.sleep(2)


async def main():
    args = parse_args()
    website_url = args.input_url
    output_file_path = args.output_file_path
    wait_in_secs_before_capture = args.wait_in_secs_before_capture

    output_dir = output_file_path.parent
    output_dir.mkdir(exist_ok=True)
    launch_config = {
        "headless": True,
        "defaultViewport": None,
    }

    if platform.system().lower() == "linux":
        if Path("/usr/bin/chromium-browser").is_file():
            launch_config["executablePath"] = "/usr/bin/chromium-browser"
        else:
            logging.error("Chromium not found. Please install it and make it available in /usr/bin/chromium-browser")

    browser = await launch(**launch_config)
    logging.info(f"Processing {website_url}")
    try:
        browser, page = await open_site(browser, website_url, output_dir.as_posix())
        # gives us some time to dismiss cookie dialog etc. Also good for throttling requests
        time.sleep(wait_in_secs_before_capture)
        await scroll_to_end(page)
        await page.pdf(
            {
                "margin": {
                    "top": 50,
                    "bottom": 50,
                    "left": 30,
                    "right": 30,
                },
                "path": output_file_path.as_posix(),
                format: "A4",
            }
        )
        await page.close()
        logging.info(f"📸 PDF saved {output_file_path}")
    except Exception:
        logging.exception(f"Error while processing {website_url}")


def setup_logging():
    logging.basicConfig(
        handlers=[logging.StreamHandler()],
        format="%(asctime)s - %(filename)s:%(lineno)d - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        level=logging.INFO,
    )
    logging.captureWarnings(capture=True)


if __name__ == "__main__":
    setup_logging()
    asyncio.get_event_loop().run_until_complete(main())
