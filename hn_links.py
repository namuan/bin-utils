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

from common.workflow import run_workflow, WorkflowBase, run_command

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
    if post_html_page_file.exists():
        logging.info(f"🌕 Loading page from cache {post_html_page_file}")
        return post_html_page_file.read_text(encoding=UTF_ENCODING)

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


def html_parser_from(page_html):
    return BeautifulSoup(page_html, "html.parser")


def relative_image_directory():
    now = datetime.now()
    year = now.strftime("%Y")
    month = now.strftime("%m")
    day = now.strftime("%d")
    return f"images/{year}/{month}/{day}"


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
        all_links = [link.get("href") for link in self.bs.find_all("a", href=True)]

        # output
        context["all_links"] = all_links


class KeepValidLinks(WorkflowBase):
    """Only keep interesting links"""

    all_links: list
    child_links_folder: Path

    def accessible(self, link, child_links_folder):
        page_slug = slug(link)
        page_path = f"{page_slug}.html"
        post_html_page_file = child_links_folder / page_path
        if post_html_page_file.exists():
            return True

        maybe_html = fetch_html(link, post_html_page_file)

        if not maybe_html:
            return False

        return True

    def is_valid_link(self, link):
        known_domains = ["ycombinator", "algolia", "HackerNews"]

        def has_known_domain(post_link):
            return any(map(lambda l: l in post_link, known_domains))

        return link.startswith("http") and not has_known_domain(link)

    def run(self, context):
        valid_links = [
            link
            for link in self.all_links
            if self.is_valid_link(link)
            and self.accessible(link, self.child_links_folder)
        ]

        # output
        context["valid_links"] = valid_links


class GrabChildLinkTitle(WorkflowBase):
    """Get page title for each valid link"""

    valid_links: list
    child_links_folder: Path

    def page_title_from(self, child_links_folder, link_in_comment):
        page_slug = slug(link_in_comment)
        page_path = f"{page_slug}.html"

        post_html_page_file = child_links_folder / page_path
        page_html = fetch_html(link_in_comment, post_html_page_file)
        bs = html_parser_from(page_html)
        return bs.title.string if bs.title else link_in_comment

    def stripped(self, page_title: str):
        return page_title.strip()

    def run(self, context):
        links_with_titles = [
            (self.stripped(self.page_title_from(self.child_links_folder, link)), link)
            for link in self.valid_links
        ]

        # output
        context["links_with_titles"] = links_with_titles


class GrabScreenThumbnail(WorkflowBase):
    """For each link, get screen thumbnail"""

    links_with_titles: list
    thumbnails_folder: Path

    def thumbnail(self, thumbnails_folder, page_link):
        page_slug = slug(page_link)
        target_path = thumbnails_folder / f"{page_slug}.png"
        cmd = f"./thumbnail_generator.py -i '{page_link}' -o {target_path}"
        if target_path.exists():
            logging.info(
                f"🌕 Thumbnail already exists for {page_link}. Run {cmd} to update it"
            )
            return target_path.as_posix()
        failed_commands = []
        try:
            run_command(cmd)
        except:  # noqa: E722
            failed_commands.append(cmd)

        for failed_command in failed_commands:
            logging.info(f"❌ Command failed. Try running it again {failed_command}")

        return target_path

    def run(self, context):
        links_with_metadata = [
            (page_title, page_link, self.thumbnail(self.thumbnails_folder, page_link))
            for page_title, page_link in self.links_with_titles
        ]

        # output
        context["links_with_metadata"] = links_with_metadata


class GenerateMarkdown(WorkflowBase):
    """Generate Markdown using the data in context"""

    def setup_template_env(self):
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
        self.setup_template_env()
        markdown_text = self.render_markdown(context)

        # output
        context["markdown_text"] = markdown_text


class AddHugoHeader(WorkflowBase):
    """Add blog header with metadata"""

    markdown_text: str

    def run(self, context):
        post_date = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
        post_title = self.markdown_text.splitlines()[0].replace("#", "").strip()

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
            post_header
            + os.linesep
            + os.linesep.join(self.markdown_text.splitlines()[2:])
        )

        # output
        post_file_name = slug(post_title) + ".md"
        context["post_file_name"] = post_file_name
        context["post_with_header"] = post_with_header


class UpdateLinksInMarkdown(WorkflowBase):
    """Use relative links in Markdown to point to images"""

    post_with_header: str
    target_folder: Path

    def run(self, context):
        thumbnails_directory = self.target_folder / "thumbnails"
        replace_from = f"![]({thumbnails_directory.as_posix()}"
        replace_with = f"![](/{relative_image_directory()}"
        md_with_updated_links = self.post_with_header.replace(
            replace_from, replace_with
        )

        # output
        context["md_with_updated_links"] = md_with_updated_links


class WriteBlogPost(WorkflowBase):
    """Write to blog directory with correct file name"""

    md_with_updated_links: str
    blog_directory: Path
    post_file_name: str

    def run(self, context):
        blog_page_path = "{}/content/posts/{}".format(
            self.blog_directory, self.post_file_name
        )
        Path(blog_page_path).write_text(self.md_with_updated_links)
        logging.info("📒 Created note at {}".format(blog_page_path))

        # output
        context["blog_page"] = blog_page_path


class CompressImages(WorkflowBase):
    """Resize images and compress them"""

    blog_directory: Path
    target_folder: Path

    def run(self, _):
        for img in self.target_folder.glob("thumbnails/*"):
            img_name = img.name
            img_path = img.as_posix()
            target_path = Path(
                "{}/static/{}/{}".format(
                    self.blog_directory, relative_image_directory(), img_name
                )
            )

            cmd = f"convert {img_path} -resize 640x480 -quality 50% {target_path}"

            if target_path.exists():
                logging.info(
                    f"🌕 {img_name} already resized/compressed. Run this to re-convert {cmd}"
                )
                continue

            Path(target_path).parent.mkdir(parents=True, exist_ok=True)
            run_command(cmd)


class OpenInEditor(WorkflowBase):
    """Open blog post in editor defined by the environment variable EDITOR"""

    open_in_editor: bool
    blog_directory: Path

    def run(self, _):
        if not self.open_in_editor:
            return
        editor = os.environ.get("EDITOR")
        print(f"Opening {self.blog_directory} in {editor}")
        run_command(f"{editor} {self.blog_directory}")


# Workflow definition
def workflow_steps():
    return [
        CreateOutputFolder,
        GrabPostHtml,
        ParsePostHtml,
        GrabPostTitle,
        ExtractAllLinksFromPost,
        KeepValidLinks,
        GrabChildLinkTitle,
        GrabScreenThumbnail,
        GenerateMarkdown,
        AddHugoHeader,
        UpdateLinksInMarkdown,
        WriteBlogPost,
        CompressImages,
        OpenInEditor,
    ]


# Boilerplate -----------------------------------------------------------------
def main(args):
    context = args.__dict__
    run_workflow(context, workflow_steps())


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
