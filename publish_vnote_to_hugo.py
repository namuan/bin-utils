#!/usr/bin/env python3
"""
Publish vNote to Hugo blog post
Usage: $ python publish_vnote_to_hugo.py <<blog-root>> <<vnote-location>>
"""

import fileinput
import os
import re
import shutil
import subprocess
from argparse import ArgumentParser, RawDescriptionHelpFormatter
from datetime import datetime
from pathlib import Path

from py_executable_checklist.workflow import WorkflowBase, run_workflow


# Common functions


def replace_string_in_file(f, from_string, to_string):
    print("Replacing {} in {} to {}".format(from_string, f, to_string))

    with fileinput.FileInput(f, inplace=True) as file:
        for line in file:
            print(line.replace(from_string, to_string), end="")


# Workflow steps


class LoadVNotePost(WorkflowBase):
    """Load vNote post"""

    vnote: str

    def run(self, context):
        vnote_post = Path(self.vnote).read_text()

        context["vnote_post"] = vnote_post


class AddHugoHeader(WorkflowBase):
    """Add Hugo header to blog post"""

    vnote_post: str

    def run(self, context):
        post_date = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
        post_title = self.vnote_post.splitlines()[0].replace("#", "").strip()
        post_header = f"""+++
date = {post_date}
title = "{post_title}"
description = ""
slug = ""
tags = []
categories = []
externalLink = ""
series = []
+++
        """
        final_post = (
            post_header + os.linesep + os.linesep.join(self.vnote_post.splitlines()[2:])
        )
        context["final_post"] = final_post


class WriteHugoPost(WorkflowBase):
    """Write Hugo post in blog directory"""

    final_post: str
    blog: str
    file_name: str

    def run(self, context):
        blog_page = "{}/content/posts/{}".format(self.blog, self.file_name)
        Path(blog_page).write_text(self.final_post)
        print("Created note at {}".format(blog_page))

        context["blog_page"] = blog_page


class CopyImageFiles(WorkflowBase):
    """Copy image files to blog directory"""

    vnote: str
    blog: str

    def rgx_find_all(self, document, search_query):
        compiled_rgx = re.compile(search_query, re.IGNORECASE)
        return compiled_rgx.findall(document)

    def image_tags_from_note(self, note_path):
        return self.rgx_find_all(
            Path(note_path).read_text(), "!\[.*\]\(vx_images\/(.*)\)"  # noqa: W605
        )

    def image_path_in_vnote(self, note_path, image):
        note = Path(note_path)
        return (note / ".." / "vx_images" / image).resolve()

    def image_path_in_blog(self, blog_root, image):
        blog = Path(blog_root)
        now = datetime.now()
        year = now.strftime("%Y")
        month = now.strftime("%m")
        target_image_dir = blog / "static" / "images" / year / month
        target_image_dir.mkdir(parents=True, exist_ok=True)
        return (target_image_dir / image).resolve()

    def run(self, _):
        images = self.image_tags_from_note(self.vnote)
        print(f"Found {len(images)} images in {self.vnote}")
        for image in images:
            source_full_path = self.image_path_in_vnote(self.vnote, image)
            target_full_path = self.image_path_in_blog(self.blog, image)
            shutil.copyfile(source_full_path, target_full_path)
            print("Copied {}".format(image))


class ReplaceImageLinks(WorkflowBase):
    """Replace image links from vNote format to Hugo format"""

    blog_page: str

    def run(self, context):
        now = datetime.now()
        year = now.strftime("%Y")
        month = now.strftime("%m")
        replace_string_in_file(self.blog_page, "vx_images/", f"/images/{year}/{month}/")
        print("Replace all images in Blog Post {}".format(self.blog_page))


class OpenInEditor(WorkflowBase):
    """Open blog in editor"""

    open_in_editor: bool

    def run(self, context):
        if not self.open_in_editor:
            return
        blog_root = context["blog"]
        editor = os.environ.get("EDITOR")
        print(f"Opening {blog_root} in {editor}")
        subprocess.call(f"{editor} {blog_root}", shell=True)


def workflow():
    return [
        LoadVNotePost,
        AddHugoHeader,
        WriteHugoPost,
        CopyImageFiles,
        ReplaceImageLinks,
        OpenInEditor,
    ]


def main(args):
    context = {
        "blog": args.blog_directory,
        "vnote": args.vnote_file_path,
        "open_in_editor": args.open_in_editor,
    }

    context["file_name"] = Path(context["vnote"]).name

    run_workflow(context, workflow())


def parse_args():
    parser = ArgumentParser(
        description=__doc__, formatter_class=RawDescriptionHelpFormatter
    )
    parser.add_argument("-b", "--blog-directory", type=str, help="Blog directory")
    parser.add_argument(
        "-n", "--vnote-file-path", type=str, required=True, help="vNote file path"
    )
    parser.add_argument(
        "-e",
        "--open-in-editor",
        action="store_true",
        default=False,
        help="Open blog site in editor",
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    main(args)
