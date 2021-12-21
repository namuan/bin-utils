#!/usr/bin/env python3
"""
Grab links from HN Post and generate Markdown post with image thumbnails
Usage: $ python hn-links.py -l https://news.ycombinator.com/item?id=25381191
"""

import logging
import os
from argparse import ArgumentParser, RawDescriptionHelpFormatter
from pathlib import Path
from urllib.parse import urlparse, parse_qs

import requests
from bs4 import BeautifulSoup
from jinja2 import Environment, FileSystemLoader
from requests import HTTPError

UTF_ENCODING = "utf-8"

logging.basicConfig(
    handlers=[
        logging.StreamHandler(),
    ],
    format="%(asctime)s - %(filename)s:%(lineno)d - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    level=logging.INFO,
)
logging.captureWarnings(capture=True)


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

    def fetch_html(self, url, post_html_page_file):
        logging.info(f"Fetching HTML title for {url}")
        try:
            user_agent = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_10_3) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/44.0.2403.89 Safari/537.36"
            headers = {"User-Agent": user_agent}
            page = requests.get(url, headers=headers)
            page_html = page.text
            logging.info(f"Caching page {post_html_page_file}")
            post_html_page_file.write_text(page_html, encoding=UTF_ENCODING)
            return page_html
        except HTTPError as err:
            logging.error(
                "Unable to fetch URL %s - HTTP Code: %s - %s",
                url,
                err.code,
                err.reason,
            )
        except Exception as err:
            logging.error("Unable to fetch URL %s - %s", url, err)

        return None

    def load_from_cache(self, post_html_page_file):
        if post_html_page_file.exists():
            logging.info(f"Loading page from cache {post_html_page_file}")
            return post_html_page_file.read_text(encoding=UTF_ENCODING)
        else:
            return None

    def run(self, context):
        hn_link = context.get("hn_link")
        target_folder = context.get("target_folder")
        hn_post_id = context.get("hn_post_id")
        post_html_page_file = Path(target_folder) / f"{hn_post_id}.html"

        page_html = self.load_from_cache(post_html_page_file) or self.fetch_html(
            hn_link, post_html_page_file
        )
        bs = BeautifulSoup(page_html, "html.parser")
        context["bs"] = bs


class ParsePostHtml(object):
    """Create BeautifulSoap parser from html"""

    def run(self, context):
        bs = context["bs"]
        page_title = bs.title.string
        context["page_title"] = page_title


class GrabPostTitle(object):
    """Extract page title using BeautifulSoap HTML parser"""

    def run(self, context):
        bs = context["bs"]
        context["post_title"] = bs.title.string


class ExtractAllLinksFromPost(object):
    """Extract all links"""

    def run(self, context):
        bs = context["bs"]
        all_links = [link.get("href") for link in bs.find_all("a", href=True)]
        context["all_links"] = all_links


class KeepValidLinks(object):
    """Only keep interesting links"""

    def is_valid_link(self, link):
        known_domains = ["ycombinator", "algolia"]

        def has_known_domain(post_link):
            return any(map(lambda l: l in post_link, known_domains))

        return link.startswith("http") and not has_known_domain(link)

    def run(self, context):
        all_links = context["all_links"]
        valid_links = [link for link in all_links if self.is_valid_link(link)]
        context["valid_links"] = valid_links


class GrabLinkTitleAndThumbnail(object):
    """For each link, get HTML title and save thumbnail"""

    def run(self, context):
        pass


class GenerateMarkdown(object):
    """Generate Markdown using the data in context"""

    def __init__(self):
        template_folder = "templates"
        template_dir = (
            os.path.dirname(os.path.abspath(__file__)) + "/" + template_folder
        )
        self.jinja_env = Environment(
            loader=FileSystemLoader(template_dir), trim_blocks=True
        )

    def render_markdown(self, context):
        rendered = self.jinja_env.get_template("hn_post_links.md.j2").render(context)
        return rendered

    def run(self, context):
        markdown_text = self.render_markdown(context)
        context["markdown_text"] = markdown_text


class SaveMarkdown(object):
    """Save generated Markdown in a target document"""

    def run(self, context):
        markdown_text = context["markdown_text"]
        target_folder = context["target_folder"]
        hn_post_id = context["hn_post_id"]
        markdown_file_path = Path(target_folder) / f"{hn_post_id}.md"
        markdown_file_path.write_text(markdown_text, encoding=UTF_ENCODING)


def run_step(step, context):
    logging.info(step.__class__.__name__ + " ➡️ " + step.__doc__)
    if context.get("verbose"):
        logging.info(context)
    step.run(context)
    logging.info("-" * 100)


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
        KeepValidLinks(),
        GrabLinkTitleAndThumbnail(),
        GenerateMarkdown(),
        SaveMarkdown(),
    ]
    for step in procedure:
        run_step(step, context)
    logging.info("Done.")


def parse_args():
    parser = ArgumentParser(
        description=__doc__, formatter_class=RawDescriptionHelpFormatter
    )
    parser.add_argument(
        "-l", "--hn-link", required=True, type=str, help="Link to HN Post"
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
    args = parse_args()
    main(args)
