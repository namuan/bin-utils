import logging
import random
import shutil
import string
import time
from functools import wraps
from pathlib import Path

import requests
from bs4 import BeautifulSoup


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
