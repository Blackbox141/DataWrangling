#!/usr/bin/env python3
from __future__ import annotations

import json
import time
from datetime import datetime
from io import BytesIO
from pathlib import Path
from typing import Dict, List, Tuple
from zoneinfo import ZoneInfo

import pandas as pd
import requests
import streamlit as st

from merge_data import normalize_ch, normalize_de


PROJECT_ROOT = Path(__file__).parent.parent.parent
PROCESSED_DATA_DIR = PROJECT_ROOT / "data" / "processed"
SAVE_DIR = Path(__file__).parent / "data"
MERGED_PATH = SAVE_DIR / "workflow_01_merged_normalized.csv"
ERROR_PATH = SAVE_DIR / "workflow_02_error_rows.csv"
WITHOUT_ERRORS_PATH = SAVE_DIR / "workflow_03_clean_rows.csv"
CLEANED_2024_PATH = SAVE_DIR / "workflow_04_final_filtered.csv"
NIGHT_PATH = SAVE_DIR / "workflow_05_night_classified.csv"
TWILIGHT_CACHE_PATH = PROCESSED_DATA_DIR / "twilight_cache.json"
API_URL = "https://api.sunrise-sunset.org/json"

INTERNAL_TO_OUTPUT_COLUMNS = {
    "AccidentUID": "Accident_ID",
    "AccidentYear": "Year",
    "AccidentMonth": "Month",
    "AccidentWeekDay": "Weekday",
    "AccidentHour": "Hour",
    "CantonCode": "Location",
    "AccidentSeverityCategory": "Severity",
    "AccidentInvolvingMotorcycle": "Motorcycle_Involved",
}
OUTPUT_TO_INTERNAL_COLUMNS = {v: k for k, v in INTERNAL_TO_OUTPUT_COLUMNS.items()}

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

VALID_VALUES = {
    "AccidentMonth": ["Jan", "Feb", "Mar", "Apr", "Mai", "Jun", "Jul", "Aug", "Sep", "Okt", "Nov", "Dez"],
    "AccidentWeekDay": ["Mo", "Di", "Mi", "Do", "Fr", "Sa", "So"],
    "AccidentHour": ["Nacht", "Vormittag", "Nachmittag", "Abend"],
    "AccidentSeverityCategory": ["Tot", "Schwer", "Leicht"],
}

WORKFLOW_STEPS = [
    "1) Eingabedaten geladen",
    "2) Merge & Normalisierung",
    "3) Fehleranalyse",
    "4) Fehlerbereinigung",
    "5) Jahresfilter / Final",
    "6) Nachtklassifikation / Ziel 5",
]

TABLE_HANDLING = {
    "DE Rohdaten": "Originaldaten (nicht verändert).",
    "CH Rohdaten": "Originaldaten (nicht verändert).",
    "Merged": "DE + CH zusammengeführt und auf gemeinsame Struktur normalisiert.",
    "Fehlerzeilen": "Zeilen mit fehlenden/ungültigen Werten, separat dokumentiert.",
    "Ohne Fehler": "Fehlerzeilen wurden herausgefiltert.",
    "Final (Jahr)": "Bereinigte Daten, zusätzlich auf gewähltes Jahr gefiltert.",
    "Final + Nacht": "Finale Daten mit numerischer Unfallstunde und effektiver Nachtklassifikation.",
}

TZ_DE = ZoneInfo("Europe/Berlin")
TZ_CH = ZoneInfo("Europe/Zurich")

DE_COORDS: dict[str, tuple[float, float]] = {
    "BW_DE": (48.6616, 9.3501),
    "BY_DE": (48.9384, 11.4283),
    "BE_DE": (52.5200, 13.4050),
    "BB_DE": (52.4126, 12.5316),
    "HB_DE": (53.0793, 8.8017),
    "HH_DE": (53.5753, 10.0153),
    "HE_DE": (50.6521, 9.1624),
    "MV_DE": (53.6127, 12.4296),
    "NI_DE": (52.6367, 9.8451),
    "NW_DE": (51.4332, 7.6616),
    "RP_DE": (50.1183, 7.3089),
    "SL_DE": (49.3964, 7.0229),
    "SN_DE": (51.1045, 13.2017),
    "ST_DE": (51.9503, 11.6923),
    "SH_DE": (54.2194, 9.6961),
    "TH_DE": (50.9051, 11.0238),
}

CH_CENTER = (46.8182, 8.2275)

MONTH_NAME_TO_NUM = {
    "Jan": 1,
    "Feb": 2,
    "Mar": 3,
    "Apr": 4,
    "Mai": 5,
    "Jun": 6,
    "Jul": 7,
    "Aug": 8,
    "Sep": 9,
    "Okt": 10,
    "Nov": 11,
    "Dez": 12,
}
MONTH_ORDER = list(MONTH_NAME_TO_NUM.keys())


def setup_ui() -> None:
    st.set_page_config(page_title="DataWrangling Workflow", page_icon="🚦", layout="wide")
    st.markdown(
        """
        <style>
          .block-container {padding-top: 1.3rem; max-width: 1200px;}
          .workflow-intro {
            border-left: 4px solid var(--primary-color);
            padding: 0.35rem 0 0.35rem 0.85rem;
            margin: 0.4rem 0 1.1rem 0;
            color: var(--text-color);
          }
          .step-header {
            display: flex;
            gap: 1rem;
            align-items: baseline;
            border-top: 1px solid rgba(128, 128, 128, 0.35);
            padding: 1.1rem 0 0.45rem 0;
            margin-top: 1rem;
          }
          .step-number {
            color: var(--primary-color);
            font-weight: 700;
            min-width: 5.6rem;
          }
          .step-title {
            font-size: 1.18rem;
            font-weight: 700;
            color: var(--text-color);
          }
          .step-detail {
            margin: 0.1rem 0 0.35rem 0;
            color: var(--text-color);
            opacity: 0.72;
            font-size: 0.93rem;
          }
          .cta-label {
            color: var(--text-color);
            font-weight: 700;
            margin-top: 0.3rem;
          }
        </style>
        """,
        unsafe_allow_html=True,
    )
    st.title("CH/DE Unfalldaten - GUI Workflow")
    st.markdown(
        """
        <div class="workflow-intro">
          Rohdaten laden, zu einer gemeinsamen Tabelle harmonisieren, bereinigen und danach die Zielanalysen auswerten.
          Ziel 5 wird erst nach der zusätzlichen Nachtklassifikation verfügbar.
        </div>
        """,
        unsafe_allow_html=True,
    )


