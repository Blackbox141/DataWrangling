#!/usr/bin/env python3
"""
Classify each accident as night-time (1) or day-time (0) using civil twilight times.

Queries sunrise-sunset.org API once per (region, month) pair using the 15th of each
month as the representative date. Results are cached locally. Applies to all 12 months
including the DST transition months (March, October) — see night_analysis_date_error.md
for the error budget.

Night definition:
    AccidentHourNumeric < civil_twilight_begin_hour  (before dawn)
    OR
    AccidentHourNumeric > civil_twilight_end_hour    (after dusk)

    Edge hours that span the transition are treated as day (conservative).

Input:  data/cleaned_2024_with_hour.csv
Output: data/cleaned_2024_night.csv
Cache:  data/twilight_cache.json
"""

from __future__ import annotations

import json
import time
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import pandas as pd
import requests

# ── Paths ─────────────────────────────────────────────────────────────────────

DATA_DIR  = Path(__file__).parent.parent.parent / "data" / "processed"
INPUT     = DATA_DIR / "cleaned_2024_with_hour.csv"
OUTPUT    = DATA_DIR / "cleaned_2024_night.csv"
CACHE     = DATA_DIR / "twilight_cache.json"

API_URL   = "https://api.sunrise-sunset.org/json"

# ── Timezones ──────────────────────────────────────────────────────────────────

TZ_DE = ZoneInfo("Europe/Berlin")
TZ_CH = ZoneInfo("Europe/Zurich")

# ── Coordinates per DE Bundesland (CantonCode → lat, lng) ─────────────────────
# All CH cantons share a single national center (see night_analysis_date_error.md)

DE_COORDS: dict[str, tuple[float, float]] = {
    "BW_DE": (48.6616,  9.3501),
    "BY_DE": (48.9384, 11.4283),
    "BE_DE": (52.5200, 13.4050),
    "BB_DE": (52.4126, 12.5316),
    "HB_DE": (53.0793,  8.8017),
    "HH_DE": (53.5753, 10.0153),
    "HE_DE": (50.6521,  9.1624),
    "MV_DE": (53.6127, 12.4296),
    "NI_DE": (52.6367,  9.8451),
    "NW_DE": (51.4332,  7.6616),
    "RP_DE": (50.1183,  7.3089),
    "SL_DE": (49.3964,  7.0229),
    "SN_DE": (51.1045, 13.2017),
    "ST_DE": (51.9503, 11.6923),
    "SH_DE": (54.2194,  9.6961),
    "TH_DE": (50.9051, 11.0238),
}

CH_CENTER = (46.8182, 8.2275)

MONTH_NAME_TO_NUM = {
    "Jan": 1, "Feb": 2, "Mar": 3, "Apr": 4,
    "Mai": 5, "Jun": 6, "Jul": 7, "Aug": 8,
    "Sep": 9, "Okt": 10, "Nov": 11, "Dez": 12,
}

# ── Cache helpers ──────────────────────────────────────────────────────────────

def load_cache() -> dict:
    if CACHE.exists():
        return json.loads(CACHE.read_text())
    return {}

def save_cache(cache: dict) -> None:
    CACHE.write_text(json.dumps(cache, indent=2))

# ── API ────────────────────────────────────────────────────────────────────────

def fetch_twilight(lat: float, lng: float, date_str: str, cache: dict) -> tuple[str, str]:
    """Return (civil_twilight_begin_utc, civil_twilight_end_utc) as ISO strings."""
    key = f"{lat},{lng},{date_str}"
    if key in cache:
        return cache[key]["begin"], cache[key]["end"]

    resp = requests.get(
        API_URL,
        params={"lat": lat, "lng": lng, "date": date_str, "formatted": 0},
        timeout=15,
    )
    resp.raise_for_status()
    data = resp.json()
    if data.get("status") != "OK":
        raise RuntimeError(f"API error for {date_str} ({lat},{lng}): {data}")

    begin = data["results"]["civil_twilight_begin"]
    end   = data["results"]["civil_twilight_end"]
    cache[key] = {"begin": begin, "end": end}
    save_cache(cache)
    time.sleep(0.4)  # stay well within API rate limits
    return begin, end

def utc_to_local_hour(utc_str: str, tz: ZoneInfo) -> int:
    return datetime.fromisoformat(utc_str).astimezone(tz).hour

# ── Main ───────────────────────────────────────────────────────────────────────

def main() -> None:
    print(f"Reading {INPUT.name} ...")
    df = pd.read_csv(INPUT, dtype={"AccidentUID": str}, low_memory=False)
    print(f"  → {len(df):,} rows")

    df["_month_num"] = df["AccidentMonth"].map(MONTH_NAME_TO_NUM)
    df["_is_ch"] = df["CantonCode"].str.endswith("_CH")

    # Build the set of (lat, lng, date_str, tz, lookup_key) to query
    unique_pairs = (
        df[["CantonCode", "_month_num", "_is_ch"]]
        .drop_duplicates()
    )

    cache = load_cache()
    twilight: dict[tuple, tuple[int, int]] = {}  # (CantonCode, month) → (dawn_h, dusk_h)

    total = len(unique_pairs)
    api_calls = 0
    cached_hits = 0

    print(f"Building twilight lookup for {total} unique (region, month) pairs ...")
    for i, (_, row) in enumerate(unique_pairs.iterrows(), 1):
        code = row["CantonCode"]
        m    = row["_month_num"]
        is_ch = row["_is_ch"]

        lat, lng = CH_CENTER if is_ch else DE_COORDS[code]
        tz       = TZ_CH     if is_ch else TZ_DE
        date_str = f"2024-{m:02d}-15"

        cache_key = f"{lat},{lng},{date_str}"
        was_cached = cache_key in cache

        begin_utc, end_utc = fetch_twilight(lat, lng, date_str, cache)
        dawn_h = utc_to_local_hour(begin_utc, tz)
        dusk_h = utc_to_local_hour(end_utc,   tz)
        twilight[(code, m)] = (dawn_h, dusk_h)

        if was_cached:
            cached_hits += 1
        else:
            api_calls += 1

        if i % 10 == 0 or i == total:
            print(f"  {i}/{total}  (API calls: {api_calls}, from cache: {cached_hits})")

    print(f"\nClassifying accidents ...")

    def classify(row) -> int:
        h = row["AccidentHourNumeric"]
        dawn, dusk = twilight[(row["CantonCode"], row["_month_num"])]
        return 1 if (h < dawn or h > dusk) else 0

    df["NightAccident"] = df.apply(classify, axis=1)

    df = df.drop(columns=["_month_num", "_is_ch"])

    night_count = int(df["NightAccident"].sum())
    day_count   = len(df) - night_count
    print(f"  Night: {night_count:,} ({night_count/len(df)*100:.1f} %)")
    print(f"  Day:   {day_count:,} ({day_count/len(df)*100:.1f} %)")

    df.to_csv(OUTPUT, index=False)
    print(f"\n✓ Written to: {OUTPUT}")
    print(f"  Rows: {len(df):,}  |  Columns: {len(df.columns)}")
    print(f"\nPreview (first 5 rows):\n{df[['AccidentUID','AccidentMonth','AccidentHour','AccidentHourNumeric','CantonCode','NightAccident']].head().to_string()}")


if __name__ == "__main__":
    main()
