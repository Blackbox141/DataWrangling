from pathlib import Path
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import matplotlib.ticker as mticker

_DATA = Path(__file__).parent.parent.parent / "data" / "processed" / "cleaned_2024_night.csv"
df = pd.read_csv(_DATA, dtype={"AccidentUID": str}, low_memory=False)

MONAT_ORDER = ["Jan","Feb","Mar","Apr","Mai","Jun","Jul","Aug","Sep","Okt","Nov","Dez"]

SAISON_MAP = {
    "Dez": "Winter", "Jan": "Winter", "Feb": "Winter",
    "Mar": "Frühling", "Apr": "Frühling", "Mai": "Frühling",
    "Jun": "Sommer",   "Jul": "Sommer",   "Aug": "Sommer",
    "Sep": "Herbst",   "Okt": "Herbst",   "Nov": "Herbst",
}

SAISON_COLORS = {
    "Winter":   "#1A3A5C",
    "Frühling": "#4A9B5F",
    "Sommer":   "#E8A020",
    "Herbst":   "#C0602A",
}

month_night = (df[df["NightAccident"] == 1]["AccidentMonth"]
               .value_counts().reindex(MONAT_ORDER, fill_value=0))
month_total = df["AccidentMonth"].value_counts().reindex(MONAT_ORDER, fill_value=0)
month_pct   = (month_night / month_total * 100).round(1)

bar_colors = [SAISON_COLORS[SAISON_MAP[m]] for m in MONAT_ORDER]

fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(18, 7))
fig.suptitle("Ziel 5 – Nachtunfälle: Monat & Saison vs. Uhrzeit-Binning",
             fontsize=14, fontweight="bold", y=1.01)

# ── Plot 1: Nachtunfälle nach Monat (absolut + Anteil-Linie) ──────────────────

bars = ax1.bar(MONAT_ORDER, month_night.values, color=bar_colors, alpha=0.88, zorder=2)

for bar, val in zip(bars, month_night.values):
    ax1.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 15,
             str(int(val)), ha="center", va="bottom", fontsize=8.5, color="#222222")

ax1_r = ax1.twinx()
ax1_r.plot(MONAT_ORDER, month_pct.values, color="#333333", marker="o",
           linewidth=2, markersize=5, zorder=3, label="Anteil (%)")
ax1_r.set_ylabel("Anteil Nachtunfälle (%)", fontsize=10)
ax1_r.set_ylim(0, month_pct.max() * 1.5)
ax1_r.yaxis.set_major_formatter(mticker.FormatStrFormatter("%.0f%%"))

for x, val in enumerate(month_pct.values):
    ax1_r.text(x, val + 0.5, f"{val:.1f}%", ha="center", va="bottom",
               fontsize=7.5, color="#444444")

ax1.set_title("Nachtunfälle nach Monat & Saison", fontweight="bold", fontsize=11)
ax1.set_ylabel("Anzahl Nachtunfälle", fontsize=10)
ax1.set_xlabel("Monat", fontsize=10)
ax1.set_ylim(0, month_night.max() * 1.25)
ax1.grid(axis="y", alpha=0.25, zorder=0)
ax1.tick_params(axis="x", rotation=0)

saison_patches = [mpatches.Patch(color=c, label=s) for s, c in SAISON_COLORS.items()]
line_handle = plt.Line2D([0], [0], color="#333333", marker="o", linewidth=2,
                          markersize=5, label="Nachtanteil (%)")
ax1.legend(handles=saison_patches + [line_handle], title="Saison / Kennlinie",
           fontsize=8.5, loc="upper center",
           bbox_to_anchor=(0.5, -0.13), ncol=3)

# ── Plot 2: Nachtunfall-Anteil je Stunde vs. Uhrzeit-Bin ─────────────────────

hours     = list(range(24))
night_pct = [df[df["AccidentHourNumeric"] == h]["NightAccident"].mean() * 100
             for h in hours]

BIN_SPANS = [
    (-0.5,  5.5, "#D6E8F5", "Nacht\n(0–5h)"),
    ( 5.5, 11.5, "#EAF4E0", "Vormittag\n(6–11h)"),
    (11.5, 17.5, "#FEF9E7", "Nachmittag\n(12–17h)"),
    (17.5, 23.5, "#FDECEA", "Abend\n(18–23h)"),
]

BIN_BAR_COLORS = {
    "Nacht":      "#1A3A5C",
    "Vormittag":  "#4A9B5F",
    "Nachmittag": "#E8A020",
    "Abend":      "#C0602A",
}

def hour_bin(h):
    if h <= 5:  return "Nacht"
    if h <= 11: return "Vormittag"
    if h <= 17: return "Nachmittag"
    return "Abend"

for x0, x1, color, _ in BIN_SPANS:
    ax2.axvspan(x0, x1, color=color, alpha=0.55, zorder=0)

bar_cols2 = [BIN_BAR_COLORS[hour_bin(h)] for h in hours]
ax2.bar(hours, night_pct, color=bar_cols2, alpha=0.88, zorder=2)

for h, pct in enumerate(night_pct):
    if 2 < pct < 97:
        ax2.text(h, pct + 2, f"{pct:.0f}%", ha="center", va="bottom",
                 fontsize=7, color="dimgray", zorder=3)

for x in [5.5, 11.5, 17.5]:
    ax2.axvline(x, color="gray", linestyle="--", linewidth=1, alpha=0.7, zorder=3)

for x0, x1, _, label in BIN_SPANS:
    ax2.text((x0 + x1) / 2, 108, label, ha="center", va="bottom",
             fontsize=8, color="dimgray")

night_in_bin = (df[df["NightAccident"] == 1]["AccidentHour"] == "Nacht").sum()
outside_pct  = (1 - night_in_bin / df["NightAccident"].sum()) * 100
bin_miss_pct = (df[(df["AccidentHour"] == "Nacht") & (df["NightAccident"] == 0)].shape[0]
                / (df["AccidentHour"] == "Nacht").sum() * 100)

ax2.text(0.98, 0.62,
         f"{outside_pct:.0f}% der Nachtunfälle\nliegen außerhalb\ndes Nacht-Bins\n\n"
         f"{bin_miss_pct:.0f}% im Nacht-Bin\nsind effektiv Tag",
         transform=ax2.transAxes, ha="right", va="top", fontsize=9,
         bbox=dict(boxstyle="round,pad=0.45", facecolor="white",
                   edgecolor="lightgray", alpha=0.92))

ax2.set_title("NightAccident-Anteil je Stunde vs. Uhrzeit-Bin", fontweight="bold", fontsize=11)
ax2.set_ylabel("Anteil NightAccident = 1 (%)", fontsize=10)
ax2.set_xlabel("Unfallstunde (0–23)", fontsize=10)
ax2.set_xticks(hours)
ax2.set_ylim(0, 120)
ax2.grid(axis="y", alpha=0.25, zorder=0)

bin_patches = [mpatches.Patch(color=BIN_BAR_COLORS[b], label=f"{b}-Bin")
               for b in ["Nacht","Vormittag","Nachmittag","Abend"]]
ax2.legend(handles=bin_patches, title="AccidentHour-Bin",
           fontsize=8.5, loc="upper center",
           bbox_to_anchor=(0.5, -0.13), ncol=4)

plt.tight_layout()
plt.subplots_adjust(bottom=0.18)
out = Path(__file__).parent.parent.parent / "plots" / "ziel5_nacht_detail.png"
plt.savefig(out, dpi=150, bbox_inches="tight")
plt.show()
print(f"Grafik gespeichert: {out}")
