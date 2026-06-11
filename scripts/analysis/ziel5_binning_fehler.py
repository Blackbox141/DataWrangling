from pathlib import Path
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
import matplotlib.patches as mpatches
import numpy as np

_DATA = Path(__file__).parent.parent.parent / "data" / "processed" / "cleaned_2024_night.csv"
df = pd.read_csv(_DATA, dtype={"AccidentUID": str}, low_memory=False)

total = len(df)

tp = df[(df["AccidentHour"] == "Nacht") & (df["NightAccident"] == 1)]
tn = df[(df["AccidentHour"] != "Nacht") & (df["NightAccident"] == 0)]
fp = df[(df["AccidentHour"] == "Nacht") & (df["NightAccident"] == 0)]
fn = df[(df["AccidentHour"] != "Nacht") & (df["NightAccident"] == 1)]

fp_by_hour = fp["AccidentHourNumeric"].value_counts().sort_index()
fn_by_hour = fn["AccidentHourNumeric"].value_counts().sort_index()

BIN_COLORS = {"Nacht": "#1A3A5C", "Vormittag": "#4A9B5F",
              "Nachmittag": "#E8A020", "Abend": "#C0602A"}

def hour_to_bin(h):
    if h <= 5:  return "Nacht"
    if h <= 11: return "Vormittag"
    if h <= 17: return "Nachmittag"
    return "Abend"

# ── Figure layout ─────────────────────────────────────────────────────────────

fig = plt.figure(figsize=(16, 9))
fig.suptitle("Binning vs. bürgerliche Dämmerung – Fehlklassifikationsanalyse",
             fontsize=14, fontweight="bold", y=1.01)

gs = gridspec.GridSpec(2, 2, figure=fig, hspace=0.45, wspace=0.35)
ax_cm   = fig.add_subplot(gs[:, 0])   # left: full height — confusion matrix
ax_fp   = fig.add_subplot(gs[0, 1])   # top right: false positives
ax_fn   = fig.add_subplot(gs[1, 1])   # bottom right: false negatives

# ── Confusion Matrix ──────────────────────────────────────────────────────────

matrix = np.array([[len(tn), len(fn)],
                   [len(fp), len(tp)]])
labels = [["True Negative\n(Bin=Tag, API=Tag)",
           "False Negative\n(Bin=Tag, API=Nacht)"],
          ["False Positive\n(Bin=Nacht, API=Tag)",
           "True Positive\n(Bin=Nacht, API=Nacht)"]]
cell_colors = [["#D5E8D4", "#F8CECC"],
               ["#FFF2CC", "#DAE8FC"]]
pcts = matrix / total * 100

ax_cm.set_xlim(0, 2)
ax_cm.set_ylim(0, 2)
ax_cm.set_aspect("equal")
ax_cm.axis("off")

for row in range(2):
    for col in range(2):
        x, y = col, 1 - row
        rect = plt.Rectangle((x, y), 1, 1,
                              facecolor=cell_colors[row][col],
                              edgecolor="white", linewidth=3)
        ax_cm.add_patch(rect)
        ax_cm.text(x + 0.5, y + 0.62, labels[row][col],
                   ha="center", va="center", fontsize=9.5,
                   color="#333333", fontweight="bold")
        ax_cm.text(x + 0.5, y + 0.38,
                   f"{matrix[row, col]:,}",
                   ha="center", va="center", fontsize=18, fontweight="bold",
                   color="#111111")
        ax_cm.text(x + 0.5, y + 0.18,
                   f"({pcts[row, col]:.1f}%)",
                   ha="center", va="center", fontsize=10, color="#555555")

# Axis labels
ax_cm.text(0.5, 2.08, "Bin = Tag (nicht Nacht)", ha="center", va="bottom",
           fontsize=10, fontweight="bold", color="#333333")
ax_cm.text(1.5, 2.08, "Bin = Nacht", ha="center", va="bottom",
           fontsize=10, fontweight="bold", color="#1A3A5C")
ax_cm.text(-0.08, 1.5, "API = Tag", ha="right", va="center",
           fontsize=10, fontweight="bold", color="#333333", rotation=90)
