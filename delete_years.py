#!/usr/bin/env python3
"""
Behält nur Zeilen mit AccidentYear == 2024, alle anderen werden gelöscht.

Usage
-----
python delete_years.py --input merged.csv --out merged_2024.csv
"""

import argparse
from pathlib import Path

import pandas as pd


_DATA_DIR = Path(__file__).parent / "data"
DEFAULT_INPUT_PATH = str(_DATA_DIR / "merged.csv")
DEFAULT_OUTPUT_PATH = str(_DATA_DIR / "merged_2024.csv")

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input",  default=DEFAULT_INPUT_PATH, help="Eingabedatei (z.B. merged.csv)")
    parser.add_argument("--out",    default=DEFAULT_OUTPUT_PATH, help="Ausgabedatei (z.B. merged_2024.csv)")
    parser.add_argument("--year",   type=int, default=2024, help="Jahr das behalten wird (default: 2024)")
    args = parser.parse_args()

    df = pd.read_csv(args.input)
    print(f"\nGeladene Zeilen: {len(df):,}")

    if "AccidentYear" not in df.columns:
        raise ValueError(
            "Pflichtspalte 'AccidentYear' fehlt. "
            "Bitte zuerst mit dem harmonisierten merge_data.py mergen."
        )

    year_numeric = pd.to_numeric(df["AccidentYear"], errors="coerce").astype("Int64")
    vorher = len(df)
    df = df[year_numeric == args.year]
    nachher = len(df)

    print(f"Behalten (AccidentYear == {args.year}): {nachher:,}")
    print(f"Gelöscht:                       {vorher - nachher:,}")

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(out_path, index=False)
    print(f"\n✓ Gespeichert: {args.out}")

if __name__ == "__main__":
    main()
