#!/usr/bin/env python3
"""
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
from argparse import ArgumentParser
from argparse import RawDescriptionHelpFormatter
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse, parse_qs

import requests
from bs4 import BeautifulSoup
from jinja2 import Environment, FileSystemLoader
from requests import HTTPError
from slug import slug

from common.workflow import run_command, run_workflow

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


def relative_image_directory():
    now = datetime.now()
    year = now.strftime("%Y")
    month = now.strftime("%m")
    day = now.strftime("%d")
    return f"images/{year}/{month}/{day}"


class CreateOutputFolder:
    """Create output folder using Post id in the temporary folder"""

    def run(self, context):
        hn_link = context.get("hn_link")
        hn_post_id = parse_qs(urlparse(hn_link).query).get("id")[0]
        download_folder = f"{os.getcwd()}/.temp"

        target_folder = Path(download_folder) / hn_post_id
        child_links_folder = target_folder / "links"
        thumbnails_folder = target_folder / "thumbnails"

        for f in [target_folder, child_links_folder, thumbnails_folder]:
            f.mkdir(parents=True, exist_ok=True)

        context["hn_post_id"] = hn_post_id
        context["target_folder"] = target_folder.as_posix()
        context["child_links_folder"] = child_links_folder
        context["thumbnails_folder"] = thumbnails_folder


class GrabPostHtml:
    """Use requests to download HTML using a browser user agent"""

    def run(self, context):
        hn_link = context.get("hn_link")
        target_folder = context.get("target_folder")
        post_html_page_file = Path(target_folder) / "hn_post.html"
        page_html = load_from_cache(post_html_page_file) or fetch_html(
            hn_link, post_html_page_file
        )
        context["page_html"] = page_html


class ParsePostHtml:
    """Create BeautifulSoap parser from html"""

    def run(self, context):
        page_html = context.get("page_html")
        context["bs"] = html_parser_from(page_html)


class GrabPostTitle:
    """Extract page title using BeautifulSoap HTML parser"""

    def run(self, context):
        bs = context.get("bs")
        context["hn_post_title"] = bs.title.string


class ExtractAllLinksFromPost:
    """Extract all links"""

    def run(self, context):
        bs = context.get("bs")
        all_links = [link.get("href") for link in bs.find_all("a", href=True)]
        context["all_links"] = all_links


class KeepValidLinks:
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


class GrabChildLinkTitle:
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


class GrabScreenThumbnail:
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


class GenerateMarkdown:
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


class SaveMarkdown:
    """Save generated Markdown in a target document"""

    def run(self, context):
        markdown_text = context.get("markdown_text")
        target_folder = context.get("target_folder")
        markdown_file_path = Path(target_folder) / "hn_links.md"
        markdown_file_path.write_text(markdown_text, encoding=UTF_ENCODING)


class LoadMarkdownFile:
    """Load file from HN Post directory"""

    def run(self, context):
        target_folder = context.get("target_folder")
        markdown_file = Path(target_folder) / "hn_links.md"
        md_content = markdown_file.read_text()
        context["md_content"] = md_content


class AddHugoHeader:
    """Add blog header with metadata"""

    def run(self, context):
        md_content = context["md_content"]
        post_date = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
        post_title = md_content.splitlines()[0].replace("#", "").strip()

        post_header = f"""+++
    date = {post_date}
    title = "{post_title}"
    description = ""
    slug = ""
    tags = ["hacker-news-links"]
    categories = []
    externalLink = ""
    series = []
+++
"""
        post_with_header = (
            post_header + os.linesep + os.linesep.join(md_content.splitlines()[2:])
        )
        context["post_with_header"] = post_with_header
        post_file_name = slug(post_title) + ".md"
        context["post_file_name"] = post_file_name


class UpdateLinksInMarkdown:
    """Use relative links in Markdown to point to images"""

    def run(self, context):
        post_with_header = context["post_with_header"]
        target_folder = context.get("target_folder")
        thumbnails_directory = Path(target_folder) / "thumbnails"
        replace_from = f"![]({thumbnails_directory.as_posix()}"
        replace_with = f"![](/{relative_image_directory()}"
        md_with_updated_links = post_with_header.replace(replace_from, replace_with)
        context["md_with_updated_links"] = md_with_updated_links


class WriteBlogPost:
    """Write to blog directory with correct file name"""

    def run(self, context):
        md_with_updated_links = context.get("md_with_updated_links")
        blog_directory = context.get("blog_directory")
        post_file_name = context["post_file_name"]
        context["blog_page"] = "{}/content/posts/{}".format(
            blog_directory, post_file_name
        )
        Path(context["blog_page"]).write_text(md_with_updated_links)
        print("Created note at {}".format(context["blog_page"]))


class CompressImages:
    """Resize images and compress them"""

    def run(self, context):
        blog_directory = context.get("blog_directory")
        target_folder = context.get("target_folder")
        for img in Path(target_folder).glob("thumbnails/*"):
            img_name = img.name
            img_path = img.as_posix()
            target_path = Path(
                "{}/static/{}/{}".format(
                    blog_directory, relative_image_directory(), img_name
                )
            )
            if target_path.exists():
                continue

            Path(target_path).parent.mkdir(parents=True, exist_ok=True)
            run_command(
                f"convert {img_path} -resize 640x480 -quality 50% {target_path}"
            )


class OpenInEditor:
    """Open blog post in editor defined by the environment variable EDITOR"""

    def run(self, context):
        open_in_editor = context["open_in_editor"]
        if not open_in_editor:
            return
        blog_directory = context.get("blog_directory")
        editor = os.environ.get("EDITOR")
        print(f"Opening {blog_directory} in {editor}")
        run_command(f"{editor} {blog_directory}")


# Workflow definition
workflow_process = [
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
    LoadMarkdownFile(),
    AddHugoHeader(),
    UpdateLinksInMarkdown(),
    WriteBlogPost(),
    CompressImages(),
    OpenInEditor(),
]


# Boilerplate -----------------------------------------------------------------
def main(args):
    context = args.__dict__
    run_workflow(context, workflow_process)


def parse_args():
    parser = ArgumentParser(
        description=__doc__, formatter_class=RawDescriptionHelpFormatter
    )
    parser.add_argument(
        "-l", "--hn-link", required=True, type=str, help="Link to HN Post"
    )
    parser.add_argument(
        "-b",
        "--blog-directory",
        type=str,
        required=True,
        help="Full path to blog directory",
    )
    parser.add_argument(
        "-e",
        "--open-in-editor",
        action="store_true",
        default=False,
        help="Open blog site in editor",
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
