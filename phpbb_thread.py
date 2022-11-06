"""
Download complete PhpBB Forum Thread and convert to a single HTML Page
"""
import logging
import os
import random
import subprocess
import time
from argparse import ArgumentParser

from common.workflow import WorkflowBase, run_workflow
from jinja2 import Environment, FileSystemLoader
from selenium import webdriver
from slug import slug

from common_utils import create_dir

logging.basicConfig(
    handlers=[logging.StreamHandler()],
    format="%(asctime)s - %(filename)s:%(lineno)d - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    level=logging.INFO,
)
logging.captureWarnings(capture=True)


def with_ignoring_errors(code_to_run, warning_msg):
    try:
        return code_to_run()
    except Exception:
        logging.exception(warning_msg)
        return "N/A"


def parse_args():
    parser = ArgumentParser(description=__doc__)
    parser.add_argument("-p", "--page-url", type=str, required=True, help="PhpBB Forum Page Url")
    return parser.parse_args()


class InitScript(WorkflowBase):
    """Initialise environment"""

    def _init_script(self):
        handlers = [
            logging.StreamHandler(),
        ]

        logging.basicConfig(
            handlers=handlers,
            format="%(asctime)s - %(filename)s:%(lineno)d - %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
            level=logging.INFO,
        )
        logging.captureWarnings(capture=True)

    def run(self, context):
        self._init_script()
        template_folder = "sample"
        template_dir = os.path.dirname(os.path.abspath(__file__)) + "/" + template_folder
        jinja_env = Environment(loader=FileSystemLoader(template_dir), trim_blocks=True, autoescape=True)
        context["jinja_env"] = jinja_env
        context["output_folder"] = output_folder = "generated"
        create_dir(output_folder, delete_existing=False)


class OpenBrowserSession(WorkflowBase):
    """Open Browser Session"""

    def run(self, context):
        page_url = context["args"].page_url
        browser = webdriver.Firefox()
        browser.get(page_url)
        context["browser"] = browser
        context["base_url"] = os.path.dirname(page_url)


class ExtractThreadDetails(WorkflowBase):
    """Extract Thread Details"""

    def run(self, context):
        browser = context["browser"]
        context["thread_topic"] = browser.find_elements_by_css_selector("h2.topic-title")[0].text
        context["slugged_thread_topic"] = slug(context["thread_topic"])
        context["complete_html_page"] = "{}.html".format(context["slugged_thread_topic"])
        context["complete_pdf_page"] = context["slugged_thread_topic"] + ".pdf"
        total_pages_elem = browser.find_elements_by_css_selector("div.pagination")[0].find_elements_by_css_selector(
            "li a"
        )[-2]
        context["total_pages"] = int(total_pages_elem.text)


class ScrapePages(WorkflowBase):
    """Scrape Pages"""

    def _get_next_page_link(self, browser, current_page):
        pages_li_elements = browser.find_elements_by_css_selector("div.pagination")[0].find_elements_by_css_selector(
            "li a"
        )
        next_page = next(p for p in pages_li_elements if p.text == str(current_page + 1))
        return next_page.get_attribute("href")

    def _extract_element_from_post(self, post_body, name, selector):
        return with_ignoring_errors(
            lambda: post_body.find_elements_by_css_selector(selector)[0],
            f"Unable to find {name}",
        )

    def _extract_post(self, post):
        post_data = {}
        post_body = post.find_elements_by_css_selector("div.postbody")[0]
        post_data["heading"] = with_ignoring_errors(
            lambda: post_body.find_elements_by_css_selector("h3 a")[0].text,
            "Unable to find heading",
        )
        post_data["username"] = with_ignoring_errors(
            lambda: post_body.find_elements_by_css_selector("a.username")[0].text,
            "Unable to find username",
        )
        post_data["time"] = with_ignoring_errors(
            lambda: post_body.find_elements_by_css_selector("time")[0].text,
            "Unable to find time",
        )
        post_data["content"] = with_ignoring_errors(
            lambda: post_body.find_elements_by_css_selector("div.content")[0].get_attribute("outerHTML"),
            "Unable to find content",
        )
        return post_data

    def _cache_page(self, target_file, file_content):
        with open(target_file, "w") as text_file:
            text_file.write(file_content)

    def run(self, context):
        browser = context["browser"]
        total_pages = context["total_pages"]
        all_posts = []
        for i in range(total_pages):
            current_page = i + 1
            thread_topic = context["thread_topic"]
            output_folder = context["output_folder"]
            page_source = browser.page_source
            html_page_path = f"{output_folder}/{current_page}_{thread_topic}.html"
            html_page_absolute_path = os.path.abspath(html_page_path)
            if os.path.exists(html_page_absolute_path):
                browser.get("file:///" + html_page_absolute_path)
            else:
                self._cache_page(html_page_path, page_source)

            total_posts_on_page = browser.find_elements_by_css_selector("div.post")
            for post in total_posts_on_page:
                post_data = self._extract_post(post)
                all_posts.append(post_data)

            rand_sleep_time = random.randrange(5, 10)
            logging.info(f"🚧 On page {current_page}, 😴 Zzzz for {rand_sleep_time} seconds")
            time.sleep(rand_sleep_time)
            if current_page != total_pages:
                next_page_link = self._get_next_page_link(browser, current_page)
                browser.get(next_page_link)

        context["all_posts"] = all_posts


class CleanUpPosts(WorkflowBase):
    """Clean Up Posts"""

    def _clean(self, post, base_url):
        post_content = post["content"]
        post["content"] = post_content.replace("./", f"{base_url}/") if post_content else ""
        return post

    def run(self, context):
        base_url = context["base_url"]
        all_posts = context["all_posts"]
        context["all_posts"] = [self._clean(post, base_url) for post in all_posts]


class CloseBrowserSession(WorkflowBase):
    """Close Browser Session"""

    def run(self, context):
        browser = context["browser"]
        browser.close()


class JoinAllPages(WorkflowBase):
    """Join All Pages"""

    def _jinja_transform_and_save(self, jinja_env, context, template_file, target_file):
        rendered = jinja_env.get_template(template_file).render(context)
        with open(target_file, "w") as text_file:
            text_file.write(rendered)

    def run(self, context):
        all_posts = context["all_posts"]
        logging.info(f"Collected {len(all_posts)} posts")
        thread_topic = context["thread_topic"]
        complete_html_page = context["complete_html_page"]
        jinja_env = context["jinja_env"]
        jinja_context = {"thread_topic": thread_topic, "all_posts": all_posts}
        self._jinja_transform_and_save(
            jinja_env,
            jinja_context,
            "phpbb_page_template.html",
            "{}/{}".format(context["output_folder"], complete_html_page),
        )


class OpenHtmlPage(WorkflowBase):
    """Open Html Page"""

    def run(self, context):
        complete_html_page = context["complete_html_page"]
        output_folder = context["output_folder"]
        subprocess.check_call(  # nosemgrep
            f"open {output_folder}/{complete_html_page}",
            shell=True,
        )


def workflow():
    return [
        InitScript,
        OpenBrowserSession,
        ExtractThreadDetails,
        ScrapePages,
        CleanUpPosts,
        CloseBrowserSession,
        JoinAllPages,
        OpenHtmlPage,
    ]


def main():
    args = parse_args()
    context = {"args": args}

    run_workflow(context, workflow())


if __name__ == "__main__":
    main()
