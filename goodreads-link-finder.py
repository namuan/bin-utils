#!/usr/bin/env python
"""
A script to find Goodreads URLs for a list of book titles using Google search.

Usage:
./goodreads-link-finder.py -h

./goodreads-link-finder.py -v  # To log INFO messages
./goodreads-link-finder.py -vv # To log DEBUG messages
"""
import logging
from argparse import ArgumentParser, RawDescriptionHelpFormatter

import googlesearch


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
    return parser.parse_args()


def get_goodreads_url(title):
    try:
        url = next(googlesearch.search(title + " Goodreads", num_results=1), None)
        if url:
            logging.info(f"Found Goodreads URL for '{title}': {url}")
            return url
        else:
            logging.warning(f"No Goodreads URL found for '{title}'")
            return None
    except Exception as e:
        logging.error(f"Error finding Goodreads URL for '{title}': {str(e)}")
        return None


def save_book(conn, title, goodreads_url):
    cursor = conn.cursor()
    cursor.execute(
        """
    INSERT INTO Books (Title, GoodreadsUrl)
    VALUES (?, ?)
    ON CONFLICT(Title) DO UPDATE SET
        GoodreadsUrl = excluded.GoodreadsUrl,
        LastUpdated = CURRENT_TIMESTAMP
    """,
        (title, goodreads_url),
    )
    conn.commit()
    logging.info(f"Saved book: {title}")


def main(args):
    book_titles = [
        "A Language Older Than Words",
        "A Pattern Language",
        "Against the Odds (James Dyson autobio)",
    ]

    for title in book_titles:
        logging.info(f"Processing book: {title}")
        goodreads_url = get_goodreads_url(title)
        print(f"**{title}** - {goodreads_url or 'No URL found'}")


if __name__ == "__main__":
    args = parse_args()
    setup_logging(args.verbose)
    main(args)
