#!/usr/bin/env python3
"""
Convert text to audio using AWS Polly

Usage:
./txt_to_audio_polly.py -i input.txt -o output.mp3

It is also possible to use the AWS_PROFILE environment variable to specify the AWS profile to use.
Otherwise you can use the -p/--profile option to specify the profile to use.
./txt_to_audio_polly.py -i input.txt -o output.mp3 -p my_profile
"""
import logging
import os
from argparse import ArgumentParser, RawDescriptionHelpFormatter
from pathlib import Path

import boto3


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
        "-i",
        "--input",
        type=Path,
        required=True,
        help="Input file",
    )
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        required=True,
        help="Output file",
    )
    parser.add_argument(
        "-p",
        "--profile",
        type=str,
        required=False,
        default=os.getenv("AWS_PROFILE", "default"),
        help="AWS Profile to use. If not provided then it'll use the AWS_PROFILE environment variable",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="count",
        default=0,
        dest="verbose",
        help="Increase verbosity of logging output",
    )
    return parser.parse_args()


def main(args):
    session = boto3.Session(profile_name=args.profile)
    polly = session.client("polly")
    with open(args.input) as f:
        text = f.read()
        response = polly.synthesize_speech(Text=text, OutputFormat="mp3", VoiceId="Matthew")
        with open(args.output, "wb") as f:
            f.write(response["AudioStream"].read())


if __name__ == "__main__":
    args = parse_args()
    setup_logging(args.verbose)
    main(args)
