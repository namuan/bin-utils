#!/usr/bin/env python3
"""
A script to process a JSON file containing tweet data, extract tweet text and images,
identify book titles using Ollama LLM and vision models, and find Goodreads links for the books.

Usage:
python process_tweets.py <path_to_json_file> [--text-model TEXT_MODEL_NAME] [--vision-model VISION_MODEL_NAME]
"""

import argparse
import json
import logging
import sys
from typing import Dict, List, Tuple

import httpx
import ollama
from googlesearch import search

# Constants
NUM_SEARCH = 10
SEARCH_TIME_LIMIT = 30  # seconds


def setup_logging():
    """Set up basic logging configuration."""
    logging.basicConfig(level=logging.ERROR, format="%(asctime)s - %(levelname)s - %(message)s")


def read_json_file(file_path: str) -> List[Dict]:
    """
    Read and parse the JSON file.

    Args:
        file_path (str): Path to the JSON file.

    Returns:
        List[Dict]: List of tweet data dictionaries.
    """
    try:
        with open(file_path, encoding="utf-8") as file:
            return json.load(file)
    except json.JSONDecodeError:
        logging.error(f"Error decoding JSON from file: {file_path}")
        sys.exit(1)
    except OSError:
        logging.error(f"Error reading file: {file_path}")
        sys.exit(1)


def extract_book_titles_from_text(tweet_text: str, model: str) -> List[str] | None:
    """
    Extract book titles from tweet text using Ollama LLM.

    Args:
        tweet_text (str): The text of the tweet.
        model (str): The name of the Ollama model to use.

    Returns:
        List[str]: A list of extracted book titles or ["No book titles found"] if none are detected.
    """
    try:
        prompt = f"""Extract and list all book titles mentioned in the following tweet.
If no book titles are found, respond with exactly 'No book titles found'.
Otherwise, only return the list of book titles, one per line.
Be sure to capture complete titles, even if they span multiple words:

{tweet_text}"""
        response = ollama.chat(
            model=model,
            messages=[
                {
                    "role": "user",
                    "content": prompt,
                },
            ],
        )
        content = response["message"]["content"].strip()

        if content == "No book titles found":
            return None

        book_titles = content.split("\n")
        return [title.strip() for title in book_titles if title.strip()]
    except Exception as e:
        logging.error(f"Error in book title extraction from text: {str(e)}")
        return None


def download_image(image_url: str) -> bytes:
    """
    Download an image from a URL.

    Args:
        image_url (str): The URL of the image to download.

    Returns:
        bytes: The raw image data.
    """
    try:
        with httpx.Client() as client:
            response = client.get(image_url)
            response.raise_for_status()
            return response.content
    except httpx.RequestError as e:
        logging.error(f"Error downloading image from {image_url}: {str(e)}")
        return b""


def extract_book_titles_from_image(image_data: bytes, model: str) -> List[str] | None:
    """
    Extract book titles from an image using a vision-capable Ollama model.

    Args:
        image_data (bytes): The raw image data.
        model (str): The name of the vision-capable Ollama model to use.

    Returns:
        List[str]: A list of extracted book titles or ["No book titles found"] if none are detected.
    """
    try:
        prompt = """Analyze this image and list all book titles visible in it.
If no book titles are found, respond with exactly 'No book titles found'.
Otherwise, only return the list of book titles, one per line."""

        response = ollama.generate(model, prompt, images=[image_data])
        content = response.strip()

        if content == "No book titles found":
            return None

        book_titles = content.split("\n")
        return [title.strip() for title in book_titles if title.strip()]
    except Exception as e:
        logging.error(f"Error in book title extraction from image: {str(e)}")
        return None


def process_image(image_url: str, vision_model: str):
    """
    Process a single image URL to extract book titles.

    Args:
        image_url (str): The URL of the image to process.
        vision_model (str): The name of the vision-capable Ollama model to use.
    """
    image_data = download_image(image_url)
    if image_data:
        image_titles = extract_book_titles_from_image(image_data, vision_model)
        if image_titles:
            print(f"Book Titles from Image: {', '.join(image_titles)}")
            return image_titles
    return []


