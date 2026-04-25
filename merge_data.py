#!/usr/bin/env python3
"""
Merge German (DE) and Swiss (CH) accident datasets into one normalized table.

Output schema (harmonized):
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
python merge_data.py
python merge_data.py --de /path/de.csv --ch /path/ch.csv --out /path/merged.csv
"""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Iterable

import pandas as pd


DEFAULT_DATA_DIR = Path("/Users/dennis/Desktop/DataWrangling")
DEFAULT_DE_PATH = DEFAULT_DATA_DIR / "RoadAccident_de.csv"
DEFAULT_CH_PATH = DEFAULT_DATA_DIR / "RoadAccident_ch.csv"
DEFAULT_OUT_PATH = DEFAULT_DATA_DIR / "merged.csv"


# ── Mapping tables ────────────────────────────────────────────────────────────

MONTH_MAP = {1:"Jan",2:"Feb",3:"Mar",4:"Apr",5:"Mai",6:"Jun",
             7:"Jul",8:"Aug",9:"Sep",10:"Okt",11:"Nov",12:"Dez"}

WEEKDAY_DE_MAP = {2:"Mo",3:"Di",4:"Mi",5:"Do",6:"Fr",7:"Sa",1:"So"}

WEEKDAY_CH_MAP = {
    "aw401":"Mo","aw402":"Di","aw403":"Mi","aw404":"Do",
    "aw405":"Fr","aw406":"Sa","aw407":"So",
}

SEVERITY_DE_MAP = {1:"Tot",2:"Schwer",3:"Leicht"}

SEVERITY_CH_MAP = {"as1":"Tot","as2":"Schwer","as3":"Leicht","as4":pd.NA}

MOTORCYCLE_TO_BINARY_MAP = {
    False: 0, True: 1,
    "false": 0, "true": 1,
    "False": 0, "True": 1,
    "FALSE": 0, "TRUE": 1,
    "0": 0, "1": 1,
    0: 0, 1: 1,
    0.0: 0, 1.0: 1,
}

DAYPART_RANGE_MAP = {
    "00-06": "Nacht",
    "06-12": "Vormittag",
    "12-18": "Nachmittag",
    "18-24": "Abend",
}

REGION_DE_MAP = {
    1:"SH_DE",2:"HH_DE",3:"NI_DE",4:"HB_DE",5:"NW_DE",6:"HE_DE",
    7:"RP_DE",8:"BW_DE",9:"BY_DE",10:"SL_DE",11:"BE_DE",12:"BB_DE",
    13:"MV_DE",14:"SN_DE",15:"ST_DE",16:"TH_DE",
}

REGION_CH_MAP = {
    "AG":"AG_CH","AI":"AI_CH","AR":"AR_CH","BE":"BE_CH","BL":"BL_CH",
    "BS":"BS_CH","FR":"FR_CH","GE":"GE_CH","GL":"GL_CH","GR":"GR_CH",
    "JU":"JU_CH","LU":"LU_CH","NE":"NE_CH","NW":"NW_CH","OW":"OW_CH",
    "SG":"SG_CH","SH":"SH_CH","SO":"SO_CH","SZ":"SZ_CH","TG":"TG_CH",
    "TI":"TI_CH","UR":"UR_CH","VD":"VD_CH","VS":"VS_CH","ZH":"ZH_CH",
    "FL":"FL_CH",
}


# ── Helpers ───────────────────────────────────────────────────────────────────

def log(msg: str) -> None:
    print(f"  {msg}")

def section(title: str) -> None:
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}")


def read_table(path: str | Path) -> pd.DataFrame:
    path = Path(path)
    suffix = path.suffix.lower()
    log(f"Reading '{path.name}' ...")
    if suffix == ".csv":
        df = pd.read_csv(path, sep=None, engine="python")
    elif suffix in {".xlsx", ".xls"}:
        df = pd.read_excel(path)
    elif suffix == ".parquet":
        df = pd.read_parquet(path)
    else:
        raise ValueError(f"Unsupported file format: {path}")
    log(f"  → {len(df):,} rows, {len(df.columns)} columns")
    return df


def ensure_columns(df: pd.DataFrame, required: Iterable[str], name: str) -> None:
    missing = [c for c in required if c not in df.columns]
    if missing:
        raise ValueError(
            f"\n[ERROR] {name}: missing required columns: {missing}\n"
            f"Available columns: {list(df.columns)}"
        )


def to_int_series(s: pd.Series) -> pd.Series:
    return pd.to_numeric(s, errors="coerce").astype("Int64")


