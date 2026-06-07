# Road Accident Night/Day Analysis — DE vs CH (2024)
**Project:** Comparative accident statistics Germany vs Switzerland  
**Focus:** Classify accidents as night-time or day-time using sunrise/sunset data  

---

## 1. Research Question

How many road accidents occur between sunset and sunrise in Germany and Switzerland in 2024, and how do the two countries compare?

---

## 2. Data Sources

### Accident Data ✅ Classified — final file ready for analysis

**Final file:** `data/cleaned_2024_night.csv` (285,662 rows, 10 columns)

| Column | Values | Notes |
|---|---|---|
| `AccidentUID` | string | Unique accident identifier |
| `AccidentYear` | 2024 | Integer |
| `AccidentMonth` | Jan … Dez | German 3-letter abbreviation |
| `AccidentWeekDay` | Mo … So | German 2-letter abbreviation |
| `AccidentHour` | Nacht / Vormittag / Nachmittag / Abend | 6h daypart bin |
| `AccidentHourNumeric` | 0 – 23 | Raw integer hour — used for night classification |
| `CantonCode` | e.g. `BW_DE`, `AG_CH` | Region + country suffix (`_DE` or `_CH`) |
| `AccidentSeverityCategory` | Tot / Schwer / Leicht | Fatal / Serious / Minor |
| `AccidentInvolvingMotorcycle` | 0 / 1 | Binary flag |
| `NightAccident` | 0 / 1 | **1 = night-time accident**, 0 = day-time |

**Results:** 41,120 night accidents (14.4 %) / 244,542 day accidents (85.6 %)

**Pipeline:**
```
cleaned_2024_data_ch_de.csv  →  add_hour.py  →  cleaned_2024_with_hour.csv
cleaned_2024_with_hour.csv   →  classify_night.py  →  cleaned_2024_night.csv
```

**Important structural notes:**
- **No separate country column.** Country is derived from `CantonCode` suffix: `_DE` = Germany, `_CH` = Switzerland.
- **No exact date.** Only year + month are available. API queries use the 15th of each month as the representative date.
- **No road type or accident type fields** in this dataset.

### Sunrise/Sunset Data (API)
**Primary:** `sunrise-sunset.org`  
```
GET https://api.sunrise-sunset.org/json?lat={lat}&lng={lng}&date={YYYY-MM-DD}&formatted=0
```
- Free, no API key required
- Returns UTC times → convert to local time (Europe/Zurich or Europe/Berlin)
- Key fields: `sunrise`, `sunset`, `civil_twilight_begin`, `civil_twilight_end`

---

## 3. Methodology

### 3.1 Geographic Reference Points

#### Switzerland — Single center point justified
- Max delta across CH (Chiasso → Schaffhausen): **~16 minutes** → negligible
- **Center:** Älggi-Alp `lat=46.8182, lng=8.2275`

#### Germany — Per Bundesland center coordinates
Using state-level coordinates because the national N/S spread causes:
- Summer solstice delta (Lörrach → Flensburg): **~1h 24min**
- Winter solstice delta (Lörrach → Flensburg): **~1h 12min**

Max intra-state error (worst case: Niedersachsen, ~5° E-W): **~20 minutes** → acceptable.

| CantonCode | Bundesland | Lat | Lng |
|---|---|---|---|
| `BW_DE` | Baden-Württemberg | 48.6616 | 9.3501 |
| `BY_DE` | Bayern | 48.9384 | 11.4283 |
| `BE_DE` | Berlin | 52.5200 | 13.4050 |
| `BB_DE` | Brandenburg | 52.4126 | 12.5316 |
| `HB_DE` | Bremen | 53.0793 | 8.8017 |
| `HH_DE` | Hamburg | 53.5753 | 10.0153 |
| `HE_DE` | Hessen | 50.6521 | 9.1624 |
| `MV_DE` | Mecklenburg-Vorpommern | 53.6127 | 12.4296 |
| `NI_DE` | Niedersachsen | 52.6367 | 9.8451 |
| `NW_DE` | Nordrhein-Westfalen | 51.4332 | 7.6616 |
| `RP_DE` | Rheinland-Pfalz | 50.1183 | 7.3089 |
| `SL_DE` | Saarland | 49.3964 | 7.0229 |
| `SN_DE` | Sachsen | 51.1045 | 13.2017 |
| `ST_DE` | Sachsen-Anhalt | 51.9503 | 11.6923 |
| `SH_DE` | Schleswig-Holstein | 54.2194 | 9.6961 |
| `TH_DE` | Thüringen | 50.9051 | 11.0238 |

### 3.2 Night-Time Definition

> Night-time is defined as the period between **civil twilight end** (evening) and **civil twilight begin** (morning).

Using civil twilight instead of raw sunset/sunrise because:
- Civil twilight provides ~25 minutes of usable light after sunset
- This buffer comfortably absorbs the ~10 min max positional error from state center coordinates
- More representative of actual visibility conditions relevant to accident risk

```
is_night = (AccidentHourNumeric < civil_twilight_begin_hour)
        OR (AccidentHourNumeric > civil_twilight_end_hour)
```

Hours that coincide with the twilight threshold are treated as **day** (conservative).  
Classification is at hourly granularity — no minute-level data is available.

