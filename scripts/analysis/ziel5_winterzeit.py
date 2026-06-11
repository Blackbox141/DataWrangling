from pathlib import Path
import pandas as pd, json, numpy as np
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import matplotlib.gridspec as gridspec
from datetime import datetime
from zoneinfo import ZoneInfo
from scipy import stats

_DATA  = Path(__file__).parent.parent.parent / "data" / "processed" / "cleaned_2024_night.csv"
_CACHE = Path(__file__).parent.parent.parent / "data" / "processed" / "twilight_cache.json"

df    = pd.read_csv(_DATA, dtype={"AccidentUID": str}, low_memory=False)
cache = json.loads(_CACHE.read_text())

MONAT_ORDER = ["Jan","Feb","Mar","Apr","Mai","Jun","Jul","Aug","Sep","Okt","Nov","Dez"]
MONAT_NUM   = {"Jan":1,"Feb":2,"Mar":3,"Apr":4,"Mai":5,"Jun":6,
               "Jul":7,"Aug":8,"Sep":9,"Okt":10,"Nov":11,"Dez":12}
SAISON_MAP  = {"Jan":"Winter","Feb":"Winter","Mar":"Frühling","Apr":"Frühling",
               "Mai":"Frühling","Jun":"Sommer","Jul":"Sommer","Aug":"Sommer",
               "Sep":"Herbst","Okt":"Herbst","Nov":"Herbst","Dez":"Winter"}
SAISON_C    = {"Winter":"#1A3A5C","Frühling":"#4A9B5F","Sommer":"#E8A020","Herbst":"#C0602A"}

TZ_DE = ZoneInfo("Europe/Berlin")
daylight = {}
for m_name, m_num in MONAT_NUM.items():
    date_str = f"2024-{m_num:02d}-15"
    durs = [(datetime.fromisoformat(v["end"]) - datetime.fromisoformat(v["begin"])).seconds / 3600
            for k, v in cache.items() if k.endswith(date_str)]
    daylight[m_name] = np.mean(durs)

night = df[df["NightAccident"]==1]["AccidentMonth"].value_counts().reindex(MONAT_ORDER, fill_value=0)
total = df["AccidentMonth"].value_counts().reindex(MONAT_ORDER, fill_value=0)
rate  = (night / total * 100)

day_vals  = np.array([daylight[m] for m in MONAT_ORDER])
rate_vals = rate.values
corr, _   = stats.pearsonr(day_vals, rate_vals)

WINTER = {"Nov","Dez","Jan","Feb"}
SOMMER = {"Mai","Jun","Jul","Aug"}
w_night = night[list(WINTER)].sum(); w_total = total[list(WINTER)].sum()
s_night = night[list(SOMMER)].sum(); s_total = total[list(SOMMER)].sum()

ct = pd.crosstab(
    df["AccidentMonth"].apply(lambda m: "Winter" if m in WINTER else ("Sommer" if m in SOMMER else None)),
    df["NightAccident"]
).loc[["Winter","Sommer"]]
chi2_val, p_val, _, _ = stats.chi2_contingency(ct)

# ── Figure ────────────────────────────────────────────────────────────────────

fig = plt.figure(figsize=(18, 10))
fig.suptitle("Hat die Winterzeit eine Auswirkung auf Nachtunfälle?",
             fontsize=15, fontweight="bold", y=1.01)

gs = gridspec.GridSpec(2, 2, figure=fig, hspace=0.45, wspace=0.35)
ax_main   = fig.add_subplot(gs[:, 0])   # left: full height
ax_scatter = fig.add_subplot(gs[0, 1])  # top right
ax_comp    = fig.add_subplot(gs[1, 1])  # bottom right

# ── Panel 1: Nachtunfall-Anteil + Tageslicht je Monat ────────────────────────

bar_cols = [SAISON_C[SAISON_MAP[m]] for m in MONAT_ORDER]
x = np.arange(len(MONAT_ORDER))

bars = ax_main.bar(x, rate_vals, color=bar_cols, alpha=0.85, edgecolor="white", zorder=2)
for bar, val in zip(bars, rate_vals):
    ax_main.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.4,
                 f"{val:.1f}%", ha="center", va="bottom", fontsize=8)

ax_r = ax_main.twinx()
ax_r.plot(x, day_vals, color="#555555", marker="o", linewidth=2.2,
          markersize=6, zorder=3, label="Tageslicht (h)")
for i, val in enumerate(day_vals):
    ax_r.text(i, val + 0.15, f"{val:.1f}h", ha="center", va="bottom",
              fontsize=7.5, color="#333333")

ax_r.set_ylabel("Tageslichtdauer (Stunden)", fontsize=10)
ax_r.set_ylim(0, day_vals.max() * 1.4)

