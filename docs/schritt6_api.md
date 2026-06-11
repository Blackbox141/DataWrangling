# Schritt 6 – API: Bürgerliche Dämmerung & Nachtklassifikation

In der Analyse haben wir festgestellt, dass durch das Uhrzeit-Binning wichtige Daten und Insights verloren gehen. Durch die geografische Lage der Schweiz und Deutschlands ist es je nach Standort und Tag unterschiedlich lange hell. Dementsprechend haben wir nachträglich die Uhrzeit hinzugefügt.

## API-Abfrage

Damit die Daten auch korrekt vom API-Provider gezogen werden, mussten wir prüfen, welche Daten wichtig sind. Bei uns sind der Kanton bzw. das Bundesland und die Uhrzeit relevant. Leider haben wir nicht den genauen Standort und die genaue Uhrzeit der Unfälle. Deshalb haben wir entschieden, den geografischen Mittelpunkt des jeweiligen Bundeslandes für Deutschland sowie den Mittelpunkt der Schweiz für die API-Abfrage zu nutzen.

Für die Abfrage verwenden wir die öffentliche API von **sunrise-sunset.org**, die für einen gegebenen Standort und ein Datum die bürgerliche Dämmerungszeiten (civil twilight begin/end) in UTC zurückgibt.

## Caching

Da wir die Daten nur einmal pro (Region, Monat)-Kombination benötigen, werden alle API-Ergebnisse lokal in einer Datei (`twilight_cache.json`) gespeichert. Bei erneuter Ausführung wird die API nicht nochmals abgefragt — stattdessen wird direkt aus dem Cache gelesen. Das reduziert die Laufzeit erheblich und schont die Rate Limits des Providers.

Als repräsentativen Stichtag pro Monat verwenden wir jeweils den **15. des Monats**. Dieser liegt mittig im Monat, minimiert den maximalen Fehler gegenüber jedem anderen Tag und erlaubt es, mit einem einzigen API-Aufruf pro (Region, Monat) auszukommen.

## Fehlermarge

Die Fehlermarge durch die Verwendung des Bundesland-Mittelpunkts beträgt maximal **20 Minuten**. Dieser Wert ergibt sich aus der geografischen Ausdehnung der größten Bundesländer: Der Unterschied im Sonnenauf- bzw. -untergang zwischen dem Zentrum und dem Rand eines Bundeslandes liegt typischerweise unter 20 Minuten. Das ist im akzeptablen Fehlerbereich, da wir die **bürgerliche Dämmerung** als Kipppunkt für Tag- oder Nachtunfälle verwenden — also den Zeitraum, in dem es trotz gesetztem oder noch nicht aufgegangenem Sonnen bereits hell genug ist, um ohne Kunstlicht zu sehen.

## Klassifikation

Ein Unfall wird als **Nachtunfall** klassifiziert, wenn die Unfallstunde außerhalb des bürgerlichen Dämmerungsfensters liegt:

```
NachtUnfall = 1,  wenn  Stunde < Dämmerungsbeginn  ODER  Stunde > Dämmerungsende
NachtUnfall = 0,  sonst  (konservativ: Randstunden gelten als Tag)
```

Das Ergebnis wird als neue Spalte `NightAccident` (0 = Tag, 1 = Nacht) in den Datensatz geschrieben.

## Bekannter Fehler: Zeitumstellung

Ein bekannter Fehler in den Daten ist die Zeitumstellung im März bzw. Oktober. Da wir jedoch für alle Monate den **15. als Stichtag** verwenden, liegt der 15. März stets *vor* der Umstellung (letzter Sonntag im März) und der 15. Oktober stets *nach* der Rückstellung (letzter Sonntag im Oktober). Beide Stichtage fallen damit in einen konsistenten Zeitzonenbereich, sodass kein DST-bedingter Versatz in die Dämmerungszeiten einfließt.
