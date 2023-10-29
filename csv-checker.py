#!/usr/bin/env python3
"""
Verify a csv file.
"""
import argparse

import pandas as pd


def verify_data(start_balance, end_balance, csv_path):
    # Read the CSV file
    df = pd.read_csv(csv_path)

    # Convert the "Date" column to datetime objects
    df["Date"] = pd.to_datetime(df["Date"], format="%d/%m/%Y", errors="coerce")

    # Check for any NaT values (not-a-time) in the "Date" column, which indicate parsing errors
    if df["Date"].isnull().any():
        return "Error: The date column contains invalid date entries."

    # Verify that the "Date" column is in reverse chronological order
    out_of_order_dates = df["Date"][df["Date"].diff() > pd.Timedelta(0)]
    if not out_of_order_dates.empty:
        return f"Error: The following date entries are not in reverse chronological order: {out_of_order_dates.dt.strftime('%d/%m/%Y').tolist()}"

    # Calculate the ending balance based on the transactions
    calculated_end_balance = start_balance + df["Amount"].sum()

    # Verify that the calculated ending balance matches the provided ending balance
    if not round(calculated_end_balance, 2) == round(end_balance, 2):
        return f"Error: The calculated ending balance ({calculated_end_balance}) does not match the provided ending balance ({end_balance})."

    return "Verification Successful: The dates are in order and the ending balance is correct."


def main():
    parser = argparse.ArgumentParser(description="Verify a csv file.")
    parser.add_argument("start_balance", type=float, help="The starting balance.")
    parser.add_argument("end_balance", type=float, help="The ending balance.")
    parser.add_argument("csv_path", type=str, help="The path to the CSV file.")

    args = parser.parse_args()
    result = verify_data(args.start_balance, args.end_balance, args.csv_path)
    print(result)


if __name__ == "__main__":
    main()
