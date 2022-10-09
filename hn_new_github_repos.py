#!/usr/bin/env python3
"""
Find Links to Github/GitLab and Bitbucket from HN new news
Send links over Telegram

Usage:
./hn_new_github_repos.py -h
"""

import argparse
import functools
import logging
import os
import time
from argparse import ArgumentParser
from datetime import datetime
from typing import List

import schedule
from dotenv import load_dotenv
from py_executable_checklist.workflow import WorkflowBase, run_workflow

from common_utils import fetch_html_page, html_parser_from, send_message_to_telegram

# Common functions across steps
load_dotenv()

DEFAULT_BOT_TOKEN = os.getenv("BOT_TOKEN")
GROUP_CHAT_ID = os.getenv("GROUP_CHAT_ID")

# Workflow steps


class GrabHackerNewsPage(WorkflowBase):
    """
    Grab HackerNews new page
    """

    def execute(self):
        page_html = fetch_html_page("https://news.ycombinator.com/newest")
        return {"hn_newest_html": page_html}


class ExtractLinks(WorkflowBase):
    """
    Select links from HTML
    """

    hn_newest_html: str

    def execute(self):
        bs = html_parser_from(self.hn_newest_html)
        return {"all_links": [link.get("href") for link in bs.find_all("a", href=True)]}


class SelectRepoLinks(WorkflowBase):
    """
    Extract repo links from the list of links
    """

    all_links: List[str]

    def interested_in(self, link):
        known_domains = ["github.com", "gitlab.com", "bitbucket.com"]

        def has_known_domain(post_link):
            return any(map(lambda l: l in post_link.lower(), known_domains))

        return link.startswith("http") and has_known_domain(link)

    def execute(self):
        return {"repo_links": [link for link in self.all_links if self.interested_in(link)]}


class SendToTelegram(WorkflowBase):
    """
    Send links as telegram messages
    """

    repo_links: List[str]

    def execute(self):
        for link in self.repo_links:
            if "HackerNews/API" not in link:
                logging.info(f"Sending {link}")
                send_message_to_telegram(DEFAULT_BOT_TOKEN, GROUP_CHAT_ID, link, disable_web_preview=False)


# Workflow definition


def workflow():
    return [GrabHackerNewsPage, ExtractLinks, SelectRepoLinks, SendToTelegram]


# Boilerplate


def setup_logging():
    logging.basicConfig(
        handlers=[logging.StreamHandler()],
        format="%(asctime)s - %(filename)s:%(lineno)d - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        level=logging.INFO,
    )
    logging.captureWarnings(capture=True)


def parse_args():
    parser = ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        default=False,
        dest="verbose",
        help="Display context variables at each step",
    )
    return parser.parse_args()


def run_on_schedule(context):
    run_workflow(context, workflow())


def main(args):
    context = args.__dict__
    print(f"Running {datetime.now()}")
    schedule.every(15).minutes.do(functools.partial(run_on_schedule, context))
    while True:
        schedule.run_pending()
        time.sleep(10 * 60)


if __name__ == "__main__":
    setup_logging()
    args = parse_args()
    main(args)
