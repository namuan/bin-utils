#!/usr/bin/env python3
"""
A script to download web pages using Vivaldi browser and SingleFile extension

Usage:
./download-urls.py -h

./download-urls.py -v file.txt # To log INFO messages
./download-urls.py -vv file.txt # To log DEBUG messages
"""
import logging
import subprocess
import time
from argparse import ArgumentParser, RawDescriptionHelpFormatter

import pyautogui


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
        "file",
        help="File containing list of URLs",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="count",
        default=0,
        dest="verbose",
        help="Increase verbosity of logging output",
    )
    return parser.parse_args()


def open_vivaldi(url):
    subprocess.Popen(["open", "-a", "Vivaldi", url])


def process_url(url):
    # Set the coordinates where you want to click
    single_file_x, single_file_y = 1493, 92
    click_x, click_y = 1489, 287

    logging.info(f"Opening Vivaldi with URL: {url}")
    open_vivaldi(url)

    # Wait for the page to load
    time.sleep(5)

    logging.debug(f"Moving to coordinates: ({single_file_x}, {single_file_y})")
    pyautogui.moveTo(single_file_x, single_file_y)

    logging.debug("Clicking at current position")
    pyautogui.click()

    logging.debug(f"Moving to coordinates: ({click_x}, {click_y})")
    pyautogui.moveTo(click_x, click_y)

    logging.info("Waiting for 15 seconds")
    time.sleep(15)


def main(args):
    # Ensure a safe exit is possible
    pyautogui.FAILSAFE = True

    # Initial delay before starting the process
    logging.info("Starting initial delay of 5 seconds")
    time.sleep(5)

    try:
        with open(args.file) as f:
            urls = f.read().splitlines()

        logging.info(f"Found {len(urls)} URLs in the file")

        for i, url in enumerate(urls, 1):
            logging.info(f"Processing URL {i} of {len(urls)}: {url}")
            process_url(url)

        logging.info("Script completed successfully.")

    except KeyboardInterrupt:
        logging.warning("Script terminated by user.")
    except Exception as e:
        logging.error(f"An error occurred: {e}")


if __name__ == "__main__":
    args = parse_args()
    setup_logging(args.verbose)
    main(args)
