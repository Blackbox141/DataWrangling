from pathlib import Path
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import scipy.stats as stats

_DATA = Path(__file__).parent.parent.parent / "data" / "processed" / "cleaned_2024_night.csv"
df = pd.read_csv(_DATA, dtype={"AccidentUID": str}, low_memory=False)

# Abgeleitete Spalten
df["Land"]     = df["CantonCode"].astype("string").str[-2:]
df["TagNacht"] = df["NightAccident"].map({0: "Tag", 1: "Nacht"})
df["Motorrad"] = pd.to_numeric(df["AccidentInvolvingMotorcycle"], errors="coerce") == 1

MONAT_ORDER  = ["Jan","Feb","Mar","Apr","Mai","Jun","Jul","Aug","Sep","Okt","Nov","Dez"]
SEV_ORDER    = ["Tot", "Schwer", "Leicht"]
SEV_COLORS   = {"Tot": "#C0392B", "Schwer": "#E67E22", "Leicht": "#2E86AB"}

# ── Konsolenausgabe ───────────────────────────────────────────────────────────

print("=== Ziel 5: Unfälle bei Nacht ===\n")

# 1. Tag-/Nacht-Verteilung
print("=== 1. Tag-/Nacht-Verteilung ===")
for gruppe, sub in [("Gesamt", df),
                    ("CH",     df[df["Land"] == "CH"]),
                    ("DE",     df[df["Land"] == "DE"])]:
    n_nacht = int(sub["NightAccident"].sum())
    n_tag   = len(sub) - n_nacht
    print(f"  {gruppe} (n={len(sub):,}):  "
          f"Tag {n_tag:,} ({n_tag/len(sub)*100:.1f}%)  |  "
          f"Nacht {n_nacht:,} ({n_nacht/len(sub)*100:.1f}%)")

# 2. Motorradbeteiligung
print("\n=== 2. Motorradbeteiligung Tag vs. Nacht ===")
ct_moto_pct = pd.crosstab(df["TagNacht"], df["Motorrad"], normalize="index") * 100
ct_moto_pct.columns = ["Ohne Motorrad", "Mit Motorrad"]
print(ct_moto_pct.round(1))

for land in ["CH", "DE"]:
    sub = df[df["Land"] == land]
    ct  = pd.crosstab(sub["TagNacht"], sub["Motorrad"], normalize="index") * 100
    ct.columns = ["Ohne Motorrad", "Mit Motorrad"]
    print(f"\n  {land} (n={len(sub):,}):")
    print(ct.round(1))

chi2, p, dof, _ = stats.chi2_contingency(pd.crosstab(df["TagNacht"], df["Motorrad"]))
print(f"\nChi²-Test Nacht × Motorrad: Chi² = {chi2:.2f}, df = {dof}, p = {p:.4f}")
print("→ Signifikant (p < 0.05)" if p < 0.05 else "→ Nicht signifikant")

# 3. Unfallschwere Tag vs. Nacht
print("\n=== 3. Unfallschwere Tag vs. Nacht ===")
ct_sev = pd.crosstab(
    df["TagNacht"], df["AccidentSeverityCategory"], normalize="index"
).reindex(columns=SEV_ORDER) * 100
print(ct_sev.round(2))

for land in ["CH", "DE"]:
    sub    = df[df["Land"] == land]
    ct_l   = pd.crosstab(
        sub["TagNacht"], sub["AccidentSeverityCategory"], normalize="index"
    ).reindex(columns=SEV_ORDER) * 100
    print(f"\n  {land} (n={len(sub):,}):")
    print(ct_l.round(2))

chi2s, ps, dofs, _ = stats.chi2_contingency(
    pd.crosstab(df["TagNacht"], df["AccidentSeverityCategory"])
)
print(f"\nChi²-Test Nacht × Schwere: Chi² = {chi2s:.2f}, df = {dofs}, p = {ps:.4f}")
print("→ Signifikant (p < 0.05)" if ps < 0.05 else "→ Nicht signifikant")

# 4. Monatliche Verteilung
print("\n=== 4. Nachtunfälle nach Monat ===")
month_night = (df[df["NightAccident"] == 1]["AccidentMonth"]
               .value_counts().reindex(MONAT_ORDER, fill_value=0))
month_total = df["AccidentMonth"].value_counts().reindex(MONAT_ORDER, fill_value=0)
month_pct   = (month_night / month_total * 100).round(1)

for m in MONAT_ORDER:
    print(f"  {m}: {int(month_night[m]):>5,}  /  {int(month_total[m]):,}  =  {month_pct[m]}%")

print(f"\nMeiste Nachtunfälle (absolut): {month_night.idxmax()} ({int(month_night.max()):,})")
print(f"Höchster Nachtunfall-Anteil:    {month_pct.idxmax()} ({month_pct.max()}%)")

# ── Grafiken (2 × 3) ─────────────────────────────────────────────────────────

fig, axes = plt.subplots(2, 3, figsize=(21, 12))

