#!/usr/bin/env -S uv run --quiet --script
# /// script
# dependencies = [
#   "pandas",
#   "persistent-cache@git+https://github.com/namuan/persistent-cache"
# ]
# ///
"""
A script to remove comments from Python files in a directory, preserving linting suppression comments.

Usage:
./remove_comments.py -h
./remove_comments.py <directory> [-v | -vv]
"""
import logging
import re
from argparse import ArgumentParser, RawDescriptionHelpFormatter
from pathlib import Path


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
        "directory",
        type=str,
        help="Directory containing Python files",
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


def is_linting_suppression(line):
    """Check if a line contains a linting suppression comment."""
    suppression_patterns = [
        r"#\s*noqa",
        r"#\s*pylint:",
        r"#\s*ruff:",
        r"#\s*type:\s*ignore",
        r"#\s*mypy:",
    ]
    logging.debug(f"Checking line for linting suppression: {line.strip()}")
    is_suppression = any(re.search(pattern, line, re.IGNORECASE) for pattern in suppression_patterns)
    if is_suppression:
        logging.debug("Line identified as linting suppression comment")
    return is_suppression


def remove_comments(content):
    """Remove single-line and multi-line comments, preserving linting suppression comments."""
    result_lines = []
    in_multiline_comment = False
    multiline_start = None
    comment_count = 0
    suppression_count = 0

    lines = content.splitlines()
    logging.debug(f"Processing {len(lines)} lines of content")
    for i, line in enumerate(lines):
        stripped_line = line.strip()
        logging.debug(f"Analyzing line {i+1}: {stripped_line}")

        # Handle multi-line comments
        if stripped_line.startswith('"""') or stripped_line.startswith("'''"):
            if in_multiline_comment:
                # End of multi-line comment
                if (stripped_line.endswith('"""') and multiline_start == '"""') or (
                        stripped_line.endswith("'''") and multiline_start == "'''"
                ):
                    in_multiline_comment = False
                    multiline_start = None
                    comment_count += 1
                    logging.debug(f"End of multi-line comment detected at line {i+1}")
                continue
            else:
                # Start of multi-line comment
                in_multiline_comment = True
                multiline_start = stripped_line[:3]
                logging.debug(f"Start of multi-line comment detected at line {i+1} with delimiter {multiline_start}")
                # Check if it's a single-line docstring
                if (multiline_start == '"""' and stripped_line.endswith('"""')) or (
                        multiline_start == "'''" and stripped_line.endswith("'''")
                ):
                    in_multiline_comment = False
                    multiline_start = None
                    comment_count += 1
                    logging.debug(f"Single-line docstring detected and removed at line {i+1}")
                continue

        # Skip lines within multi-line comments
        if in_multiline_comment:
            logging.debug(f"Skipping line {i+1} (inside multi-line comment)")
            continue

        # Handle single-line comments
        if stripped_line.startswith("#"):
            if is_linting_suppression(line):
                result_lines.append(line)
                suppression_count += 1
                logging.debug(f"Preserving linting suppression comment at line {i+1}")
            else:
                comment_count += 1
                logging.debug(f"Removing single-line comment at line {i+1}")
            continue

        # Handle inline comments
        if "#" in line:
            if not is_linting_suppression(line):
                # Remove inline comment, preserving the code before it
                code_part = line.split("#")[0].rstrip()
                if code_part:
                    result_lines.append(code_part)
                    comment_count += 1
                    logging.debug(f"Removing inline comment at line {i+1}, keeping code: {code_part}")
                else:
                    comment_count += 1
                    logging.debug(f"Removing pure comment line {i+1}")
            else:
                result_lines.append(line)
                suppression_count += 1
                logging.debug(f"Preserving inline linting suppression comment at line {i+1}")
        else:
            result_lines.append(line)
            logging.debug(f"Keeping non-comment line {i+1}")

    logging.info(f"Removed {comment_count} comments, preserved {suppression_count} linting suppression comments")
    return "\n".join(result_lines)


def process_python_files(directory):
    """Process all Python files in the given directory."""
    directory_path = Path(directory)
    if not directory_path.is_dir():
        logging.error(f"Directory {directory} does not exist")
        return

    python_files = list(directory_path.glob("*.py"))
    logging.info(f"Found {len(python_files)} Python files in {directory}")

    for file_path in python_files:
        logging.info(f"Processing file: {file_path}")
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()
                logging.debug(f"Read {len(content.splitlines())} lines from {file_path}")

            new_content = remove_comments(content)
            logging.debug(f"Processed content, new line count: {len(new_content.splitlines())}")

            with open(file_path, "w", encoding="utf-8") as f:
                f.write(new_content)
            logging.info(f"Successfully processed and updated {file_path}")
        except Exception as e:
            logging.error(f"Error processing {file_path}: {str(e)}")


def main(args):
    logging.debug(f"Starting script with verbosity level: {args.verbose}")
    logging.info(f"Processing directory: {args.directory}")
    process_python_files(args.directory)
    logging.info("Comment removal process completed")


if __name__ == "__main__":
    args = parse_args()
    setup_logging(args.verbose)
    main(args)