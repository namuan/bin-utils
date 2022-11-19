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

from py_executable_checklist.workflow import WorkflowBase, run_workflow

# Common functions across steps

# Workflow steps


class DoSomething(WorkflowBase):
    """
    Go to this page
    Copy the command
    Run the command
    Copy the output and paste it into the email
    """

    username: str

    def execute(self):
        logging.info(f"Hello {self.username}")

        # output
        return {"greetings": f"Hello {self.username}"}


# Workflow definition


def workflow():
    return [
        DoSomething,
    ]


# Boilerplate


def setup_logging():
    logging.basicConfig(
        handlers=[logging.StreamHandler()],
        format="%(asctime)s - %(filename)s:%(lineno)d - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        level=logging.INFO,
    )
    logging.captureWarnings(capture=True)


def parse_args():
    parser = ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
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
    run_workflow(context, workflow())


if __name__ == "__main__":
    setup_logging()
    args = parse_args()
    main(args)
