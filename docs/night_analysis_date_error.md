# Date Approximation Error — Using the 15th as Representative Day

**Context:** The accident dataset contains only `AccidentYear` and `AccidentMonth` — no exact date.  
To query sunrise/sunset times from the API, we must pick a representative day per month.  
This document quantifies the error introduced by always choosing the **15th of each month**.

**Metric:** Maximum difference (in minutes) between the civil twilight time on the 15th and the civil  
twilight time on any other day in the same month. Shown as **max(Δ dawn, Δ dusk)** — whichever  
is larger, since dusk almost always dominates.

All times are in local time (Europe/Berlin for DE, Europe/Zurich for CH).  
Data year: 2024. Computed with the `astral` library.

---

## Results — Max Δ per State and Month (minutes)

`*` = DST transition month (clocks change after the 15th → structural offset included in delta)

| Code | State / Region | Jan | Feb | Mar* | Apr | Mai | Jun | Jul | Aug | Sep | Okt* | Nov | Dez | **Max (no DST)** |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| BW_DE | Baden-Württemberg  | 23 | 25 | **85*** | 30 | 23 | 11 | 22 | 33 | 32 | **88*** | 20 | 14 | **33** |
| BY_DE | Bayern             | 23 | 25 | **85*** | 30 | 24 | 11 | 23 | 33 | 32 | **88*** | 21 | 14 | **33** |
| SL_DE | Saarland           | 23 | 26 | **85*** | 31 | 24 | 12 | 23 | 34 | 33 | **88*** | 21 | 14 | **34** |
| RP_DE | Rheinland-Pfalz    | 24 | 26 | **86*** | 31 | 25 | 12 | 24 | 35 | 33 | **89*** | 22 | 14 | **35** |
| HE_DE | Hessen             | 24 | 27 | **87*** | 32 | 26 | 12 | 25 | 35 | 34 | **90*** | 22 | 14 | **35** |
| SN_DE | Sachsen            | 25 | 27 | **87*** | 33 | 26 | 13 | 25 | 36 | 34 | **90*** | 22 | 14 | **36** |
| TH_DE | Thüringen          | 25 | 27 | **87*** | 32 | 26 | 12 | 25 | 36 | 34 | **90*** | 22 | 14 | **36** |
| NW_DE | Nordrhein-Westfalen| 25 | 27 | **88*** | 33 | 27 | 13 | 26 | 36 | 35 | **90*** | 23 | 14 | **36** |
| ST_DE | Sachsen-Anhalt     | 25 | 28 | **88*** | 34 | 27 | 13 | 26 | 37 | 35 | **91*** | 23 | 15 | **37** |
| BB_DE | Brandenburg        | 26 | 28 | **89*** | 34 | 28 | 14 | 27 | 38 | 36 | **91*** | 23 | 15 | **38** |
| BE_DE | Berlin             | 26 | 28 | **89*** | 34 | 28 | 14 | 27 | 38 | 36 | **92*** | 24 | 15 | **38** |
| NI_DE | Niedersachsen      | 26 | 29 | **89*** | 35 | 28 | 14 | 28 | 38 | 36 | **92*** | 24 | 15 | **38** |
| HB_DE | Bremen             | 26 | 29 | **90*** | 35 | 29 | 14 | 28 | 39 | 37 | **92*** | 24 | 15 | **39** |
| HH_DE | Hamburg            | 27 | 29 | **90*** | 36 | 30 | 15 | 29 | 39 | 37 | **93*** | 25 | 15 | **39** |
| MV_DE | Mecklenburg-Vorp.  | 27 | 30 | **90*** | 36 | 30 | 15 | 29 | 39 | 37 | **93*** | 25 | 15 | **39** |
| SH_DE | Schleswig-Holstein | 27 | 30 | **91*** | 37 | 31 | 15 | 30 | 40 | 38 | **93*** | 25 | 16 | **40** |
| CH    | Switzerland        | 22 | 23 | **83*** | 28 | 22 | 10 | 20 | 31 | 30 | **86*** | 19 | 13 | **31** |

*Sorted south → north by latitude within DE.*

---

## Why March and October Spike

DST transitions in 2024 fall on:
- **March 31** — clocks spring forward +1 h (CET → CEST)
- **October 27** — clocks fall back −1 h (CEST → CET)

Both transitions happen **after the 15th**, so the representative date sits in the pre-transition timezone while the last ~5–10 days of the month sit in the post-transition timezone.

| Effect | Mar | Okt |
|---|---|---|
| Natural day-length drift within month | ~30–38 min | ~30–38 min |
| DST clock jump | +60 min | +60 min |
| **Combined worst-case delta** | **83–91 min** | **86–93 min** |

The DST jump contributes ~60 of those ~85–93 minutes. The remaining ~25–33 min is pure day-length change.

---

## Natural Variation (non-DST months)

Excluding March and October, the worst month is consistently **August**:  
day length is shortening fast after the solstice, but the absolute change per day is still high (~2 min/day).  
**June** is always the best month (~10–15 min), because the rate of change is near zero at the solstice.

| Tier | States | Typical range (non-DST max) |
|---|---|---|
| South (lat ~48–50°) | BW_DE, BY_DE, SL_DE, RP_DE | 23–35 min |
| Mid (lat ~50–53°) | HE_DE, SN_DE, TH_DE, NW_DE, ST_DE | 25–37 min |
| North (lat ~53–54°) | BB_DE, BE_DE, NI_DE, HB_DE, HH_DE, MV_DE, SH_DE | 26–40 min |
| Switzerland | CH (single center) | 13–31 min |

Switzerland's smaller delta is due to its lower latitude and the single-center approach smoothing out extremes.

---

## Context: How Large Is 40 Minutes?

| Source of uncertainty | Size |
|---|---|
| Data precision (`AccidentHourNumeric` is integer 0–23) | ±30 min (accident can fall anywhere in the hour) |
| Civil twilight buffer vs. astronomical dark | ~25 min |
| Date approximation error — non-DST months (worst case SH_DE Aug) | **~40 min** |
| Date approximation error — DST months (worst case SH_DE Mar/Okt) | **~90 min** |

For non-DST months the date error (~40 min) is comparable to the data precision (±30 min) — both are sub-hour uncertainties and the civil twilight buffer partially absorbs them.

For DST months (~90 min error), the combined uncertainty exceeds one full hour, which means an accident at 18:00 on October 28 could be wrongly classified as night or day depending on which representative date is used.

---

## Decision Made

**The 15th is used for all 12 months including March and October** (`classify_night.py`).  
The two-date alternative was considered but not implemented. The DST limitation is documented below.

**Known limitation — DST months:**
> *"For March and October, night classification carries an additional ±60-minute uncertainty for accidents occurring after the DST transition (Mar 31 / Oct 27). This affects at most 5 days per month (~16 % of monthly accidents in those two months, or ~2.7 % of annual accidents)."*

---

## API Call Budget (actual)

Using 15th only for all months:

| Period | Dates queried | DE states | CH cantons (shared center) | Total calls |
|---|---|---|---|---|
| All 12 months | 15th only | 16 × 12 = 192 | 1 × 12 = 12 | **204** |

All 489 unique (CantonCode, month) pairs resolved to 204 distinct coordinate+date combinations  
(all 41 CH cantons share the same center coordinates). Results cached in `data/twilight_cache.json`.