# FIX: report_unmapped now receives source values + mapped values directly,
#      instead of looking up columns that don't exist in the raw df.
def report_unmapped(source_values: pd.Series, mapped_values: pd.Series,
                    src_label: str, tgt_label: str, dataset: str) -> None:
    mask = source_values.notna() & mapped_values.isna()
    if mask.any():
        bad = sorted(source_values[mask].astype(str).unique().tolist())
        print(f"  [WARN] {dataset}: {mask.sum()} unmapped values in "
              f"'{src_label}' → '{tgt_label}': {bad}")
    else:
        log(f"✓ All values mapped: '{src_label}' → '{tgt_label}'")


def map_hour_to_daypart(s: pd.Series) -> pd.Series:
    raw = s.astype("string").str.strip()

    # 1) Already binned ranges such as 00-06, 06-12, ...
    mapped_range = raw.map(DAYPART_RANGE_MAP)

    # 2) Numeric hour values (0-23)
    hours = pd.to_numeric(raw, errors="coerce")

    def _map_numeric_hour(h):
        if pd.isna(h):
            return pd.NA
        h = int(h)
        if 0 <= h < 6:
            return "Nacht"
        if 6 <= h < 12:
            return "Vormittag"
        if 12 <= h < 18:
            return "Nachmittag"
        if 18 <= h < 24:
            return "Abend"
        return pd.NA

    mapped_numeric = hours.map(_map_numeric_hour)

    # 3) Keep already normalized values if present
    already_normalized = raw.where(raw.isin(set(DAYPART_RANGE_MAP.values())), pd.NA)

    # Priority: normalized labels > explicit range mapping > numeric mapping
    return already_normalized.fillna(mapped_range).fillna(mapped_numeric)


def map_motorcycle_to_binary(s: pd.Series) -> pd.Series:
    mapped = s.map(MOTORCYCLE_TO_BINARY_MAP)
    return pd.to_numeric(mapped, errors="coerce").astype("Int64")


# ── Normalizers ───────────────────────────────────────────────────────────────

def normalize_de(df: pd.DataFrame) -> pd.DataFrame:
    section("Normalizing DE dataset")
    required = ["UJAHR", "UMONAT", "UWOCHENTAG", "USTUNDE", "ULAND", "UKATEGORIE", "IstKrad"]
    ensure_columns(df, required, "Data_DE")

    out = pd.DataFrame()

    out["AccidentUID"] = df["UIDENTSTLAE"].astype("string").str.strip() if "UIDENTSTLAE" in df.columns else pd.NA

    out["AccidentYear"] = to_int_series(df["UJAHR"])
    log(f"AccidentYear: {out['AccidentYear'].min()} – {out['AccidentYear'].max()}")

    monat_src = to_int_series(df["UMONAT"])
    out["AccidentMonth"] = monat_src.map(MONTH_MAP)
    report_unmapped(monat_src, out["AccidentMonth"], "UMONAT", "AccidentMonth", "DE")

    wt_src = to_int_series(df["UWOCHENTAG"])
    out["AccidentWeekDay"] = wt_src.map(WEEKDAY_DE_MAP)
    report_unmapped(wt_src, out["AccidentWeekDay"], "UWOCHENTAG", "AccidentWeekDay", "DE")

    out["AccidentHour"] = map_hour_to_daypart(df["USTUNDE"])
    log(f"AccidentHour distribution:\n{out['AccidentHour'].value_counts().to_string()}")

    reg_src = to_int_series(df["ULAND"])
    out["CantonCode"] = reg_src.map(REGION_DE_MAP)
    report_unmapped(reg_src, out["CantonCode"], "ULAND", "CantonCode", "DE")

    sev_src = to_int_series(df["UKATEGORIE"])
    out["AccidentSeverityCategory"] = sev_src.map(SEVERITY_DE_MAP)
    report_unmapped(sev_src, out["AccidentSeverityCategory"], "UKATEGORIE", "AccidentSeverityCategory", "DE")

    out["AccidentInvolvingMotorcycle"] = map_motorcycle_to_binary(df["IstKrad"])
    log(
        "AccidentInvolvingMotorcycle 1: "
        f"{(out['AccidentInvolvingMotorcycle'] == 1).sum():,} / "
        f"0: {(out['AccidentInvolvingMotorcycle'] == 0).sum():,}"
    )

    out = out[[
        "AccidentUID",
        "AccidentYear",
        "AccidentMonth",
        "AccidentWeekDay",
        "AccidentHour",
        "CantonCode",
        "AccidentSeverityCategory",
        "AccidentInvolvingMotorcycle",
    ]]

    log(f"\n→ DE normalized: {len(out):,} rows")
    return out


