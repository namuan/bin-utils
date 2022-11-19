#!/usr/bin/env python3

import logging
import os
from argparse import ArgumentParser, RawDescriptionHelpFormatter

from dotenv import load_dotenv
from playwright.sync_api import Playwright, sync_playwright

load_dotenv()

TWITTER_USER_NAME = os.getenv("TWITTER_USER_NAME")
TWITTER_USER_PASSWORD = os.getenv("TWITTER_USER_PASSWORD")


def run(playwright: Playwright, headless_mode) -> None:
    browser = playwright.chromium.launch(headless=headless_mode)
    context = browser.new_context()

    page = context.new_page()
    page.goto("https://twitter.com/")
    page.get_by_role("button", name="Accept all cookies").click()

    page.get_by_test_id("login").click()
    page.wait_for_url("https://twitter.com/i/flow/login")
    page.get_by_label("Phone, email address, or username").click()
    page.get_by_label("Phone, email address, or username").fill(TWITTER_USER_NAME)

    page.get_by_role("button", name="Next").click()
    page.get_by_label("Password").click()
    page.get_by_label("Password").fill(TWITTER_USER_PASSWORD)

    page.get_by_test_id("LoginForm_Login_Button").click()
    page.wait_for_url("https://twitter.com/home")

    try:
        page.get_by_role("button", name="Skip for now").click()
    except Exception:
        print("Didn't get the option to skip notifications")

    context.close()
    browser.close()


def setup_logging(verbosity):
    logging_level = logging.WARNING
    if verbosity == 1:
        logging_level = logging.INFO
    elif verbosity >= 2:
        logging_level = logging.DEBUG

    logging.basicConfig(
        handlers=[
            logging.StreamHandler(),
        ],
        format="%(asctime)s - %(filename)s:%(lineno)d - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        level=logging_level,
    )
    logging.captureWarnings(capture=True)


def parse_args():
    parser = ArgumentParser(description=__doc__, formatter_class=RawDescriptionHelpFormatter)
    parser.add_argument(
        "-v",
        "--verbose",
        action="count",
        default=0,
        dest="verbose",
        help="Increase verbosity of logging output",
    )
    parser.add_argument(
        "-i",
        "--invisible",
        action="store_true",
        default=False,
        help="Run session in headless mode",
    )
    return parser.parse_args()


def main(args):
    with sync_playwright() as playwright:
        run(playwright, args.invisible)


if __name__ == "__main__":
    args = parse_args()
    setup_logging(args.verbose)
    main(args)
