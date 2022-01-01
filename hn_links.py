#!/usr/bin/env python3
r"""
Grab links from HN Post and generate Markdown post with image thumbnails
It also creates a Hugo blog post from Markdown and images generated

SUPPORT: To regenerate thumbnail, just delete the image file under thumbnails folder inside the post directory.
SUPPORT: To remove any link from the blog post, delete the entry after the post is created **in the blog directory**
Note down all the links somewhere then run the following command from blog directory to delete them
E.g. Image links will be like

![](/images/2021/12/21/httpsunixstackexchangecoma88682.png)
![](/images/2021/12/21/httpscleaveapp.png)

$ pbpaste | awk -F\/ '{print $6}' | tr -d ')' | while read img; do find . -name $img -delete; done # noqa: W605

Usage:
$ python hn-links.py -l https://news.ycombinator.com/item?id=25381191 -b <blog_directory> --open-in-editor
"""

import logging
import os
from argparse import ArgumentParser, RawDescriptionHelpFormatter
from datetime import datetime
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from bs4 import BeautifulSoup
from py_executable_checklist.workflow import WorkflowBase, run_command, run_workflow

from common_utils import fetch_html_page, html_parser_from

UTF_ENCODING = "utf-8"


# Common functions


def fetch_html(url, post_html_page_file):
    logging.info(f"Fetching HTML title for {url}")
    if post_html_page_file.exists():
        logging.info(f"🌕 Loading page from cache {post_html_page_file}")
        return post_html_page_file.read_text(encoding=UTF_ENCODING)

    page_html = fetch_html_page(url)
    logging.info(f"Caching page {post_html_page_file}")
    post_html_page_file.write_text(page_html, encoding=UTF_ENCODING)
    return page_html


def relative_image_directory():
    now = datetime.now()
    year = now.strftime("%Y")
    month = now.strftime("%m")
    day = now.strftime("%d")
    return f"images/{year}/{month}/{day}"


# Workflow steps


class CreateOutputFolder(WorkflowBase):
    """Create output folder using Post id in the temporary folder"""

    hn_link: str

    def run(self, context):
        hn_post_id = parse_qs(urlparse(self.hn_link).query).get("id")[0]
        download_folder = f"{os.getcwd()}/.temp"

        target_folder = Path(download_folder) / hn_post_id
        child_links_folder = target_folder / "links"
        thumbnails_folder = target_folder / "thumbnails"

        for f in [target_folder, child_links_folder, thumbnails_folder]:
            f.mkdir(parents=True, exist_ok=True)

        # output
        context["hn_post_id"] = hn_post_id
        context["target_folder"] = target_folder
        context["child_links_folder"] = child_links_folder
        context["thumbnails_folder"] = thumbnails_folder


class GrabPostHtml(WorkflowBase):
    """Use requests to download HTML using a browser user agent"""

    hn_link: str
    target_folder: str

    def run(self, context):
        post_html_page_file = Path(self.target_folder) / "hn_post.html"
        page_html = fetch_html(self.hn_link, post_html_page_file)

        # output
        context["page_html"] = page_html


class ParsePostHtml(WorkflowBase):
    """Create BeautifulSoap parser from html"""

    page_html: str

    def run(self, context):
        # output
        context["bs"] = html_parser_from(self.page_html)


class GrabPostTitle(WorkflowBase):
    """Extract page title using BeautifulSoap HTML parser"""

    bs: BeautifulSoup

    def run(self, context):
        # output
        context["hn_post_title"] = self.bs.title.string


class ExtractAllLinksFromPost(WorkflowBase):
    """Extract all links"""

    bs: BeautifulSoup

    def run(self, context):
        all_links = {link.get("href") for link in self.bs.find_all("a", href=True)}

        # output
        context["all_links"] = all_links


class WriteLinksToFile(WorkflowBase):
    """Write all links to file so that the next script can read them"""

    all_links: set

    def run(self, context):
        links_file = Path(context["target_folder"]) / "links.txt"
        links_file.write_text("\n".join(self.all_links), encoding=UTF_ENCODING)

        context["links_file"] = links_file


class CallLinksToHugoScript(WorkflowBase):
    """Call other script to download thumbnails and generate Hugo post"""

    links_file: Path
    hn_post_title: str
    blog_directory: str

    def run(self, _):
        cmd = (
            f"./venv/bin/python3 links_to_hugo.py "
            f'--links-file "{self.links_file}" '
            f'--post-title "{self.hn_post_title}" '
            f'--blog-directory "{self.blog_directory}"  '
            f"--open-in-editor"
        )
        run_command(cmd)


# Workflow definition


def workflow_steps():
    return [
        CreateOutputFolder,
        GrabPostHtml,
        ParsePostHtml,
        GrabPostTitle,
        ExtractAllLinksFromPost,
        WriteLinksToFile,
        CallLinksToHugoScript,
    ]


# Boilerplate


def setup_logging():
    logging.basicConfig(
        handlers=[logging.StreamHandler()],
        format="%(asctime)s - %(filename)s:%(lineno)d - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        level=logging.INFO,
    )
    logging.captureWarnings(capture=True)


def main(args):
    context = args.__dict__
    run_workflow(context, workflow_steps())


def parse_args():
    parser = ArgumentParser(description=__doc__, formatter_class=RawDescriptionHelpFormatter)
    parser.add_argument("-l", "--hn-link", required=True, type=str, help="Link to HN Post")
    parser.add_argument(
        "-b",
        "--blog-directory",
        type=str,
        required=True,
        help="Full path to blog directory",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        default=False,
        dest="verbose",
        help="Display context variables at each step",
    )
    return parser.parse_args()


if __name__ == "__main__":
    setup_logging()
    args = parse_args()
    main(args)
