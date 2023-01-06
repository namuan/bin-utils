#!/usr/bin/env python3

import logging
import os
import random
import time
from argparse import ArgumentParser, RawDescriptionHelpFormatter
from pathlib import Path

from dotenv import load_dotenv
from playwright.sync_api import Playwright
from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
from playwright.sync_api import sync_playwright
from slug import slug

load_dotenv()


def scroll_speed():
    return random.randint(300, 500)


def scroll_to_end(page):
    current_scroll_position, new_height = 0, 1
    while current_scroll_position <= new_height:
        page.evaluate(f"""() => {{ window.scrollTo(0, {current_scroll_position}); }} """)
        new_height = page.evaluate("""() => { return document.body.scrollHeight; } """)
        current_scroll_position += scroll_speed()
        logging.info(f"current_scroll_position: {current_scroll_position}, new_height: {new_height}")
        time.sleep(2)


def urls_to_fetch(input_url: str, input_file: Path) -> list[str]:
    if not input_url and not input_file:
        logging.error("No input URL or file provided")
        raise ValueError("No input URL or file provided")
    urls_from_file = input_file.read_text().splitlines() if input_file else []
    urls_from_file.append(input_url) if input_url else None
    return urls_from_file


def click_on_element(page_action):
    try:
        el = page_action()
        if el:
            el.click(timeout=5000)
    except PlaywrightTimeoutError as e:
        logging.debug(e)


def generate_output_file_name(output_dir, url):
    url_as_path = Path(url)
    return output_dir.joinpath(f"{slug(f'{url_as_path.parent.name}-{url_as_path.stem}')}.pdf")


def run(playwright: Playwright, args) -> None:
    auth_session_file = args.auth_session_file
    convert_to_pdf = args.convert_to_pdf
    input_url = args.input_url
    input_file = args.input_file

    urls_from_file = urls_to_fetch(input_url, input_file)

    browser = playwright.chromium.launch(headless=False)
    for url in urls_from_file:
        if not url:
            continue

        logging.info(f"Processing URL: {url}")
        if auth_session_file and Path.cwd().joinpath(auth_session_file).exists():
            logging.debug(f"Creating new context with authentication session: {auth_session_file}")
            context = browser.new_context(storage_state=auth_session_file)
        else:
            logging.debug("Creating new context")
            context = browser.new_context()

        page = context.new_page()
        page.goto(url)
        try:
            page.wait_for_load_state("networkidle")
        except PlaywrightTimeoutError as e:
            logging.error(f"Timeout waiting for page: {url} to load", e)
            continue

        click_on_element(lambda: page.get_by_test_id("close-button"))
        click_on_element(lambda: page.get_by_role("button", name="Accept all cookies"))
        click_on_element(lambda: page.get_by_role("button", name="Accept all"))

        page.focus("body")

        scroll_to_end(page)

        if convert_to_pdf:
            output_dir = Path.cwd().joinpath("target/pdfs")
            output_dir.mkdir(parents=True, exist_ok=True)
            output_file_path = generate_output_file_name(output_dir, url)
            page.pdf(path=output_file_path.as_posix(), format="A4")
        else:
            page.pause()

        if input_file:
            urls_from_file.remove(url)
            output_list = os.linesep.join([str(x) for x in urls_from_file])
            input_file.write_text(output_list)

        context.close()


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
    parser.add_argument("-f", "--input-file", type=Path, required=False, help="Input file with URLs")
    parser.add_argument("-i", "--input-url", type=str, required=False, help="Web Url")
    parser.add_argument("-a", "--auth-session-file", type=str, help="Playwright authentication session")
    parser.add_argument("-p", "--convert-to-pdf", action="store_true", help="Convert to PDF")
    return parser.parse_args()


def main(args):
    with sync_playwright() as playwright:
        run(playwright, args)


if __name__ == "__main__":
    args = parse_args()
    setup_logging(args.verbose)
    main(args)