### 3.3 Workflow ✅ Complete

```
✅ 1. Load cleaned_2024_with_hour.csv (285,662 rows)
✅ 2. Derive country from CantonCode suffix:
          CantonCode.endswith("_DE") → Germany (Europe/Berlin)
          CantonCode.endswith("_CH") → Switzerland (Europe/Zurich)
✅ 3. Build lookup: month × CantonCode → representative date (15th of each month)
          e.g. AccidentMonth="Mai" → 2024-05-15
✅ 4. Query sunrise-sunset.org API for each unique month × coordinate pair
          489 unique pairs → 204 live API calls + 285 from cache
          DE: per-Bundesland center coordinates (see table above)
          CH: single national center (lat=46.8182, lng=8.2275)
          Results cached in data/twilight_cache.json
✅ 5. Parse UTC response times → convert to local timezone
          DE → Europe/Berlin  |  CH → Europe/Zurich
✅ 6. Join twilight hours back to accident data on CantonCode + month
✅ 7. Classify: NightAccident = 1 if hour < dawn_hour OR hour > dusk_hour, else 0
          → 41,120 night (14.4%)  |  244,542 day (85.6%)
          → saved to data/cleaned_2024_night.csv
[ ] 8. Validate using 4×6h block distribution (see section 4)
[ ] 9. Aggregate and compare DE vs CH
```

---

## 4. Validation — 4×6h Block Check

Split the day into four 6-hour blocks using `AccidentHourNumeric` and check that night accident distribution is plausible.
These blocks map exactly to the existing `AccidentHour` daypart bins:

| Block | AccidentHourNumeric | AccidentHour (bin) | Expected night share |
|---|---|---|---|
| Block A | 0 – 5 | Nacht | High (most hours are night year-round) |
| Block B | 6 – 11 | Vormittag | Mixed (night in winter mornings) |
| Block C | 12 – 17 | Nachmittag | Low (rarely night) |
| Block D | 18 – 23 | Abend | Mixed (night in winter evenings) |

This is a **plausibility check**, not ground truth. Night accidents should cluster heavily in Block A and partially in B/D depending on season.

---

## 5. Margin of Error Documentation

Full analysis in `night_analysis_date_error.md`. Summary:

| Source of uncertainty | Max error | Impact |
|---|---|---|
| CH single center point (coordinate) | ~8 min | Negligible |
| DE state center points (coordinate) | ~10 min | Negligible — within twilight buffer |
| Civil twilight buffer vs. astronomical dark | ~25 min | Absorbs coordinate errors |
| Date approximation — non-DST months (worst: SH_DE Aug) | ~40 min | Comparable to ±30 min data precision |
| Date approximation — DST months Mar/Okt (worst: SH_DE) | ~90 min | Exceeds one hour; ~16 % of monthly accidents affected |

**DST limitation:** The 15th of March (pre-DST, CET) and October (pre-DST, CEST) is used as the representative date for the entire month. Accidents after the clock change (Mar 31 / Oct 27) carry up to ~90 min of additional twilight-time error. This is documented as a known limitation.

**Methodology note for report:**
> *"Civil twilight times were queried from the sunrise-sunset.org API using the 15th of each month as a representative date, with per-Bundesland center coordinates for Germany and a single national center for Switzerland. Night-time is defined as AccidentHourNumeric < civil_twilight_begin_hour OR AccidentHourNumeric > civil_twilight_end_hour (local time). For March and October, classification of accidents after the DST transition carries an additional ±60-minute uncertainty affecting at most ~16 % of accidents in those months."*

---

## 6. Output / Analysis Goals

- [ ] Total accidents by day/night per country (derived from `CantonCode` suffix)
- [ ] Night accident share (%) DE vs CH
- [ ] Seasonal breakdown (night share by month — using `AccidentMonth`)
- [ ] Severity distribution: are night accidents more severe? (using `AccidentSeverityCategory`: Tot / Schwer / Leicht)
- [ ] Motorcycle involvement: are night accidents more often motorcycle-related? (using `AccidentInvolvingMotorcycle`)
- [ ] Bundesland-level heatmap for DE (using `CantonCode` values ending in `_DE`)
- [ ] Canton-level breakdown for CH (using `CantonCode` values ending in `_CH`)

---

## 7. Tech Stack

- **Language:** Python
- **Key libraries:** `pandas`, `requests`, `zoneinfo`
- **Error analysis:** `astral` (used in `night_analysis_date_error.md` computations only)
- **API:** sunrise-sunset.org (free, no key) — cache: `data/twilight_cache.json`
- **Visualization:** TBD (matplotlib / plotly / seaborn)

---

## 8. To-Do

- [x] Clean and merge accident data (DE + CH)
- [x] Add `AccidentHourNumeric` (0–23) to merged file → `cleaned_2024_with_hour.csv`
- [x] Analyse date approximation error → `night_analysis_date_error.md`
- [x] Build sunrise/sunset API fetcher with CantonCode → coordinate lookup → `classify_night.py`
- [x] Cache API results → `data/twilight_cache.json` (204 calls, re-runs free)
- [x] Classify `NightAccident` → `data/cleaned_2024_night.csv`
- [ ] Run validation (4×6h blocks using `AccidentHourNumeric`, see section 4)
- [ ] Build output visualizations
