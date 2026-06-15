# DataWrangling: Verkehrsunfälle CH/DE

Dieses Projekt bereitet Verkehrsunfalldaten aus Deutschland und der Schweiz auf, harmonisiert beide Datensätze in ein gemeinsames Schema und wertet die Daten für das Jahr 2024 aus. Im Fokus stehen Unterschiede zwischen CH und DE, Unfallzeitpunkte, Saisonalität, Wochentage, Unfallschwere, Motorradbeteiligung und Nachtunfälle.

Die Rohdaten werden zuerst gemerged, geprüft und bereinigt. Danach entstehen finale CSV-Dateien in `data/processed/` und Auswertungsgrafiken in `plots/`.

Die Rohdaten, welche noch nicht verarbeitet wurden, befinden sich im Ordner /data/raw (Ursprungsdaten).

## Fragestellungen

- Ziel 1: Gibt es einen Zusammenhang zwischen Motorradbeteiligung und Unfallschwere?
- Ziel 2: Passieren am Abend und in der Nacht mehr oder schwerere Unfälle als tagsüber?
- Ziel 3: Gibt es im Winter Unterschiede zwischen Schweiz und Deutschland?
- Ziel 4: An welchem Wochentag passieren die meisten und die tödlichsten Unfälle?
- Ziel 5: Wie unterscheiden sich echte Nachtunfälle von der groben Tageszeit-Kategorie `Nacht`?

## Installation

```bash
pip install -r requirements.txt
```

## GUI starten

Die Streamlit-GUI führt Schritt für Schritt durch den Workflow:

```bash
PYTHONPATH=scripts/preprocessing streamlit run scripts/gui/workflow_gui.py
```

In der GUI werden die beiden Rohdateien hochgeladen, anschliessend laufen Merge, Fehlerprüfung, Bereinigung, Jahresfilter und die Nachtklassifikation für Ziel 5.

## Pipeline per Terminal

### 1. Daten mergen

```bash
python scripts/preprocessing/merge_data.py \
  --de data/processed/RoadAccident_de.csv \
  --ch data/processed/RoadAccident_ch.csv \
  --out data/processed/merged.csv
```

### 2. Fehlerzeilen erkennen

```bash
python scripts/preprocessing/filter_missing_values.py \
  --input data/processed/merged.csv \
  --errors-out data/processed/error_entries.csv
```

### 3. Fehler entfernen und Jahr filtern

```bash
python scripts/preprocessing/Delete_error_data.py \
  --input data/processed/merged.csv \
  --errors data/processed/error_entries.csv \
  --out-without-errors data/processed/without_error_entries.csv \
  --out-cleaned-2024 data/processed/cleaned_2024_data_ch_de.csv \
  --year 2024
```

### 4. Ziel 5 vorbereiten

Ziel 5 braucht zusätzlich die originale numerische Unfallstunde. Danach wird mithilfe bürgerlicher Dämmerungszeiten je Region und Monat berechnet, ob ein Unfall effektiv bei Nacht passiert ist.

```bash
PYTHONPATH=scripts/preprocessing python scripts/preprocessing/add_hour.py
python scripts/preprocessing/classify_night.py
```

Hinweis: `classify_night.py` nutzt die API von `sunrise-sunset.org`. Ergebnisse werden in `data/processed/twilight_cache.json` gecached, damit spätere Läufe nicht erneut alle Werte laden müssen.

## Analysen ausführen

Nach der Pipeline können die Ziele einzeln ausgeführt werden:

```bash
python scripts/analysis/goal1.py
python scripts/analysis/goal2.py
python scripts/analysis/goal3.py
python scripts/analysis/goal4.py
python scripts/analysis/goal5.py
```

Die Grafiken werden in `plots/` gespeichert.

## Wichtige Dateien

- `data/processed/merged.csv`: harmonisierte CH/DE-Gesamttabelle
- `data/processed/error_entries.csv`: erkannte Fehlerzeilen
- `data/processed/without_error_entries.csv`: bereinigte Tabelle ohne Fehlerzeilen
- `data/processed/cleaned_2024_data_ch_de.csv`: finale 2024-Daten für Ziele 1 bis 4
- `data/processed/cleaned_2024_with_hour.csv`: finale 2024-Daten mit numerischer Unfallstunde
- `data/processed/cleaned_2024_night.csv`: finale 2024-Daten mit `NightAccident` für Ziel 5

## Ziel 5 in der Pipeline

Ziel 5 war ursprünglich stärker vom restlichen Workflow getrennt, weil es nicht nur die bereinigten 2024-Daten braucht, sondern auch die originale Stunde aus den Rohdaten und eine zusätzliche Nachtklassifikation. Diese Schritte sind jetzt als eigener Pipeline-Abschnitt dokumentiert und in der GUI als Schritt 6 integriert.
