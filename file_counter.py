#!/usr/bin/env python3
"""
Count number of files by type in a directory

input:
    - directory
    - file extensions

output:
    - total number of files
"""
from pathlib import Path
from typing import List

import fire

from media_manager import valid_file


def main(source_directory: str, extensions: List[str]):
    print(f"Source directory: {source_directory}, extensions: {extensions}")
    source_directory = Path(source_directory).expanduser()
    if not source_directory.is_dir():
        raise ValueError(f"{source_directory} is not a directory")

    files_in_directory = [
        p.resolve()
        for p in source_directory.glob("**/*")
        if p.is_file() and p.suffix.lower() in extensions and valid_file(p)
    ]
    print(files_in_directory[0])
    print(f"Total files: {len(files_in_directory)}")


if __name__ == "__main__":
    fire.Fire(main)
