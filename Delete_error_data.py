#!/usr/bin/env python3
"""
Entfernt fehlerhafte Zeilen aus dem Merge-Output und erstellt danach einen 2024-Subset.

Standard-Workflow:
1) merged.csv minus error_entries.csv -> without_error_entries.csv
2) without_error_entries.csv auf AccidentYear == 2024 filtern
   -> cleaned_2024_data_ch_de.csv

Usage
-----
python Delete_error_data.py
python Delete_error_data.py --input /path/merged.csv --errors /path/error_entries.csv
"""

from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd


DEFAULT_DATA_DIR = Path("/Users/dennis/Desktop/DataWrangling")
DEFAULT_INPUT_PATH = DEFAULT_DATA_DIR / "merged.csv"
DEFAULT_ERRORS_PATH = DEFAULT_DATA_DIR / "error_entries.csv"
DEFAULT_WITHOUT_ERRORS_PATH = DEFAULT_DATA_DIR / "without_error_entries.csv"
DEFAULT_CLEANED_2024_PATH = DEFAULT_DATA_DIR / "cleaned_2024_data_ch_de.csv"


def remove_error_entries(df: pd.DataFrame, errors: pd.DataFrame) -> pd.DataFrame:
    if errors.empty:
        return df.copy()

    common_cols = [col for col in df.columns if col in errors.columns]
    if not common_cols:
        raise ValueError(
            "Keine gemeinsamen Spalten zwischen Input und error_entries gefunden. "
            "Fehlerdaten koennen nicht entfernt werden."
        )

    df_cmp = df[common_cols].astype("string").fillna("<NA>")
    errors_cmp = errors[common_cols].astype("string").fillna("<NA>")

    left = df_cmp.assign(_row_id=df_cmp.groupby(common_cols, dropna=False).cumcount())
    right = errors_cmp.assign(_row_id=errors_cmp.groupby(common_cols, dropna=False).cumcount())

    matched = left.merge(
        right,
        on=common_cols + ["_row_id"],
        how="left",
        indicator=True,
    )["_merge"].eq("both")

    return df.loc[~matched].copy()


def main() -> None:
    parser = argparse.ArgumentParser(description="Delete error rows and build cleaned 2024 dataset")
    parser.add_argument("--input", default=str(DEFAULT_INPUT_PATH), help="Pfad zur merged.csv")
    parser.add_argument("--errors", default=str(DEFAULT_ERRORS_PATH), help="Pfad zur error_entries.csv")
    parser.add_argument(
        "--out-without-errors",
        default=str(DEFAULT_WITHOUT_ERRORS_PATH),
        help="Ausgabepfad ohne Fehlerzeilen",
    )
    parser.add_argument(
        "--out-cleaned-2024",
        default=str(DEFAULT_CLEANED_2024_PATH),
        help="Ausgabepfad fuer bereinigte 2024-Daten",
    )
    parser.add_argument("--year", type=int, default=2024, help="Jahr fuer finalen Filter")
    args = parser.parse_args()

    input_path = Path(args.input)
    errors_path = Path(args.errors)
    out_without_errors_path = Path(args.out_without_errors)
    out_cleaned_2024_path = Path(args.out_cleaned_2024)

    if not input_path.exists():
        raise FileNotFoundError(f"Input-Datei nicht gefunden: {input_path}")
    if not errors_path.exists():
        raise FileNotFoundError(f"Fehlerdatei nicht gefunden: {errors_path}")

    print(f"Input:         {input_path}")
    print(f"Error entries: {errors_path}")

    df = pd.read_csv(input_path)
    errors = pd.read_csv(errors_path)

    print(f"\nGeladene Input-Zeilen:      {len(df):,}")
    print(f"Geladene Fehler-Zeilen:     {len(errors):,}")

    without_errors = remove_error_entries(df, errors)
    removed_count = len(df) - len(without_errors)

    out_without_errors_path.parent.mkdir(parents=True, exist_ok=True)
    without_errors.to_csv(out_without_errors_path, index=False)

    print(f"\nEntfernte Fehler-Zeilen:    {removed_count:,}")
    print(f"Verbleibende Zeilen:        {len(without_errors):,}")
    print(f"Gespeichert:               {out_without_errors_path}")

    if "AccidentYear" not in without_errors.columns:
        raise ValueError("Pflichtspalte 'AccidentYear' fehlt in without_error_entries.csv")

    year_numeric = pd.to_numeric(without_errors["AccidentYear"], errors="coerce").astype("Int64")
    cleaned_2024 = without_errors[year_numeric == args.year].copy()

    out_cleaned_2024_path.parent.mkdir(parents=True, exist_ok=True)
    cleaned_2024.to_csv(out_cleaned_2024_path, index=False)

    print(f"\nZeilen mit AccidentYear == {args.year}: {len(cleaned_2024):,}")
    print(f"Gespeichert:                      {out_cleaned_2024_path}")


if __name__ == "__main__":
    main()
