#!/usr/bin/env python3
"""
A custom browser for headless printing
"""
import logging
import random
import sys
from argparse import ArgumentParser, RawDescriptionHelpFormatter
from pathlib import Path

from PyQt5.QtCore import QUrl
from PyQt5.QtWebEngineWidgets import QWebEngineView
from PyQt5.QtWidgets import QAction, QApplication, QMainWindow, QToolBar, qApp
from slug import slug

BROWSER_NAME = "Deskriders"


def scroll_speed():
    return random.randint(300, 500)


READABILITY_JAVASCRIPT = (Path.cwd() / "Readability.js").read_text(encoding="utf-8")
READABILITY_JAVASCRIPT += """
var documentClone = document.cloneNode(true);
var loc = document.location;
var uri = {
  spec: loc.href,
  host: loc.host,
  prePath: loc.protocol + "//" + loc.host,
  scheme: loc.protocol.substr(0, loc.protocol.indexOf(":")),
  pathBase: loc.protocol + "//" + loc.host +
            loc.pathname.substr(0, loc.pathname.lastIndexOf("/") + 1)
};
var article = new Readability(uri, documentClone).parse();
"<html><title>" + article.title + "</title><body>" + article.content + "</body></html>";
"""


class MainWindow(QMainWindow):
    def __init__(self, url, output_dir, wait_time, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.new_height = 1
        self.current_scroll_position = 0
        self.wait_time = wait_time
        self.output_dir = output_dir

        self.browser = QWebEngineView()
        self.browser.setUrl(QUrl(url))
        self.browser.loadFinished.connect(self.page_loaded)
        self.setCentralWidget(self.browser)

        navtb = QToolBar("Navigation")
        self.addToolBar(navtb)

        reload_btn = QAction("Reload", self)
        reload_btn.triggered.connect(self.browser.reload)
        navtb.addAction(reload_btn)

        print_btn = QAction("Print", self)
        print_btn.triggered.connect(self.print_page)
        navtb.addAction(print_btn)

    def val_screen_height(self, val):
        logging.info(f"New height: {val}")
        self.new_height = val
        self.current_scroll_position += scroll_speed()
        logging.info(f"current_scroll_position: {self.current_scroll_position}, new_height: {self.new_height}")

        if self.current_scroll_position <= self.new_height:
            self.page_down()
        else:
            self.print_page()

    def page_down(self):
        logging.info(f"Scrolling to {self.current_scroll_position}")
        self.browser.page().runJavaScript(f"""window.scrollTo(0, {self.current_scroll_position});""")
        self.browser.page().runJavaScript("""document.body.scrollHeight;""", self.val_screen_height)

    def after_rendered_clean_html(self, ok: bool):
        logging.info(f"Rendered Readability HTML -> {ok}")
        self.browser.loadFinished.disconnect()
        self.page_down()

    def val_readability_html(self, html):
        logging.info("Cleaning up HTML")
        self.browser.loadFinished.connect(self.after_rendered_clean_html)
        self.browser.page().setHtml(html)

    def readability(self):
        self.browser.page().runJavaScript(READABILITY_JAVASCRIPT, self.val_readability_html)

    def page_loaded(self, ok: bool):
        self.browser.loadFinished.disconnect()

        title = self.browser.page().title()
        logging.info(f"Page loaded: {title} -> {ok}")
        self.setWindowTitle(f"{title} - {BROWSER_NAME}")
        self.readability()

    def pdf_print_finished(self, pth, status):
        logging.info(f"Printing finished {pth} - {status}")
        self.quit()

    def print_page(self):
        web_page = self.browser.page()
        web_page.pdfPrintingFinished.connect(self.pdf_print_finished)
        web_page_title = slug(web_page.title())
        output_file_path = self.output_dir / f"{web_page_title}.pdf"
        web_page.printToPdf(output_file_path.as_posix())

    def quit(self):
        logging.info("Quitting")
        try:
            qApp.exit(0)
        except BaseException:
            pass


def main(args):
    app = QApplication(sys.argv)
    app.setApplicationName(BROWSER_NAME)
    window = MainWindow(
        url=args.webpage_url, output_dir=args.output_directory_path, wait_time=args.wait_in_secs_before_capture
    )
    window.showMaximized()
    # window.show()
    sys.exit(app.exec_())


def parse_args():
    parser = ArgumentParser(description=__doc__, formatter_class=RawDescriptionHelpFormatter)
    parser.add_argument("-u", "--webpage-url", type=str, required=True, help="Webpage Url")
    parser.add_argument(
        "-o", "--output-directory-path", type=Path, required=True, help="Output directory for the generated PDF file"
    )
    parser.add_argument(
        "-w",
        "--wait-in-secs-before-capture",
        type=int,
        default=10,
        help="Wait (in secs) before capturing page",
    )
    parser.add_argument(
        "-s",
        "--headless",
        action="store_true",
        default=False,
        help="Run headless (no browser window)",
    )
    return parser.parse_args()


def setup_logging():
    logging.basicConfig(
        handlers=[logging.StreamHandler()],
        format="%(asctime)s - %(filename)s:%(lineno)d - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        level=logging.INFO,
    )
    logging.captureWarnings(capture=True)


if __name__ == "__main__":
    args = parse_args()
    setup_logging()
    main(args)
