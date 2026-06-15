from pathlib import Path
import pandas as pd
import matplotlib.pyplot as plt
import scipy.stats as stats

_ROOT = Path(__file__).parent.parent.parent
_DATA = _ROOT / "data" / "processed" / "cleaned_2024_data_ch_de.csv"
df = pd.read_csv(_DATA)

# Land ableiten
df["Land"] = df["CantonCode"].str[-2:]

# Tageszeit in zwei Gruppen einteilen
tag_map = {
    "Vormittag": "Tag",
    "Nachmittag": "Tag",
    "Abend": "Nacht/Abend",
    "Nacht": "Nacht/Abend"
}
df["TagNacht"] = df["AccidentHour"].map(tag_map)

# Prüfen ob alle Werte gemappt wurden
print("Nicht gemappte Werte:", df["TagNacht"].isna().sum())
print("Tageszeit-Verteilung:\n", df["AccidentHour"].value_counts())

order = ["Vormittag", "Nachmittag", "Abend", "Nacht"]

# Gesamt (absolut + relativ)
gesamt = df["AccidentHour"].value_counts().reindex(order)
gesamt_pct = (gesamt / gesamt.sum() * 100).round(1)

print("=== Gesamt: Unfälle nach Tageszeit ===")
for tz in order:
    print(f"  {tz:<12} {gesamt[tz]:>6,}  ({gesamt_pct[tz]}%)")

# Nach Land
for land in ["CH", "DE"]:
    sub = df[df["Land"] == land]
    vc = sub["AccidentHour"].value_counts().reindex(order)
    pct = (vc / vc.sum() * 100).round(1)
    print(f"\n=== {land} (n={len(sub):,}) ===")
    for tz in order:
        print(f"  {tz:<12} {vc[tz]:>6,}  ({pct[tz]}%)")

# Tag vs. Nacht/Abend Zusammenfassung
print("\n=== Tag vs. Nacht/Abend (Gesamt) ===")
print(df["TagNacht"].value_counts(normalize=True).mul(100).round(1))

# Kreuztabelle: Tageszeit × Schwere (zeilenprozente)
ct = pd.crosstab(
    df["AccidentHour"],
    df["AccidentSeverityCategory"],
    normalize="index"
).reindex(order) * 100

print("=== Unfallschwere nach Tageszeit (%) ===")
print(ct.round(1))

# Gleiche Tabelle nach Land
for land in ["CH", "DE"]:
    sub = df[df["Land"] == land]
    ct_land = pd.crosstab(
        sub["AccidentHour"],
        sub["AccidentSeverityCategory"],
        normalize="index"
    ).reindex(order) * 100
    print(f"\n=== {land}: Unfallschwere nach Tageszeit (%) ===")
    print(ct_land.round(1))

# Test: Gibt es einen signifikanten Zusammenhang Tageszeit × Schwere?
ct_abs = pd.crosstab(df["AccidentHour"], df["AccidentSeverityCategory"])
chi2, p, dof, _ = stats.chi2_contingency(ct_abs)

print(f"=== Chi-Quadrat-Test: Tageszeit × Schwere ===")
print(f"Chi² = {chi2:.2f}, df = {dof}, p = {p:.4f}")
if p < 0.05:
    print("→ Signifikanter Zusammenhang (p < 0.05)")
else:
    print("→ Kein signifikanter Zusammenhang")

# Auch für Tag vs. Nacht/Abend (vereinfacht)
ct_abs2 = pd.crosstab(df["TagNacht"], df["AccidentSeverityCategory"])
chi2b, pb, dofb, _ = stats.chi2_contingency(ct_abs2)
print(f"\n=== Chi-Quadrat-Test: Tag/Nacht × Schwere ===")
print(f"Chi² = {chi2b:.2f}, df = {dofb}, p = {pb:.4f}")

fig, axes = plt.subplots(2, 2, figsize=(16, 12))

