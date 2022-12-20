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

import dataset
import schedule
from dataset import Table
from dotenv import load_dotenv
from py_executable_checklist.workflow import WorkflowBase, run_workflow

from common_utils import fetch_html_page, html_parser_from, send_message_to_telegram

# Common functions across steps
load_dotenv()

DEFAULT_BOT_TOKEN = os.getenv("BOT_TOKEN")
GROUP_CHAT_ID = os.getenv("GROUP_CHAT_ID")
DB_FILE = "hn_new_github_repos.db"

# Workflow steps


class GrabHackerNewsPage(WorkflowBase):
    """
    Grab HackerNews new page
    """

    def execute(self):
        try:
            page_html = fetch_html_page("https://news.ycombinator.com/newest")
        except Exception as e:
            logging.error("Unable to fetch Hackernews page", e)
            return {"hn_newest_html": "<html></html>"}

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
            return any(map(lambda link: link in post_link.lower(), known_domains))

        return link.startswith("http") and has_known_domain(link)

    def execute(self):
        logging.info(f"SelectRepoLinks: {len(self.all_links)}")
        return {"repo_links": [link for link in self.all_links if self.interested_in(link)]}


class SendToTelegram(WorkflowBase):
    """
    Send links as telegram messages
    """

    saved_repo_links: List[str]

    def execute(self):
        logging.info(f"SendToTelegram: {len(self.saved_repo_links)}")
        for link in self.saved_repo_links:
            if "HackerNews/API" not in link:
                try:
                    send_message_to_telegram(DEFAULT_BOT_TOKEN, GROUP_CHAT_ID, link, disable_web_preview=False)
                    logging.info(f"Sent {link}")
                except Exception as e:
                    logging.error(f"Unable to send telegram message for {link}", e)


class FilterExistingLinks(WorkflowBase):
    """
    Ignore links already stored in the database
    """

    repo_links: List[str]
    db_table: Table

    def _in_database(self, repo_link):
        return self.db_table.find_one(repo_link=repo_link)

    def execute(self):
        logging.info(f"FilterExistingLinks: {len(self.repo_links)}")
        return {"new_repo_links": [link for link in self.repo_links if not self._in_database(link)]}


class SaveLinks(WorkflowBase):
    """
    Save links in the database
    """

    new_repo_links: List[str]
    db_table: Table

    def execute(self):
        logging.info(f"SaveLinks: {len(self.new_repo_links)}")
        for link in self.new_repo_links:
            entry_row = {
                "repo_link": link,
            }
            self.db_table.insert(entry_row)
            logging.info(f"Updated database: {entry_row}")

        return {"saved_repo_links": self.new_repo_links}


class SetupDatabase(WorkflowBase):
    """
    Set up SQLite database
    """

    def execute(self):
        home_dir = os.getenv("HOME")
        table_name = "hn_repo_links"
        db_connection_string = f"sqlite:///{home_dir}/{DB_FILE}"
        db = dataset.connect(db_connection_string)
        logging.info(f"Connecting to database {db_connection_string} and table {table_name}")
        return {"db_table": db.create_table(table_name)}


# Workflow definition


def workflow():
    return [
        SetupDatabase,
        GrabHackerNewsPage,
        ExtractLinks,
        SelectRepoLinks,
        FilterExistingLinks,
        SaveLinks,
        SendToTelegram,
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


def main(context):
    print(f"Running {datetime.now()}")
    schedule.every(15).minutes.do(functools.partial(run_on_schedule, context))
    while True:
        schedule.run_pending()
        time.sleep(10 * 60)


if __name__ == "__main__":
    setup_logging()
    args = parse_args()
    main(args.__dict__)
    # run_on_schedule(args.__dict__)
