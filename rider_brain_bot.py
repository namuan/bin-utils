#!/usr/bin/env python3
"""
Telegram bot to bookmark links
"""
import argparse
import logging
import os
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse

import dataset
import py_executable_checklist.workflow
import telegram
from dotenv import load_dotenv
from slug import slug
from telegram import Update
from telegram.ext import CommandHandler, Filters, MessageHandler, Updater

from common_utils import (
    decode,
    encode,
    fetch_html_page,
    html_parser_from,
    retry,
    send_file_to_telegram,
)
from twitter_api import get_tweet

load_dotenv()

logging.basicConfig(
    handlers=[logging.StreamHandler()],
    format="%(asctime)s - %(filename)s:%(lineno)d - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    level=logging.INFO,
)
logging.captureWarnings(capture=True)

DEFAULT_BOT_TOKEN = os.getenv("BOT_TOKEN")
GROUP_CHAT_ID = os.getenv("GROUP_CHAT_ID")

HOME_DIR = os.getenv("HOME")
DB_FILE = "rider_brain.db"
DB_CONNECTION_STRING = f"sqlite:///{HOME_DIR}/{DB_FILE}"
OUTPUT_DIR = Path.home().joinpath("OutputDir", "web-to-pdf")
BOOKMARKS_TABLE = "bookmarks"

db = dataset.connect(DB_CONNECTION_STRING)
logging.info(f"Connecting to database {DB_CONNECTION_STRING}")
logging.info(f"Creating table {BOOKMARKS_TABLE}")
bookmarks_table = db.create_table(BOOKMARKS_TABLE)


def welcome(update: Update, _):
    if update.message:
        update.message.reply_text("👋 Hi there. ⬇️ I'm a bot to save bookmarks ⬆️. " "Try sending me a link")


def help_command(update: Update, _):
    if update.message:
        update.message.reply_text("Help!")


def handle_web_page(web_page_url: str) -> str:
    page_html = fetch_html_page(web_page_url)
    bs = html_parser_from(page_html)
    web_page_title = slug(bs.title.string if bs.title and bs.title.string else web_page_url)
    target_file = OUTPUT_DIR / f"{web_page_title}.pdf"
    cmd = f'./webpage_to_pdf.py -i "{web_page_url}" -o "{target_file}" --headless'
    py_executable_checklist.workflow.run_command(cmd)
    return target_file.as_posix()


def update_user(bot, chat_id, original_message_id, reply_message_id, incoming_text, downloaded_file_path):
    bot.delete_message(chat_id, original_message_id)
    bot.delete_message(chat_id, reply_message_id)
    if downloaded_file_path and Path(downloaded_file_path).is_file():
        # send_message_to_telegram(DEFAULT_BOT_TOKEN, GROUP_CHAT_ID, link, disable_web_preview=False)
        send_file_to_telegram(DEFAULT_BOT_TOKEN, GROUP_CHAT_ID, incoming_text, downloaded_file_path)
        # bot.send_chat_action(chat_id, "upload_document")
        # bot.sendDocument(chat_id, open(downloaded_file_path, "rb"))
    else:
        bot.send_message(chat_id, f"🔖 {incoming_text} bookmarked")


def verified_chat_id(chat_id):
    auth_chat_id = os.getenv("AUTH_CHAT_ID")
    if chat_id != int(auth_chat_id):
        logging.warning(f"🚫 Chat ID {chat_id} is not authorized. Authorized Chat Id: {auth_chat_id}")
        return False
    return True


class BaseHandler:
    def __init__(self, url):
        self.url = url

    def _find_existing_bookmark(self):
        return bookmarks_table.find_one(link=self.url)

    def bookmark(self) -> str:
        existing_bookmark = self._find_existing_bookmark()
        if existing_bookmark:
            logging.info(f"Found one already bookmarked: {existing_bookmark}")
            return decode(existing_bookmark.get("archived"))

        archived_entry = self._bookmark()
        entry_row = {
            "source": self.__class__.__name__,
            "link": self.url,
            "created_at": datetime.now(),
            "archived": encode(archived_entry),
        }
        bookmarks_table.insert(entry_row)
        logging.info(f"Updated database: {entry_row}")
        return archived_entry

    def _bookmark(self) -> str:
        pass


class Youtube(BaseHandler):
    def _bookmark(self) -> str:
        return self.url


class Twitter(BaseHandler):
    def _bookmark(self) -> str:
        parsed_tweet = urlparse(self.url)
        tweet_id = os.path.basename(parsed_tweet.path)
        tweet = get_tweet(tweet_id)
        return tweet.text


class WebPage(BaseHandler):
    def _bookmark(self) -> str:
        logging.info(f"Bookmarking WebPage: {self.url}")
        return handle_web_page(self.url)


def message_handler_for(incoming_url) -> BaseHandler:
    urls_to_handler = [
        {"urls": ["https://twitter.com"], "handler": Twitter},
        {"urls": ["https://youtube.com", "https://www.youtube.com"], "handler": Youtube},
    ]

    for entry in urls_to_handler:
        for url in entry.get("urls"):
            logging.info(f"Checking {url} against {incoming_url}")
            if incoming_url.startswith(url):
                return entry.get("handler")(incoming_url)

    return WebPage(incoming_url)


def process_message(update: Update, context) -> None:
    bot = context.bot
    chat_id = update.effective_chat.id

    original_message_id = update.message.message_id
    update_message_text = update.message.text

    logging.info(f"📡 Processing message: {update_message_text} from {chat_id}")
    if not verified_chat_id(chat_id):
        return

    if update_message_text.startswith("http"):
        reply_message = bot.send_message(
            chat_id,
            f"Got {update_message_text}. 👀 at 🌎",
            disable_web_page_preview=True,
        )
        message_handler = message_handler_for(update_message_text)
        downloaded_file_path = message_handler.bookmark()
        update_user(
            bot, chat_id, original_message_id, reply_message.message_id, update_message_text, downloaded_file_path
        )
        logging.info(f"✅ Document sent back to user {chat_id}")
    else:
        logging.warning(f"🚫 Ignoring message: {update_message_text}")


@retry(telegram.error.TimedOut, tries=3)
def adapter(update: Update, context):
    try:
        process_message(update, context)
    except telegram.error.TimedOut:
        raise
    except Exception as e:
        error_message = f"🚨 🚨 🚨 {e}"
        update.message.reply_text(error_message)
        raise e


def start_bot():
    """Start bot and hook callback functions"""
    logging.info("🏗 Starting bot")
    bot_token = os.getenv("RIDER_BRAIN_BOT_TOKEN")
    if not bot_token:
        logging.warning("🚫 Please make sure that you set the RIDER_BRAIN_BOT_TOKEN environment variable.")
        return False

    updater = Updater(bot_token, use_context=True)
    dispatcher = updater.dispatcher

    dispatcher.add_handler(CommandHandler("start", welcome))
    dispatcher.add_handler(CommandHandler("help", help_command))
    dispatcher.add_handler(MessageHandler(Filters.text & ~Filters.command, adapter))

    updater.start_polling()
    updater.idle()
    return True


def setup_directories():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def parse_args():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    setup_directories()
    start_bot()
