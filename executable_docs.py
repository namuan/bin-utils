#!/usr/bin/env python3
"""
Shows an example of executable documentation.

Usage:
./executable_docs.py -h

./executable_docs.py --username johndoe
"""

import argparse
import logging
from argparse import ArgumentParser

from common.workflow2 import run_workflow2, WorkflowBase

logging.basicConfig(
    handlers=[logging.StreamHandler()],
    format="%(asctime)s - %(filename)s:%(lineno)d - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    level=logging.INFO,
)
logging.captureWarnings(capture=True)


class DoSomething(WorkflowBase):
    """
    Go to this page
    Copy the command
    Run the command
    Copy the output and paste it into the email
    """

    username: str

    def run(self, context):
        logging.info(f"Hello {self.username}")

        # output
        context["greetings"] = f"Hello {context['username']}"


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
    procedure = [DoSomething]
    run_workflow2(context, procedure)


if __name__ == "__main__":
    args = parse_args()
    main(args)
