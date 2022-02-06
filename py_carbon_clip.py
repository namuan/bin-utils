#!/usr/bin/env python3
"""
Generate beautiful screenshots of code using carbon.now.sh and puts it on the clipboard.
"""
import asyncio
import os
import platform
import subprocess
from argparse import ArgumentParser, RawDescriptionHelpFormatter
from urllib import parse

import pyperclip
from pyppeteer import launch

CWD = os.getcwd()
DOWNLOAD_FOLDER = f"{CWD}/.temp"


async def preview_image(carbon_file_path):
    if platform.system() == "Darwin":
        open_file_cmd = f"open {carbon_file_path}"
    elif platform.system() == "Windows":
        open_file_cmd = f"start {carbon_file_path}"
    else:
        open_file_cmd = f"xdg-open {carbon_file_path}"

    subprocess.check_call(open_file_cmd, shell=True)  # nosemgrep


async def copy_image_to_clip(carbon_file_path):
    if platform.system() == "Darwin":
        copy_img_cmd = "osascript -e 'set the clipboard to (read (POSIX file \"{}\") as JPEG picture)'".format(
            carbon_file_path
        )
    elif platform.system() == "Windows":
        copy_img_cmd = f"nircmd clipboard copyimage {carbon_file_path}"
    else:
        copy_img_cmd = f"xclip -selection clipboard -t image/png -i {carbon_file_path}"

    subprocess.check_call(copy_img_cmd, shell=True)  # nosemrep


async def download_image(page):
    export_button = await page.querySelector("button[data-cy='quick-export-button']")
    await export_button.click()
    await page.waitFor(2000)


async def open_site(uri_encoded_clip_text):
    browser = await launch(defaultViewport=None)
    page = await browser.newPage()
    await page._client.send(
        "Page.setDownloadBehavior",
        {"behavior": "allow", "downloadPath": DOWNLOAD_FOLDER},
    )
    await page.goto("https://carbon.now.sh?code=" + uri_encoded_clip_text)
    return browser, page


async def encode_clip_text():
    clip_text = pyperclip.paste()
    uri_encoded_clip_text = parse.quote_plus(clip_text)
    return uri_encoded_clip_text


async def main(args):
    uri_encoded_clip_text = await encode_clip_text()

    browser, page = await open_site(uri_encoded_clip_text)
    await download_image(page)
    await browser.close()

    carbon_file_path = f"{DOWNLOAD_FOLDER}/carbon.png"
    await copy_image_to_clip(carbon_file_path)
    await preview_image(carbon_file_path)


def parse_args():
    parser = ArgumentParser(description=__doc__, formatter_class=RawDescriptionHelpFormatter)
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    asyncio.get_event_loop().run_until_complete(main(args))
