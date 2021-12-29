#!/usr/bin/env python3
from time import sleep

from helium import start_firefox
from selenium.webdriver import FirefoxOptions

options = FirefoxOptions()
options.add_argument("--start-maximized")
options.set_preference("print.always_print_silent", True)
options.set_preference("print.printer_Mozilla_Save_to_PDF.print_to_file", True)
options.set_preference("print_printer", "Mozilla Save to PDF")

driver = start_firefox("https://www.deskriders.dev/posts/1639863087-python-selenium/", options=options)

driver.execute_script("window.print();")
sleep(2)  # Found that a little wait is needed for the print to be rendered otherwise the file will be corrupted

driver.quit()
