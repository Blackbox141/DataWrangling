# Schritt 6 – Fehlklassifikationsanalyse: Uhrzeit-Binning vs. bürgerliche Dämmerung

## Fragestellung

Das ursprüngliche Dataset enthält keine genaue Unfallstunde, sondern nur ein Uhrzeit-Bin (`Nacht`, `Vormittag`, `Nachmittag`, `Abend`). Das Bin `Nacht` umfasst dabei die Stunden 0–5 Uhr.

Die Frage ist: **Wie viele Unfälle wurden durch dieses Binning falsch als Nacht- bzw. Tagunfall eingestuft**, verglichen mit der API-basierten Klassifikation über die bürgerliche Dämmerung?

---

## Konfusionsmatrix

|  | Bin = Tag (nicht Nacht) | Bin = Nacht |
|---|---|---|
| **API = Tag** | 242.447 ✅ True Negative (84,9 %) | 2.095 ❌ False Positive (0,7 %) |
| **API = Nacht** | 28.851 ❌ False Negative (10,1 %) | 12.269 ✅ True Positive (4,3 %) |

Gesamtzahl Unfälle: **285.662**

---

## False Positives – Bin sagt Nacht, war aber Tag (2.095 | 0,7 %)

Diese Fälle sind überschaubar und konzentrieren sich ausschließlich auf die frühen Morgenstunden:

| Stunde | Anzahl |
|---|---|
| 3 Uhr | 27 |
| 4 Uhr | 394 |
| 5 Uhr | 1.674 |

**Ursache:** Das Nacht-Bin endet erst um 6 Uhr. In den Sommermonaten beginnt die bürgerliche Dämmerung jedoch bereits ab ca. 3–4 Uhr morgens — der Tag bricht also an, während das Bin noch „Nacht" anzeigt. Stunde 5 ist mit Abstand der größte Treiber.

---

## False Negatives – Bin sagt nicht Nacht, war aber Nacht (28.851 | 10,1 %)

Das ist das eigentliche Problem. Über 28.000 Nachtunfälle wurden vom Binning **nicht als Nacht erkannt** — fast das 14-fache der False Positives.

### Aufschlüsselung nach Bin:

| Bin | Anzahl | Anteil an FN |
|---|---|---|
| Abend-Bin (18–23 Uhr) | 24.671 | 85,5 % |
| Vormittag-Bin (6 Uhr) | 2.872 | 10,0 % |
| Nachmittag-Bin (17 Uhr) | 1.308 | 4,5 % |

### Aufschlüsselung nach Stunde:

| Stunde | Anzahl | Bin |
|---|---|---|
| 6 Uhr | 2.872 | Vormittag |
| 17 Uhr | 1.308 | Nachmittag |
| 18 Uhr | 3.955 | Abend |
| 19 Uhr | 4.097 | Abend |
| 20 Uhr | 3.858 | Abend |
| 21 Uhr | 3.897 | Abend |
| 22 Uhr | 4.745 | Abend |
| 23 Uhr | 4.119 | Abend |

**Ursache:** Das Abend-Bin endet nicht — es läuft bis 23 Uhr durch. In den Herbst- und Wintermonaten ist es ab ca. 16–17 Uhr bereits dunkel. Das Binning berücksichtigt diese saisonale Verschiebung nicht, weshalb tausende Unfälle bei Dunkelheit fälschlicherweise als „Abend" (= Tag) klassifiziert werden. Stunde 22 ist der stärkste Einzeltreiber (4.745 Fälle).

---

## Betroffene Monate

### False Positives nach Monat

| Monat | Anzahl | Ursache |
|---|---|---|
| Jan | 0 | Dämmerung beginnt nach 6 Uhr → kein Fehler |
| Feb | 0 | Dämmerung beginnt nach 6 Uhr → kein Fehler |
| **Mar** | **145** | Dämmerung rückt vor 6 Uhr |
| **Apr** | **307** | Dämmerung ca. 5:40 Uhr |
| **Mai** | **376** | Dämmerung ca. 4:30 Uhr |
| **Jun** | **454** | Dämmerung ca. 3:50 Uhr |
| **Jul** | **464** | Dämmerung ca. 3:10–4:00 Uhr |
| **Aug** | **349** | Dämmerung ca. 4:00 Uhr |
| Sep | 0 | Dämmerung wieder nach 6 Uhr |
| Okt–Dez | 0 | Dämmerung nach 6 Uhr |

**Betroffen: nur März bis August** — wenn die Sonne so früh aufgeht, dass die bürgerliche Dämmerung beginnt, bevor der Nacht-Bin endet (6 Uhr).

---

### False Negatives nach Monat (gestapelt nach Bin)

| Monat | Vormittag-Bin | Nachmittag-Bin | Abend-Bin | **Gesamt** |
|---|---|---|---|---|
| Jan | 759 | 0 | 3.317 | **4.076** |
| Feb | 382 | 0 | 2.366 | **2.748** |
| Mar | 0 | 0 | 2.192 | **2.192** |
| Apr | 0 | 0 | 1.201 | **1.201** |
| Mai | 0 | 0 | 968 | **968** |
| Jun | 0 | 0 | 479 | **479** |
| Jul | 0 | 0 | 670 | **670** |
| Aug | 0 | 0 | 1.147 | **1.147** |
| Sep | 0 | 0 | 1.820 | **1.820** |
| Okt | 791 | 0 | 2.586 | **3.377** |
| Nov | 390 | 271 | 4.215 | **4.876** |
| Dez | 550 | 1.037 | 3.710 | **5.297** |

**Drei Fehlertypen je nach Jahreszeit:**

- **Vormittag-Bin (Stunde 6):** Jan, Feb, Okt, Nov, Dez — 6 Uhr liegt noch in der Nacht, weil die Sonne erst um 7–8 Uhr aufgeht
- **Nachmittag-Bin (Stunde 17):** Nov, Dez — Sonnenuntergang bereits vor 17 Uhr, 17 Uhr ist also schon Nacht
- **Abend-Bin (18–23 Uhr):** alle Monate betroffen, Winter am stärksten — das Abend-Bin endet nicht und umfasst Stunden, die im Winter vollständig im Dunkeln liegen

---

## Fazit

Das Uhrzeit-Binning ist als Grundlage für eine Nacht/Tag-Klassifikation **ungeeignet**, weil es die jahreszeitliche Variation des Sonnenauf- und -untergangs vollständig ignoriert.

- **10,1 % aller Unfälle** (28.851 Fälle) werden fälschlicherweise als Tagunfall gewertet.
- Der Fehler ist **asymmetrisch**: False Negatives überwiegen die False Positives um Faktor 14.
- Hauptproblem ist das **Abend-Bin**: In den Wintermonaten ist es zu diesen Stunden längst Nacht.

Die API-basierte Klassifikation über die bürgerliche Dämmerung behebt diesen systematischen Fehler, indem der tatsächliche Dämmerungszeitpunkt je Standort und Monat berücksichtigt wird.
