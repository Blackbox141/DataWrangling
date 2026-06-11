from pathlib import Path
import pandas as pd
import matplotlib.pyplot as plt
import scipy.stats as stats

_DATA = Path(__file__).parent / "data" / "cleaned_2024_data_ch_de.csv"
df = pd.read_csv(_DATA)

# Land ableiten
df["Land"] = df["CantonCode"].str[-2:]

# Monatsnamen auf Nummern mappen
monat_map = {
    "Jan": 1,  "Feb": 2,  "Mar": 3,  "Apr": 4,
    "Mai": 5,  "Jun": 6,  "Jul": 7,  "Aug": 8,
    "Sep": 9,  "Okt": 10, "Nov": 11, "Dez": 12
}
df["MonatNr"] = df["AccidentMonth"].map(monat_map)

# Winter = Dez, Jan, Feb (meteorologisch)
winter_monate = [12, 1, 2]
df["Saison"] = df["MonatNr"].apply(
    lambda m: "Winter" if m in winter_monate else "Rest des Jahres"
)

# Prüfen
print("Saison-Verteilung:\n", df["Saison"].value_counts())
print("\nLand-Verteilung:\n", df["Land"].value_counts())

print("=== Winteranteil an allen Unfällen: CH vs. DE ===\n")

for land in ["CH", "DE"]:
    sub = df[df["Land"] == land]
    total = len(sub)
    winter = (sub["Saison"] == "Winter").sum()
    pct = winter / total * 100
    print(f"{land}: {winter:,} Winterunfälle von {total:,} gesamt → {pct:.1f}%")

# Monat für Monat: relativer Anteil pro Land
print("\n=== Monatlicher Anteil an Jahresunfällen: CH vs. DE ===")
monat_order = ["Jan","Feb","Mar","Apr","Mai","Jun",
               "Jul","Aug","Sep","Okt","Nov","Dez"]

for land in ["CH", "DE"]:
    sub = df[df["Land"] == land]
    vc = sub["AccidentMonth"].value_counts(normalize=True).reindex(monat_order) * 100
    print(f"\n{land}:")
    print(vc.round(1).to_string())

# Unfallschwere im Winter vs. Rest, getrennt nach Land
print("=== Unfallschwere Winter vs. Rest: CH ===")
ch = df[df["Land"] == "CH"]
ct_ch = pd.crosstab(ch["Saison"], ch["AccidentSeverityCategory"],
                    normalize="index") * 100
print(ct_ch.round(1))

print("\n=== Unfallschwere Winter vs. Rest: DE ===")
de = df[df["Land"] == "DE"]
ct_de = pd.crosstab(de["Saison"], de["AccidentSeverityCategory"],
                    normalize="index") * 100
print(ct_de.round(1))

# Direkter Vergleich: Anteil schwerer Unfälle im Winter CH vs. DE
print("\n=== Anteil schwerer/tödlicher Unfälle im Winter ===")
for land, sub in [("CH", ch), ("DE", de)]:
    winter_sub = sub[sub["Saison"] == "Winter"]
    schwer_cols = [c for c in winter_sub["AccidentSeverityCategory"].unique()
                   if c.lower() in ["schwer","tod","tödlich","schwerverletzt"]]
    schwer_n = winter_sub["AccidentSeverityCategory"].isin(schwer_cols).sum()
    total_w = len(winter_sub)
    print(f"{land} Winter: {schwer_n:,} schwer/tödlich von {total_w:,} → {schwer_n/total_w*100:.1f}%")

# Test 1: Ist der Winteranteil in CH signifikant anders als in DE?
# Kontingenztabelle: Land × Saison
ct_land_saison = pd.crosstab(df["Land"], df["Saison"])
chi2, p, dof, _ = stats.chi2_contingency(ct_land_saison)
print("=== Chi²-Test: Land × Saison (Winter vs. Rest) ===")
print(f"Chi² = {chi2:.2f}, df = {dof}, p = {p:.4f}")
if p < 0.05:
    print("→ Signifikanter Unterschied zwischen CH und DE")
else:
    print("→ Kein signifikanter Unterschied")

# Test 2: Unterscheidet sich die Schwere im Winter zwischen CH und DE?
winter_df = df[df["Saison"] == "Winter"]
ct_schwere = pd.crosstab(winter_df["Land"], winter_df["AccidentSeverityCategory"])
chi2b, pb, dofb, _ = stats.chi2_contingency(ct_schwere)
print("\n=== Chi²-Test: Unfallschwere im Winter – CH vs. DE ===")
print(f"Chi² = {chi2b:.2f}, df = {dofb}, p = {pb:.4f}")
if pb < 0.05:
    print("→ Signifikanter Unterschied in der Schwere")
