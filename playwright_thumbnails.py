#!/usr/bin/env python3

import logging
import time
from argparse import ArgumentParser, RawDescriptionHelpFormatter
from pathlib import Path

from dotenv import load_dotenv
from playwright.sync_api import Playwright, sync_playwright

load_dotenv()


def run(playwright: Playwright, args) -> None:
    input_url = args.input_url
    output_path = args.output_file_path
    headless_mode = args.headless
    auth_session_file = args.auth_session_file
    wait_in_secs_before_capture = args.wait_in_secs_before_capture

    browser = playwright.chromium.launch(headless=headless_mode)
    if auth_session_file and Path.cwd().joinpath(auth_session_file).exists():
        logging.debug(f"Creating new context with authentication session: {auth_session_file}")
        context = browser.new_context(storage_state=auth_session_file)
    else:
        logging.debug("Creating new context")
        context = browser.new_context()

    page = context.new_page()
    page.goto(input_url)

    time.sleep(wait_in_secs_before_capture)

    page.screenshot(path=output_path)
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
    parser.add_argument("-i", "--input-url", type=str, required=True, help="Web Url")
    parser.add_argument("-o", "--output-file-path", type=str, required=True, help="Output file path")
    parser.add_argument("-a", "--auth-session-file", type=str, help="Playwright authentication session")
    parser.add_argument(
        "-s",
        "--headless",
        action="store_true",
        default=False,
        help="Run in headless mode (no browser window)",
    )
    parser.add_argument(
        "-w",
        "--wait-in-secs-before-capture",
        type=int,
        default=2,
        help="Wait (in secs) before capturing screenshot",
    )

    return parser.parse_args()


def main(args):
    with sync_playwright() as playwright:
        run(playwright, args)


if __name__ == "__main__":
    args = parse_args()
    setup_logging(args.verbose)
    main(args)
