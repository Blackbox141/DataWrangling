#!/usr/bin/env python3
"""
Enrich cleaned_2024_data_ch_de.csv with the raw numeric accident hour.

Joins the original numeric hour (0-23) from the raw source files back onto
the cleaned 2024 dataset using AccidentUID as the join key.

Sources:
  CH  ->  RoadAccident_ch.csv   column: AccidentHour   (0-23)
  DE  ->  RoadAccident_de.csv   column: USTUNDE        (0-23)

Output: data/cleaned_2024_with_hour.csv
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from merge_data import read_table, to_int_series

DATA_DIR = Path(__file__).parent.parent.parent / "data" / "processed"
BASE_PATH = DATA_DIR / "cleaned_2024_data_ch_de.csv"
CH_PATH = DATA_DIR / "RoadAccident_ch.csv"
DE_PATH = DATA_DIR / "RoadAccident_de.csv"
OUT_PATH = DATA_DIR / "cleaned_2024_with_hour.csv"


def _ch_hours(path: Path) -> pd.DataFrame:
    df = read_table(path)
    out = pd.DataFrame()
    out["AccidentUID"] = df["AccidentUID"].astype("string").str.strip()
    out["AccidentHourNumeric"] = to_int_series(df["AccidentHour"])
    return out.dropna(subset=["AccidentHourNumeric"])


def _de_hours(path: Path) -> pd.DataFrame:
    df = read_table(path)
    out = pd.DataFrame()
    out["AccidentUID"] = df["UIDENTSTLAE"].astype("string").str.strip()
    out["AccidentHourNumeric"] = to_int_series(df["USTUNDE"])
    return out.dropna(subset=["AccidentHourNumeric"])


def main() -> None:
    print(f"Reading base: {BASE_PATH.name}")
    base = pd.read_csv(BASE_PATH, dtype={"AccidentUID": str})
    base["AccidentUID"] = base["AccidentUID"].str.strip()
    print(f"  → {len(base):,} rows")

    ch_hours = _ch_hours(CH_PATH)
    de_hours = _de_hours(DE_PATH)

    hours = (
        pd.concat([ch_hours, de_hours], ignore_index=True)
        .drop_duplicates(subset=["AccidentUID"])
    )
    print(f"Hour lookup: {len(hours):,} unique entries (CH + DE combined)")

    result = base.merge(hours, on="AccidentUID", how="left")

    cols = list(result.columns)
    cols.remove("AccidentHourNumeric")
    hour_idx = cols.index("AccidentHour")
    cols.insert(hour_idx + 1, "AccidentHourNumeric")
    result = result[cols]

    matched = result["AccidentHourNumeric"].notna().sum()
    print(f"Matched: {matched:,} / {len(result):,} rows")

    result.to_csv(OUT_PATH, index=False)
    print(f"\n✓ Written to: {OUT_PATH}")
    print(f"  Rows: {len(result):,}  |  Columns: {len(result.columns)}")
    print(f"\nColumns: {list(result.columns)}")
    print(f"\nPreview (first 5 rows):\n{result.head().to_string()}")


if __name__ == "__main__":
    main()