def read_uploaded_file(uploaded_file) -> pd.DataFrame:
    suffix = Path(uploaded_file.name).suffix.lower()
    if suffix == ".csv":
        return pd.read_csv(uploaded_file, sep=None, engine="python")
    if suffix in {".xlsx", ".xls"}:
        return pd.read_excel(uploaded_file)
    if suffix == ".parquet":
        return pd.read_parquet(uploaded_file)
    raise ValueError(f"Nicht unterstütztes Format: {uploaded_file.name}")


def normalize_motorcycle(series: pd.Series) -> pd.Series:
    mapped = series.map(
        {
            0: 0,
            1: 1,
            0.0: 0,
            1.0: 1,
            "0": 0,
            "1": 1,
            False: 0,
            True: 1,
            "false": 0,
            "true": 1,
            "False": 0,
            "True": 1,
            "FALSE": 0,
            "TRUE": 1,
        }
    )
    return pd.to_numeric(mapped, errors="coerce")


def find_error_entries(df: pd.DataFrame) -> Tuple[pd.DataFrame, pd.Series]:
    missing_required = [c for c in REQUIRED_COLUMNS if c not in df.columns]
    if missing_required:
        raise ValueError(f"Pflichtspalten fehlen: {missing_required}")

    problem_mask = pd.Series(False, index=df.index)
    reasons = {idx: [] for idx in df.index}

    for col in REQUIRED_COLUMNS:
        miss = df[col].isna()
        if miss.any():
            problem_mask |= miss
            for idx in df.index[miss]:
                reasons[idx].append(f"Missing:{col}")

    for col, valid in VALID_VALUES.items():
        invalid = df[col].notna() & ~df[col].isin(valid)
        if invalid.any():
            problem_mask |= invalid
            for idx in df.index[invalid]:
                reasons[idx].append(f"Invalid:{col}")

    year_numeric = pd.to_numeric(df["AccidentYear"], errors="coerce")
    invalid_year = df["AccidentYear"].notna() & year_numeric.isna()
    if invalid_year.any():
        problem_mask |= invalid_year
        for idx in df.index[invalid_year]:
            reasons[idx].append("Invalid:AccidentYear")

    motorcycle_numeric = normalize_motorcycle(df["AccidentInvolvingMotorcycle"])
    invalid_mc = df["AccidentInvolvingMotorcycle"].notna() & motorcycle_numeric.isna()
    if invalid_mc.any():
        problem_mask |= invalid_mc
        for idx in df.index[invalid_mc]:
            reasons[idx].append("Invalid:AccidentInvolvingMotorcycle")

    error_df = df[problem_mask].copy()
    error_df["ErrorReasons"] = ["; ".join(reasons[idx]) for idx in error_df.index]
    return error_df, problem_mask


def to_csv_bytes(df: pd.DataFrame) -> bytes:
    return df.to_csv(index=False).encode("utf-8")


