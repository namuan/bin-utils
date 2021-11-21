#!/usr/bin/env python3
"""
Shows an example of executable documentation.

Usage:
./executable_docs.py -h

./executable_docs.py --username johndoe
"""

import argparse
from argparse import ArgumentParser


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
        print(context)


def run_step(step, context):
    print(step.__class__.__name__)
    print(step.__doc__)
    step.run(context)
    print("-" * 100)


def parse_args():
    parser = ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("-u", "--username", type=str, required=True, help="User name")
    return parser.parse_args()


def main(args):
    context = args.__dict__
    procedure = [
        DoSomething(),
    ]
    for step in procedure:
        run_step(step, context)
    print("Done.")


if __name__ == "__main__":
    args = parse_args()
    main(args)