ax_cm.text(-0.08, 0.5, "API = Nacht", ha="right", va="center",
           fontsize=10, fontweight="bold", color="#1A3A5C", rotation=90)
ax_cm.text(1.0, -0.08, "Uhrzeit-Bin", ha="center", va="top",
           fontsize=11, fontweight="bold")
ax_cm.text(-0.22, 1.0, "Bürgerliche\nDämmerung (API)", ha="center", va="center",
           fontsize=11, fontweight="bold", rotation=90)
ax_cm.set_title("Konfusionsmatrix\nBin vs. API-Klassifikation",
                fontweight="bold", fontsize=11, pad=14)

# ── False Positives by Hour ───────────────────────────────────────────────────

hours_fp  = fp_by_hour.index.tolist()
vals_fp   = fp_by_hour.values
bars = ax_fp.bar(hours_fp, vals_fp, color="#FFC000", edgecolor="white",
                 linewidth=0.8, alpha=0.9)

for bar, val in zip(bars, vals_fp):
    ax_fp.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 20,
               f"{val:,}", ha="center", va="bottom", fontsize=9)

ax_fp.set_title(f"False Positives: Bin=Nacht, aber effektiv Tag  (n={len(fp):,} | {len(fp)/total*100:.1f}%)",
                fontweight="bold", fontsize=9.5)
ax_fp.set_xlabel("Unfallstunde")
ax_fp.set_ylabel("Anzahl Unfälle")
ax_fp.set_xticks(hours_fp)
ax_fp.set_ylim(0, vals_fp.max() * 1.25)
ax_fp.grid(axis="y", alpha=0.25)
ax_fp.annotate("Dämmerung beginnt,\nBin endet erst um 6h",
               xy=(5, vals_fp[-1]), xytext=(4.3, vals_fp[-1] * 0.65),
               fontsize=8, color="#555555",
               arrowprops=dict(arrowstyle="->", color="#888888", lw=1))

# ── False Negatives by Hour ───────────────────────────────────────────────────

hours_fn = fn_by_hour.index.tolist()
vals_fn  = fn_by_hour.values
bar_cols = [BIN_COLORS[hour_to_bin(h)] for h in hours_fn]

bars2 = ax_fn.bar(hours_fn, vals_fn, color=bar_cols, edgecolor="white",
                  linewidth=0.8, alpha=0.9)

for bar, val in zip(bars2, vals_fn):
    ax_fn.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 30,
               f"{val:,}", ha="center", va="bottom", fontsize=8)

ax_fn.set_title(f"False Negatives: nicht Nacht-Bin, aber effektiv Nacht  (n={len(fn):,} | {len(fn)/total*100:.1f}%)",
                fontweight="bold", fontsize=9.5)
ax_fn.set_xlabel("Unfallstunde")
ax_fn.set_ylabel("Anzahl Unfälle")
ax_fn.set_xticks(hours_fn)
ax_fn.set_ylim(0, vals_fn.max() * 1.3)
ax_fn.grid(axis="y", alpha=0.25)

fn_patches = [mpatches.Patch(color=BIN_COLORS[b], label=f"{b}-Bin")
              for b in ["Vormittag", "Nachmittag", "Abend"]]
ax_fn.legend(handles=fn_patches, fontsize=8, title="Bin", loc="upper left")

fn_abend = fn[fn["AccidentHour"] == "Abend"]
ax_fn.annotate(f"Abend-Bin: {len(fn_abend):,}\n({len(fn_abend)/len(fn)*100:.0f}% der FN)",
               xy=(22, fn_by_hour.get(22, 0)),
               xytext=(19.5, vals_fn.max() * 1.05),
               fontsize=8, color="#555555",
               arrowprops=dict(arrowstyle="->", color="#888888", lw=1))

plt.tight_layout()
plt.subplots_adjust(left=0.08)
out = Path(__file__).parent.parent.parent / "plots" / "ziel5_binning_fehler.png"
plt.savefig(out, dpi=150, bbox_inches="tight")
plt.show()
print(f"Grafik gespeichert: {out}")