def process_tweets(tweets: List[Dict], text_model: str, vision_model: str) -> List[str]:
    """
    Process a list of tweets to extract book titles from text and images.

    Args:
        tweets (List[Dict]): A list of tweet data dictionaries.
        text_model (str): The name of the Ollama text model to use.
        vision_model (str): The name of the vision-capable Ollama model to use.

    Returns:
        List[str]: A list of all unique book titles found.
    """
    all_books = set()
    for tweet in tweets:
        tweet_text = tweet.get("tweetText", "").strip()
        tweet_images = tweet.get("tweetImages", [])

        if tweet_text:
            print(f"Tweet: {tweet_text}")
            # Extract book titles from text
            text_titles = extract_book_titles_from_text(tweet_text, text_model)
            if text_titles:
                print(f"📚 Books extracted fom Text: {', '.join(text_titles)}")
                all_books.update(text_titles)
            else:
                logging.info("No books found in text")
        elif tweet_images:
            image_titles = None
            if isinstance(tweet_images, list) and tweet_images:
                logging.info(f"Image URL: {tweet_images[0]}")
                image_titles = process_image(tweet_images[0], vision_model)
            elif isinstance(tweet_images, str) and tweet_images:
                logging.info(f"Image URL: {tweet_images}")
                image_titles = process_image(tweet_images, vision_model)

            if image_titles:
                print(f"🪩 Books extracted from Image: {', '.join(image_titles)}")
                all_books.update(image_titles)
        else:
            print("No text or images in this tweet")

    return list(all_books)


def google_search(query: str) -> List[str]:
    """
    Perform a Google search and return the top results.

    Args:
        query (str): The search query.

    Returns:
        List[str]: A list of URLs from the search results.
    """
    try:
        return list(search(f"{query} site:goodreads.com", num_results=NUM_SEARCH))
    except Exception as e:
        logging.error(f"Error performing Google search: {str(e)}")
        return []


def extract_goodreads_link(urls: List[str]) -> str:
    """
    Extract the Goodreads link from a list of URLs.

    Args:
        urls (List[str]): A list of URLs.

    Returns:
        str: The Goodreads link or an empty string if not found.
    """
    for url in urls:
        if "goodreads.com/book/show/" in url:
            return url
    return ""


def process_books_with_goodreads(books: List[str]) -> List[Tuple[str, str]]:
    """
    Process the list of books and find Goodreads links for each.

    Args:
        books (List[str]): A list of book titles.

    Returns:
        List[Tuple[str, str]]: A list of tuples containing book titles and their Goodreads links.
    """
    books_with_links = []
    for book in books:
        logging.info(f"Searching for Goodreads link for: {book}")
        search_results = google_search(book)
        goodreads_link = extract_goodreads_link(search_results)
        books_with_links.append((book, goodreads_link))
    return books_with_links


def main(file_path: str, text_model: str, vision_model: str):
    """
    Main function to orchestrate the tweet processing, book title extraction, and Goodreads link finding.

    Args:
        file_path (str): Path to the JSON file containing tweet data.
        text_model (str): The name of the Ollama text model to use.
        vision_model (str): The name of the vision-capable Ollama model to use.
    """
    tweets = read_json_file(file_path)
    print(f"Total tweets loaded: {len(tweets)}")
    print("Processing the first 10 tweets for testing purposes...")
    all_books = process_tweets(tweets, text_model, vision_model)

    print("\nAll Books Found:")
    if all_books:
        books_with_links = process_books_with_goodreads(all_books)
        for i, (book, link) in enumerate(books_with_links, 1):
            if link:
                print(f"{i}. {book}: {link}")
            else:
                print(f"{i}. {book}: No Goodreads link found")
    else:
        print("No books were found in any of the processed tweets.")


if __name__ == "__main__":
    setup_logging()
    parser = argparse.ArgumentParser(
        description="Process tweets, extract book titles using Ollama LLM, and find Goodreads links."
    )
    parser.add_argument("file_path", help="Path to the JSON file containing tweet data")
    parser.add_argument("--text-model", default="llama2", help="Name of the Ollama text model to use (default: llama2)")
    parser.add_argument(
        "--vision-model", default="llava", help="Name of the vision-capable Ollama model to use (default: llava)"
    )
    args = parser.parse_args()

    main(args.file_path, args.text_model, args.vision_model)
