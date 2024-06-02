#!/usr/bin/env python3
"""
Import prompts from awesome-chatgpt-prompts as Alfred Snippets

Usage:
$ ./alfred-llm-prompts-import.py
"""
import csv
import json
import os
import re
import shutil
import subprocess
import sys
import uuid
from argparse import ArgumentParser, RawDescriptionHelpFormatter
from pathlib import Path

from common_utils import setup_logging

# Install requests library if not already installed
try:
    import requests
except ImportError:
    subprocess.check_call([sys.executable, "-m", "pip", "install", "requests"])
    import requests


def replace_double_quotes(text):
    # Use regular expression to find text inside double quotes and replace it with {clipboard}
    return re.sub(r'"(.*?)"', '"{clipboard}"', text)


def main():
    source_file = "prompts.csv"

    # URL of the CSV file
    url = f"https://raw.githubusercontent.com/f/awesome-chatgpt-prompts/main/{source_file}"
    # Download the file
    response = requests.get(url)
    # Save the file locally
    with open(source_file, "wb") as file:
        file.write(response.content)

    # Main script functionality
    output_dir = "output"
    field_names = ["name", "keyword", "content"]

    # Ensure the output directory exists
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    # Specify the encoding and error handling
    encoding = "utf-8"  # Change this to the appropriate encoding if needed

    with open(source_file, newline="", encoding=encoding, errors="replace") as csv_file:
        reader = csv.DictReader(csv_file, fieldnames=field_names)
        for row in reader:
            uid = str(uuid.uuid4())
            output = json.dumps(
                {
                    "alfredsnippet": {
                        "snippet": replace_double_quotes(row["keyword"]),
                        "uid": uid,
                        "name": row["name"],
                        "keyword": "",
                    }
                },
                sort_keys=False,
                indent=4,
                separators=(",", ": "),
            )
            output_file = os.path.join(output_dir, f"{uid}.json")
            with open(output_file, "w", encoding="utf-8") as f:
                f.write(output)

    # Zip the output directory
    shutil.make_archive(output_dir, "zip", output_dir)

    # Remove the output directory
    shutil.rmtree(output_dir)
    os.unlink("prompts.csv")
    shutil.move("output.zip", Path("target") / "chatgpt-prompts.alfredsnippets")


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
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    setup_logging(args.verbose)
    main()
