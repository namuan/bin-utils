#!/usr/env/bin python3
"""
[] Organise photos and videos

TODO:
Handle ignored files
"""
import json
import shutil
from argparse import ArgumentParser, RawDescriptionHelpFormatter
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from exif import Image
from plum.exceptions import UnpackError


@dataclass
class PhotoMetadata:
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
    return parser.parse_args()


def get_datetime_from_exif(file_path, image):
    datetime_to_parse = image.get('datetime_original', image.get('datetime'))
    if not datetime_to_parse:
        file_directory = file_path.parent
        json_file = file_directory / (file_path.name + ".json")
        if json_file.exists():
            with open(json_file, "r") as f:
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

    year = "{:04d}".format(media_created_date_time.year)
    month = "{:02d}".format(media_created_date_time.month)
    day = "{:02d}".format(media_created_date_time.day)
    time = "{:02d}{:02d}".format(media_created_date_time.time().hour,
                                 media_created_date_time.time().minute)
    return PhotoMetadata(
        has_metadata=image.has_exif,
        year=year,
        month=month,
        day=day,
        time=time
    )


def move_to_target_directory(file_path, target_directory, photo_metadata):
    target_folder = target_directory / photo_metadata.year / photo_metadata.month / photo_metadata.day
    target_folder.mkdir(parents=True, exist_ok=True)
    if not file_path.suffix:
        target_folder = target_directory / "ToSort"

    target_file = target_folder / "{}_{}_{}_{}{}".format(
        photo_metadata.year,
        photo_metadata.month,
        photo_metadata.day,
        photo_metadata.time,
        file_path.suffix
    )

    print(f"📓 {file_path} => {target_file}")
    if not target_file.exists():
        shutil.copy2(file_path, target_file)


def valid_file(file_path):
    invalid_file_extensions = [".json", ".ini", ".zip"]
    return file_path.exists() and not file_path.is_dir() and file_path.suffix.lower() not in invalid_file_extensions


def process_later(file_path, target_directory):
    target_file = target_directory / "ToSort" / file_path.name
    if not target_file.exists():
        shutil.copyfile(file_path, target_file)


def process_media(file_path, target_directory):
    try:
        photo_metadata = get_photo_metadata(file_path)
        if photo_metadata is None:
            return

        move_to_target_directory(file_path, target_directory, photo_metadata)
    except UnpackError as e:
        print(f"❌ Unable to process {file_path} 🗄 Moving to process later.")
        process_later(file_path, target_directory)


def create_required_directories(target_directory):
    target_directory.mkdir(exist_ok=True)
    (target_directory / "ToSort").mkdir(exist_ok=True)


def collect_media_files_from(args):
    if args.source_file:
        source_file = Path(args.source_file)
        media_files = [source_file]
    else:
        source_directory = Path(args.source_directory).expanduser()
        media_files = source_directory.glob("**/*")
    return media_files


def main(args):
    if not args.source_directory and not args.source_file:
        raise ValueError("Either source_file or source_directory must be specified")

    if args.source_directory and args.source_file:
        raise ValueError("Only one of source_file or source_directory can be specified")

    media_files = collect_media_files_from(args)

    target_directory = Path(args.target_directory).expanduser()
    create_required_directories(target_directory)

    for media_file in media_files:
        try:
            source_file = Path(media_file)
            if valid_file(source_file):
                print(f"⏳ Processing {media_file}")
                process_media(source_file, target_directory)
        except Exception as e:
            print(f"❌ Unable to process {media_file}")
            raise e
    print("Done.")


if __name__ == "__main__":
    args = parse_args()
    main(args)
