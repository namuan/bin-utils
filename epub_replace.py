#!/usr/bin/env -S uv run --quiet --script
# /// script
# dependencies = [
#   "ebooklib",
#   "beautifulsoup4",
# ]
# ///
"""
EPUB Search & Replace utility

Usage:
./epub_replace.py your_book_file.epub
"""

import os
import sys
from ebooklib import epub
from bs4 import BeautifulSoup


def main():
    if len(sys.argv) < 4:
        print("Usage: ./epub_replace.py <epub_file> <search_term> <replace_term>")
        sys.exit(1)

    epub_path = sys.argv[1]
    if not os.path.exists(epub_path):
        print(f"File not found: {epub_path}")
        sys.exit(1)

    print(f"✅ Opening: {epub_path}")

    # Get search and replace terms from command line
    search_term = sys.argv[2]
    replace_term = sys.argv[3]

    if not search_term:
        print("❌ Search term cannot be empty")
        sys.exit(1)

    # Open epub
    book = epub.read_epub(epub_path)
    modified_count = 0

    print(f"\n🔍 Searching for: '{search_term}'")

    # Iterate all documents
    for item in book.get_items():
        if item.get_type() == 9:
            content = item.get_content().decode("utf-8")

            if search_term in content:
                soup = BeautifulSoup(content, "html.parser")
                occurrences = 0

                # Only replace text nodes, skip tags/attributes
                for text_node in soup.find_all(string=True):
                    if search_term in text_node:
                        new_text = text_node.replace(search_term, replace_term)
                        text_node.replace_with(new_text)
                        occurrences += 1

                if occurrences > 0:
                    item.set_content(str(soup).encode("utf-8"))
                    modified_count += occurrences
                    print(
                        f"✅ Replaced {occurrences} occurrence(s) in {item.get_name()}"
                    )

    if modified_count == 0:
        print("\n⚠️ No matches found for the search term.")
        sys.exit(0)

    # Save output file
    output_path = os.path.splitext(epub_path)[0] + "_modified.epub"
    epub.write_epub(output_path, book, {})

    print(f"\n✅ Done! Total replacements made: {modified_count}")
    print(f"📖 Modified EPUB saved to: {output_path}")


if __name__ == "__main__":
    main()