# --- Plot 1: Anzahl Unfälle nach Tageszeit (Gesamt) ---
ax = axes[0, 0]
counts = df["AccidentHour"].value_counts().reindex(order)
bars = ax.bar(order, counts, color=["#4C9BE8","#4C9BE8","#E8724C","#E8724C"])
ax.set_title("Anzahl Unfälle nach Tageszeit (Gesamt)", fontweight="bold")
ax.set_ylabel("Anzahl Unfälle")
for bar, val in zip(bars, counts):
    ax.text(bar.get_x()+bar.get_width()/2, bar.get_height()+200,
            f"{val:,}", ha="center", va="bottom", fontsize=10)

# --- Plot 2: Anteil Unfälle nach Tageszeit, CH vs DE ---
ax = axes[0, 1]
x = range(len(order))
width = 0.35
for i, (land, color) in enumerate([("CH","#2E86AB"), ("DE","#E84855")]):
    sub = df[df["Land"]==land]
    pct = sub["AccidentHour"].value_counts(normalize=True).reindex(order) * 100
    bars = ax.bar([xi + i*width for xi in x], pct, width, label=land, color=color, alpha=0.85)
ax.set_xticks([xi + width/2 for xi in x])
ax.set_xticklabels(order)
ax.set_title("Anteil Unfälle nach Tageszeit: CH vs DE (%)", fontweight="bold")
ax.set_ylabel("Anteil (%)")
ax.legend()

# --- Plot 3: Unfallschwere nach Tageszeit (Gesamt, gestapelt) ---
ax = axes[1, 0]
ct_plot = pd.crosstab(
    df["AccidentHour"],
    df["AccidentSeverityCategory"],
    normalize="index"
).reindex(order) * 100
ct_plot.plot(kind="bar", stacked=True, ax=ax, rot=0, colormap="RdYlGn_r")
ax.set_title("Unfallschwere nach Tageszeit – Gesamt (%)", fontweight="bold")
ax.set_ylabel("Anteil (%)")
ax.legend(title="Schwere", bbox_to_anchor=(1,1))

# --- Plot 4: Unfallschwere nach Tageszeit, CH vs DE nebeneinander ---
ax = axes[1, 1]
# Anteil schwerer+tödlicher Unfälle pro Tageszeit und Land
results = []
for land in ["CH", "DE"]:
    sub = df[df["Land"]==land]
    ct_l = pd.crosstab(sub["AccidentHour"], sub["AccidentSeverityCategory"], normalize="index") * 100
    # Schwere Kategorie anpassen falls nötig (z.B. "Schwer" oder "Tod")
    schwer_cols = [c for c in ct_l.columns if c.lower() in ["schwer","tod","tödlich","schwerverletzt"]]
    ct_l["Schwer+Tod"] = ct_l[schwer_cols].sum(axis=1)
    ct_l["Land"] = land
    results.append(ct_l[["Schwer+Tod","Land"]])

combined = pd.concat(results).reset_index()
for i, (land, color) in enumerate([("CH","#2E86AB"), ("DE","#E84855")]):
    sub = combined[combined["Land"]==land].set_index("AccidentHour").reindex(order)
    ax.bar([xi + i*width for xi in x], sub["Schwer+Tod"], width,
           label=land, color=color, alpha=0.85)
ax.set_xticks([xi + width/2 for xi in x])
ax.set_xticklabels(order)
ax.set_title("Anteil schwerer/tödlicher Unfälle CH vs DE (%)", fontweight="bold")
ax.set_ylabel("Anteil schwer+tödlich (%)")
ax.legend()

plt.suptitle("Ziel 2: Unfälle nach Tageszeit", fontsize=15, y=1.01, fontweight="bold")
plt.tight_layout()
plt.savefig(_ROOT / "plots" / "ziel2_tageszeit.png", dpi=150, bbox_inches="tight")
plt.show()
print("Grafik gespeichert als: ziel2_tageszeit.png")
