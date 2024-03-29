#!/usr/bin/env python3
"""
[] Organise photos and videos

TODO:
Handle ignored files
"""
import json
import logging
import shutil
from argparse import ArgumentParser, RawDescriptionHelpFormatter
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from exif import Image
from plum.exceptions import UnpackError

logging.basicConfig(
    handlers=[
        logging.StreamHandler(),
    ],
    format="%(asctime)s - %(filename)s:%(lineno)d - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    level=logging.INFO,
)
logging.captureWarnings(capture=True)


@dataclass
class MediaMetadata:
    has_metadata: bool
    year: str
    month: str
    day: str
    time: str


def parse_args():
    parser = ArgumentParser(description=__doc__, formatter_class=RawDescriptionHelpFormatter)
    parser.add_argument("-f", "--source-file", type=str, help="Source file")
    parser.add_argument("-s", "--source-directory", type=str, help="Source directory")
    parser.add_argument("-t", "--target-directory", type=str, required=True, help="Target directory")
    parser.add_argument(
        "-r",
        "--remove-source",
        action="store_true",
        default=False,
        help="Remove source file",
    )
    return parser.parse_args()


def get_datetime_from_exif(file_path, image):
    datetime_to_parse = image.get("datetime_original", image.get("datetime"))
    if not datetime_to_parse:
        file_directory = file_path.parent
        json_file = file_directory / (file_path.name + ".json")
        if json_file.exists():
            with open(json_file) as f:
                json_data = json.load(f)
                datetime_to_parse = json_data["creationTime"]["timestamp"]

    formats_to_try = ["%Y:%m:%d %H:%M:%S", "%Y:%m:%d:%H:%M:%S"]
    datetime_from_exif = None
    for format_to_try in formats_to_try:
        try:
            datetime_from_exif = datetime.strptime(datetime_to_parse, format_to_try)
        except (ValueError, TypeError):
            pass

    if not datetime_from_exif:
        try:
            datetime_from_exif = datetime.fromtimestamp(float(datetime_to_parse))
        except (ValueError, TypeError):
            pass

    if not datetime_from_exif:
        try:
            datetime_from_exif = datetime.fromtimestamp(file_path.stat().st_birthtime)
        except ValueError:
            pass

    if not datetime_from_exif:
        raise Exception(f"Unable to parse date time from exif data: {dir(image)} , formats: {formats_to_try}")

    return datetime_from_exif


def get_photo_metadata(file_path):
    image = Image(file_path.as_posix())
    if not image.has_exif:
        media_created_date_time = datetime.fromtimestamp(file_path.stat().st_birthtime)
    else:
        media_created_date_time = get_datetime_from_exif(file_path, image)

    year = f"{media_created_date_time.year:04d}"
    month = f"{media_created_date_time.month:02d}"
    day = f"{media_created_date_time.day:02d}"
    time = f"{media_created_date_time.time().hour:02d}{media_created_date_time.time().minute:02d}"
    return MediaMetadata(has_metadata=image.has_exif, year=year, month=month, day=day, time=time)


def build_target_file_path(file_path, target_directory, metadata):
    target_folder = target_directory / metadata.year / metadata.month / metadata.day
    target_folder.mkdir(parents=True, exist_ok=True)
    if not file_path.suffix:
        target_folder = target_directory / "ToSort"

    return target_folder / "{}_{}_{}_{}_{}{}".format(
        metadata.year,
        metadata.month,
        metadata.day,
        metadata.time,
        file_path.stem.lower(),
        file_path.suffix.lower(),
    )


def valid_file(file_path):
    invalid_file_extensions = [".json", ".ini", ".zip"]
    invalid_names = [".ds_store"]
    return (
        file_path.exists()
        and not file_path.is_dir()
        and file_path.suffix.lower() not in invalid_file_extensions
        and file_path.name.lower() not in invalid_names
    )


def process_later(file_path, target_directory):
    target_file = target_directory / "ToSort" / file_path.name
    if not target_file.exists():
        shutil.copyfile(file_path, target_file)


def is_video_file(file_path):
    return file_path.suffix.lower() in [".mp4", ".mov", ".m4v", ".avi", ".3gp", ".flv"]


def get_video_metadata(file_path):
    media_created_date_time = datetime.fromtimestamp(file_path.stat().st_birthtime)

    year = f"{media_created_date_time.year:04d}"
    month = f"{media_created_date_time.month:02d}"
    day = f"{media_created_date_time.day:02d}"
    time = f"{media_created_date_time.time().hour:02d}{media_created_date_time.time().minute:02d}"
    return MediaMetadata(has_metadata=False, year=year, month=month, day=day, time=time)


def process_media(file_path, target_directory):
    if is_video_file(file_path):
        metadata = get_video_metadata(file_path)
    else:
        metadata = get_photo_metadata(file_path)

    if metadata is None:
        raise ValueError(f"Unable to parse metadata for {file_path}")

    target_file = build_target_file_path(file_path, target_directory, metadata)
    if not target_file.exists():
        shutil.copy2(file_path, target_file)

    return target_file


def create_required_directories(target_directory):
    target_directory.mkdir(exist_ok=True)
    (target_directory / "ToSort").mkdir(exist_ok=True)


def collect_media_files_from(args):
    if args.source_file:
        source_file = Path(args.source_file)
        media_files = [source_file]
    else:
        source_directory = Path(args.source_directory).expanduser()
        media_files = (p.resolve() for p in source_directory.glob("**/*") if p.is_file() and valid_file(p))

    return list(media_files)


def main(args):
    if not args.source_directory and not args.source_file:
        raise ValueError("Either source_file or source_directory must be specified")

    if args.source_directory and args.source_file:
        raise ValueError("Only one of source_file or source_directory can be specified")

    media_files = collect_media_files_from(args)
    logging.info(f"📂 {len(media_files)} files found")
    target_directory = Path(args.target_directory).expanduser()
    create_required_directories(target_directory)

    for idx, media_file in enumerate(media_files):
        source_file = Path(media_file)
        try:
            logging.info(f"⏳ Processing {source_file}")
            target_file = process_media(source_file, target_directory)
            if args.remove_source:
                source_file.unlink()
                logging.info(f"🗑 Removing source file: {source_file}")

            logging.info(f"📓 [{idx}] {source_file} => {target_file}")
        except UnpackError as e:
            logging.warning(f"❌ Unknown file format -> 🗄 Moving to process later: {source_file} ERROR: {e}")
            process_later(source_file, target_directory)
    logging.info("Done.")


if __name__ == "__main__":
    args = parse_args()
    main(args)
