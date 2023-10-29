#!/usr/bin/env python3
"""
A simple script

Usage:
./template_py_scripts.py -h

./template_py_scripts.py -v # To log INFO messages
./template_py_scripts.py -vv # To log DEBUG messages
"""
import logging
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
        "-v",
        "--verbose",
        action="count",
        default=0,
        dest="verbose",
        help="Increase verbosity of logging output",
    )
    return parser.parse_args()


def show_position():
    while True:
        # Get the current mouse position.
        mouse_position = pyautogui.position()

        # Print the current mouse position.
        print(mouse_position)

        # Sleep for 1 second.
        time.sleep(1)


def move_to_prompt_box():
    pyautogui.moveTo(828, 921)
    pyautogui.click()
    time.sleep(1)
    pyautogui.click()


def send_prompt():
    # pyautogui.moveTo(1480, 925)
    # pyautogui.click()
    pyautogui.hotkey("command", "enter")
    time.sleep(30)


def main(args):
    # Get the current mouse position.
    # show_position()
    with open("sample/dev-prompt.txt") as file:
        data = file.read().split("---")
    data = [section.strip() for section in data if section.strip() != ""]

    for prompt in data:
        print(f"Running Prompt: {prompt}")
        move_to_prompt_box()
        pyautogui.write(prompt)
        # pyautogui.press("Enter")
        time.sleep(1)
        send_prompt()


if __name__ == "__main__":
    args = parse_args()
    setup_logging(args.verbose)
    main(args)
