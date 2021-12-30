#!/usr/bin/env python3
import logging
import os
from pathlib import Path

import py_executable_checklist.workflow
from dotenv import load_dotenv
from slug import slug
from telegram import Update
from telegram.ext import CommandHandler, Filters, MessageHandler, Updater

load_dotenv()

OUTPUT_DIR = Path.cwd().joinpath("output_dir")


def welcome(update: Update, _):
    if update.message:
        update.message.reply_text(
            "👋 Hi there. ⬇️ I'm a bot that converts web pages to PDFs. ⬆️. " "Try sending me a link to a web page"
        )


def help_command(update: Update, _):
    if update.message:
        update.message.reply_text("Help!")


def _handle_web_page(web_page_url: str) -> str:
    slug_web_page_url = slug(web_page_url)
    target_file = OUTPUT_DIR / f"{slug_web_page_url}.pdf"
    cmd = f'./webpage_to_pdf.py -i "{web_page_url}" -o "{target_file}"'
    py_executable_checklist.workflow.run_command(cmd)
    return target_file.as_posix()


def _process_message(update: Update, context) -> None:
    bot = context.bot
    chat_id = update.effective_chat.id
    original_message_id = update.message.message_id
    update_message_text = update.message.text

    if update_message_text.startswith("http"):
        logging.info(f"📡 Processing message: {update_message_text}")
        reply_message = bot.send_message(
            chat_id,
            "Got {}. 👀 at 🌎".format(update_message_text),
            disable_web_page_preview=True,
        )
        downloaded_file_path = _handle_web_page(update_message_text)
        bot.delete_message(chat_id, original_message_id)
        bot.delete_message(chat_id, reply_message.message_id)
        bot.send_chat_action(chat_id, "upload_document")
        bot.sendDocument(chat_id, open(downloaded_file_path, "rb"))
    else:
        logging.warning(f"🚫 Ignoring message: {update_message_text}")


def adapter(update: Update, context):
    try:
        _process_message(update, context)
    except Exception as e:
        logging.exception(e)
        update.message.reply_text(str(e))


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


def setup_directories():
    OUTPUT_DIR.mkdir(exist_ok=True)


if __name__ == "__main__":
    setup_logging()
    setup_directories()
    start_bot()