# ── Plot 1: Tag-/Nacht-Anteil je Gruppe (%) ───────────────────────────────────
ax = axes[0, 0]
gruppen = ["Gesamt", "CH", "DE"]
subs    = [df, df[df["Land"] == "CH"], df[df["Land"] == "DE"]]
x, width = range(len(gruppen)), 0.35

for i, (label, color) in enumerate([("Tag", "#4C9BE8"), ("Nacht", "#1A1A2E")]):
    pcts = [(sub["NightAccident"] == i).sum() / len(sub) * 100 for sub in subs]
    bars = ax.bar([xi + i * width for xi in x], pcts, width,
                  label=label, color=color, alpha=0.88)
    for bar, val in zip(bars, pcts):
        ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.5,
                f"{val:.1f}%", ha="center", va="bottom", fontsize=9)

ax.set_xticks([xi + width / 2 for xi in x])
ax.set_xticklabels(gruppen)
ax.set_title("Tag-/Nacht-Anteil je Gruppe (%)", fontweight="bold")
ax.set_ylabel("Anteil (%)")
ax.set_ylim(0, 105)
ax.legend(title="Zeitraum")
for gruppe, sub in zip(gruppen, subs):
    ax.text(gruppen.index(gruppe) + width / 2, 2,
            f"n={len(sub):,}", ha="center", fontsize=8, color="gray")

# ── Plot 2: Motorradbeteiligung Tag vs. Nacht (%) ────────────────────────────
ax = axes[0, 1]
tn_labels   = ["Tag", "Nacht"]
x2          = range(len(tn_labels))
land_groups = [
    ("Gesamt", "#555555", df),
    ("CH",     "#2E86AB", df[df["Land"] == "CH"]),
    ("DE",     "#E84855", df[df["Land"] == "DE"]),
]
width2 = 0.25

for i, (land, color, sub) in enumerate(land_groups):
    pcts = [sub[sub["TagNacht"] == tn]["Motorrad"].mean() * 100 for tn in tn_labels]
    bars = ax.bar([xi + i * width2 for xi in x2], pcts, width2,
                  label=land, color=color, alpha=0.88)
    for bar, val in zip(bars, pcts):
        ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.1,
                f"{val:.1f}%", ha="center", va="bottom", fontsize=8)

ax.set_xticks([xi + width2 for xi in x2])
ax.set_xticklabels(tn_labels)
ax.set_title("Motorradbeteiligung bei Tag vs. Nacht (%)", fontweight="bold")
ax.set_ylabel("Anteil mit Motorrad (%)")
ax.legend(title="Land")

# ── Plot 3: Unfallschwere Tag vs. Nacht — Gesamt (gestapelt %) ───────────────
ax = axes[0, 2]
ct_plot = pd.crosstab(
    df["TagNacht"], df["AccidentSeverityCategory"], normalize="index"
).reindex(index=["Tag", "Nacht"], columns=SEV_ORDER) * 100

bottom = pd.Series([0.0, 0.0], index=["Tag", "Nacht"])
for sev in SEV_ORDER:
    vals = ct_plot[sev]
    bars = ax.bar(["Tag", "Nacht"], vals, bottom=bottom,
                  label=sev, color=SEV_COLORS[sev], alpha=0.88)
    for bar, val, bot in zip(bars, vals, bottom):
        if val > 2:
            ax.text(bar.get_x() + bar.get_width() / 2,
                    bot + val / 2,
                    f"{val:.1f}%", ha="center", va="center",
                    fontsize=9, color="white", fontweight="bold")
    bottom += vals

ax.set_title("Unfallschwere bei Tag vs. Nacht — Gesamt (%)", fontweight="bold")
ax.set_ylabel("Anteil (%)")
ax.set_ylim(0, 105)
ax.legend(title="Schwere", loc="upper right")
# annotate n
for label, sub in [("Tag", df[df["TagNacht"]=="Tag"]), ("Nacht", df[df["TagNacht"]=="Nacht"])]:
    ax.text(["Tag","Nacht"].index(label), 101,
            f"n={len(sub):,}", ha="center", fontsize=8, color="gray")

# ── Plot 4: Nachtunfälle nach Monat (absolut) ────────────────────────────────
ax = axes[1, 0]
WINTER     = {"Dez", "Jan", "Feb"}
bar_colors = ["#0D1B2A" if m in WINTER else "#4C9BE8" for m in MONAT_ORDER]
bars = ax.bar(MONAT_ORDER, month_night.values, color=bar_colors, alpha=0.88)
for bar, val in zip(bars, month_night.values):
    ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 10,
            str(int(val)), ha="center", va="bottom", fontsize=8)

ax.set_title("Nachtunfälle nach Monat (absolut)", fontweight="bold")
ax.set_ylabel("Anzahl Nachtunfälle")
ax.set_xlabel("Monat")
ax.legend(handles=[
    mpatches.Patch(color="#0D1B2A", label="Winter (Dez–Feb)"),
    mpatches.Patch(color="#4C9BE8", label="Übrige Monate"),
], title="Saison")

