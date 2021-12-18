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


class CopyImageFiles(object):
    def rgx_find_all(self, document, search_query):
        compiled_rgx = re.compile(search_query, re.IGNORECASE)
        return compiled_rgx.findall(document)

    def image_tags_from_note(self, note_path):
        return self.rgx_find_all(
            Path(note_path).read_text(), "!\[\]\(vx_images\/(.*)\)"  # noqa: W605
        )

    def image_path_in_vnote(self, note_path, image):
        note = Path(note_path)
        return (note / ".." / "vx_images" / image).resolve()

    def image_path_in_blog(self, blog_root, image):
        blog = Path(blog_root)
        return blog.joinpath("static", image).resolve()

    def run(self, context):
        note_path = context["vnote"]
        blog_root = context["blog"]

        images = self.image_tags_from_note(note_path)
        for image in images:
            source_full_path = self.image_path_in_vnote(note_path, image)
            target_full_path = self.image_path_in_blog(blog_root, image)
            shutil.copyfile(source_full_path, target_full_path)
            print("Copied {}".format(image))


class ReplaceImageLinks(object):
    def replace_string_in_file(self, f, from_string, to_string):
        print("Replacing {} in {} to {}".format(from_string, f, to_string))

        with fileinput.FileInput(f, inplace=True) as file:
            for line in file:
                print(line.replace(from_string, to_string), end="")

    def run(self, context):
        blog_page = context["blog_page"]
        self.replace_string_in_file(blog_page, "vx_images/", "/images/")
        print("Replace all images in Blog Post {}".format(blog_page))


class ServeSite(object):
    def run(self, context):
        blog_root = context["blog"]
        os.chdir(blog_root)
        subprocess.call('open -a "iTerm.app" {}'.format(blog_root), shell=True)
        print("Serving site ...")


class AddHugoHeader:
    def run(self, context):
        vnote_post = context["vnote_post"]
        post_date = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
        post_title = vnote_post.splitlines()[0].replace("#", "").strip()
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
            post_header + os.linesep + os.linesep.join(vnote_post.splitlines()[2:])
        )
        context["final_post"] = final_post


class LoadVNotePost:
    def run(self, context):
        vnote = context["vnote"]
        vnote_post = Path(vnote).read_text()
        context["vnote_post"] = vnote_post


class WriteHugoPost:
    def run(self, context):
        final_post = context["final_post"]
        blog_root = context["blog"]
        file_name = context["file_name"]
        context["blog_page"] = "{}/content/posts/{}".format(blog_root, file_name)
        Path(context["blog_page"]).write_text(final_post)
        print("Created note at {}".format(context["blog_page"]))


def main(args):
    context = {"blog": args.blog_directory, "vnote": args.vnote_file_path}

    context["file_name"] = Path(context["vnote"]).name

    procedure = [
        LoadVNotePost(),
        AddHugoHeader(),
        WriteHugoPost(),
        CopyImageFiles(),
        ReplaceImageLinks(),
        ServeSite(),
    ]
    for step in procedure:
        print("==" * 50)
        step.run(context)
    print("Done.")


def parse_args():
    parser = ArgumentParser(
        description=__doc__, formatter_class=RawDescriptionHelpFormatter
    )
    parser.add_argument("-b", "--blog-directory", type=str, help="Blog directory")
    parser.add_argument(
        "-n", "--vnote-file-path", type=str, required=True, help="vNote file path"
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    main(args)
