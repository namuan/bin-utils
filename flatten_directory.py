#!/usr/bin/env python3
"""
Flatten files in a directory.

Input:
    - source directory
    - target directory

Output:
    - flattened files in target directory
        file name = source file name + source directory name joined with a '_'
"""
import shutil
from pathlib import Path

import fire


def main(source_dir: str, target_dir: str):
    source_dir_path = Path(source_dir).expanduser()
    target_dir_path = Path(target_dir).expanduser()
    if not target_dir_path.exists():
        target_dir_path.mkdir(parents=True)

    file_cache = {}
    for source_file_path in source_dir_path.glob("**/*"):
        if source_file_path.is_file():
            norm_source_parent_path = (
                source_file_path.parent.as_posix()
                .replace("/", "_")
                .replace(" ", "_")
                .replace("-", "_")
                .replace("(", "_")
                .replace(")", "_")
                .replace(".", "")
            )
            norm_source_parent_path = norm_source_parent_path.replace(
                source_dir_path.as_posix().replace("/", "_"), ""
            )
            target_file_path = target_dir_path / (
                source_file_path.stem
                + norm_source_parent_path
                + source_file_path.suffix
            )
            print(f"Copying {source_file_path} to {target_file_path}")
            shutil.copy2(source_file_path, target_file_path)

            # Recording any duplicates
            if file_cache.get(source_file_path.stem) is None:
                file_cache[source_file_path.stem] = [source_file_path.as_posix()]
            else:
                file_cache[source_file_path.stem].append(source_file_path.as_posix())

    for k, v in file_cache.items():
        if len(v) > 1:
            print(f"{len(v)} Duplicate files found for {k}")
            print(f"{v}")


if __name__ == "__main__":
    fire.Fire(main)