# ── Plot 5: Nachtunfall-Anteil nach Monat (%) ────────────────────────────────
ax = axes[1, 1]
for label, color, sub in [
    ("Gesamt", "#1A1A2E", df),
    ("CH",     "#2E86AB", df[df["Land"] == "CH"]),
    ("DE",     "#E84855", df[df["Land"] == "DE"]),
]:
    mn = (sub[sub["NightAccident"] == 1]["AccidentMonth"]
          .value_counts().reindex(MONAT_ORDER, fill_value=0))
    mt = sub["AccidentMonth"].value_counts().reindex(MONAT_ORDER, fill_value=0)
    mp = (mn / mt.replace(0, pd.NA) * 100).fillna(0)
    ax.plot(MONAT_ORDER, mp.values, marker="o", linewidth=2,
            label=label, color=color, alpha=0.9)

ax.set_title("Nachtunfall-Anteil nach Monat — CH, DE, Gesamt (%)", fontweight="bold")
ax.set_ylabel("Anteil Nachtunfälle (%)")
ax.set_xlabel("Monat")
ax.legend(title="Land")
ax.grid(axis="y", alpha=0.3)
ax.tick_params(axis="x", rotation=45)
ax.set_ylim(0, ax.get_ylim()[1] * 1.15)

# ── Plot 6: Effektive Nacht vs. Nacht-Bin — Anteil NightAccident=1 je Stunde ──
ax = axes[1, 2]

hours     = list(range(24))
night_pct = [df[df["AccidentHourNumeric"] == h]["NightAccident"].mean() * 100
             for h in hours]

# Background shading per AccidentHour bin
BIN_SPANS = [
    (-0.5,  5.5, "#BBCCE8", "Nacht-Bin\n(0–5h)"),
    ( 5.5, 11.5, "#D6EAF8", "Vormittag\n(6–11h)"),
    (11.5, 17.5, "#FEF9E7", "Nachmittag\n(12–17h)"),
    (17.5, 23.5, "#FADBD8", "Abend\n(18–23h)"),
]
for x0, x1, color, _ in BIN_SPANS:
    ax.axvspan(x0, x1, color=color, alpha=0.55, zorder=0)

# Bars: NightAccident share per hour
bar_colors = ["#1A1A2E" if h <= 5 else
              "#4C9BE8" if h <= 11 else
              "#F0A500" if h <= 17 else
              "#E84855"
              for h in hours]
ax.bar(hours, night_pct, color=bar_colors, alpha=0.85, zorder=2)

# Label non-zero bars outside the clear 100% / 0% zones
for h, pct in enumerate(night_pct):
    if 1 < pct < 99:
        ax.text(h, pct + 2, f"{pct:.0f}%", ha="center", va="bottom",
                fontsize=7, color="dimgray", zorder=3)

# Bin boundary lines
for x in [5.5, 11.5, 17.5]:
    ax.axvline(x, color="gray", linestyle="--", linewidth=1, alpha=0.6, zorder=3)

# Bin labels just above the plot area
for x0, x1, _, label in BIN_SPANS:
    ax.text((x0 + x1) / 2, 104, label, ha="center", va="bottom",
            fontsize=7.5, color="dimgray")

# Key finding annotation
night_in_bin = (df[df["NightAccident"] == 1]["AccidentHour"] == "Nacht").sum()
outside_pct  = (1 - night_in_bin / df["NightAccident"].sum()) * 100
bin_miss_pct = (df[(df["AccidentHour"] == "Nacht") & (df["NightAccident"] == 0)].shape[0]
                / (df["AccidentHour"] == "Nacht").sum() * 100)
ax.text(0.98, 0.60,
        f"{outside_pct:.0f}% der Nachtunfälle\nliegen außerhalb\ndes Nacht-Bins\n\n"
        f"{bin_miss_pct:.0f}% im Nacht-Bin\nsind effektiv Tag",
        transform=ax.transAxes, ha="right", va="top", fontsize=8.5,
        bbox=dict(boxstyle="round,pad=0.4", facecolor="white", edgecolor="lightgray", alpha=0.9))

ax.set_title("Effektive Nacht vs. Nacht-Bin: NightAccident-Anteil je Stunde (%)",
             fontweight="bold")
ax.set_ylabel("Anteil NightAccident=1 (%)")
ax.set_xlabel("Unfallstunde (0–23)")
ax.set_xticks(hours)
ax.set_ylim(0, 115)
ax.legend(handles=[
    mpatches.Patch(color="#1A1A2E", label="Nacht-Bin (0–5h)"),
    mpatches.Patch(color="#4C9BE8", label="Vormittag (6–11h)"),
    mpatches.Patch(color="#F0A500", label="Nachmittag (12–17h)"),
    mpatches.Patch(color="#E84855", label="Abend (18–23h)"),
], fontsize=8, title="AccidentHour-Bin", loc="upper left")

plt.suptitle("Ziel 5: Unfälle bei Nacht", fontsize=15, fontweight="bold", y=1.01)
plt.tight_layout()
plt.savefig(Path(__file__).parent.parent.parent / "plots" / "ziel5_nacht.png", dpi=150, bbox_inches="tight")
plt.show()
print("Grafik gespeichert als: ziel5_nacht.png")