def save_csv(df: pd.DataFrame, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(path, index=False)


def build_hour_lookup(de_df: pd.DataFrame, ch_df: pd.DataFrame) -> pd.DataFrame:
    required_de = {"UIDENTSTLAE", "USTUNDE"}
    required_ch = {"AccidentUID", "AccidentHour"}
    missing_de = sorted(required_de - set(de_df.columns))
    missing_ch = sorted(required_ch - set(ch_df.columns))
    if missing_de or missing_ch:
        raise ValueError(f"Stundenspalten fehlen. DE: {missing_de}, CH: {missing_ch}")

    de_hours = pd.DataFrame(
        {
            "AccidentUID": de_df["UIDENTSTLAE"].astype("string").str.strip(),
            "AccidentHourNumeric": pd.to_numeric(de_df["USTUNDE"], errors="coerce").astype("Int64"),
        }
    )
    ch_hours = pd.DataFrame(
        {
            "AccidentUID": ch_df["AccidentUID"].astype("string").str.strip(),
            "AccidentHourNumeric": pd.to_numeric(ch_df["AccidentHour"], errors="coerce").astype("Int64"),
        }
    )
    return (
        pd.concat([ch_hours, de_hours], ignore_index=True)
        .dropna(subset=["AccidentHourNumeric"])
        .drop_duplicates(subset=["AccidentUID"])
    )


def add_numeric_hour(cleaned: pd.DataFrame, de_df: pd.DataFrame, ch_df: pd.DataFrame) -> pd.DataFrame:
    if "AccidentUID" not in cleaned.columns:
        raise ValueError("Pflichtspalte 'AccidentUID' fehlt in den finalen Daten.")

    result = cleaned.copy()
    result["AccidentUID"] = result["AccidentUID"].astype("string").str.strip()
    result = result.merge(build_hour_lookup(de_df, ch_df), on="AccidentUID", how="left")

    if "AccidentHour" in result.columns and "AccidentHourNumeric" in result.columns:
        cols = list(result.columns)
        cols.remove("AccidentHourNumeric")
        cols.insert(cols.index("AccidentHour") + 1, "AccidentHourNumeric")
        result = result[cols]
    return result


def load_twilight_cache() -> dict:
    if TWILIGHT_CACHE_PATH.exists():
        return json.loads(TWILIGHT_CACHE_PATH.read_text())
    return {}


def save_twilight_cache(cache: dict) -> None:
    TWILIGHT_CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
    TWILIGHT_CACHE_PATH.write_text(json.dumps(cache, indent=2))


def fetch_twilight(lat: float, lng: float, date_str: str, cache: dict) -> tuple[str, str]:
    key = f"{lat},{lng},{date_str}"
    if key in cache:
        return cache[key]["begin"], cache[key]["end"]

    response = requests.get(
        API_URL,
        params={"lat": lat, "lng": lng, "date": date_str, "formatted": 0},
        timeout=15,
    )
    response.raise_for_status()
    data = response.json()
    if data.get("status") != "OK":
        raise RuntimeError(f"API-Fehler für {date_str} ({lat}, {lng}): {data}")

    begin = data["results"]["civil_twilight_begin"]
    end = data["results"]["civil_twilight_end"]
    cache[key] = {"begin": begin, "end": end}
    save_twilight_cache(cache)
    time.sleep(0.4)
    return begin, end


def utc_to_local_hour(utc_str: str, tz: ZoneInfo) -> int:
    return datetime.fromisoformat(utc_str).astimezone(tz).hour


def classify_night_accidents(df: pd.DataFrame, year: int) -> pd.DataFrame:
    required = {"AccidentMonth", "CantonCode", "AccidentHourNumeric"}
    missing = sorted(required - set(df.columns))
    if missing:
        raise ValueError(f"Pflichtspalten für Ziel 5 fehlen: {missing}")

    result = df.copy()
    result["_month_num"] = result["AccidentMonth"].map(MONTH_NAME_TO_NUM)
    result["_is_ch"] = result["CantonCode"].astype("string").str.endswith("_CH")

    if result["_month_num"].isna().any():
        raise ValueError("Mindestens ein Monat konnte nicht gemappt werden.")
    if result["AccidentHourNumeric"].isna().any():
        raise ValueError("Nicht für alle Zeilen konnte die numerische Unfallstunde ergänzt werden.")

    unique_pairs = result[["CantonCode", "_month_num", "_is_ch"]].drop_duplicates()
    cache = load_twilight_cache()
    twilight: dict[tuple[str, int], tuple[int, int]] = {}

    for _, row in unique_pairs.iterrows():
        code = str(row["CantonCode"])
        month = int(row["_month_num"])
        is_ch = bool(row["_is_ch"])
        lat, lng = CH_CENTER if is_ch else DE_COORDS[code]
        tz = TZ_CH if is_ch else TZ_DE
        begin_utc, end_utc = fetch_twilight(lat, lng, f"{year}-{month:02d}-15", cache)
        twilight[(code, month)] = (utc_to_local_hour(begin_utc, tz), utc_to_local_hour(end_utc, tz))

    def classify(row) -> int:
        dawn, dusk = twilight[(str(row["CantonCode"]), int(row["_month_num"]))]
        hour = int(row["AccidentHourNumeric"])
        return 1 if hour < dawn or hour > dusk else 0

    result["NightAccident"] = result.apply(classify, axis=1)
    return result.drop(columns=["_month_num", "_is_ch"])


def monthly_daylight_hours(cache: dict, year: int) -> dict[str, float | None]:
    daylight: dict[str, float | None] = {}
    for month_name, month_num in MONTH_NAME_TO_NUM.items():
        date_str = f"{year}-{month_num:02d}-15"
        durations = []
        for key, value in cache.items():
            if key.endswith(date_str):
                begin = datetime.fromisoformat(value["begin"])
                end = datetime.fromisoformat(value["end"])
                durations.append((end - begin).total_seconds() / 3600)
        daylight[month_name] = sum(durations) / len(durations) if durations else None
    return daylight


def format_int_de(value: int) -> str:
    return f"{value:,}".replace(",", ".")


def format_percent_de(value: float) -> str:
    return f"{value:.1f}".replace(".", ",") + " %"


def format_hours_de(value: float | None) -> str:
    if value is None:
        return "-"
    return f"{value:.1f}".replace(".", ",") + " h"


def to_output_location(value: object) -> object:
    if pd.isna(value):
        return value
    text = str(value).strip()
    parts = text.split("_")
    if len(parts) != 2:
        return text
    left, right = parts[0].upper(), parts[1].upper()
    if left in {"CH", "DE"}:
        return f"{left}_{right}"
    if right in {"CH", "DE"}:
        return f"{right}_{left}"
    return text


def to_internal_location(value: object) -> object:
    if pd.isna(value):
        return value
    text = str(value).strip()
    parts = text.split("_")
    if len(parts) != 2:
        return text
    left, right = parts[0].upper(), parts[1].upper()
    if left in {"CH", "DE"}:
        return f"{right}_{left}"
    if right in {"CH", "DE"}:
        return f"{left}_{right}"
    return text


def to_internal_schema(df: pd.DataFrame) -> pd.DataFrame:
    out = df.rename(columns=OUTPUT_TO_INTERNAL_COLUMNS).copy()
    if "CantonCode" in out.columns:
        out["CantonCode"] = out["CantonCode"].apply(to_internal_location)
    return out


def transform_error_reasons_to_output(df: pd.DataFrame) -> pd.DataFrame:
    if "ErrorReasons" not in df.columns:
        return df
    out = df.copy()
    for old_col, new_col in INTERNAL_TO_OUTPUT_COLUMNS.items():
        out["ErrorReasons"] = out["ErrorReasons"].str.replace(old_col, new_col, regex=False)
    return out


def to_output_schema(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    if "CantonCode" in out.columns:
        out["CantonCode"] = out["CantonCode"].apply(to_output_location)
    out = out.rename(columns=INTERNAL_TO_OUTPUT_COLUMNS)
    out = transform_error_reasons_to_output(out)
    return out


def has_required_columns(df: pd.DataFrame) -> bool:
    return all(col in df.columns for col in REQUIRED_COLUMNS)


def render_sidebar_progress(
    base_loaded: bool,
    merged_df: pd.DataFrame | None,
    error_df: pd.DataFrame | None,
    without_errors: pd.DataFrame | None,
    cleaned: pd.DataFrame | None,
    night_df: pd.DataFrame | None,
) -> None:
    done = [
        base_loaded,
        merged_df is not None,
        error_df is not None,
        without_errors is not None,
        cleaned is not None,
        night_df is not None,
    ]
    progress_value = sum(done) / len(done)

    st.sidebar.subheader("Workflow auf einen Blick")
    st.sidebar.progress(progress_value)
    labels = [
        "1) Daten geladen",
        "2) Merge fertig",
        "3) Fehleranalyse fertig",
        "4) Bereinigung fertig",
        "5) Jahr gefiltert",
        "6) Nachtklassifikation fertig",
    ]
    for ok, label in zip(done, labels):
        st.sidebar.write(f"{'✅' if ok else '⬜'} {label}")


def render_quick_insights(df: pd.DataFrame, title: str) -> None:
    st.markdown("---")
    st.subheader(f"Schnelleinschätzung: {title}")

    rows = len(df)
    cols = len(df.columns)
    missing_cells = int(df.isna().sum().sum()) if rows else 0
    missing_pct = (missing_cells / (rows * cols) * 100) if rows and cols else 0.0

    k1, k2, k3, k4 = st.columns(4)
    with k1:
        st.metric("Zeilen", f"{rows:,}")
    with k2:
        st.metric("Spalten", f"{cols:,}")
    with k3:
        st.metric("Leere Zellen", f"{missing_cells:,}")
    with k4:
        st.metric("Fehlanteil", f"{missing_pct:.2f}%")

    highlights: List[str] = []

    if "AccidentUID" in df.columns:
        dup_count = int(df["AccidentUID"].duplicated().sum())
        highlights.append(f"Doppelte AccidentUID: {dup_count:,}")

    if "AccidentWeekDay" in df.columns and not df["AccidentWeekDay"].dropna().empty:
        weekday_counts = df["AccidentWeekDay"].value_counts()
        top_day = weekday_counts.idxmax()
        highlights.append(f"Meiste Unfälle am: {top_day} ({int(weekday_counts.iloc[0]):,})")
        order = ["Mo", "Di", "Mi", "Do", "Fr", "Sa", "So"]
        st.bar_chart(weekday_counts.reindex(order, fill_value=0), use_container_width=True)

    if "AccidentSeverityCategory" in df.columns and not df["AccidentSeverityCategory"].dropna().empty:
        sev_norm = df["AccidentSeverityCategory"].astype("string").str.strip().str.lower()
        fatal_mask = sev_norm.isin({"tot", "tod", "toedlich", "tödlich"})
        fatal_n = int(fatal_mask.sum())
        fatal_pct = (fatal_n / rows * 100) if rows else 0.0
        highlights.append(f"Tödliche Unfälle: {fatal_n:,} ({fatal_pct:.2f}%)")

    if "AccidentInvolvingMotorcycle" in df.columns and not df["AccidentInvolvingMotorcycle"].dropna().empty:
        mc = pd.to_numeric(df["AccidentInvolvingMotorcycle"], errors="coerce")
        mc_n = int((mc == 1).sum())
        mc_pct = (mc_n / rows * 100) if rows else 0.0
        highlights.append(f"Mit Motorradbeteiligung: {mc_n:,} ({mc_pct:.2f}%)")

    if highlights:
        st.markdown("**Was jemand ohne Projektkontext sofort wissen sollte**")
        for item in highlights:
            st.write(f"- {item}")


def render_step_info(step_title: str, text: str) -> None:
    st.caption(f"{step_title}: {text}")


def render_step_header(step_number: int, title: str, detail: str) -> None:
    st.markdown(
        f"""
        <div class="step-header">
          <div class="step-number">Schritt {step_number}</div>
          <div>
            <div class="step-title">{title}</div>
            <div class="step-detail">{detail}</div>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_cta_label(text: str) -> None:
    st.markdown(f'<div class="cta-label">{text}</div>', unsafe_allow_html=True)


def render_goals_dashboard(df: pd.DataFrame | None, night_df: pd.DataFrame | None) -> None:
    st.markdown("---")
    st.subheader("Ziele (Abschlussanalyse)")
    if df is None or df.empty:
        st.caption("Die Zielanalyse wird aktiv, sobald Schritt 5 abgeschlossen ist.")
        return

    weekday_order = ["Mo", "Di", "Mi", "Do", "Fr", "Sa", "So"]
    month_map = {"Jan": 1, "Feb": 2, "Mar": 3, "Apr": 4, "Mai": 5, "Jun": 6, "Jul": 7, "Aug": 8, "Sep": 9, "Okt": 10, "Nov": 11, "Dez": 12}

    sev_norm = df["AccidentSeverityCategory"].astype("string").str.strip().str.lower()
    fatal_mask = sev_norm.isin({"tot", "tod", "toedlich", "tödlich"})
    severe_mask = sev_norm.isin({"tot", "tod", "toedlich", "tödlich", "schwer"})
    mc = pd.to_numeric(df["AccidentInvolvingMotorcycle"], errors="coerce")
    is_mc = mc == 1

    tabs = st.tabs(["Ziel 1", "Ziel 2", "Ziel 3", "Ziel 4", "Ziel 5"])

    with tabs[0]:
        st.write("**Ziel 1:** Gibt es einen Zusammenhang zwischen Motorradbeteiligung und der Schwere von Unfällen (insbesondere Todesfällen)?")
        table = pd.crosstab(is_mc.map({True: "Mit Motorrad", False: "Ohne Motorrad"}), df["AccidentSeverityCategory"], normalize="index") * 100
        st.dataframe(table.round(2), use_container_width=True)
        st.bar_chart(table.fillna(0), use_container_width=True)

    with tabs[1]:
        st.write("**Ziel 2:** Passieren am Abend und in der Nacht mehr Unfälle als tagsüber – und ist die Schwere erhöht?")
        day_group = df["AccidentHour"].map({"Vormittag": "Tag", "Nachmittag": "Tag", "Abend": "Nacht/Abend", "Nacht": "Nacht/Abend"})
        counts = day_group.value_counts().reindex(["Tag", "Nacht/Abend"], fill_value=0)
        severe_rate = (severe_mask.groupby(day_group).mean() * 100).reindex(["Tag", "Nacht/Abend"], fill_value=0)
        c1, c2 = st.columns(2)
        with c1:
            st.metric("Unfälle Tag", f"{int(counts['Tag']):,}")
            st.metric("Schwer/Tödlich Tag", f"{severe_rate['Tag']:.2f}%")
        with c2:
            st.metric("Unfälle Nacht/Abend", f"{int(counts['Nacht/Abend']):,}")
            st.metric("Schwer/Tödlich Nacht/Abend", f"{severe_rate['Nacht/Abend']:.2f}%")

    with tabs[2]:
        st.write("**Ziel 3:** Gibt es im Winter in der Schweiz und in Deutschland prozentual mehr schwere Verkehrsunfälle als im Sommer?")
        country = df["CantonCode"].astype("string").str[-2:]
        season = df["AccidentMonth"].map(month_map).map(lambda m: "Winter" if m in {12, 1, 2} else "Sommer/Rest")
        analysis = pd.DataFrame({"Land": country, "Saison": season, "SchwerOderToedlich": severe_mask})
        grouped = analysis.groupby(["Land", "Saison"], dropna=False)["SchwerOderToedlich"].mean().mul(100).round(2).unstack(fill_value=0)
        grouped = grouped.reindex(["CH", "DE"], fill_value=0)
        st.dataframe(grouped, use_container_width=True)

    with tabs[3]:
        st.write("**Ziel 4:** An welchem Wochentag geschehen die meisten Unfälle, und welcher ist der tödlichste?")
        counts = df["AccidentWeekDay"].value_counts().reindex(weekday_order, fill_value=0)
        fatal_counts = df[fatal_mask]["AccidentWeekDay"].value_counts().reindex(weekday_order, fill_value=0)
        fatal_rate = (fatal_counts / counts.replace(0, pd.NA) * 100).fillna(0)
        top_day = counts.idxmax() if int(counts.sum()) else "-"
        deadliest = fatal_rate[counts > 0].idxmax() if int((counts > 0).sum()) else "-"
        c1, c2 = st.columns(2)
        with c1:
            st.metric("Meiste Unfälle", f"{top_day} ({int(counts[top_day]):,})" if top_day != "-" else "-")
        with c2:
            st.metric("Tödlichster Wochentag", f"{deadliest} ({fatal_rate[deadliest]:.2f}%)" if deadliest != "-" else "-")
        st.write("**Diagramm 1: Anzahl Unfälle pro Wochentag**")
        st.bar_chart(counts.rename_axis("Wochentag").to_frame("Unfälle"), use_container_width=True)
        st.write("**Diagramm 2: Tödlichkeitsrate pro Wochentag in %**")
        st.bar_chart(fatal_rate.rename_axis("Wochentag").to_frame("Toedlichkeitsrate_Prozent"), use_container_width=True)

    with tabs[4]:
        st.write("**Ziel 5: Auswirkung Winterzeit**")
        if night_df is None or night_df.empty or "NightAccident" not in night_df.columns:
            st.caption("Ziel 5 wird aktiv, sobald Schritt 6 abgeschlossen ist.")
            return

        night = night_df.copy()
        analysis_year = int(st.session_state.get("analysis_year", 2024))
        daylight = monthly_daylight_hours(load_twilight_cache(), analysis_year)

        total_counts = night["AccidentMonth"].value_counts().reindex(MONTH_ORDER, fill_value=0)

        rows = []
        for month in MONTH_ORDER:
            month_df = night[night["AccidentMonth"] == month]
            api_night = month_df["NightAccident"] == 1
            bin_night = month_df["AccidentHour"] == "Nacht"

            total = int(total_counts[month])
            bin_count = int(bin_night.sum())
            api_count = int(api_night.sum())
            both_count = int((bin_night & api_night).sum())
            only_api = int((~bin_night & api_night).sum())
            only_bin = int((bin_night & ~api_night).sum())
            api_rate = (api_count / total * 100) if total else 0.0
            rows.append(
                {
                    "Monat": month,
                    "Tageslicht (h)": format_hours_de(daylight[month]),
                    "Bin Nacht": format_int_de(bin_count),
                    "API effektiv Nacht": format_int_de(api_count),
                    "Beide Nacht": format_int_de(both_count),
                    "Nur API Nacht": format_int_de(only_api),
                    "Nur Bin Nacht": format_int_de(only_bin),
                    "Gesamt": format_int_de(total),
                    "API Anteil": format_percent_de(api_rate),
                }
            )

        st.caption("Monatlicher Vergleich: ursprünglicher Uhrzeit-Bin `Nacht` vs. API-klassifizierte effektive Nacht (`NightAccident = 1`).")
        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)


def build_table_registry(
    de_df: pd.DataFrame | None,
    ch_df: pd.DataFrame | None,
    merged_df: pd.DataFrame | None,
    error_df: pd.DataFrame | None,
    without_errors: pd.DataFrame | None,
    cleaned: pd.DataFrame | None,
    night_df: pd.DataFrame | None,
) -> Dict[str, pd.DataFrame]:
    tables: Dict[str, pd.DataFrame] = {}
    if de_df is not None:
        tables["DE Rohdaten"] = de_df
    if ch_df is not None:
        tables["CH Rohdaten"] = ch_df
    if merged_df is not None:
        tables["Merged"] = merged_df
    if error_df is not None:
        tables["Fehlerzeilen"] = error_df
    if without_errors is not None:
        tables["Ohne Fehler"] = without_errors
    if cleaned is not None:
        tables["Final (Jahr)"] = cleaned
    if night_df is not None:
        tables["Final + Nacht"] = night_df
    return tables


def enrich_error_table(error_df: pd.DataFrame) -> pd.DataFrame:
    if error_df.empty or "ErrorReasons" not in error_df.columns:
        out = error_df.copy()
        out["IssueCount"] = 0
        out["ProblemColumns"] = ""
        out["ProblemColumnsCount"] = 0
        out["IsFullyInvalid"] = False
        return out

    out = error_df.copy()

    def split_reasons(value) -> List[str]:
        if pd.isna(value):
            return []
        return [part.strip() for part in str(value).split(";") if part.strip()]

    reason_lists = out["ErrorReasons"].apply(split_reasons)
    problem_columns = reason_lists.apply(
        lambda reasons: sorted(
            {
                r.split(":", 1)[1].strip() if ":" in r else r.strip()
                for r in reasons
                if str(r).strip()
            }
        )
    )

    out["IssueCount"] = reason_lists.apply(len)
    out["ProblemColumns"] = problem_columns.apply(lambda cols: ", ".join(cols))
    out["ProblemColumnsCount"] = problem_columns.apply(len)
    out["IsFullyInvalid"] = problem_columns.apply(lambda cols: set(REQUIRED_COLUMNS).issubset(set(cols)))
    return out


def infer_current_step(
    merged_df: pd.DataFrame | None,
    error_df: pd.DataFrame | None,
    without_errors: pd.DataFrame | None,
    night_df: pd.DataFrame | None,
    base_loaded: bool,
) -> str:
    if night_df is not None:
        return WORKFLOW_STEPS[5]
    if without_errors is not None:
        return WORKFLOW_STEPS[3]
    if error_df is not None:
        return WORKFLOW_STEPS[2]
    if merged_df is not None:
        return WORKFLOW_STEPS[1]
    if base_loaded:
        return WORKFLOW_STEPS[0]
    return WORKFLOW_STEPS[0]


def render_documentation_dashboard(tables: Dict[str, pd.DataFrame], current_step: str, merged_df: pd.DataFrame | None) -> None:
    st.markdown("---")
    st.subheader("Dokumentations-Dashboard")
    st.caption("Zwischenschritt und Tabelle direkt wählen, Kennzahlen dokumentieren und Fehlerbehandlung transparent zeigen.")

    top1, top2, top3 = st.columns(3)
    with top1:
        st.metric("Aktueller Schritt", current_step)
    with top2:
        merged_rows = len(merged_df) if merged_df is not None else 0
        st.metric("Zeilen nach Merge", f"{merged_rows:,}")
    with top3:
        error_rows = len(tables["Fehlerzeilen"]) if "Fehlerzeilen" in tables else 0
        error_rate = (error_rows / len(merged_df) * 100) if merged_df is not None and len(merged_df) else 0.0
        st.metric("Fehlerzeilen", f"{error_rows:,}", f"{error_rate:.2f}%")

    available_names = list(tables.keys())
    if not available_names:
        st.caption("Noch keine Tabelle verfügbar. Lade zuerst DE- und CH-Datei hoch.")
        return

    default_table_by_step = {
        WORKFLOW_STEPS[0]: "DE Rohdaten",
        WORKFLOW_STEPS[1]: "Merged",
        WORKFLOW_STEPS[2]: "Fehlerzeilen",
        WORKFLOW_STEPS[3]: "Ohne Fehler",
        WORKFLOW_STEPS[4]: "Final (Jahr)",
        WORKFLOW_STEPS[5]: "Final + Nacht",
    }

    default_table = default_table_by_step.get(current_step, available_names[0])
    if default_table not in available_names:
        default_table = available_names[0]

    selected_table = st.selectbox(
        "Tabelle zur Analyse",
        available_names,
        index=available_names.index(default_table),
    )

    selected_df = tables[selected_table]
    selected_df_output = to_output_schema(selected_df)
    st.write(f"**{selected_table}**")
    st.caption(TABLE_HANDLING.get(selected_table, ""))

    info1, info2, info3 = st.columns(3)
    with info1:
        st.metric("Zeilen", f"{len(selected_df_output):,}")
    with info2:
        st.metric("Spalten", f"{len(selected_df_output.columns):,}")
    with info3:
        missing_cells = int(selected_df_output.isna().sum().sum()) if not selected_df_output.empty else 0
        st.metric("Leere Zellen", f"{missing_cells:,}")

    if selected_table == "Fehlerzeilen" and "ErrorReasons" in selected_df.columns:
        base_enriched = enrich_error_table(selected_df)
        enriched = base_enriched.copy()
        view_mode = st.radio(
            "Filter Fehlerzeilen",
            ["Alle Fehlerzeilen", "Nur komplett fehlerhafte Zeilen", "Nur teilweise fehlerhafte Zeilen"],
            horizontal=True,
        )

        if view_mode == "Nur komplett fehlerhafte Zeilen":
            enriched = enriched[enriched["IsFullyInvalid"]]
        elif view_mode == "Nur teilweise fehlerhafte Zeilen":
            enriched = enriched[~enriched["IsFullyInvalid"]]

        reason_series = (
            selected_df["ErrorReasons"]
            .dropna()
            .astype(str)
            .str.split(";")
            .explode()
            .str.strip()
        )
        reason_counts = reason_series[reason_series != ""].value_counts().rename_axis("Fehlertyp").reset_index(name="Anzahl")

        stats1, stats2 = st.columns(2)
        with stats1:
            st.metric("Komplett fehlerhaft", f"{int(base_enriched['IsFullyInvalid'].sum()):,}")
        with stats2:
            avg_issues = float(base_enriched["IssueCount"].mean()) if not selected_df.empty else 0.0
            st.metric("Ø Fehler pro Zeile", f"{avg_issues:.2f}")

        st.dataframe(reason_counts, use_container_width=True)
        st.dataframe(to_output_schema(enriched), use_container_width=True)
        return

    st.dataframe(selected_df_output, use_container_width=True)


def main() -> None:
    setup_ui()

    st.sidebar.header("Workflow-Status")
    persist_to_disk = st.sidebar.checkbox("CSV-Ergebnisse lokal speichern", value=False)

    de_df = None
    ch_df = None
    base_loaded = False

    with st.container():
        render_step_header(
            1,
            "Rohdaten laden",
            "Lade die DE- und CH-Datei hoch. Danach werden die weiteren Aktionen freigeschaltet.",
        )
        col1, col2 = st.columns(2)
        with col1:
            de_file = st.file_uploader("RoadAccident_de.csv", type=["csv", "xlsx", "xls", "parquet"], key="de")
        with col2:
            ch_file = st.file_uploader("RoadAccident_ch.csv", type=["csv", "xlsx", "xls", "parquet"], key="ch")

    if de_file and ch_file:
        try:
            de_df = read_uploaded_file(de_file)
            ch_df = read_uploaded_file(ch_file)
            base_loaded = True
        except Exception as exc:
            st.error(f"Fehler beim Lesen der Dateien: {exc}")
            de_df, ch_df = None, None
    else:
        st.caption("Warte auf beide Rohdateien: `RoadAccident_de.csv` und `RoadAccident_ch.csv`.")

    if de_df is not None and ch_df is not None:
        with st.expander("Vorschau Eingabedaten", expanded=False):
            c1, c2 = st.columns(2)
            with c1:
                st.write("DE", de_df.head(5))
            with c2:
                st.write("CH", ch_df.head(5))

        with st.container():
            render_step_header(
                2,
                "Merge und Normalisierung",
                "Erzeugt aus beiden Rohdaten eine gemeinsame Basistabelle mit einheitlichen Spalten.",
            )
            render_cta_label("Nächste Aktion")
            if st.button("Merge & Normalisierung ausführen", type="primary", use_container_width=True):
                try:
                    merged = pd.concat([normalize_de(de_df), normalize_ch(ch_df)], ignore_index=True)
                    merged["AccidentYear"] = pd.to_numeric(merged["AccidentYear"], errors="coerce").astype("Int64")
                    merged["AccidentInvolvingMotorcycle"] = pd.to_numeric(
                        merged["AccidentInvolvingMotorcycle"], errors="coerce"
                    ).astype("Int64")
                    st.session_state["merged"] = merged
                    st.session_state.pop("error_df", None)
                    st.session_state.pop("problem_mask", None)
                    st.session_state.pop("without_errors", None)
                    st.session_state.pop("cleaned", None)
                    st.session_state.pop("night_df", None)
                    if persist_to_disk:
                        save_csv(to_output_schema(merged), MERGED_PATH)
                        st.success(f"Merge erfolgreich. Gespeichert: {MERGED_PATH}")
                    else:
                        st.success("Merge erfolgreich (nur im Arbeitsspeicher).")
                except Exception as exc:
                    st.error(f"Merge fehlgeschlagen: {exc}")

    merged_df = st.session_state.get("merged")

    if merged_df is not None:
        base_loaded = True
        merged_export = to_output_schema(merged_df)
        st.dataframe(merged_export.head(15), use_container_width=True)
        with st.expander("Optional: Export", expanded=False):
            st.download_button(
                "workflow_01_merged_normalized.csv herunterladen",
                data=to_csv_bytes(merged_export),
                file_name="workflow_01_merged_normalized.csv",
                mime="text/csv",
                use_container_width=True,
                type="secondary",
            )

    with st.container():
        render_step_header(
            3,
            "Fehlerzeilen prüfen",
            "Markiert Zeilen mit fehlenden oder ungültigen Werten für die Bereinigung.",
        )
        can_check_errors = merged_df is not None and has_required_columns(merged_df)
        if merged_df is not None and not has_required_columns(merged_df):
            st.warning("Basis-Tabelle hat nicht alle Pflichtspalten für die Fehleranalyse. Dokumentations-Übersicht bleibt trotzdem verfügbar.")
        render_cta_label("Nächste Aktion")
        if st.button("Fehlerzeilen prüfen", type="primary", disabled=not can_check_errors, use_container_width=True):
            try:
                error_df, problem_mask = find_error_entries(merged_df)
                st.session_state["error_df"] = error_df
                st.session_state["problem_mask"] = problem_mask
                st.session_state.pop("without_errors", None)
                st.session_state.pop("cleaned", None)
                st.session_state.pop("night_df", None)
                if persist_to_disk:
                    save_csv(to_output_schema(error_df), ERROR_PATH)
                    st.success(f"Fehlercheck fertig. {len(error_df):,} Fehlerzeilen gespeichert: {ERROR_PATH}")
                else:
                    st.success(f"Fehlercheck fertig. {len(error_df):,} Fehlerzeilen im Speicher bereit.")
            except Exception as exc:
                st.error(f"Fehlercheck fehlgeschlagen: {exc}")

    error_df = st.session_state.get("error_df")
    problem_mask = st.session_state.get("problem_mask")

    if error_df is not None:
        error_export = to_output_schema(error_df)
        st.dataframe(error_export.head(15), use_container_width=True)
        with st.expander("Optional: Export", expanded=False):
            st.download_button(
                "workflow_02_error_rows.csv herunterladen",
                data=to_csv_bytes(error_export),
                file_name="workflow_02_error_rows.csv",
                mime="text/csv",
                use_container_width=True,
                type="secondary",
            )

    with st.container():
        render_step_header(
            4,
            "Fehler entfernen",
            "Entfernt die markierten Fehlerzeilen und erzeugt die bereinigte Arbeitstabelle.",
        )
        can_remove = problem_mask is not None and merged_df is not None
        render_cta_label("Nächste Aktion")
        if st.button("Fehlerzeilen entfernen", type="primary", disabled=not can_remove, use_container_width=True):
            without_errors = merged_df.loc[~problem_mask].copy()
            st.session_state["without_errors"] = without_errors
            st.session_state.pop("cleaned", None)
            st.session_state.pop("night_df", None)
            if persist_to_disk:
                save_csv(to_output_schema(without_errors), WITHOUT_ERRORS_PATH)
                st.success(f"Bereinigt gespeichert: {WITHOUT_ERRORS_PATH}")
            else:
                st.success("Bereinigung fertig (nur im Arbeitsspeicher).")

    without_errors = st.session_state.get("without_errors")
    if without_errors is not None:
        without_export = to_output_schema(without_errors)
        st.dataframe(without_export.head(15), use_container_width=True)
        with st.expander("Optional: Export", expanded=False):
            st.download_button(
                "workflow_03_clean_rows.csv herunterladen",
                data=to_csv_bytes(without_export),
                file_name="workflow_03_clean_rows.csv",
                mime="text/csv",
                use_container_width=True,
                type="secondary",
            )

    with st.container():
        render_step_header(
            5,
            "Analysejahr wählen",
            "Filtert die bereinigten Daten auf ein Jahr. Diese Tabelle ist die Basis für Ziele 1 bis 4 und für Schritt 6.",
        )
        year = st.number_input("Jahr", min_value=1900, max_value=2100, value=2024, step=1)
        can_filter = without_errors is not None
        render_cta_label("Nächste Aktion")
        if st.button("Auf Analysejahr filtern", type="primary", disabled=not can_filter, use_container_width=True):
            year_num = pd.to_numeric(without_errors["AccidentYear"], errors="coerce").astype("Int64")
            cleaned = without_errors.loc[year_num == int(year)].copy()
            st.session_state["cleaned"] = cleaned
            st.session_state["analysis_year"] = int(year)
            st.session_state.pop("night_df", None)
            if persist_to_disk:
                save_csv(to_output_schema(cleaned), CLEANED_2024_PATH)
                st.success(f"Final gespeichert: {CLEANED_2024_PATH}")
            else:
                st.success("Jahresfilter fertig (nur im Arbeitsspeicher).")

    cleaned = st.session_state.get("cleaned")
    if cleaned is not None:
        cleaned_export = to_output_schema(cleaned)
        st.dataframe(cleaned_export.head(15), use_container_width=True)
        with st.expander("Optional: Export", expanded=False):
            st.download_button(
                "workflow_04_final_filtered.csv herunterladen",
                data=to_csv_bytes(cleaned_export),
                file_name="workflow_04_final_filtered.csv",
                mime="text/csv",
                use_container_width=True,
                type="secondary",
            )

    with st.container():
        render_step_header(
            6,
            "Ziel 5 vorbereiten",
            "Ergänzt die originale Unfallstunde und berechnet effektive Nachtunfälle anhand bürgerlicher Dämmerungszeiten.",
        )
        can_prepare_night = cleaned is not None and de_df is not None and ch_df is not None
        if cleaned is not None and (de_df is None or ch_df is None):
            st.warning("Für Ziel 5 werden zusätzlich die hochgeladenen Rohdaten benötigt, damit die numerische Unfallstunde ergänzt werden kann.")
        render_cta_label("Nächste Aktion für Ziel 5")
        if st.button("Nachtklassifikation berechnen", type="primary", disabled=not can_prepare_night, use_container_width=True):
            try:
                analysis_year = int(st.session_state.get("analysis_year", year))
                with_hour = add_numeric_hour(cleaned, de_df, ch_df)
                night_df = classify_night_accidents(with_hour, analysis_year)
                st.session_state["night_df"] = night_df
                if persist_to_disk:
                    save_csv(to_output_schema(night_df), NIGHT_PATH)
                    st.success(f"Nachtklassifikation fertig. Gespeichert: {NIGHT_PATH}")
                else:
                    st.success("Nachtklassifikation fertig (nur im Arbeitsspeicher).")
            except Exception as exc:
                st.error(f"Nachtklassifikation fehlgeschlagen: {exc}")

    night_df = st.session_state.get("night_df")
    if night_df is not None:
        night_export = to_output_schema(night_df)
        st.dataframe(night_export.head(15), use_container_width=True)
        with st.expander("Optional: Export", expanded=False):
            st.download_button(
                "workflow_05_night_classified.csv herunterladen",
                data=to_csv_bytes(night_export),
                file_name="workflow_05_night_classified.csv",
                mime="text/csv",
                use_container_width=True,
                type="secondary",
            )

    render_sidebar_progress(
        base_loaded=base_loaded,
        merged_df=merged_df,
        error_df=error_df,
        without_errors=without_errors,
        cleaned=cleaned,
        night_df=night_df,
    )

    render_goals_dashboard(cleaned, night_df)

    if persist_to_disk:
        st.caption(f"Lokaler Speicherpfad: {SAVE_DIR}")
    else:
        st.caption("CSV-Export ist deaktiviert. Ergebnisse bleiben für diese Session im GUI.")


if __name__ == "__main__":
    main()
