# Changelog

## [Unreleased]

### Fixed
- Replaced all hardcoded absolute paths (`/Users/dennis/Desktop/DataWrangling/`) with portable paths relative to each script's own location (`Path(__file__).parent / "data"`) in every Python file:
  - `merge_data.py` — `DEFAULT_DATA_DIR`
  - `filter_missing_values.py` — `DEFAULT_INPUT_PATH`, `DEFAULT_ERRORS_OUT_PATH`
  - `Delete_error_data.py` — `DEFAULT_DATA_DIR`
  - `delete_years.py` — `DEFAULT_INPUT_PATH`, `DEFAULT_OUTPUT_PATH`
  - `goal1.py` – `goal4.py` — CSV input path and PNG output paths
  - `workflow_gui.py` — `SAVE_DIR`

## [1.0.0] – 2026-05-31

### Added
- `merge_data.py` — merges and normalises DE (`RoadAccident_de.csv`) and CH (`RoadAccident_ch.csv`) road-accident datasets into a unified 8-column schema (`AccidentUID`, `AccidentYear`, `AccidentMonth`, `AccidentWeekDay`, `AccidentHour`, `CantonCode`, `AccidentSeverityCategory`, `AccidentInvolvingMotorcycle`); supports CSV, Excel, and Parquet I/O
- `filter_missing_values.py` — scans the merged output for missing (`NaN`) values and invalid categorical entries; writes all problematic rows to `error_entries.csv`
- `Delete_error_data.py` — removes flagged error rows from the merged dataset and produces a year-filtered clean subset (`cleaned_2024_data_ch_de.csv`)
- `delete_years.py` — standalone utility to keep only rows matching a given year (default 2024)
- `goal1.py` — chi-square analysis of motorcycle involvement vs. accident severity; saves `ziel1_motorrad_schwere.png`
- `goal2.py` — time-of-day accident analysis (Vormittag / Nachmittag / Abend / Nacht) with CH vs. DE comparison; saves `ziel2_tageszeit.png`
- `goal3.py` — winter season (Dec / Jan / Feb) accident and severity analysis, CH vs. DE; saves `ziel3_winter.png`
- `goal4.py` — weekday analysis: most accidents and highest fatality rate per day, CH vs. DE; saves `ziel4_wochentag.png`
- `workflow_gui.py` — Streamlit web application providing a step-by-step interactive workflow (load → merge → error detection → error removal → year filter) with inline analysis of all four goals
- Initial data files added under `data/`: `RoadAccident_de.csv`, `RoadAccident_ch.csv`, `merged.csv`, `error_entries.csv`, `without_error_entries.csv`, `cleaned_2024_data_ch_de.csv`
