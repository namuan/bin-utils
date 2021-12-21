#!/usr/bin/env python3

import asyncio
import os
import platform
import subprocess
from urllib import parse

import pyperclip
from pyppeteer import launch

CWD = os.getcwd()
DOWNLOAD_FOLDER = f"{CWD}/.temp"


async def preview_image(carbon_file_path):
    if platform.system() == "Darwin":
        open_file_cmd = "open {}".format(carbon_file_path)
    elif platform.system() == "Windows":
        open_file_cmd = "start {}".format(carbon_file_path)
    else:
        open_file_cmd = "xdg-open {}".format(carbon_file_path)

    subprocess.call(open_file_cmd, shell=True)


async def copy_image_to_clip(carbon_file_path):
    if platform.system() == "Darwin":
        copy_img_cmd = "osascript -e 'set the clipboard to (read (POSIX file \"{}\") as JPEG picture)'".format(
            carbon_file_path
        )
    elif platform.system() == "Windows":
        copy_img_cmd = "nircmd clipboard copyimage {}".format(carbon_file_path)
    else:
        copy_img_cmd = "xclip -selection clipboard -t image/png -i {}".format(
            carbon_file_path
        )

    subprocess.call(copy_img_cmd, shell=True)


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


async def main():
    uri_encoded_clip_text = await encode_clip_text()

    browser, page = await open_site(uri_encoded_clip_text)
    await download_image(page)
    await browser.close()

    carbon_file_path = f"{DOWNLOAD_FOLDER}/carbon.png"
    await copy_image_to_clip(carbon_file_path)
    await preview_image(carbon_file_path)


asyncio.get_event_loop().run_until_complete(main())
