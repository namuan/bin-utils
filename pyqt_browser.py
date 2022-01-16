# importing required libraries
import sys

from PyQt5.QtCore import QUrl
from PyQt5.QtWebEngineWidgets import QWebEngineView
from PyQt5.QtWidgets import (
    QAction,
    QApplication,
    QLineEdit,
    QMainWindow,
    QStatusBar,
    QToolBar,
)
from slug import slug


class MainWindow(QMainWindow):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.browser = QWebEngineView()

        self.browser.setUrl(QUrl("http://google.com"))

        self.browser.urlChanged.connect(self.update_urlbar)

        self.browser.loadFinished.connect(self.update_title)

        self.setCentralWidget(self.browser)

        self.status = QStatusBar()

        self.setStatusBar(self.status)

        navtb = QToolBar("Navigation")

        self.addToolBar(navtb)

        back_btn = QAction("Back", self)

        back_btn.setStatusTip("Back to previous page")

        back_btn.triggered.connect(self.browser.back)

        navtb.addAction(back_btn)

        next_btn = QAction("Forward", self)
        next_btn.setStatusTip("Forward to next page")

        next_btn.triggered.connect(self.browser.forward)
        navtb.addAction(next_btn)

        reload_btn = QAction("Reload", self)
        reload_btn.setStatusTip("Reload page")

        reload_btn.triggered.connect(self.browser.reload)
        navtb.addAction(reload_btn)

        home_btn = QAction("Home", self)
        home_btn.setStatusTip("Go home")
        home_btn.triggered.connect(self.navigate_home)
        navtb.addAction(home_btn)

        print_btn = QAction("Print", self)
        print_btn.setStatusTip("Print page")
        print_btn.triggered.connect(self.print_page)
        navtb.addAction(print_btn)

        navtb.addSeparator()

        self.urlbar = QLineEdit()

        self.urlbar.returnPressed.connect(self.navigate_to_url)

        navtb.addWidget(self.urlbar)

        stop_btn = QAction("Stop", self)
        stop_btn.setStatusTip("Stop loading current page")

        stop_btn.triggered.connect(self.browser.stop)
        navtb.addAction(stop_btn)

        self.show()

    def update_title(self):
        title = self.browser.page().title()
        self.setWindowTitle("% s - Geek Browser" % title)

    def pdf_print_finished(self, pth, status):
        print(f"Printing finished {pth} - {status}")

    def print_page(self):
        web_page = self.browser.page()
        web_page.pdfPrintingFinished.connect(self.pdf_print_finished)
        web_page_title = slug(web_page.title())
        web_page.printToPdf(f"{web_page_title}.pdf")

    def navigate_home(self):
        self.browser.setUrl(QUrl("http://www.google.com"))

    def navigate_to_url(self):
        q = QUrl(self.urlbar.text())

        if q.scheme() == "":
            q.setScheme("http")

        self.browser.setUrl(q)

    def update_urlbar(self, q):
        self.urlbar.setText(q.toString())

        # setting cursor position of the url bar
        self.urlbar.setCursorPosition(0)


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("Geek Browser")
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
