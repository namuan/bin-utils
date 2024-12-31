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
    clipboard_item = ImageGrab.grabclipboard()

    if isinstance(clipboard_item, Image.Image):
        if args.compress:
            clipboard_item = clipboard_item.copy()
            clipboard_item = clipboard_item.resize(
                (clipboard_item.width, clipboard_item.height), Image.Resampling.LANCZOS
            )

        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as temp_file:
            clipboard_item.save(temp_file.name, format="PNG", optimize=True, compress_level=9)
            print(temp_file.name)
    else:
        logging.warning("Clipboard does not contain an image.")


if __name__ == "__main__":
    args = parse_args()
    main(args)
