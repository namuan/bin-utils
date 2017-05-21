from argparse import ArgumentParser
from pathlib import Path

import requests


# arguments
# -d paypal_general_errors.html -p https://developer.paypal.com/docs/classic/api/errors/general/

def download_html(url):
    print("Downloading webpage from {0}".format(url))
    page = requests.get(url)
    return page.text


def write_html_to_disk(file_path, contents):
    file_path.write_text(contents)
    print("Finished writing file to {0}".format(file_path))


def parse_args():
    parser = ArgumentParser(
        description="Download HTML page and save to disk"
    )
    parser.add_argument('-p', '--page', type=str, help='HTML page to download')
    parser.add_argument('-d', '--downloadfile', type=str, help='Name of the file to save')
    return parser.parse_args()


def main():
    args = parse_args()
    url = args.page
    filename = args.downloadfile
    file_path = Path(filename)
    if not file_path.exists():
        contents = download_html(url)
        write_html_to_disk(file_path, contents)
    else:
        print("File already exists")


if __name__ == '__main__':
    main()
