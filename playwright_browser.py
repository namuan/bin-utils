#!/usr/bin/env python3

import logging
from argparse import ArgumentParser, RawDescriptionHelpFormatter
from pathlib import Path

from dotenv import load_dotenv
from playwright.sync_api import Playwright, sync_playwright

load_dotenv()


def run(playwright: Playwright, args) -> None:
    input_url = args.input_url
    auth_session_file = args.auth_session_file

    browser = playwright.chromium.launch(headless=False)
    if auth_session_file and Path.cwd().joinpath(auth_session_file).exists():
        logging.debug(f"Creating new context with authentication session: {auth_session_file}")
        context = browser.new_context(storage_state=auth_session_file)
    else:
        logging.debug("Creating new context")
        context = browser.new_context()

    page = context.new_page()
    page.goto(input_url)
    page.wait_for_load_state("networkidle")
    page.pause()


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
    parser.add_argument("-a", "--auth-session-file", type=str, help="Playwright authentication session")
    return parser.parse_args()


def main(args):
    with sync_playwright() as playwright:
        run(playwright, args)


if __name__ == "__main__":
    args = parse_args()
    setup_logging(args.verbose)
    main(args)
