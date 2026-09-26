#!/usr/bin/env -S uv run --quiet --script
# /// script
# requires-python = ">=3.10"
# dependencies = [
#   "playwright",
#   "slug",
# ]
# ///
"""
Generate PDF from a webpage (macOS / Apple Silicon).

`webpage_to_pdf.py` is kept as-is for Linux. This variant differs in four ways:

1. Uses Playwright instead of pyppeteer. pyppeteer 2.0.0 is unmaintained and
   pins an x86_64-only Chromium build, which cannot launch on Apple Silicon
   without Rosetta.
2. Resolves a usable browser by probing, instead of assuming a Playwright
   browser is already downloaded for the installed version.
3. Scales to fit. page.pdf() crops content wider than the paper rather than
   shrinking it, so a wide page silently loses everything past the right
   margin. This is what truncated the right-hand side before.
4. Uses mm for the page size; Playwright's width/height reject "pt".
"""

import argparse
import asyncio
import glob
import logging
import os
import random
from pathlib import Path
from urllib.parse import quote, urlparse, urlunparse

from playwright.async_api import async_playwright
from slug import slug

A4_W = "210mm"
A4_H = "297mm"
A4_W_PT = 595.28
MARGIN_PX = 30
AVAIL_PX = (A4_W_PT - 2 * MARGIN_PX) / 72 * 96

CONTENT_WIDTH_JS = """() => {
    const a = document.querySelector('article') || document.body;
    const ar = a.getBoundingClientRect();
    let bleed = 0;
    for (const el of a.querySelectorAll('*')) {
        const r = el.getBoundingClientRect();
        if (r.width > 0) {
            bleed = Math.max(bleed, r.right - ar.right, ar.left - r.left);
        }
    }
    return {col: Math.round(ar.width), bleed: Math.round(bleed)};
}"""


def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("-i", "--input-url", type=str, required=True, help="Web Url, or path to a local HTML file")
    parser.add_argument(
        "-o",
        "--output-file-path",
        type=Path,
        default=Path.cwd().joinpath("target"),
        help="Full output file path for PDF",
    )
    parser.add_argument(
        "-w",
        "--wait-in-secs-before-capture",
        type=int,
        default=5,
        help="Wait (in secs) before capturing screenshot",
    )
    parser.add_argument(
        "-s",
        "--headless",
        action="store_true",
        default=False,
        help="Run headless (no browser window)",
    )
    parser.add_argument(
        "-n",
        "--no-fit",
        action="store_true",
        default=False,
        help="Do not scale down to fit the page width (may crop the right edge)",
    )
    return parser.parse_args()


def to_url(raw):
    """Accept either a URL or a local filesystem path."""
    parsed = urlparse(raw)
    if parsed.scheme in ("http", "https", "file"):
        return raw
    path = Path(raw).expanduser().resolve()
    if path.is_file():
        return urlunparse(("file", "", quote(path.as_posix()), "", "", ""))
    return raw


def find_browser():
    """Locate a launchable Chromium/Chrome binary, newest Playwright cache first."""
    candidates = []
    home = Path.home()
    for pat in (
        "Library/Caches/ms-playwright/chromium-*/chrome-mac*/**/Google Chrome for Testing",
        "Library/Caches/ms-playwright/chromium-*/chrome-mac*/**/Chromium",
        "Library/Caches/ms-playwright/chromium_headless_shell-*/chrome-mac/headless_shell",
    ):
        for hit in glob.glob(str(home / pat), recursive=True):
            if os.access(hit, os.X_OK):
                candidates.append(hit)
    candidates += [
        "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
        "/Applications/Chromium.app/Contents/MacOS/Chromium",
        "/usr/bin/chromium-browser",
        "/usr/bin/google-chrome",
        "/usr/bin/chromium",
    ]
    for path in candidates:
        if os.path.isfile(path) and os.access(path, os.X_OK):
            return path
    return None


def scroll_speed():
    return random.randint(300, 500)


async def scroll_to_end(page):
    current_scroll_position, new_height = 0, 1
    while current_scroll_position <= new_height:
        await page.evaluate(f"""() => {{ window.scrollTo(0, {current_scroll_position}); }} """)
        new_height = await page.evaluate("""() => { return document.body.scrollHeight; } """)
        current_scroll_position += scroll_speed()
        logging.info(f"current_scroll_position: {current_scroll_position}, new_height: {new_height}")
        await page.wait_for_timeout(1500)


async def open_site(browser, website_url, output_dir):
    page = await browser.new_page(viewport={"width": 800, "height": 900})
    await page.goto(website_url, wait_until="networkidle")
    return browser, page


async def generate_pdf(page, output_file_path, do_fit):
    await page.emulate_media(media="print")
    await page.wait_for_timeout(500)

    scale = 1.0
    if do_fit:
        metrics = await page.evaluate(CONTENT_WIDTH_JS)
        content_w = metrics["col"] + metrics["bleed"]
        scale = min(1.0, AVAIL_PX / content_w) if content_w else 1.0
        logging.info(f"content width {content_w}px, printable {AVAIL_PX:.1f}px, scale {scale:.4f}")

    return await page.pdf(
        width=A4_W,
        height=A4_H,
        path=str(output_file_path),
        print_background=True,
        scale=scale,
        margin={
            "top": f"{MARGIN_PX}px",
            "bottom": f"{MARGIN_PX}px",
            "left": f"{MARGIN_PX}px",
            "right": f"{MARGIN_PX}px",
        },
    )


async def main():
    args = parse_args()
    website_url = to_url(args.input_url)
    output_file_path = args.output_file_path
    if output_file_path.suffix.lower() != ".pdf":
        output_file_path = output_file_path.joinpath(f"{slug(website_url)}.pdf")

    output_dir = output_file_path.parent
    output_dir.mkdir(parents=True, exist_ok=True)

    executable = find_browser()
    if executable:
        logging.info(f"Using browser {executable}")
    else:
        logging.info("No local browser found, falling back to Playwright's managed build")

    async with async_playwright() as p:
        launch_kwargs = {"headless": args.headless}
        if executable:
            launch_kwargs["executable_path"] = executable
        try:
            browser = await p.chromium.launch(**launch_kwargs)
        except Exception:
            logging.exception("Launch failed, retrying with Playwright's managed browser")
            launch_kwargs.pop("executable_path", None)
            browser = await p.chromium.launch(**launch_kwargs)

        logging.info(f"Processing {website_url}")
        try:
            browser, page = await open_site(browser, website_url, output_dir)
            await page.wait_for_timeout(args.wait_in_secs_before_capture * 1000)
            await scroll_to_end(page)
            await page.evaluate("window.scrollTo(0, 0)")
            await page.wait_for_timeout(500)
            logging.info("Reached end of page. Trying to capture PDF")
            await asyncio.wait_for(generate_pdf(page, output_file_path, not args.no_fit), timeout=60)
            logging.info(f"PDF saved {output_file_path}")
            await page.close()
        except Exception:
            logging.exception(f"Error while processing {website_url}")
        finally:
            await browser.close()


def setup_logging():
    logging.basicConfig(
        handlers=[logging.StreamHandler()],
        format="%(asctime)s - %(filename)s:%(lineno)d - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        level=logging.INFO,
    )
    logging.captureWarnings(capture=True)


if __name__ == "__main__":
    setup_logging()
    asyncio.run(main())
