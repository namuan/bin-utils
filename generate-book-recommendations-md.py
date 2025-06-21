#!/usr/bin/env -S uv run --quiet --script
# /// script
# ///
"""
Generate a Markdown document from a JSON file of tweets containing book suggestions.

Usage:
./generate-book-recommendations-md.py -h

./generate-book-recommendations-md.py -v # To log INFO messages
./generate-book-recommendations-md.py -vv # To log DEBUG messages
./generate-book-recommendations-md.py tweets.json
"""
import logging
import json
from argparse import ArgumentParser, RawDescriptionHelpFormatter
from pathlib import Path


def extract_book_info(tweet):
    """
    Extract book information from tweet text or image.
    Returns a tuple of (book_title, image_url) where book_title might be None if not in text.
    """
    return (tweet.get("tweetText")), (tweet.get("tweetImages"))


def generate_markdown(tweet_file):
    """
    Generate Markdown content from a JSON file of tweets.
    """
    logging.info(f"Processing file: {tweet_file}")
    try:
        with open(tweet_file, "r", encoding="utf-8") as f:
            tweets = json.load(f)
    except FileNotFoundError:
        logging.error(f"Error: File '{tweet_file}' not found.")
        return
    except json.JSONDecodeError:
        logging.error(f"Error: '{tweet_file}' is not a valid JSON file.")
        return

    markdown_content = "# Book Suggestions from Tweets\n\n"

    for tweet in tweets:
        author_name = tweet.get("authorName", "Unknown Author").split("\n@")[0].strip()
        book_title, image_url = extract_book_info(tweet)

        logging.debug(f"Processing tweet by {author_name}: title={book_title}, image={image_url}")
        if not (book_title and image_url):
            continue

        markdown_content += f"**by {author_name}**\n\n"

        if book_title:
            markdown_content += f"> {book_title}\n"

        if image_url:
            markdown_content += f"![Book Image]({image_url})\n\n"

    output_file = Path(tweet_file).with_suffix(".md")
    try:
        with open(output_file, "w", encoding="utf-8") as f:
            f.write(markdown_content)
        logging.info(f"Markdown file generated: {output_file}")
    except IOError as e:
        logging.error(f"Error writing to Markdown file: {e}")


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
    parser.add_argument("json_file", type=str, help="Path to the JSON file containing tweet data")
    return parser.parse_args()


def main(args):
    logging.debug(f"Starting script with verbosity level: {args.verbose}")
    logging.info(f"Processing JSON file: {args.json_file}")
    generate_markdown(args.json_file)


if __name__ == "__main__":
    args = parse_args()
    setup_logging(args.verbose)
    main(args)
