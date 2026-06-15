from pathlib import Path
import pandas as pd
import matplotlib.pyplot as plt
import scipy.stats as stats


_ROOT = Path(__file__).parent.parent.parent
_DATA = _ROOT / "data" / "processed" / "cleaned_2024_data_ch_de.csv"
df = pd.read_csv(_DATA)

# Land aus CantonCode ableiten
df["Land"] = df["CantonCode"].astype("string").str[-2:]

weekday_order = ["Mo", "Di", "Mi", "Do", "Fr", "Sa", "So"]

# Toedliche Unfaelle markieren (robust gegen unterschiedliche Schreibweisen)
severity_norm = df["AccidentSeverityCategory"].astype("string").str.strip().str.lower()
fatal_labels = {"tot", "tod", "toedlich", "tödlich"}
df["IsFatal"] = severity_norm.isin(fatal_labels)
df["Motorrad"] = pd.to_numeric(df["AccidentInvolvingMotorcycle"], errors="coerce") == 1

# Gesamtanalyse
weekday_counts = df["AccidentWeekDay"].value_counts().reindex(weekday_order, fill_value=0)
fatal_counts = (
    df[df["IsFatal"]]["AccidentWeekDay"]
    .value_counts()
    .reindex(weekday_order, fill_value=0)
)
fatal_rate = (fatal_counts / weekday_counts.replace(0, pd.NA) * 100).fillna(0)

most_accidents_day = weekday_counts.idxmax()
deadliest_day_rate = fatal_rate[weekday_counts > 0].idxmax()
deadliest_day_abs = fatal_counts.idxmax()

print("=== Ziel 4: Wochentag-Analyse (Gesamt) ===")
print("Unfaelle pro Wochentag:")
for day in weekday_order:
    print(f"  {day}: {int(weekday_counts[day]):,}")

print("\nToedliche Unfaelle pro Wochentag (absolut):")
for day in weekday_order:
    print(f"  {day}: {int(fatal_counts[day]):,}")

print("\nAnteil toedlicher Unfaelle pro Wochentag (%):")
for day in weekday_order:
    print(f"  {day}: {fatal_rate[day]:.2f}%")

print("\nErgebnis:")
print(f"- Meiste Unfaelle passieren am: {most_accidents_day} ({int(weekday_counts[most_accidents_day]):,})")
print(f"- Toedlichster Wochentag (relativ): {deadliest_day_rate} ({fatal_rate[deadliest_day_rate]:.2f}% toedlich)")
print(f"- Meiste toedliche Unfaelle (absolut): {deadliest_day_abs} ({int(fatal_counts[deadliest_day_abs]):,})")

# Zusatzfrage: Toedliche Unfaelle mit Motorradbeteiligung nach Wochentag
fatal_df = df[df["IsFatal"]].copy()
fatal_moto_by_day = (
    fatal_df.groupby("AccidentWeekDay")["Motorrad"]
    .sum()
    .reindex(weekday_order, fill_value=0)
)
fatal_total_by_day = fatal_df["AccidentWeekDay"].value_counts().reindex(weekday_order, fill_value=0)
fatal_moto_rate_by_day = (fatal_moto_by_day / fatal_total_by_day.replace(0, pd.NA) * 100).fillna(0)

print("\n=== Toedliche Unfaelle mit Motorradbeteiligung (nach Wochentag) ===")
for day in weekday_order:
    print(
        f"  {day}: {int(fatal_moto_by_day[day]):,} von {int(fatal_total_by_day[day]):,}"
        f" ({fatal_moto_rate_by_day[day]:.2f}%)"
    )

print(
    f"\n- Am toedlichsten Wochentag ({deadliest_day_rate}) mit Motorradbeteiligung: "
    f"{int(fatal_moto_by_day[deadliest_day_rate]):,} von {int(fatal_total_by_day[deadliest_day_rate]):,}"
    f" ({fatal_moto_rate_by_day[deadliest_day_rate]:.2f}%)"
)
print(
    f"- Am Wochentag mit den meisten Unfaellen ({most_accidents_day}) toedlich + Motorrad: "
    f"{int(fatal_moto_by_day[most_accidents_day]):,} von {int(fatal_total_by_day[most_accidents_day]):,}"
    f" ({fatal_moto_rate_by_day[most_accidents_day]:.2f}%)"
)

