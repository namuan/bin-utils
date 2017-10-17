#!/usr/bin/env python
"""
Extract all paths from jsondoc file
Usage: $ curl -s -X GET http://some-url/restapidoc.json | python jsondoc_parser.py
"""

import argparse
import io
import json
import sys

ENCODE_IN = 'utf-8'
ENCODE_OUT = 'utf-8'


def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('-i', '--infile',
                        type=lambda x: open(x, encoding=ENCODE_IN),
                        default=io.TextIOWrapper(
                            sys.stdin.buffer, encoding=ENCODE_IN)
                        )
    parser.add_argument('-o', '--outfile',
                        type=lambda x: open(x, 'w', encoding=ENCODE_OUT),
                        default=io.TextIOWrapper(
                            sys.stdout.buffer, encoding=ENCODE_OUT)
                        )
    return parser.parse_args()


def read_instream(in_stream):
    return json.loads(in_stream.read())


def extract_endpoint(api_node):
    return next(method.get('path') for method in api_node.get('methods'))


def manipulate_data(data):
    return [extract_endpoint(api) for api in data.get('apis')]


def main():
    args = parse_args()
    data = read_instream(args.infile)
    results = manipulate_data(data)
    args.outfile.write(json.dumps(results))


if __name__ == '__main__':
    main()
