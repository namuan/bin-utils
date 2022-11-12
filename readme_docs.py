#!/usr/bin/env python3
"""
Generates documentation for the readme.md file
"""
import logging
import os
import re
import subprocess
from argparse import ArgumentParser, RawDescriptionHelpFormatter
from pathlib import Path

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
    return parser.parse_args()


def main(args):
    # These files will be ignored during processing
    ignored_files = [
        "page_to_pdf_selenium.py",
        "file_counter.py",
        "phpbb_thread.py",
        "download_html_to_file.py",
        "generate_paypal_errors.py",
        "firefox_browser_session.py",
        "common_utils.py",
        "flatten_directory.py",
        "git_log_to_sqlite.py",
        "reddit_api.py",
        "twitter_api.py",
        "yt_api.py",
    ]
    py_scripts_with_help = []
    # Grab all the python scripts in the current directory and collect output from running the help command
    for f in Path(".").glob("*.py"):
        if f.name in ignored_files:
            continue
        logging.info(f"Running python --help on {f}")
        py_help_output = subprocess.run([f"./{f.as_posix()} --help"], shell=True, capture_output=True)  # nosemgrep
        py_scripts_with_help.append(
            "[_{}_](https://namuan.github.io/bin-utils/{}.html){}```{}{}{}```".format(
                f.name, f.stem, os.linesep, os.linesep, py_help_output.stdout.decode("utf-8"), os.linesep
            )
        )

    logging.info("Loaded all files. Now replacing regex patterns")
    # Generate output within the start/end pattern
    start_pattern = "<!-- START makefile-doc -->"
    end_pattern = "<!-- END makefile-doc -->"
    docs_placeholder_regex = re.compile(f"{start_pattern}(.*){end_pattern}", re.DOTALL)
    replacement_string = "\n".join(py_scripts_with_help)
    replacement_string_with_placeholder = f"{start_pattern}{os.linesep}{replacement_string}{os.linesep}{end_pattern}"

    # Replace section in README.md
    readme_file = Path("README.md")
    readme_contents = readme_file.read_text(encoding="utf-8")
    readme_file.write_text(
        re.sub(docs_placeholder_regex, replacement_string_with_placeholder, readme_contents), encoding="utf-8"
    )


if __name__ == "__main__":
    args = parse_args()
    main(args)
