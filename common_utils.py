import base64
import json
import logging
import random
import shutil
import string
import time
from functools import wraps
from pathlib import Path

import requests
from bs4 import BeautifulSoup


def setup_logging(verbosity):
    logging_level = logging.WARNING
    if verbosity == 1:
        logging_level = logging.INFO
    elif verbosity >= 2:
        logging_level = logging.DEBUG

    logging.basicConfig(
        handlers=[
            logging.StreamHandler(),
        ],
        format="%(asctime)s - %(filename)s:%(lineno)d - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        level=logging_level,
    )
    logging.captureWarnings(capture=True)


def create_dir(output_dir, delete_existing=False):
    path = Path(output_dir)
    if path.exists() and delete_existing:
        shutil.rmtree(output_dir)
    elif not path.exists():
        path.mkdir()


def random_string(length):
    return "".join(random.choice(string.ascii_uppercase + string.digits) for _ in range(length))


def job_hash(job):
    return random_string(len(job.get("q")))


def fetch_html_page(page_url):
    user_agent = (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_10_3) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/44.0.2403.89 Safari/537.36"
    )
    headers = {"User-Agent": user_agent}
    page = requests.get(page_url, headers=headers, timeout=10)
    return page.text


def html_parser_from(page_html):
    return BeautifulSoup(page_html, "html.parser")


def get_telegram_api_url(method, token):
    return f"https://api.telegram.org/bot{token}/{method}"


def send_message_to_telegram(bot_token, chat_id, message, format="Markdown", disable_web_preview=True):
    data = {
        "chat_id": chat_id,
        "text": message,
        "parse_mode": format,
        "disable_web_page_preview": disable_web_preview,
    }
    requests.post(get_telegram_api_url("sendMessage", bot_token), data=data)


def decode(src):
    logging.info(f"Decoding {src}")
    src_in_bytes_base64 = bytes(src, encoding="utf-8")
    src_in_string_bytes = base64.standard_b64decode(src_in_bytes_base64)
    return src_in_string_bytes.decode(encoding="utf-8")


def encode(src):
    logging.info(f"Encoding {src}")
    src_in_bytes = bytes(src, encoding="utf-8")
    src_in_bytes_base64 = base64.standard_b64encode(src_in_bytes)
    return src_in_bytes_base64.decode(encoding="utf-8")


def obj_to_json(given_obj):
    return json.dumps(given_obj)


def retry(exceptions, tries=4, delay=3, back_off=2):
    def deco_retry(f):
        @wraps(f)
        def f_retry(*args, **kwargs):
            m_retries, m_delay = tries, delay
            while m_retries > 1:
                try:
                    return f(*args, **kwargs)
                except exceptions as e:
                    msg = f"{e}, Retrying in {m_delay} seconds..."
                    logging.warning(msg)
                    time.sleep(m_delay)
                    m_retries -= 1
                    m_delay *= back_off
            return f(*args, **kwargs)

        return f_retry  # true decorator

    return deco_retry
