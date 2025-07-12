#!/usr/bin/env -S uv run --quiet --script
# /// script
# dependencies = [
#   "pandas",
#   "pillow",
# ]
# ///
"""
A simple script to save an image from the clipboard to a temporary PNG file.

This script checks the clipboard for an image. If an image is found, it saves the image
to a temporary PNG file and prints the full path to the file. If the clipboard does not
contain an image, a warning message is logged.

Recommended to create a symlink to a folder which is included in $PATH
$ ln -s ~/workspace/bin-utils/png-paste.py ~/bin/png-paste

So that it can be run from anywhere with just `png-paste`

Usage:
png-paste
or
./png-paste.py
"""
import logging
import tempfile
from argparse import ArgumentParser, RawDescriptionHelpFormatter

from PIL import Image, ImageGrab


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
        "--compress",
        action="store_true",
        default=True,
        dest="compress",
        help="Compress the image before saving (default: True)",
    )
    return parser.parse_args()


def main(args):
    log_level = logging.WARNING
    if args.verbose == 1:
        log_level = logging.INFO
    elif args.verbose >= 2:
        log_level = logging.DEBUG

    logging.basicConfig(level=log_level, format="%(asctime)s - %(levelname)s - %(message)s")

    logging.debug("Checking clipboard for an image")
    clipboard_item = ImageGrab.grabclipboard()

    if isinstance(clipboard_item, Image.Image):
        logging.info("Image found on clipboard")
        if args.compress:
            logging.debug("Compressing image")
            clipboard_item = clipboard_item.copy()
            clipboard_item = clipboard_item.resize(
                (clipboard_item.width, clipboard_item.height), Image.Resampling.LANCZOS
            )

        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as temp_file:
            logging.debug(f"Saving image to temporary file: {temp_file.name}")
            clipboard_item.save(temp_file.name, format="PNG", optimize=True, compress_level=9)
            print(temp_file.name)
            logging.info(f"Image saved to {temp_file.name}")
    else:
        logging.warning("Clipboard does not contain an image.")


if __name__ == "__main__":
    args = parse_args()
    main(args)
