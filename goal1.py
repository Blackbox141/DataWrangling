import pandas as pd
import matplotlib.pyplot as plt
import scipy.stats as stats

df = pd.read_csv("/Users/dennis/Desktop/DataWrangling/cleaned_2024_data_ch_de.csv")

# Land aus CantonCode ableiten (endet auf _CH oder _DE)
df["Land"] = df["CantonCode"].str[-2:]

# Motorrad: 1.0 = Ja, 0.0 = Nein → in Bool umwandeln
df["Motorrad"] = df["AccidentInvolvingMotorcycle"] == 1.0

# Unfallschwere-Spalte prüfen – welche Werte gibt es?
print(df["AccidentSeverityCategory"].unique())

# Kreuztabelle mit relativen Anteilen (%)
ct = pd.crosstab(
    df["Motorrad"],
    df["AccidentSeverityCategory"],
    normalize="index"   # Zeilenprozente: Anteil je Motorrad ja/nein
) * 100

ct.index = ["Ohne Motorrad", "Mit Motorrad"]
print("\n=== Unfallschwere nach Motorradbeteiligung (%) ===")
print(ct.round(1))

for land in ["CH", "DE"]:
    subset = df[df["Land"] == land]
    ct_land = pd.crosstab(
        subset["Motorrad"],
        subset["AccidentSeverityCategory"],
        normalize="index"
    ) * 100
    ct_land.index = ["Ohne Motorrad", "Mit Motorrad"]
    print(f"\n=== {land}: Unfallschwere nach Motorradbeteiligung (%) ===")
    print(ct_land.round(1))
    print(f"   (n = {len(subset):,} Unfälle)")

    # Absolute Häufigkeiten für den Test
    ct_abs = pd.crosstab(df["Motorrad"], df["AccidentSeverityCategory"])

    chi2, p, dof, expected = stats.chi2_contingency(ct_abs)

    print(f"\n=== Chi-Quadrat-Test ===")
    print(f"Chi² = {chi2:.2f}, df = {dof}, p = {p:.4f}")

    if p < 0.05:
        print("→ Signifikanter Zusammenhang (p < 0.05)")
    else:
        print("→ Kein signifikanter Zusammenhang")


fig, axes = plt.subplots(1, 3, figsize=(15, 5))
titles = ["Gesamt", "Schweiz (CH)", "Deutschland (DE)"]
subsets = [df, df[df["Land"]=="CH"], df[df["Land"]=="DE"]]

for ax, title, subset in zip(axes, titles, subsets):
    ct_plot = pd.crosstab(
        subset["Motorrad"],
        subset["AccidentSeverityCategory"],
        normalize="index"
    ) * 100
    ct_plot.index = ["Ohne\nMotorrad", "Mit\nMotorrad"]
    ct_plot.plot(kind="bar", ax=ax, rot=0, colormap="Set2")
    ax.set_title(title, fontsize=13, fontweight="bold")
    ax.set_ylabel("Anteil (%)")
    ax.set_xlabel("")
    ax.legend(title="Schwere", fontsize=9)
    ax.set_ylim(0, 100)
    n = len(subset)
    ax.text(0.98, 0.98, f"n={n:,}", transform=ax.transAxes,
            ha="right", va="top", fontsize=9, color="gray")

plt.suptitle("Unfallschwere nach Motorradbeteiligung", fontsize=14, y=1.02)
plt.tight_layout()
plt.savefig("ziel1_motorrad_schwere.png", dpi=150, bbox_inches="tight")
plt.show()
print("Grafik gespeichert als: ziel1_motorrad_schwere.png")