def normalize_ch(df: pd.DataFrame) -> pd.DataFrame:
    section("Normalizing CH dataset")

    # fix known typo in column name
    if "AccidentSeverityCategory" not in df.columns and "AccidentSeverityCaytegory" in df.columns:
        df = df.rename(columns={"AccidentSeverityCaytegory": "AccidentSeverityCategory"})
        log("Fixed typo: 'AccidentSeverityCaytegory' → 'AccidentSeverityCategory'")

    required = [
        "AccidentYear",
        "AccidentMonth",
        "AccidentWeekDay",
        "AccidentHour",
        "CantonCode",
        "AccidentSeverityCategory",
        "AccidentInvolvingMotorcycle",
    ]
    ensure_columns(df, required, "Data_CH")

    out = pd.DataFrame()

    out["AccidentUID"] = df["AccidentUID"].astype("string").str.strip() if "AccidentUID" in df.columns else pd.NA

    out["AccidentYear"] = to_int_series(df["AccidentYear"])
    log(f"AccidentYear: {out['AccidentYear'].min()} – {out['AccidentYear'].max()}")

    monat_src = to_int_series(df["AccidentMonth"])
    out["AccidentMonth"] = monat_src.map(MONTH_MAP)
    report_unmapped(monat_src, out["AccidentMonth"], "AccidentMonth", "AccidentMonth", "CH")

    wt_src = df["AccidentWeekDay"].astype("string").str.strip()
    out["AccidentWeekDay"] = wt_src.map(WEEKDAY_CH_MAP)
    report_unmapped(wt_src, out["AccidentWeekDay"], "AccidentWeekDay", "AccidentWeekDay", "CH")

    out["AccidentHour"] = map_hour_to_daypart(df["AccidentHour"])
    log(f"AccidentHour distribution:\n{out['AccidentHour'].value_counts().to_string()}")

    reg_src = df["CantonCode"].astype("string").str.strip()
    out["CantonCode"] = reg_src.map(REGION_CH_MAP)
    report_unmapped(reg_src, out["CantonCode"], "CantonCode", "CantonCode", "CH")

    sev_src = df["AccidentSeverityCategory"].astype("string").str.strip()
    out["AccidentSeverityCategory"] = sev_src.map(SEVERITY_CH_MAP)
    report_unmapped(sev_src, out["AccidentSeverityCategory"], "AccidentSeverityCategory", "AccidentSeverityCategory", "CH")

    out["AccidentInvolvingMotorcycle"] = map_motorcycle_to_binary(df["AccidentInvolvingMotorcycle"])
    log(
        "AccidentInvolvingMotorcycle 1: "
        f"{(out['AccidentInvolvingMotorcycle'] == 1).sum():,} / "
        f"0: {(out['AccidentInvolvingMotorcycle'] == 0).sum():,}"
    )

    out = out[[
        "AccidentUID",
        "AccidentYear",
        "AccidentMonth",
        "AccidentWeekDay",
        "AccidentHour",
        "CantonCode",
        "AccidentSeverityCategory",
        "AccidentInvolvingMotorcycle",
    ]]

    log(f"\n→ CH normalized: {len(out):,} rows")
    return out


# ── Main ──────────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(description="Merge DE + CH accident datasets")
    parser.add_argument(
        "--de",
        default=str(DEFAULT_DE_PATH),
        help="Path to DE file (.csv/.xlsx/.parquet)",
    )
    parser.add_argument(
        "--ch",
        default=str(DEFAULT_CH_PATH),
        help="Path to CH file (.csv/.xlsx/.parquet)",
    )
    parser.add_argument(
        "--out",
        default=str(DEFAULT_OUT_PATH),
        help="Output path (.csv/.xlsx/.parquet)",
    )
    args = parser.parse_args()

    section("Reading input files")
    log(f"DE input: {args.de}")
    log(f"CH input: {args.ch}")
    log(f"Output:   {args.out}")
    df_de = read_table(args.de)
    df_ch = read_table(args.ch)

    norm_de = normalize_de(df_de)
    norm_ch = normalize_ch(df_ch)

    section("Merging datasets")
    merged = pd.concat([norm_de, norm_ch], ignore_index=True)
    merged["AccidentYear"] = pd.to_numeric(merged["AccidentYear"], errors="coerce").astype("Int64")
    merged["AccidentInvolvingMotorcycle"] = pd.to_numeric(
        merged["AccidentInvolvingMotorcycle"], errors="coerce"
    ).astype("Int64")

    log(f"Total rows after merge: {len(merged):,}")
    log(f"Columns: {list(merged.columns)}")
    log(f"\nNull counts per column:\n{merged.isna().sum().to_string()}")

    section("Writing output")
    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    suffix = out_path.suffix.lower()
    if suffix == ".csv":
        merged.to_csv(out_path, index=False)
    elif suffix in {".xlsx", ".xls"}:
        merged.to_excel(out_path, index=False)
    elif suffix == ".parquet":
        merged.to_parquet(out_path, index=False)
    else:
        raise ValueError("Output must end with .csv, .xlsx/.xls, or .parquet")

    log(f"✓ Done! Output written to: {out_path}")
    log(f"  Rows: {len(merged):,}  |  Columns: {len(merged.columns)}")

    section("Preview (first 5 rows)")
    print(merged.head().to_string())


if __name__ == "__main__":
    main()
