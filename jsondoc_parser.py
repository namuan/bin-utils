#!/usr/bin/env python3
"""
Extract all paths from jsondoc file
Usage: $ curl -s -X GET http://some-url/restapidoc.json | python jsondoc_parser.py
"""

import argparse
import io
import json
import sys
from itertools import chain

ENCODE_IN = "utf-8"
ENCODE_OUT = "utf-8"


def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument(
        "-i",
        "--infile",
        type=lambda x: open(x, encoding=ENCODE_IN),
        default=io.TextIOWrapper(sys.stdin.buffer, encoding=ENCODE_IN),
    )
    parser.add_argument(
        "-o",
        "--outfile",
        type=lambda x: open(x, "w", encoding=ENCODE_OUT),
        default=io.TextIOWrapper(sys.stdout.buffer, encoding=ENCODE_OUT),
    )
    return parser.parse_args()


def read_instream(in_stream):
    return json.loads(in_stream.read())


def flatten(nested_list):
    return list(chain.from_iterable(nested_list))


def extract_endpoint(api_node):
    return flatten([method.get("path") for method in api_node.get("methods")])


def extract_methods(api_node):
    return flatten([extract_endpoint(api) for api in api_node])


def manipulate_data(data):
    return flatten([extract_methods(v) for k, v in data.get("apis").items()])


def main():
    args = parse_args()
    data = read_instream(args.infile)
    results = manipulate_data(data)
    args.outfile.write(json.dumps(results))


if __name__ == "__main__":
    main()
