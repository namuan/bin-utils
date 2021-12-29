#!/usr/bin/env python3
"""
Find/Delete files from source directory that are not used in any file in the target directory.
"""
import logging
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
    parser.add_argument("-s", "--source", required=True, help="Source directory")
    parser.add_argument("-t", "--target", required=True, help="Target directory")
    parser.add_argument("-d", "--delete", action="store_true", help="Delete unused files")
    parser.add_argument("-v", "--verbose", action="store_true")
    return parser.parse_args()


def file_name_is_used_in(files_in_target, file_name):
    for target_file in files_in_target:
        if target_file.is_file() and file_name in file_contents(target_file):
            return True
    else:
        return False


def file_contents(target_file):
    try:
        return target_file.read_text()
    except UnicodeDecodeError:
        return ""


def main(args):
    source_dir = args["source"]
    target_dir = args["target"]
    delete_file = args["delete"]
    logging.info(f"Find/delete({'y' if delete_file else 'n'}) files in {source_dir} which are not used in {target_dir}")

    files_in_source = Path(source_dir).glob("**/*")
    files_in_target = list(Path(target_dir).glob("**/*"))
    unused_files = [
        source
        for source in files_in_source
        if source.is_file() and not file_name_is_used_in(files_in_target, source.name)
    ]

    for unused_file in unused_files:
        logging.info(f"{unused_file.name} is unused in {target_dir}")
        if delete_file:
            unused_file.unlink()

    logging.info(f"{len(unused_files)} files {'deleted' if delete_file else 'found'}")


if __name__ == "__main__":
    args = parse_args()
    main(args.__dict__)
