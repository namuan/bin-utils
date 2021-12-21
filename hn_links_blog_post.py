#!/usr/bin/env python3
"""
Create blog post from Markdown and images generated from hn_links.py

Usage:
./hn_links_blog_post.py -b <blog_directory> -p <hn_post_directory>
"""

import argparse
from argparse import ArgumentParser
import logging

logging.basicConfig(
    handlers=[logging.StreamHandler()],
    format="%(asctime)s - %(filename)s:%(lineno)d - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    level=logging.INFO,
)
logging.captureWarnings(capture=True)


def wait_for_enter():
    input("Press Enter to continue: ")


class DoSomething(object):
    """
    Go to this page
    Copy the command
    Run the command
    Copy the output and paste it into the email
    """

    def run(self, context):
        logging.info(context)


def run_step(step, context):
    logging.info(step.__class__.__name__ + " ➡️ " + step.__doc__)
    if context.get("verbose"):
        logging.info(context)
    step.run(context)
    logging.info("-" * 100)


def parse_args():
    parser = ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("-u", "--username", type=str, required=True, help="User name")
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        default=False,
        dest="verbose",
        help="Display context variables at each step",
    )
    return parser.parse_args()


def main(args):
    context = args.__dict__
    procedure = [DoSomething()]
    for step in procedure:
        run_step(step, context)
    logging.info("Done.")


if __name__ == "__main__":
    args = parse_args()
    main(args)