else:
    print("→ Kein signifikanter Unterschied in der Schwere")


fig, axes = plt.subplots(2, 2, figsize=(16, 12))
monat_order = ["Jan","Feb","Mar","Apr","Mai","Jun",
               "Jul","Aug","Sep","Okt","Nov","Dez"]
winter_farbe = "#4C9BE8"
sommer_farbe = "#B0C4DE"
farben_land = {"CH": "#2E86AB", "DE": "#E84855"}

# --- Plot 1: Monatlicher Anteil CH vs. DE ---
ax = axes[0, 0]
x = range(len(monat_order))
width = 0.35
for i, land in enumerate(["CH", "DE"]):
    sub = df[df["Land"] == land]
    pct = sub["AccidentMonth"].value_counts(normalize=True).reindex(monat_order) * 100
    winter_col = {"CH": "#2E86AB", "DE": "#E84855"}[land]
    sommer_col = {"CH": "#A8C8DC", "DE": "#F0A0A8"}[land]
    farben = [winter_col if m in ["Dez","Jan","Feb"] else sommer_col
              for m in monat_order]
    ax.bar([xi + i*width for xi in range(len(monat_order))], pct, width,
           color=farben, label=land, alpha=0.85)
ax.set_xticks([xi + width/2 for xi in range(len(monat_order))])
ax.set_xticklabels(monat_order, rotation=45)
ax.axvspan(-0.5, 1.5 + width, alpha=0.08, color="#2E86AB", label="Winter")
ax.axvspan(10.5, 11.5 + width, alpha=0.08, color="#2E86AB")
ax.set_title("Monatlicher Unfallanteil: CH vs. DE (%)", fontweight="bold")
ax.set_ylabel("Anteil an Jahresunfällen (%)")
ax.legend()

# --- Plot 2: Winteranteil gesamt CH vs. DE ---
ax = axes[0, 1]
winter_pct = []
for land in ["CH", "DE"]:
    sub = df[df["Land"] == land]
    pct = (sub["Saison"] == "Winter").mean() * 100
    winter_pct.append(pct)
bars = ax.bar(["CH", "DE"], winter_pct,
              color=[farben_land["CH"], farben_land["DE"]], alpha=0.85, width=0.4)
ax.axhline(y=100/12*3, color="gray", linestyle="--", alpha=0.6,
           label="Gleichverteilung (3/12 Monate = 25%)")
ax.set_title("Winteranteil an Gesamtunfällen: CH vs. DE", fontweight="bold")
ax.set_ylabel("Anteil (%)")
ax.set_ylim(0, 35)
ax.legend()
for bar, val in zip(bars, winter_pct):
    ax.text(bar.get_x()+bar.get_width()/2, bar.get_height()+0.3,
            f"{val:.1f}%", ha="center", fontsize=11, fontweight="bold")

# --- Plot 3: Unfallschwere Winter vs. Rest – CH ---
ax = axes[1, 0]
ct_ch_plot = pd.crosstab(ch["Saison"], ch["AccidentSeverityCategory"],
                         normalize="index") * 100
ct_ch_plot.plot(kind="bar", stacked=True, ax=ax, rot=0, colormap="RdYlGn_r")
ax.set_title("Unfallschwere Winter vs. Rest – CH (%)", fontweight="bold")
ax.set_ylabel("Anteil (%)")
ax.legend(title="Schwere", bbox_to_anchor=(1, 1))

# --- Plot 4: Unfallschwere Winter vs. Rest – DE ---
ax = axes[1, 1]
ct_de_plot = pd.crosstab(de["Saison"], de["AccidentSeverityCategory"],
                         normalize="index") * 100
ct_de_plot.plot(kind="bar", stacked=True, ax=ax, rot=0, colormap="RdYlGn_r")
ax.set_title("Unfallschwere Winter vs. Rest – DE (%)", fontweight="bold")
ax.set_ylabel("Anteil (%)")
ax.legend(title="Schwere", bbox_to_anchor=(1, 1))

plt.suptitle("Ziel 3: Winterunfälle CH vs. DE", fontsize=15, y=1.01, fontweight="bold")
plt.tight_layout()
plt.savefig(Path(__file__).parent / "ziel3_winter.png", dpi=150, bbox_inches="tight")
plt.show()
print("Grafik gespeichert als: ziel3_winter.png")