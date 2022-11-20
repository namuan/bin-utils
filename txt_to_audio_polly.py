#!/usr/bin/env python3
"""
Convert text to audio using AWS Polly

Usage:
./txt_to_audio_polly.py -i input.txt

It is also possible to use the AWS_PROFILE environment variable to specify the AWS profile to use.
Otherwise you can use the -p/--profile option to specify the profile to use.
./txt_to_audio_polly.py -i input.txt -p my_profile
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


def yield_text_by_paragraphs(text):
    yield from text.splitlines()


def yield_text_by_fullstops(text):
    counter = 1
    para = ""
    for sentence in text.split("."):
        if len(para) + len(sentence) > 1500:
            yield para, counter
            counter += 1
            para = ""
        para += sentence + "."
    yield para, counter


def main(args):
    session = boto3.Session(profile_name=args.profile)
    polly = session.client("polly")
    input_file = args.input
    output_directory_from_input: Path = input_file.parent
    output_file_base = input_file.stem
    with open(input_file) as f:
        text = f.read()
        for para, counter in yield_text_by_fullstops(text):
            response = polly.synthesize_speech(
                OutputFormat="mp3",
                Text=para,
                TextType="text",
                VoiceId="Matthew",
            )
            with open(
                output_directory_from_input.joinpath(f"{output_file_base}-{counter}.mp3").as_posix(), "wb"
            ) as out:
                out.write(response["AudioStream"].read())


if __name__ == "__main__":
    args = parse_args()
    setup_logging(args.verbose)
    main(args)
