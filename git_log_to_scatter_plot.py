#!/usr/bin/env python
"""
Generate scatter plot based on git commits
"""
import os
import sys
from argparse import ArgumentParser, RawDescriptionHelpFormatter

import git
import matplotlib.pyplot as plt
import pandas as pd


def main():
    # check if the directory is a git repo
    if not os.path.isdir(".git"):
        print("Not a git repo")
        sys.exit(1)

    dates = []
    hours = []
    lines_changed = []

    repo = git.Repo("./")
    for commit in repo.iter_commits():
        date_time_str = str(commit.committed_datetime)
        date_str, time_str = date_time_str.split(" ")[0], date_time_str.split(" ")[1]
        lines_changed.append(len(commit.stats.files))
        dates.append(date_str)
        hours.append(time_str.split(":")[0])

    df = pd.DataFrame({"Date": dates, "Hour": hours, "Lines Changed": lines_changed})

    # Convert 'Date' column to datetime format
    df["Date"] = pd.to_datetime(df["Date"])

    # Plotting
    plt.scatter(df["Date"], df["Hour"], s=df["Lines Changed"] * 10)  # Adjust the size of scatter points
    plt.title("Lines Changed by Date and Hour")
    plt.xlabel("Date")
    plt.ylabel("Hour of Day")
    plt.gca().invert_yaxis()  # Invert y-axis to start from 00 at the top
    plt.show()


def parse_args():
    parser = ArgumentParser(description=__doc__, formatter_class=RawDescriptionHelpFormatter)
    parser.add_argument(
        "-v",
        "--verbose",
        action="count",
        default=0,
        dest="verbose",
        help="Increase verbosity of logging output",
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    main()
