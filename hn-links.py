#!/usr/bin/env python3
"""
Grab links from HN Post and generate Markdown post with image thumbnails
Usage: $ python hn-links.py -l https://news.ycombinator.com/item?id=25381191
"""

import os
from argparse import ArgumentParser, RawDescriptionHelpFormatter
from pathlib import Path
from urllib.parse import urlparse, parse_qs


class CreateOutputFolder(object):
    """Create output folder using Post id in the temporary folder"""

    def run(self, context):
        download_folder = context["download_folder"]
        hn_post_id = context["hn_post_id"]
        target_folder = Path(download_folder) / hn_post_id
        target_folder.mkdir(parents=True, exist_ok=True)
        context["target_folder"] = target_folder.as_posix()


class GrabPostHtml(object):
    """Use requests to download HTML using a browser user agent"""

    def run(self, context):
        pass


class ParsePostHtml(object):
    """Create BeautifulSoap parser from html"""

    def run(self, context):
        pass


class GrabPostTitle(object):
    """Extract page title using BeautifulSoap HTML parser"""

    def run(self, context):
        pass


class ExtractAllLinksFromPost(object):
    """Extract all links"""

    def run(self, context):
        pass


class GrabLinkTitleAndThumbnail(object):
    """For each link, get HTML title and save thumbnail"""

    def run(self, context):
        pass


class ExportMarkdownPage(object):
    """Export Markdown page using the data in context"""

    def run(self, context):
        pass


def run_step(step, context):
    print(step.__class__.__name__ + " ➡️ " + step.__doc__)
    step.run(context)
    print("-" * 100)


def main(args):
    context = args.__dict__
    hn_link = context.get("hn_link")
    post_id = parse_qs(urlparse(hn_link).query).get("id")[0]
    download_folder = f"{os.getcwd()}/.temp"

    context["hn_post_id"] = post_id
    context["download_folder"] = download_folder

    procedure = [
        CreateOutputFolder(),
        GrabPostHtml(),
        ParsePostHtml(),
        GrabPostTitle(),
        ExtractAllLinksFromPost(),
        GrabLinkTitleAndThumbnail(),
        ExportMarkdownPage(),
    ]
    for step in procedure:
        run_step(step, context)
    print("Done.")


def parse_args():
    parser = ArgumentParser(
        description=__doc__, formatter_class=RawDescriptionHelpFormatter
    )
    parser.add_argument(
        "-l", "--hn-link", required=True, type=str, help="Link to HN Post"
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    main(args)
