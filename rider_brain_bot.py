import logging
import os

import py_executable_checklist.workflow
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import CommandHandler, Filters, MessageHandler, Updater

load_dotenv()


def welcome(update: Update, _):
    if update.message:
        update.message.reply_text("Hi!")


def help_command(update: Update, _):
    if update.message:
        update.message.reply_text("Help!")


def _handle_web_page(web_page_url: str) -> str:
    cmd = f'./webpage_to_pdf.py -i "{web_page_url}" -o "output.pdf"'
    py_executable_checklist.workflow.run_command(cmd)
    return f"✅ Processed web page: {web_page_url}"


def _process_message(update_message_text: str) -> str:
    if update_message_text.startswith("http"):
        return _handle_web_page(update_message_text)

    return f'Unknown command "{update_message_text}"'


def adapter(update: Update, _):
    response = _process_message(update.message.text)
    update.message.reply_text(response)


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
    start_bot()
