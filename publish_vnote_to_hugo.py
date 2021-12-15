#!/usr/bin/env python3
"""
Publish vNote to Hugo blog post
Usage: $ python publish_vnote_to_hugo.py <<blog-root>> <<vnote-location>>
"""

import os
import sys
import subprocess
import shutil
from pathlib import Path
import fileinput
import re


class CreateHugoPost(object):
    def run(self, context):
        blog_root = context["blog"]
        vnote = context["vnote"]
        file_name = context["file_name"]
        context["blog_page"] = "{}/content/posts/{}".format(blog_root, file_name)
        shutil.copyfile(vnote, context["blog_page"])
        print("Created note at {}".format(context["blog_page"]))


class CopyImageFiles(object):
    def rgx_find_all(self, document, search_query):
        compiled_rgx = re.compile(search_query, re.IGNORECASE)
        return compiled_rgx.findall(document)

    def image_tags_from_note(self, note_path):
        return self.rgx_find_all(Path(note_path).read_text(), "((images/.*.[gif|png]))")

    def image_path_in_vnote(self, note_path, image):
        note = Path(note_path)
        return note.joinpath("..", image).resolve()

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
        self.replace_string_in_file(blog_page, "images/", "/images/")
        print("Replace all images in Blog Post {}".format(blog_page))


class ServeSite(object):
    def run(self, context):
        blog_root = context["blog"]
        os.chdir(blog_root)
        subprocess.call('open -a "iTerm.app" {}'.format(blog_root), shell=True)
        print("Serving site ...")


if __name__ == "__main__":
    context = {"blog": sys.argv[1], "vnote": sys.argv[2]}

    context["file_name"] = Path(context["vnote"]).name

    procedure = [
        CreateHugoPost(),
        CopyImageFiles(),
        ReplaceImageLinks(),
        ServeSite(),
    ]
    for step in procedure:
        print("==" * 50)
        step.run(context)
    print("Done.")
