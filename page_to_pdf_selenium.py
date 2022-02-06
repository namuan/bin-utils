# !/usr/bin/env python3
"""
Convert a webpage to a pdf file using selenium.
"""
import logging
from argparse import ArgumentParser, RawDescriptionHelpFormatter
from time import sleep

from helium import start_firefox
from selenium.webdriver import FirefoxOptions

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
    options = FirefoxOptions()
    options.add_argument("--start-maximized")
    options.set_preference("print.always_print_silent", True)
    options.set_preference("print.printer_Mozilla_Save_to_PDF.print_to_file", True)
    options.set_preference("print_printer", "Mozilla Save to PDF")

    driver = start_firefox("https://www.deskriders.dev/posts/1639863087-python-selenium/", options=options)

    driver.execute_script("window.print();")
    sleep(2)  # Found that a little wait is needed for the print to be rendered otherwise the file will be corrupted

    driver.quit()


if __name__ == "__main__":
    args = parse_args()
    main(args)
