
#!/usr/bin/env python3
"""
Zeigt alle Zeilen mit fehlenden oder unzulässigen Werten im harmonisierten Merge-Output.

Erwartetes Schema:
- AccidentUID
- AccidentYear
- AccidentMonth
- AccidentWeekDay
- AccidentHour
- CantonCode
- AccidentSeverityCategory
- AccidentInvolvingMotorcycle

Usage
-----
python filter_missing_values.py --input merged.csv
"""

import argparse
from pathlib import Path

import pandas as pd


_DATA_DIR = Path(__file__).parent / "data"
DEFAULT_INPUT_PATH = str(_DATA_DIR / "merged.csv")
DEFAULT_ERRORS_OUT_PATH = str(_DATA_DIR / "error_entries.csv")

VALID_VALUES = {
    "AccidentMonth": {"Jan", "Feb", "Mar", "Apr", "Mai", "Jun", "Jul", "Aug", "Sep", "Okt", "Nov", "Dez"},
    "AccidentWeekDay": {"Mo", "Di", "Mi", "Do", "Fr", "Sa", "So"},
    "AccidentHour": {"Nacht", "Vormittag", "Nachmittag", "Abend"},
    "AccidentSeverityCategory": {"Tot", "Schwer", "Leicht"},
}

REQUIRED_COLUMNS = [
    "AccidentUID",
    "AccidentYear",
    "AccidentMonth",
    "AccidentWeekDay",
    "AccidentHour",
    "CantonCode",
    "AccidentSeverityCategory",
    "AccidentInvolvingMotorcycle",
]


def find_missing_required_columns(df: pd.DataFrame) -> list[str]:
    return [col for col in REQUIRED_COLUMNS if col not in df.columns]


def normalize_motorcycle(series: pd.Series) -> pd.Series:
    mapped = series.map({
        0: 0, 1: 1,
        0.0: 0, 1.0: 1,
        "0": 0, "1": 1,
        False: 0, True: 1,
        "false": 0, "true": 1,
        "False": 0, "True": 1,
        "FALSE": 0, "TRUE": 1,
    })
    return pd.to_numeric(mapped, errors="coerce").astype("Int64")

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--input",
        default=DEFAULT_INPUT_PATH,
        help="Pfad zur merged.csv",
    )
    parser.add_argument(
        "--errors-out",
        default=DEFAULT_ERRORS_OUT_PATH,
        help="Pfad zur CSV mit allen Fehlerzeilen",
    )
    args = parser.parse_args()

    df = pd.read_csv(args.input)
    print(f"\nGeladene Zeilen: {len(df):,}  |  Spalten: {list(df.columns)}\n")

    missing_required = find_missing_required_columns(df)
    if missing_required:
        raise ValueError(
            "Fehlende Pflichtspalten im harmonisierten Merge-Output: "
            f"{missing_required}"
        )

    problem_mask = pd.Series(False, index=df.index)

    # 1. Fehlende Werte (NaN / leer)
    print("=" * 60)
    print("  Fehlende Werte (NaN) pro Spalte")
    print("=" * 60)
    for col in df.columns:
        n = df[col].isna().sum()
        if n > 0:
            print(f"  [FEHLT]  {col}: {n:,} fehlende Werte")
            problem_mask |= df[col].isna()
        else:
            print(f"  ✓        {col}: keine fehlenden Werte")

    # 2. Unzulässige Werte in kategorischen Spalten
    print("\n" + "=" * 60)
    print("  Unzulässige Werte in kategorischen Spalten")
    print("=" * 60)
    for col, valid in VALID_VALUES.items():
        invalid_mask = df[col].notna() & ~df[col].isin(valid)
        n = invalid_mask.sum()
        if n > 0:
            bad = sorted(df.loc[invalid_mask, col].astype(str).unique().tolist())
            print(f"  [UNGÜLTIG] {col}: {n:,} Zeilen mit unbekannten Werten: {bad}")
            problem_mask |= invalid_mask
        else:
            print(f"  ✓          {col}: alle Werte gültig")

    # 3. Datentyp-/Werte-Checks für numerische Zielspalten
    print("\n" + "=" * 60)
    print("  Numerische Prüfungen")
    print("=" * 60)

    accident_year_numeric = pd.to_numeric(df["AccidentYear"], errors="coerce")
    invalid_year_mask = df["AccidentYear"].notna() & accident_year_numeric.isna()
    if invalid_year_mask.any():
        bad = sorted(df.loc[invalid_year_mask, "AccidentYear"].astype(str).unique().tolist())
        print(f"  [UNGÜLTIG] AccidentYear: {invalid_year_mask.sum():,} nicht-numerische Werte: {bad}")
        problem_mask |= invalid_year_mask
    else:
        print("  ✓          AccidentYear: numerisch")

    motorcycle_norm = normalize_motorcycle(df["AccidentInvolvingMotorcycle"])
    invalid_motorcycle_mask = df["AccidentInvolvingMotorcycle"].notna() & motorcycle_norm.isna()
    if invalid_motorcycle_mask.any():
        bad = sorted(df.loc[invalid_motorcycle_mask, "AccidentInvolvingMotorcycle"].astype(str).unique().tolist())
        print(
            "  [UNGÜLTIG] AccidentInvolvingMotorcycle: "
            f"{invalid_motorcycle_mask.sum():,} Werte außerhalb von 0/1: {bad}"
        )
        problem_mask |= invalid_motorcycle_mask
    else:
        print("  ✓          AccidentInvolvingMotorcycle: gültige 0/1-Werte")

    # 4. Zusammenfassung
    print("\n" + "=" * 60)
    print("  Zusammenfassung")
    print("=" * 60)
    total_problems = problem_mask.sum()
    print(f"  Zeilen mit mindestens einem Problem: {total_problems:,} von {len(df):,}")

    error_rows = df[problem_mask].copy()
    error_out_path = Path(args.errors_out)
    error_out_path.parent.mkdir(parents=True, exist_ok=True)
    error_rows.to_csv(error_out_path, index=False)
    print(f"\n  Fehlerzeilen gespeichert: {len(error_rows):,}")
    print(f"  Datei: {error_out_path}")

    if total_problems > 0:
        print(f"\n  Vorschau der ersten 10 Problemzeilen:")
        print(error_rows.head(10).to_string())

if __name__ == "__main__":
    main()
