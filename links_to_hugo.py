#!/usr/bin/env python3
"""
Read a list of links from a file (Each line should contain a single link to a webpage)
Check if the link is still valid
Grab title of the webpage
Grab screenshot/thumbnail of the webpage
Create a blog post with list of links along with the thumbnail

Usage:
$ python3 links_to_hugo.py -l links.txt -t "<blog title>" -b <blog_directory> --open-in-editor

Process:
1. Use curl to download the webpage
```
$ curl -s <page-url> > .temp/<filename>.html
```

2. Use pup to extract links and output to a file
```
$ cat <filename>.html | pup 'a attr{href}' >> links.txt
```

3. Run this script
```
$ EDITOR=/usr/local/bin/idea ./links_to_hugo.py --links-file .temp/links.txt --post-title "Post title" \
    --blog-directory "<full-path-to-blog-directory"  --open-in-editor
```

4. Review blog post in the editor and remove any links if necessary

5. Run this script to clean up any images that are left behind due to deleted links
```
$ ./unused_files.py -s <blog-root>/static/images -t <blog-root>/content -d
```

6. make deploy from blog directory
7. make commit-all from blog directory
"""

import logging
import os
from argparse import ArgumentParser
from argparse import RawDescriptionHelpFormatter
from datetime import datetime
from pathlib import Path

import requests
from bs4 import BeautifulSoup
from jinja2 import Environment, FileSystemLoader
from py_executable_checklist.workflow import (
    WorkflowBase,
    run_command,
    notify_me,
    run_workflow,
)
from slug import slug

UTF_ENCODING = "utf-8"


# Common functions


def fetch_html(url, post_html_page_file):
    logging.info(f"Fetching HTML title for {url}")
    if post_html_page_file.exists():
        logging.info(f"🌕 Loading page from cache {post_html_page_file}")
        return post_html_page_file.read_text(encoding=UTF_ENCODING)

    user_agent = (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_10_3) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/44.0.2403.89 Safari/537.36"
    )
    headers = {"User-Agent": user_agent}
    page = requests.get(url, headers=headers)
    page_html = page.text
    logging.info(f"Caching page {post_html_page_file}")
    post_html_page_file.write_text(page_html, encoding=UTF_ENCODING)
    return page_html


def html_parser_from(page_html):
    return BeautifulSoup(page_html, "html.parser")


def relative_image_directory():
    now = datetime.now()
    year = now.strftime("%Y")
    month = now.strftime("%m")
    day = now.strftime("%d")
    return f"images/{year}/{month}/{day}"


# Workflow steps


class CreateOutputFolder(WorkflowBase):
    """Create output folder using Post id in the temporary folder"""

    post_title: str

    def run(self, context):
        blog_title_slug = slug(self.post_title)
        download_folder = f"{os.getcwd()}/.temp"

        target_folder = Path(download_folder) / blog_title_slug
        child_links_folder = target_folder / "links"
        thumbnails_folder = target_folder / "thumbnails"

        for f in [target_folder, child_links_folder, thumbnails_folder]:
            f.mkdir(parents=True, exist_ok=True)

        # output
        context["target_folder"] = target_folder
        context["child_links_folder"] = child_links_folder
        context["thumbnails_folder"] = thumbnails_folder


class ExtractAllLinksFromPost(WorkflowBase):
    """Extract all links"""

    links_file: str

    def run(self, context):
        all_links = Path(self.links_file).read_text(encoding=UTF_ENCODING).splitlines()

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
        try:
            if post_html_page_file.exists():
                return True

            fetch_html(link, post_html_page_file)
        except Exception as e:
            logging.error(f"💥 {e}")
            return False

        return True

    def is_valid_link(self, link):
        known_domains = ["ycombinator", "algolia", "hackernews", "youtube"]

        def has_known_domain(post_link):
            return any(map(lambda l: l in post_link.lower(), known_domains))

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
        return bs.title.string if bs.title and bs.title.string else link_in_comment

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
        except:  # noqa: B001, E722
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


class NotifyMe(WorkflowBase):
    """Notify when the blog post is ready to review"""

    post_title: str

    def run(self, _):
        pushover_config = {
            "pushover_url": os.getenv("PUSHOVER_URL"),
            "pushover_token": os.getenv("PUSHOVER_TOKEN"),
            "pushover_user": os.getenv("PUSHOVER_USER"),
        }
        notify_me(f"✅ {self.post_title} done!", pushover_config)


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
        NotifyMe,
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
    parser = ArgumentParser(
        description=__doc__, formatter_class=RawDescriptionHelpFormatter
    )
    parser.add_argument(
        "-l", "--links-file", required=True, type=str, help="Path to links file"
    )
    parser.add_argument(
        "-t", "--post-title", required=True, type=str, help="Blog post title"
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
    setup_logging()
    args = parse_args()
    main(args)