# Zusatz: CH vs DE
print("\n=== CH vs DE ===")
for land in ["CH", "DE"]:
    sub = df[df["Land"] == land]
    if sub.empty:
        print(f"{land}: keine Daten vorhanden")
        continue

    counts_land = sub["AccidentWeekDay"].value_counts().reindex(weekday_order, fill_value=0)
    fatal_land = sub[sub["IsFatal"]]["AccidentWeekDay"].value_counts().reindex(weekday_order, fill_value=0)
    fatal_rate_land = (fatal_land / counts_land.replace(0, pd.NA) * 100).fillna(0)

    max_day_land = counts_land.idxmax()
    deadliest_land = fatal_rate_land[counts_land > 0].idxmax()

    print(f"\n{land} (n={len(sub):,})")
    print(f"- Meiste Unfaelle: {max_day_land} ({int(counts_land[max_day_land]):,})")
    print(f"- Toedlichster Tag: {deadliest_land} ({fatal_rate_land[deadliest_land]:.2f}% toedlich)")

# Statistiktest: Zusammenhang Wochentag x Schwere
ct_abs = pd.crosstab(df["AccidentWeekDay"], df["AccidentSeverityCategory"]).reindex(weekday_order, fill_value=0)
chi2, p, dof, _ = stats.chi2_contingency(ct_abs)
print("\n=== Chi-Quadrat-Test: Wochentag x Schwere ===")
print(f"Chi2 = {chi2:.2f}, df = {dof}, p = {p:.4f}")
if p < 0.05:
    print("-> Signifikanter Zusammenhang (p < 0.05)")
else:
    print("-> Kein signifikanter Zusammenhang")


fig, axes = plt.subplots(2, 2, figsize=(16, 11))

# Plot 1: Absolute Unfallzahl pro Wochentag
ax = axes[0, 0]
bars = ax.bar(weekday_order, weekday_counts.values, color="#2E86AB", alpha=0.9)
ax.set_title("Unfaelle pro Wochentag (absolut)", fontweight="bold")
ax.set_ylabel("Anzahl Unfaelle")
for bar, val in zip(bars, weekday_counts.values):
    ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 50, f"{int(val):,}", ha="center", va="bottom", fontsize=9)

# Plot 2: Toedliche Unfaelle pro Wochentag (absolut)
ax = axes[0, 1]
bars = ax.bar(weekday_order, fatal_counts.values, color="#E84855", alpha=0.9)
ax.set_title("Toedliche Unfaelle pro Wochentag (absolut)", fontweight="bold")
ax.set_ylabel("Anzahl toedlicher Unfaelle")
for bar, val in zip(bars, fatal_counts.values):
    ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 1, f"{int(val):,}", ha="center", va="bottom", fontsize=9)

# Plot 3: Anteil toedlicher Unfaelle pro Wochentag
ax = axes[1, 0]
bars = ax.bar(weekday_order, fatal_rate.values, color="#F29E4C", alpha=0.9)
ax.set_title("Anteil toedlicher Unfaelle pro Wochentag (%)", fontweight="bold")
ax.set_ylabel("Anteil toedlich (%)")
for bar, val in zip(bars, fatal_rate.values):
    ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.05, f"{val:.2f}%", ha="center", va="bottom", fontsize=9)

# Plot 4: Unfallanteil pro Wochentag, CH vs DE
ax = axes[1, 1]
x = range(len(weekday_order))
width = 0.36
for i, (land, color) in enumerate([("CH", "#2E86AB"), ("DE", "#E84855")]):
    sub = df[df["Land"] == land]
    if sub.empty:
        continue
    pct = sub["AccidentWeekDay"].value_counts(normalize=True).reindex(weekday_order, fill_value=0) * 100
    ax.bar([xi + i * width for xi in x], pct.values, width, label=land, color=color, alpha=0.85)

ax.set_xticks([xi + width / 2 for xi in x])
ax.set_xticklabels(weekday_order)
ax.set_title("Unfallanteil pro Wochentag: CH vs DE (%)", fontweight="bold")
ax.set_ylabel("Anteil (%)")
ax.legend()

plt.suptitle("Ziel 4: Wochentag mit meisten und toedlichsten Unfaellen", fontsize=15, y=1.01, fontweight="bold")
plt.tight_layout()
plt.savefig(_ROOT / "plots" / "ziel4_wochentag.png", dpi=150, bbox_inches="tight")
plt.show()
print("Grafik gespeichert als: ziel4_wochentag.png")
