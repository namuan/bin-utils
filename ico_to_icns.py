#!/usr/bin/env python3
"""
A script to convert ICO files to ICNS format.

Usage:
./ico_to_icns.py -h

./ico_to_icns.py input.ico output.icns -v # To log INFO messages
./ico_to_icns.py input.ico output.icns -vv # To log DEBUG messages
"""
import logging
import os
import subprocess
from argparse import ArgumentParser, RawDescriptionHelpFormatter

from PIL import Image


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
    parser.add_argument("source", help="Path to the source ICO file")
    parser.add_argument("target", help="Path for the target ICNS file")
    parser.add_argument(
        "-v",
        "--verbose",
        action="count",
        default=0,
        dest="verbose",
        help="Increase verbosity of logging output",
    )
    return parser.parse_args()


def ico_to_icns(ico_path, output_path):
    logging.info(f"Converting {ico_path} to {output_path}")
    img = Image.open(ico_path)

    temp_dir = "icon.iconset"
    os.makedirs(temp_dir, exist_ok=True)
    logging.debug(f"Created temporary directory: {temp_dir}")

    icon_sizes = [
        (16, "16x16"),
        (32, "16x16@2x"),
        (32, "32x32"),
        (64, "32x32@2x"),
        (128, "128x128"),
        (256, "128x128@2x"),
        (256, "256x256"),
        (512, "256x256@2x"),
        (512, "512x512"),
        (1024, "512x512@2x"),
    ]

    for size, name in icon_sizes:
        img_resized = img.resize((size, size), Image.LANCZOS)
        img_resized.save(f"{temp_dir}/icon_{name}.png")
        logging.debug(f"Saved icon_{name}.png")

    logging.info("Running iconutil command")
    subprocess.run(["iconutil", "-c", "icns", temp_dir, "-o", output_path])

    for file in os.listdir(temp_dir):
        os.remove(os.path.join(temp_dir, file))
    os.rmdir(temp_dir)
    logging.debug("Cleaned up temporary directory")


def main(args):
    if not args.source.lower().endswith(".ico"):
        logging.error("Source file must be an ICO file.")
        return

    if not args.target.lower().endswith(".icns"):
        logging.error("Target file must have .icns extension.")
        return

    if not os.path.exists(args.source):
        logging.error(f"Source file '{args.source}' does not exist.")
        return

    try:
        ico_to_icns(args.source, args.target)
        logging.info(f"Successfully converted '{args.source}' to '{args.target}'")
    except Exception as e:
        logging.error(f"An error occurred: {str(e)}")


if __name__ == "__main__":
    args = parse_args()
    setup_logging(args.verbose)
    main(args)
