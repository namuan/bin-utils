#!/usr/bin/env python3
"""
A script to convert JSON file to PDF with embedded images using pandoc

Usage:
./json_to_pdf_pandoc.py -h

./json_to_pdf_pandoc.py -i input.json -o output.pdf -t "Your Custom Title"
./json_to_pdf_pandoc.py -i input.json -o output.pdf -t "Your Custom Title" -v # To log INFO messages
./json_to_pdf_pandoc.py -i input.json -o output.pdf -t "Your Custom Title" -vv # To log DEBUG messages
"""
import base64
import json
import logging
import os
import re
import subprocess
import tempfile
from argparse import ArgumentParser, RawDescriptionHelpFormatter

import requests


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
        "-v",
        "--verbose",
        action="count",
        default=0,
        dest="verbose",
        help="Increase verbosity of logging output",
    )
    parser.add_argument(
        "-i",
        "--input",
        required=True,
        help="Input JSON file",
    )
    parser.add_argument(
        "-o",
        "--output",
        required=True,
        help="Output PDF file",
    )
    parser.add_argument(
        "-t",
        "--title",
        required=True,
        help="Title for the document",
    )
    return parser.parse_args()


def get_image_as_base64(url):
    if not url:
        logging.warning("Empty URL provided")
        return None

    try:
        response = requests.get(url)
        response.raise_for_status()
        image_content = response.content
        image_base64 = base64.b64encode(image_content).decode("utf-8")
        file_extension = url.split(".")[-1].lower()
        if file_extension not in ["jpg", "jpeg", "png", "gif"]:
            file_extension = "png"  # Default to PNG if extension is not recognized
        return f"data:image/{file_extension};base64,{image_base64}"
    except requests.RequestException as e:
        logging.error(f"Error fetching image from {url}: {e}")
        return None


def detect_json_format(json_data):
    if isinstance(json_data, list) and len(json_data) > 0:
        first_item = json_data[0]
        if "authorName" in first_item and "tweetText" in first_item:
            return "new"
        elif "text" in first_item:
            return "old"
    return "unknown"


def json_to_markdown_old_format(json_data, title):
    logging.info("Converting JSON to Markdown with embedded images (old format)")
    markdown = f"""---
geometry: margin=1in
title: "{title}"
---

# {title}

"""

    for item in json_data:
        text = item["text"].strip()
        images = item.get("images", [])

        logging.debug(f"Processing text: {text[:50]}...")

        # Remove numbering from the beginning of the text
        text = re.sub(r"^\d+\s*\/?\s*", "", text)

        # Convert URLs to markdown links
        text = re.sub(r"(https?://\S+)", r"[\1](\1)", text)

        # Handle headers
        if text.startswith("If you like such threads"):
            logging.debug("Skipping last repeated tweet")
            continue  # Skip the last repeated tweet
        elif re.match(r"^[\d.]+\s*[)/]?\s*", text):
            markdown += f"## {text}\n\n"
        else:
            markdown += f"{text}\n\n"

        # Add images
        for image_url in images:
            if image_url.endswith(".svg"):
                logging.debug(f"Skipping SVG image: {image_url}")
                continue  # Skip SVG images

            image_base64 = get_image_as_base64(image_url)
            if image_base64:
                markdown += f"![Image]({image_base64})\n\n"
            else:
                logging.warning(f"Failed to embed image: {image_url}")
                markdown += f"![Image]({image_url})\n\n"

    logging.info("JSON to Markdown conversion with embedded images completed (old format)")
    return markdown


def json_to_markdown_new_format(json_data, title):
    logging.info("Converting JSON to Markdown with minimal content")
    markdown = f"""---
geometry: margin=1in
title: "{title}"
header-includes:
    - \\usepackage{{fancyhdr}}
    - \\pagestyle{{fancy}}
    - \\fancyhead[L]{{{title}}}
    - \\fancyfoot[C]{{Page \\thepage}}
---

# {title}

"""

    for item in json_data:
        handle = item.get("handle", "unknown_handle")
        tweet_text = item.get("tweetText", "").strip()
        tweet_images = item.get("tweetImages", [])

        logging.debug(f"Processing tweet from: @{handle}")

        # Add Twitter handle
        markdown += f"**@{handle}**\n\n"

        # Add tweet text
        if tweet_text:
            markdown += f"{tweet_text}\n\n"
        else:
            markdown += "*(No tweet text)*\n\n"

        # Add tweet images
        for image_url in tweet_images:
            image_base64 = get_image_as_base64(image_url)
            if image_base64:
                markdown += f"![Tweet Image]({image_base64})\n\n"
            else:
                logging.warning(f"Failed to embed tweet image: {image_url}")
                markdown += f"![Tweet Image]({image_url})\n\n"

        # Add horizontal line as separator
        markdown += "---\n\n"

    logging.info("JSON to Markdown conversion completed")
    return markdown


def json_to_markdown(json_data, title):
    format_type = detect_json_format(json_data)
    if format_type == "new":
        return json_to_markdown_new_format(json_data, title)
    elif format_type == "old":
        return json_to_markdown_old_format(json_data, title)
    else:
        raise ValueError("Unknown JSON format")


def markdown_to_pdf(markdown_content, output_file):
    logging.info("Converting Markdown to PDF using pandoc")

    with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False) as temp_md:
        temp_md.write(markdown_content)
        temp_md_path = temp_md.name

    try:
        subprocess.run(
            [
                "pandoc",
                temp_md_path,
                "-o",
                output_file,
                "--pdf-engine=xelatex",
                "--css=",  # This enables the CSS styles in the markdown
                "-V",
                "geometry:margin=1in",
                "--highlight-style=tango",
            ],
            check=True,
        )
        logging.info(f"PDF file '{output_file}' has been created.")
    except subprocess.CalledProcessError as e:
        logging.error(f"Error during PDF conversion: {e}")
    finally:
        os.unlink(temp_md_path)
        logging.debug(f"Temporary file {temp_md_path} has been removed.")


def main(args):
    logging.info(f"Reading JSON file: {args.input}")
    with open(args.input) as file:
        json_data = json.load(file)

    markdown_content = json_to_markdown(json_data, args.title)
    markdown_to_pdf(markdown_content, args.output)


if __name__ == "__main__":
    args = parse_args()
    setup_logging(args.verbose)
    main(args)