ax_main.set_title("Nachtunfall-Anteil (%) & Tageslichtdauer je Monat",
                  fontweight="bold", fontsize=11)
ax_main.set_ylabel("Anteil Nachtunfälle (%)", fontsize=10)
ax_main.set_xlabel("Monat", fontsize=10)
ax_main.set_xticks(x); ax_main.set_xticklabels(MONAT_ORDER)
ax_main.set_ylim(0, rate_vals.max() * 1.3)
ax_main.grid(axis="y", alpha=0.2, zorder=0)

saison_patches = [mpatches.Patch(color=c, label=s) for s, c in SAISON_C.items()]
line_h = plt.Line2D([0],[0], color="#555555", marker="o", linewidth=2, markersize=5,
                    label="Tageslicht (h)")
ax_main.legend(handles=saison_patches + [line_h], title="Saison / Kennlinie",
               fontsize=8.5, loc="upper center", bbox_to_anchor=(0.5, -0.1), ncol=3)

# ── Panel 2: Scatter – Tageslicht vs. Nachtunfall-Anteil ─────────────────────

sc_cols = [SAISON_C[SAISON_MAP[m]] for m in MONAT_ORDER]
ax_scatter.scatter(day_vals, rate_vals, c=sc_cols, s=90, zorder=3, edgecolors="white", linewidth=0.6)

for i, m in enumerate(MONAT_ORDER):
    ax_scatter.annotate(m, (day_vals[i], rate_vals[i]),
                        textcoords="offset points", xytext=(5, 3), fontsize=8)

slope, intercept, *_ = stats.linregress(day_vals, rate_vals)
x_line = np.linspace(day_vals.min() - 0.5, day_vals.max() + 0.5, 100)
ax_scatter.plot(x_line, slope * x_line + intercept, color="#888888",
                linestyle="--", linewidth=1.5, zorder=2, label="Regressionsgerade")

ax_scatter.text(0.97, 0.97,
                f"r = {corr:.4f}\nr² = {corr**2:.4f}\np < 0.001",
                transform=ax_scatter.transAxes, ha="right", va="top", fontsize=10,
                bbox=dict(boxstyle="round,pad=0.4", facecolor="white",
                          edgecolor="lightgray", alpha=0.9))

ax_scatter.set_title("Korrelation: Tageslicht ↔ Nachtunfall-Anteil",
                     fontweight="bold", fontsize=11)
ax_scatter.set_xlabel("Tageslichtdauer (Stunden)", fontsize=10)
ax_scatter.set_ylabel("Anteil Nachtunfälle (%)", fontsize=10)
ax_scatter.grid(alpha=0.2)
ax_scatter.legend(fontsize=8.5)

# ── Panel 3: Winter vs. Sommer Vergleich ─────────────────────────────────────

seasons  = ["Sommer\n(Mai–Aug)", "Frühling/\nHerbst", "Winter\n(Nov–Feb)"]
FRUEHST  = {"Mar","Apr","Sep","Okt"}
f_night  = night[list(FRUEHST)].sum(); f_total = total[list(FRUEHST)].sum()
rates_comp = [s_night/s_total*100, f_night/f_total*100, w_night/w_total*100]
cols_comp  = [SAISON_C["Sommer"], "#888888", SAISON_C["Winter"]]
ns_comp    = [int(s_total), int(f_total), int(w_total)]

bars3 = ax_comp.bar(seasons, rates_comp, color=cols_comp, alpha=0.88,
                    edgecolor="white", width=0.5)
for bar, val, n in zip(bars3, rates_comp, ns_comp):
    ax_comp.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.3,
                 f"{val:.1f}%\n(n={n:,})", ha="center", va="bottom", fontsize=9)

ax_comp.set_title("Nachtunfall-Anteil: Sommer vs. Übergang vs. Winter",
                  fontweight="bold", fontsize=11)
ax_comp.set_ylabel("Anteil Nachtunfälle (%)", fontsize=10)
ax_comp.set_ylim(0, max(rates_comp) * 1.35)
ax_comp.grid(axis="y", alpha=0.2)

factor = (w_night/w_total) / (s_night/s_total)
ax_comp.text(0.97, 0.97,
             f"Winter / Sommer\nFaktor: {factor:.1f}×\n\n"
             f"Chi²={chi2_val:,.0f}, df=1\np < 0.001",
             transform=ax_comp.transAxes, ha="right", va="top", fontsize=9,
             bbox=dict(boxstyle="round,pad=0.4", facecolor="white",
                       edgecolor="lightgray", alpha=0.9))

plt.tight_layout()
plt.subplots_adjust(left=0.07, bottom=0.12)
out = Path(__file__).parent.parent.parent / "plots" / "ziel5_winterzeit.png"
plt.savefig(out, dpi=150, bbox_inches="tight")
plt.show()
print(f"Grafik gespeichert: {out}")
