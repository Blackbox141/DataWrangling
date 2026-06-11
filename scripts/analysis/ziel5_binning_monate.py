from pathlib import Path
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import numpy as np

_DATA = Path(__file__).parent.parent.parent / "data" / "processed" / "cleaned_2024_night.csv"
df = pd.read_csv(_DATA, dtype={"AccidentUID": str}, low_memory=False)

MONAT_ORDER = ["Jan","Feb","Mar","Apr","Mai","Jun","Jul","Aug","Sep","Okt","Nov","Dez"]

SAISON_COLORS = {
    "Winter":   "#1A3A5C",
    "Frühling": "#4A9B5F",
    "Sommer":   "#E8A020",
    "Herbst":   "#C0602A",
}
SAISON_MAP = {
    "Jan":"Winter","Feb":"Winter","Mar":"Frühling","Apr":"Frühling","Mai":"Frühling",
    "Jun":"Sommer","Jul":"Sommer","Aug":"Sommer",
    "Sep":"Herbst","Okt":"Herbst","Nov":"Herbst","Dez":"Winter",
}

fp = df[(df["AccidentHour"] == "Nacht") & (df["NightAccident"] == 0)]
fn = df[(df["AccidentHour"] != "Nacht") & (df["NightAccident"] == 1)]

fp_m  = fp["AccidentMonth"].value_counts().reindex(MONAT_ORDER, fill_value=0)
fn_mb = (fn.groupby(["AccidentMonth","AccidentHour"])
           .size().unstack(fill_value=0)
           .reindex(MONAT_ORDER, fill_value=0))

for col in ["Abend","Nachmittag","Vormittag"]:
    if col not in fn_mb.columns:
        fn_mb[col] = 0

fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(16, 6))
fig.suptitle("Fehlklassifikationen nach Monat – Binning vs. bürgerliche Dämmerung",
             fontsize=13, fontweight="bold", y=1.01)

# ── False Positives nach Monat ────────────────────────────────────────────────

bar_cols_fp = [SAISON_COLORS[SAISON_MAP[m]] for m in MONAT_ORDER]
bars = ax1.bar(MONAT_ORDER, fp_m.values, color=bar_cols_fp, alpha=0.88, edgecolor="white")

for bar, val in zip(bars, fp_m.values):
    if val > 0:
        ax1.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 8,
                 str(int(val)), ha="center", va="bottom", fontsize=8.5)

ax1.set_title(f"False Positives: Bin=Nacht, aber effektiv Tag\n(gesamt: {int(fp_m.sum()):,} | nur Mär–Aug betroffen)",
              fontweight="bold", fontsize=10)
ax1.set_ylabel("Anzahl Unfälle")
ax1.set_xlabel("Monat")
ax1.set_ylim(0, fp_m.max() * 1.3)
ax1.grid(axis="y", alpha=0.25)

ax1.annotate("Jan–Feb & Sep–Dez:\nDämmerung beginnt\nnach 6 Uhr → kein Fehler",
             xy=(0, 5), xytext=(1.5, fp_m.max() * 0.6),
             fontsize=8, color="#555555",
             arrowprops=dict(arrowstyle="->", color="#888888", lw=1))
ax1.annotate("Jun/Jul: Dämmerung\nab ~2–3 Uhr",
             xy=(5, fp_m["Jun"]), xytext=(6.5, fp_m.max() * 0.85),
             fontsize=8, color="#555555",
             arrowprops=dict(arrowstyle="->", color="#888888", lw=1))

saison_patches = [mpatches.Patch(color=c, label=s) for s, c in SAISON_COLORS.items()]
ax1.legend(handles=saison_patches, title="Saison", fontsize=8.5,
           loc="upper center", bbox_to_anchor=(0.5, -0.13), ncol=4)

# ── False Negatives nach Monat (gestapelt nach Bin) ───────────────────────────

BIN_COLORS = {"Abend": "#C0602A", "Nachmittag": "#E8A020", "Vormittag": "#4A9B5F"}
bin_order  = ["Vormittag", "Nachmittag", "Abend"]

x    = np.arange(len(MONAT_ORDER))
bottom = np.zeros(len(MONAT_ORDER))

for bin_name in bin_order:
    vals = fn_mb[bin_name].values.astype(float)
    bars2 = ax2.bar(x, vals, bottom=bottom,
                    color=BIN_COLORS[bin_name], alpha=0.88,
                    edgecolor="white", label=bin_name)
    for i, (bar, val) in enumerate(zip(bars2, vals)):
        if val > 150:
            ax2.text(bar.get_x() + bar.get_width() / 2,
                     bottom[i] + val / 2,
                     f"{int(val):,}", ha="center", va="center",
                     fontsize=7, color="white", fontweight="bold")
    bottom += vals

# total labels on top
for i, tot in enumerate(fn_mb[bin_order].sum(axis=1)):
    ax2.text(i, tot + 50, f"{int(tot):,}", ha="center", va="bottom",
             fontsize=8, color="#222222")

ax2.set_title(f"False Negatives: nicht Nacht-Bin, aber effektiv Nacht\n(gesamt: {int(fn_mb.sum().sum()):,} | alle Monate betroffen)",
              fontweight="bold", fontsize=10)
ax2.set_ylabel("Anzahl Unfälle")
ax2.set_xlabel("Monat")
ax2.set_xticks(x)
ax2.set_xticklabels(MONAT_ORDER)
ax2.set_ylim(0, fn_mb[bin_order].sum(axis=1).max() * 1.2)
ax2.grid(axis="y", alpha=0.25)

bin_patches = [mpatches.Patch(color=BIN_COLORS[b], label=f"{b}-Bin") for b in bin_order]
ax2.legend(handles=bin_patches, title="Bin", fontsize=8.5,
           loc="upper center", bbox_to_anchor=(0.5, -0.13), ncol=3)

ax2.annotate("Nov/Dez: 17 Uhr\nbereits dunkel",
             xy=(10, fn_mb.loc["Nov","Nachmittag"] + fn_mb.loc["Nov","Abend"] + fn_mb.loc["Nov","Vormittag"]),
             xytext=(7.5, fn_mb[bin_order].sum(axis=1).max() * 1.05),
             fontsize=8, color="#555555",
             arrowprops=dict(arrowstyle="->", color="#888888", lw=1))
ax2.annotate("Jan/Feb: 6 Uhr\nnoch dunkel",
             xy=(0, fn_mb.loc["Jan", bin_order].sum()),
             xytext=(1.5, fn_mb[bin_order].sum(axis=1).max() * 0.85),
             fontsize=8, color="#555555",
             arrowprops=dict(arrowstyle="->", color="#888888", lw=1))

plt.tight_layout()
plt.subplots_adjust(bottom=0.18)
out = Path(__file__).parent.parent.parent / "plots" / "ziel5_binning_monate.png"
plt.savefig(out, dpi=150, bbox_inches="tight")
plt.show()
print(f"Grafik gespeichert: {out}")
