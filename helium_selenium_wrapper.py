#!/usr/bin/env python3
"""
Demonstrates how to use helium to automate a web browser.
"""
import logging
from argparse import ArgumentParser, RawDescriptionHelpFormatter

from helium import start_firefox

logging.basicConfig(
    handlers=[
        logging.StreamHandler(),
    ],
    format="%(asctime)s - %(filename)s:%(lineno)d - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    level=logging.INFO,
)
logging.captureWarnings(capture=True)


def parse_args():
    parser = ArgumentParser(description=__doc__, formatter_class=RawDescriptionHelpFormatter)
    return parser.parse_args()


def main(args):
    print(args)
    driver = start_firefox()
    driver.execute_script("window.alert('Hello World')")


if __name__ == "__main__":
    args = parse_args()
    main(args)
