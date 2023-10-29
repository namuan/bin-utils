#!/usr/bin/env python3
"""
Process a CSV file and generate formatted output for MarkWhen.

./csv-markwhen.py ~/Downloads/main.csv > ~/Downloads/main_timeline.mw
npx -i @markwhen/mw ~/Downloads/main_timeline.mw ~/Downloads/main_timeline.html
open ~/Downloads/main_timeline.html
"""
import argparse

import pandas as pd


def process_csv(file_path):
    # Read the CSV file
    try:
        df = pd.read_csv(file_path)
    except Exception as e:
        print(f"An error occurred while reading the CSV file: {e}")
        return

    # Check if required columns are present
    required_columns = ["Date", "Amount", "Memo"]
    if not all(column in df.columns for column in required_columns):
        print("The CSV file must contain the columns: Date, Amount, Memo")
        return

    # Sort the data frame by Date in ascending order
    df["Date"] = pd.to_datetime(df["Date"], format="%d/%m/%Y", errors="coerce")
    df = df.sort_values(by="Date", ascending=True)

    # Remove rows with invalid dates
    df = df.dropna(subset=["Date"])

    # Output the formatted text
    print("---")
    print("title: Welcome to Markwhen!")
    print("\n#Project1: #d336b1")
    print("---")
    print("section All Projects")
    print("group Project 1 #Project1")
    for _, row in df.iterrows():
        date = row["Date"].strftime("%Y-%m-%d")
        memo = row["Memo"]
        amount = row["Amount"]
        print(f"{date}: {memo} ({amount})")
    print("end-group")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("csv_file", type=str, help="Path to the CSV file")
    args = parser.parse_args()
    process_csv(args.csv_file)
