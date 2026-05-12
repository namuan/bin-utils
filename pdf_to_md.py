#!/usr/bin/env -S uv run --quiet --script
# /// script
# dependencies = [
#   "pymupdf",
# ]
# ///
"""
Convert PDF article to Markdown

Extracts text while preserving headings, paragraphs, and basic structure.

Usage:
    ./pdf_to_md.py <input.pdf> [-o output.md]

    ./pdf_to_md.py article.pdf -o article.md
    ./pdf_to_md.py -v article.pdf
    ./pdf_to_md.py -vv article.pdf
"""
import logging
import re
import sys
from argparse import ArgumentParser, RawDescriptionHelpFormatter
from pathlib import Path

import fitz  # pymupdf


def setup_logging(verbosity):
    logging_level = logging.WARNING
    if verbosity == 1:
        logging_level = logging.INFO
    elif verbosity >= 2:
        logging_level = logging.DEBUG

    logging.basicConfig(
        handlers=[logging.StreamHandler()],
        format="%(asctime)s - %(filename)s:%(lineno)d - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        level=logging_level,
    )
    logging.captureWarnings(capture=True)


def parse_args():
    parser = ArgumentParser(description=__doc__, formatter_class=RawDescriptionHelpFormatter)
    parser.add_argument("input_pdf", type=Path, help="Path to the PDF file to convert")
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        default=None,
        help="Output Markdown file (default: stdout)",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="count",
        default=0,
        dest="verbose",
        help="Increase verbosity of logging output",
    )
    return parser.parse_args()


def classify_heading(text: str, font_size: float, page_width: float) -> str | None:
    stripped = text.strip()
    if not stripped or len(stripped) < 2:
        return None
    # Heuristic: larger font or centered short text → likely a heading
    is_large = font_size > 16
    is_short = len(stripped.split()) <= 15
    if is_large and is_short:
        return f"## {stripped}"
    return None


def convert_pdf_to_markdown(pdf_path: Path) -> str:
    doc = fitz.open(str(pdf_path))
    pages_md = []

    for page_num, page in enumerate(doc):
        logging.debug(f"Processing page {page_num + 1}/{len(doc)}")
        blocks = page.get_text("dict", sort=True)["blocks"]
        page_blocks = []
        page_width = page.rect.width

        for block in blocks:
            if block.get("type") != 0:  # skip images
                continue

            lines = block.get("lines", [])
            block_text = ""
            fonts_in_block = set()

            for line in lines:
                spans = line.get("spans", [])
                for span in spans:
                    fonts_in_block.add(round(span.get("size", 12), 1))

                line_text = "".join(s.get("text", "") for s in spans)
                block_text += line_text + " "

            block_text = block_text.strip()
            if not block_text:
                continue

            # Determine if this is a heading
            avg_font = max(fonts_in_block) if fonts_in_block else 12
            heading = classify_heading(block_text, avg_font, page_width)

            if heading:
                page_blocks.append(heading)
            else:
                page_blocks.append(block_text)

        pages_md.append("\n\n".join(page_blocks))

    doc.close()
    result = "\n\n".join(pages_md)
    # Clean up extra whitespace
    result = re.sub(r"\n{3,}", "\n\n", result)
    return result.strip()


def main(args):
    pdf_path = args.input_pdf
    if not pdf_path.exists():
        logging.error(f"Input file not found: {pdf_path}")
        sys.exit(1)

    logging.info(f"Converting {pdf_path} to Markdown")
    markdown = convert_pdf_to_markdown(pdf_path)

    if args.output:
        args.output.write_text(markdown, encoding="utf-8")
        logging.info(f"Written to {args.output}")
    else:
        print(markdown)


if __name__ == "__main__":
    args = parse_args()
    setup_logging(args.verbose)
    main(args)
