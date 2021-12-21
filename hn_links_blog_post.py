#!/usr/bin/env python3
"""
Create blog post from Markdown and images generated from hn_links.py
* To remove any link from the blog post, delete the entry after the post is created in the blog directory
Note down all the links somewhere then run the following command from blog directory to delete them
Image links will be like

![](/images/2021/12/21/httpsunixstackexchangecoma88682.png)
![](/images/2021/12/21/httpscleaveapp.png)

$ pbpaste | awk -F\/ '{print $6}' | tr -d ')' | while read img; do find . -name $img -delete; done # noqa: W605

Usage:
./hn_links_blog_post.py -b <blog_directory> -p <hn_post_directory>
"""

import argparse
import logging
import os
import subprocess
from argparse import ArgumentParser
from datetime import datetime
from pathlib import Path

from slug import slug

logging.basicConfig(
    handlers=[logging.StreamHandler()],
    format="%(asctime)s - %(filename)s:%(lineno)d - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    level=logging.INFO,
)
logging.captureWarnings(capture=True)


def run_command(command):
    logging.info(f"⚡ {command}")
    return subprocess.check_output(command, shell=True).decode("utf-8")


def wait_for_enter():
    input("Press Enter to continue: ")


def run_step(step, context):
    logging.info(step.__class__.__name__ + " ➡️ " + step.__doc__)
    if context.get("verbose"):
        logging.info(context)
    step.run(context)
    logging.info("-" * 100)


def parse_args():
    parser = ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument(
        "-b",
        "--blog-directory",
        type=str,
        required=True,
        help="Full path to blog directory",
    )
    parser.add_argument(
        "-p",
        "--hn-post-directory",
        type=str,
        required=True,
        help="Full path to generated HN post directory",
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


def relative_image_directory():
    now = datetime.now()
    year = now.strftime("%Y")
    month = now.strftime("%m")
    day = now.strftime("%d")
    return f"images/{year}/{month}/{day}"


class LoadMarkdownFile:
    """Load file from HN Post directory"""

    def run(self, context):
        hn_post_directory = context.get("hn_post_directory")
        markdown_file = Path(hn_post_directory) / "hn_links.md"
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
        hn_post_directory = context.get("hn_post_directory")
        thumbnails_directory = Path(hn_post_directory) / "thumbnails"
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
        hn_post_directory = context.get("hn_post_directory")
        for img in Path(hn_post_directory).glob("thumbnails/*"):
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


class OpenInEditor(object):
    """Open blog post in editor defined by the environment variable EDITOR"""

    def run(self, context):
        open_in_editor = context["open_in_editor"]
        if not open_in_editor:
            return
        blog_directory = context.get("blog_directory")
        editor = os.environ.get("EDITOR")
        print(f"Opening {blog_directory} in {editor}")
        run_command(f"{editor} {blog_directory}")


def main(args):
    context = args.__dict__
    procedure = [
        LoadMarkdownFile(),
        AddHugoHeader(),
        UpdateLinksInMarkdown(),
        WriteBlogPost(),
        CompressImages(),
        OpenInEditor(),
    ]
    for step in procedure:
        run_step(step, context)
    logging.info("Done.")


if __name__ == "__main__":
    args = parse_args()
    main(args)
