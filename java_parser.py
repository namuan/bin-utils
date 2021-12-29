#!/usr/bin/env python3
"""
Parses the java files and creates a list of all the classes and their methods.
"""
import logging
from argparse import ArgumentParser, RawDescriptionHelpFormatter
from pathlib import Path

import javalang

logging.basicConfig(
    handlers=[
        logging.StreamHandler(),
    ],
    format="%(asctime)s - %(filename)s:%(lineno)d - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    level=logging.INFO,
)
logging.captureWarnings(capture=True)


def parse_args():
    parser = ArgumentParser(description=__doc__, formatter_class=RawDescriptionHelpFormatter)
    parser.add_argument(
        "-s",
        "--source-directory",
        type=str,
        required=True,
        help="Input source directory",
    )
    return parser.parse_args()


def parse_java_file(file_contents):
    java_tree = javalang.parse.parse(file_contents)
    for class_declaration in java_tree.types:
        logging.info("Class: %s", class_declaration.name)
        for variable_declaration in class_declaration.fields:
            logging.info("--> Variables: %s", variable_declaration)

        for method_declaration in class_declaration.methods:
            logging.info("-> Method: %s", method_declaration.name)


def main(args):
    source_directory = Path(args.source_directory)
    java_files = list(source_directory.glob("**/*.java"))
    for java_file in java_files:
        java_file_contents = Path(java_file).read_text()
        parse_java_file(java_file_contents)


if __name__ == "__main__":
    args = parse_args()
    main(args)
