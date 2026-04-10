#!/usr/bin/env -S uv run --quiet --script
# /// script
# dependencies = [
#   "pymupdf",
# ]
# ///
"""
PDF Search & Replace utility

Usage:
./pdf_replace.py your_file.pdf <search_term> <replace_term>

Note: Replacement text is rendered in Helvetica, which may differ from the
original font. For watermark removal, this is usually acceptable.
"""

import os
import sys
import fitz  # pymupdf


def main():
    if len(sys.argv) < 4:
        print("Usage: ./pdf_replace.py <pdf_file> <search_term> <replace_term>")
        sys.exit(1)

    pdf_path = sys.argv[1]
    if not os.path.exists(pdf_path):
        print(f"File not found: {pdf_path}")
        sys.exit(1)

    search_term = sys.argv[2]
    replace_term = sys.argv[3]

    if not search_term:
        print("❌ Search term cannot be empty")
        sys.exit(1)

    print(f"✅ Opening: {pdf_path}")
    print(f"\n🔍 Searching for: '{search_term}'")

    doc = fitz.open(pdf_path)
    modified_count = 0

    for page_num, page in enumerate(doc, start=1):
        instances = page.search_for(search_term)
        if not instances:
            continue

        for rect in instances:
            page.add_redact_annot(rect, replace_term)

        page.apply_redactions()
        modified_count += len(instances)
        print(f"✅ Replaced {len(instances)} occurrence(s) on page {page_num}")

    if modified_count == 0:
        print("\n⚠️  No matches found for the search term.")
        sys.exit(0)

    output_path = os.path.splitext(pdf_path)[0] + "_modified.pdf"
    doc.save(output_path, garbage=4, deflate=True)
    doc.close()

    print(f"\n✅ Done! Total replacements made: {modified_count}")
    print(f"📖 Modified PDF saved to: {output_path}")


if __name__ == "__main__":
    main()
