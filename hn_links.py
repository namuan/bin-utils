#!/usr/bin/env python3
"""
Grab links from HN Post and generate Markdown post with image thumbnails
* To regenerate thumbnail, just delete the image file under thumbnails folder inside the post directory.

Usage: $ python hn-links.py -l https://news.ycombinator.com/item?id=25381191
"""

import logging
import os
import subprocess
from argparse import ArgumentParser, RawDescriptionHelpFormatter
from pathlib import Path
from urllib.parse import urlparse, parse_qs

import requests
from bs4 import BeautifulSoup
from jinja2 import Environment, FileSystemLoader
from requests import HTTPError
from slug import slug

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


def run_command(command):
    logging.info(f"⚡ {command}")
    return subprocess.check_output(command, shell=True).decode("utf-8")


def fetch_html(url, post_html_page_file):
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
            "Unable to fetch URL %s - HTTP: %s",
            url,
            err,
        )
    except Exception as err:
        logging.error("Unable to fetch URL %s - %s", url, err)

    return None


def load_from_cache(post_html_page_file):
    if post_html_page_file.exists():
        logging.info(f"Loading page from cache {post_html_page_file}")
        return post_html_page_file.read_text(encoding=UTF_ENCODING)
    else:
        return None


def html_parser_from(page_html):
    return BeautifulSoup(page_html, "html.parser")


class CreateOutputFolder(object):
    """Create output folder using Post id in the temporary folder"""

    def run(self, context):
        download_folder = context.get("download_folder")
        hn_post_id = context.get("hn_post_id")
        target_folder = Path(download_folder) / hn_post_id
        child_links_folder = target_folder / "links"
        thumbnails_folder = target_folder / "thumbnails"

        for f in [target_folder, child_links_folder, thumbnails_folder]:
            f.mkdir(parents=True, exist_ok=True)

        context["target_folder"] = target_folder.as_posix()
        context["child_links_folder"] = child_links_folder
        context["thumbnails_folder"] = thumbnails_folder


class GrabPostHtml(object):
    """Use requests to download HTML using a browser user agent"""

    def run(self, context):
        hn_link = context.get("hn_link")
        target_folder = context.get("target_folder")
        post_html_page_file = Path(target_folder) / "hn_post.html"
        page_html = load_from_cache(post_html_page_file) or fetch_html(
            hn_link, post_html_page_file
        )
        context["page_html"] = page_html


class ParsePostHtml(object):
    """Create BeautifulSoap parser from html"""

    def run(self, context):
        page_html = context.get("page_html")
        context["bs"] = html_parser_from(page_html)


class GrabPostTitle(object):
    """Extract page title using BeautifulSoap HTML parser"""

    def run(self, context):
        bs = context.get("bs")
        context["hn_post_title"] = bs.title.string


class ExtractAllLinksFromPost(object):
    """Extract all links"""

    def run(self, context):
        bs = context.get("bs")
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
        all_links = context.get("all_links")
        valid_links = [link for link in all_links if self.is_valid_link(link)]
        context["valid_links"] = valid_links


class GrabChildLinkTitle(object):
    """Get page title for each valid link"""

    def page_title_from(self, target_folder, link_in_comment):
        page_slug = slug(link_in_comment)
        page_path = f"{page_slug}.html"

        post_html_page_file = Path(target_folder) / page_path
        page_html = load_from_cache(post_html_page_file) or fetch_html(
            link_in_comment, post_html_page_file
        )
        bs = html_parser_from(page_html)
        return bs.title.string if bs.title else link_in_comment

    def run(self, context):
        valid_links = context.get("valid_links")
        child_links_folder = context.get("child_links_folder")
        links_with_titles = [
            (self.stripped(self.page_title_from(child_links_folder, link)), link)
            for link in valid_links
        ]
        context["links_with_titles"] = links_with_titles

    def stripped(self, page_title: str):
        return page_title.strip()


class GrabScreenThumbnail(object):
    """For each link, get screen thumbnail"""

    def thumbnail(self, thumbnails_folder, page_link):
        page_slug = slug(page_link)
        target_path = thumbnails_folder / f"{page_slug}.png"
        cmd = f"./thumbnail_generator.py -i {page_link} -o {target_path}"
        if target_path.exists():
            logging.info(
                f"Thumbnail already exists for {page_link}. Run {cmd} to update it"
            )
            return target_path.as_posix()

        run_command(cmd)
        return target_path

    def run(self, context):
        links_with_titles = context.get("links_with_titles")
        thumbnails_folder = context.get("thumbnails_folder")

        links_with_metadata = [
            (page_title, page_link, self.thumbnail(thumbnails_folder, page_link))
            for page_title, page_link in links_with_titles
        ]
        context["links_with_metadata"] = links_with_metadata


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
        markdown_text = context.get("markdown_text")
        target_folder = context.get("target_folder")
        markdown_file_path = Path(target_folder) / "hn_links.md"
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
        GrabChildLinkTitle(),
        GrabScreenThumbnail(),
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
