#!/usr/bin/env python3
"""
A custom browser for headless printing
"""
import logging
import sys
from argparse import ArgumentParser, RawDescriptionHelpFormatter
from pathlib import Path

from PyQt5.QtCore import QUrl
from PyQt5.QtWebEngineWidgets import QWebEngineView
from PyQt5.QtWidgets import (
    QAction,
    QApplication,
    QLineEdit,
    QMainWindow,
    QToolBar,
    qApp,
)
from slug import slug

BROWSER_NAME = "Deskriders"
HOMEPAGE = "https://www.deskriders.dev"


class MainWindow(QMainWindow):
    def __init__(self, url, output_dir, wait_time, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.wait_time = wait_time
        self.output_dir = output_dir

        self.browser = QWebEngineView()
        self.browser.setUrl(QUrl(url))
        self.browser.loadFinished.connect(self.page_loaded)
        self.setCentralWidget(self.browser)

        navtb = QToolBar("Navigation")
        self.addToolBar(navtb)

        reload_btn = QAction("Reload", self)
        reload_btn.setStatusTip("Reload page")

        reload_btn.triggered.connect(self.browser.reload)
        navtb.addAction(reload_btn)

        navtb.addSeparator()

        self.urlbar = QLineEdit()

        self.urlbar.returnPressed.connect(self.navigate_to_url)

        navtb.addWidget(self.urlbar)

    def page_loaded(self, ok: bool):
        title = self.browser.page().title()
        logging.info(f"Page loaded: {title} -> {ok}")
        self.setWindowTitle(f"{title} - {BROWSER_NAME}")
        self.print_page()

    def pdf_print_finished(self, pth, status):
        logging.info(f"Printing finished {pth} - {status}")
        self.quit()

    def print_page(self):
        web_page = self.browser.page()
        web_page.pdfPrintingFinished.connect(self.pdf_print_finished)
        web_page_title = slug(web_page.title())
        output_file_path = self.output_dir / f"{web_page_title}.pdf"
        web_page.printToPdf(output_file_path.as_posix())

    def navigate_home(self):
        self.browser.setUrl(QUrl(HOMEPAGE))

    def navigate_to_url(self):
        q = QUrl(self.urlbar.text())

        if q.scheme() == "":
            q.setScheme("http")

        self.browser.setUrl(q)

    def update_urlbar(self, q):
        self.urlbar.setText(q.toString())

        # setting cursor position of the url bar
        self.urlbar.setCursorPosition(0)

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
    window.show()
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
