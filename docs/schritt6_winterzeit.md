# Schritt 6 – Hat die Winterzeit eine Auswirkung auf Nachtunfälle?

## Fragestellung

Hat die Jahreszeit — konkret die kürzeren Tage im Winter — eine messbare Auswirkung auf den Anteil der Nachtunfälle?

---

## Methodik

Als Grundlage dienen die API-klassifizierten Nachtunfälle (`NightAccident = 1`), die auf der bürgerlichen Dämmerung basieren. Ergänzend wurde die durchschnittliche Tageslichtdauer je Monat aus dem Twilight-Cache berechnet (Mittelwert über alle Regionen, Stichtag jeweils der 15. des Monats).

---

## Ergebnisse

### Nachtunfall-Anteil und Tageslichtdauer nach Monat

| Monat | Tageslicht (h) | Nachtunfälle | Gesamt | Anteil |
|---|---|---|---|---|
| Jan | 9,6 h | 5.248 | 17.988 | **29,2 %** |
| Feb | 11,1 h | 3.637 | 16.555 | **22,0 %** |
| Mar | 13,0 h | 3.066 | 20.430 | **15,0 %** |
| Apr | 15,1 h | 2.006 | 23.711 | **8,5 %** |
| Mai | 17,0 h | 1.815 | 28.193 | **6,4 %** |
| Jun | 18,2 h | 1.471 | 28.702 | **5,1 %** |
| Jul | 17,6 h | 1.578 | 29.054 | **5,4 %** |
| Aug | 15,8 h | 2.239 | 28.653 | **7,8 %** |
| Sep | 13,8 h | 3.132 | 27.775 | **11,3 %** |
| Okt | 11,8 h | 4.531 | 24.376 | **18,6 %** |
| Nov | 10,1 h | 6.042 | 21.892 | **27,6 %** |
| Dez | 9,2 h | 6.355 | 18.333 | **34,7 %** |

Der Nachtunfall-Anteil steigt mit abnehmender Tageslichtdauer nahezu linear an.

---

### Korrelation: Tageslicht ↔ Nachtunfall-Anteil

| Kennzahl | Wert |
|---|---|
| Pearson r | **−0,9605** |
| r² | **0,9226** |
| p-Wert | **< 0,001** |

Mit r = −0,96 besteht eine **sehr starke negative Korrelation**: Je kürzer der Tag, desto höher der Anteil der Nachtunfälle. Das Bestimmtheitsmaß r² = 0,92 zeigt, dass über **92 % der monatlichen Variation** im Nachtunfall-Anteil allein durch die Tageslichtdauer erklärt werden.

---

### Saisonvergleich: Winter vs. Sommer

| Jahreszeit | Nachtunfälle | Gesamt | Anteil |
|---|---|---|---|
| Sommer (Mai–Aug) | 7.103 | 114.602 | **6,2 %** |
| Frühling/Herbst (Mar/Apr/Sep/Okt) | 12.735 | 96.292 | **13,2 %** |
| Winter (Nov–Feb) | 21.282 | 74.768 | **28,5 %** |

Im Winter liegt der Nachtunfall-Anteil **4,6× höher** als im Sommer.

**Chi²-Test (Winter vs. Sommer):** Chi² = 17.603, df = 1, **p < 0,001** → hochsignifikant.

---

## Antwort auf die Fragestellung

**Ja, die Winterzeit hat eine sehr starke Auswirkung auf den Anteil der Nachtunfälle.**

Der Effekt ist nicht zufällig, sondern direkt auf die kürzere Tageslichtdauer zurückzuführen:

1. **Physikalische Ursache:** Im Winter gibt es weniger Tageslicht (Dez: 9,2 h vs. Jun: 18,2 h). Mehr Verkehr findet damit bei Dunkelheit statt — besonders in den Abend- und frühen Morgenstunden.

2. **Starke Korrelation:** r = −0,96 zwischen Tageslichtdauer und Nachtunfall-Anteil zeigt, dass die beiden Größen nahezu spiegelbildlich verlaufen.

3. **Faktor 4,6:** Im Winter passieren anteilig 4,6× mehr Nachtunfälle als im Sommer — ein drastischer und statistisch hochsignifikanter Unterschied.

4. **Bestätigung durch API-Klassifikation:** Erst durch die bürgerliche Dämmerung als Grundlage (statt des fixen Uhrzeit-Binnings) wird dieser Effekt sichtbar — das Binning hätte einen großen Teil dieser Winterunfälle als „Abend" klassifiziert und den Effekt verschleiert.
