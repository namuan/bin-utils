#!/usr/bin/env python3
"""
Create a video sequence from PNG files in a directory, with a date frame at the start.

Usage:
./animate_pngs.py -h
./animate_pngs.py -i /path/to/png/directory
./animate_pngs.py -i /path/to/png/directory -o custom_output.mp4
./animate_pngs.py -i /path/to/png/directory -f 30 -v
./animate_pngs.py -i /path/to/png/directory --open-dir
"""

import glob
import logging
import os
import subprocess
from argparse import ArgumentParser, RawDescriptionHelpFormatter
from datetime import datetime

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont


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


def get_sorted_png_files(directory):
    """Get a sorted list of PNG files from the specified directory."""
    png_files = glob.glob(os.path.join(directory, "*.png"))
    sorted_files = sorted(png_files)
    logging.info(f"Found {len(sorted_files)} PNG files")
    logging.debug("Sorted PNG files:")
    for file in sorted_files:
        logging.debug(f"  {os.path.basename(file)}")
    return sorted_files


def generate_default_output_filename(input_dir):
    """Generate a default output filename in the input directory."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return os.path.join(input_dir, f"animated_{timestamp}.mp4")


def create_date_frame(date, size=(640, 480), font_file=None):
    """Create a frame with the given date in a very large font."""
    img = Image.new("RGB", size, color="black")
    draw = ImageDraw.Draw(img)

    # Use a larger font size (adjust as needed)
    font_size = min(size) // 10
    logging.debug(f"Attempting to use font size: {font_size}")

    if font_file and os.path.exists(font_file):
        try:
            font = ImageFont.truetype(font_file, font_size)
            logging.info(f"Using custom font: {font_file}")
        except OSError:
            logging.warning(f"Failed to load custom font: {font_file}")
            font = None
    else:
        font = None

    if font is None:
        # List of fonts to try (add or remove based on your system)
        font_names = ["Arial.ttf", "Helvetica.ttf", "DejaVuSans.ttf", "FreeSans.ttf"]

        for font_name in font_names:
            try:
                font = ImageFont.truetype(font_name, font_size)
                logging.info(f"Using font: {font_name}")
                break
            except OSError:
                continue

        if font is None:
            logging.warning("No suitable TrueType font found, using default font")
            font = ImageFont.load_default()

    date_str = date.strftime("%Y-%m-%d")
    logging.debug(f"Date string: {date_str}")

    # Get the size of the text
    bbox = draw.textbbox((0, 0), date_str, font=font)
    text_width = bbox[2] - bbox[0]
    text_height = bbox[3] - bbox[1]
    logging.debug(f"Text size: {text_width}x{text_height}")

    # Calculate position to center the text
    position = ((size[0] - text_width) / 2, (size[1] - text_height) / 2)
    logging.debug(f"Text position: {position}")

    # Draw the text
    draw.text(position, date_str, fill="white", font=font)
    return img


def get_common_size(images):
    """Determine the most common image size in the list."""
    sizes = [img.size for img in images if isinstance(img, Image.Image)]
    if not sizes:
        return (640, 480)  # Default size if no valid sizes found
    return max(set(sizes), key=sizes.count)


def resize_image(img, size):
    """Resize the image to the given size, maintaining aspect ratio and filling with black."""
    if not isinstance(img, Image.Image):
        return img  # Return as-is if not a PIL Image (e.g., the date frame)
    img_ratio = img.width / img.height
    target_ratio = size[0] / size[1]
    if img_ratio > target_ratio:
        # Image is wider, resize based on width
        new_size = (size[0], int(size[0] / img_ratio))
    else:
        # Image is taller, resize based on height
        new_size = (int(size[1] * img_ratio), size[1])
    resized_img = img.resize(new_size, Image.LANCZOS)
    new_img = Image.new("RGB", size, (0, 0, 0))
    paste_pos = ((size[0] - new_size[0]) // 2, (size[1] - new_size[1]) // 2)
    new_img.paste(resized_img, paste_pos)
    return new_img


def create_video(png_files, output_file, fps, start_date, codec="mp4v", font_file=None):
    """Create a video from the list of PNG files, including a date frame at the start."""
    images = []

    # Add date frame
    date_frame = create_date_frame(start_date, font_file=font_file)
    images.append(date_frame)

    # Process PNG files
    for png_file in png_files:
        logging.info(f"Processing file: {png_file}")
        try:
            img = Image.open(png_file)
            images.append(img)
        except Exception as e:
            logging.error(f"Error processing {png_file}: {str(e)}")

    if len(images) > 1:
        # Determine common size
        common_size = get_common_size(images)
        logging.info(f"Resizing images to {common_size}")

        # Resize images
        resized_images = [resize_image(img, common_size) for img in images]

        # Convert to numpy arrays
        np_images = [cv2.cvtColor(np.array(img), cv2.COLOR_RGB2BGR) for img in resized_images]

        # Create video writer
        fourcc = cv2.VideoWriter_fourcc(*codec)
        out = cv2.VideoWriter(output_file, fourcc, fps, common_size)

        logging.info(f"Creating video: {output_file}")
        for img in np_images:
            out.write(img)

        out.release()
        actual_duration = len(np_images) / fps
        logging.info(f"Video created successfully. Duration: {actual_duration:.2f} seconds")
    else:
        logging.error("Not enough valid images to create a video")


def open_directory(directory):
    """Open the specified directory using the default file manager."""
    try:
        if os.name == "nt":  # For Windows
            os.startfile(directory)
        elif os.name == "posix":  # For macOS and Linux
            opener = "open" if os.uname().sysname == "Darwin" else "xdg-open"
            subprocess.call([opener, directory])
        logging.info(f"Opened directory: {directory}")
    except Exception as e:
        logging.error(f"Failed to open directory: {str(e)}")


def parse_args():
    parser = ArgumentParser(description=__doc__, formatter_class=RawDescriptionHelpFormatter)
    parser.add_argument("-i", "--input-dir", required=True, help="Directory containing PNG files")
    parser.add_argument("-o", "--output-file", help="Output video file name")
    parser.add_argument("--fps", type=int, default=30, help="Frames per second (default: 30)")
    parser.add_argument("--codec", default="mp4v", help="Codec to use (default: mp4v)")
    parser.add_argument("--open-dir", action="store_true", help="Open the input directory after processing")
    parser.add_argument(
        "-v",
        "--verbose",
        action="count",
        default=0,
        dest="verbose",
        help="Increase verbosity of logging output",
    )
    parser.add_argument("--font", help="Path to a TrueType font file to use for the date frame", type=str, default=None)
    return parser.parse_args()


def main(args):
    setup_logging(args.verbose)

    logging.info(f"Processing PNG files in directory: {args.input_dir}")
    png_files = get_sorted_png_files(args.input_dir)

    if not png_files:
        logging.error(f"No PNG files found in directory: {args.input_dir}")
        return

    logging.info("Files to be processed (in order):")
    for file in png_files:
        logging.info(f"  {os.path.basename(file)}")

    if args.output_file:
        output_file = args.output_file
    else:
        output_file = generate_default_output_filename(args.input_dir)

    logging.info(f"Output file: {output_file}")

    try:
        # Extract date from the first PNG file
        first_file = os.path.basename(png_files[0])
        start_date = datetime.strptime(first_file[:8], "%Y%m%d")

        create_video(png_files, output_file, args.fps, start_date, args.codec, font_file=args.font)

        if args.open_dir:
            open_directory(args.input_dir)
    except ValueError as e:
        logging.error(f"Error parsing date from filename: {str(e)}")
    except Exception as e:
        logging.error(f"An unexpected error occurred: {str(e)}")


if __name__ == "__main__":
    args = parse_args()
    main(args)
