from argparse import ArgumentParser
from pathlib import Path
from bs4 import BeautifulSoup
import json

# Arguments
# correct: -f sample/paypal_general_errors.html -o errors_data.json
# fail: -f paypal_general_unknown.html

errors_json_file = 'errors_data.json'


def parse_args():
    parser = ArgumentParser(
        description="Extracts error codes for Paypal"
    )
    parser.add_argument('-f', '--file', type=str, help='HTML file')
    parser.add_argument('-o', '--output', type=str, help='JSON file to save data')
    return parser.parse_args()


def get_data_from_row(table_row):
    tds = table_row.find_all('td')
    error_id = tds[0].text.strip()
    error_description = tds[1].text.strip()
    error_data = {
        'company': 'Paypal',
        'category': 'SOAP APIs',
        'version': '1.0.0',
        'error_id': error_id,
        'error_description': error_description
    }
    return error_data


def extract_errors(html_page):
    soup_page = BeautifulSoup(html_page, 'html.parser')
    errors = []
    for tr in soup_page.select('table tbody tr'):
        errors.append(get_data_from_row(tr))
    return json.dumps(errors)


def main():
    args = parse_args()
    html_file = Path(args.file)
    json_file = Path(args.output)

    if not html_file.exists():
        raise FileNotFoundError("Unable to find file: {0}".format(args.file))
    errors_json = extract_errors(html_file.read_text())
    json_file.write_text(errors_json)
    print("Errors saved in {0}".format(json_file))


if __name__ == '__main__':
    main()
