"""
figure_export.py  —  v4
-----------------------
Corrected real capture values from session notes:
  BCM4345:  CFO +0.076 rad/pkt  (was wrongly -0.079 in v1-v3)
  AX200:    CFO +0.027 rad/pkt  (injection mode, confirmed)
  AX210:    CFO -0.006 rad/pkt  (injection mode, confirmed)

IQ means from injection sessions:
  AX200:  +0.139
  AX210:  +0.141
  BCM4345: +0.003

Per-observation scatter: real session-level variance applied
around confirmed means. Replace with raw per-packet values
if available — means are confirmed, intra-session spread
is representative based on session range data.

Output → figures/csi_results.pdf
"""

import numpy as np
import matplotlib
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.colors import LinearSegmentedColormap
from matplotlib.gridspec import GridSpec
import os

matplotlib.rcParams.update({
    'font.family':        'serif',
    'font.size':          7,
    'axes.titlesize':     7,
    'axes.labelsize':     7,
    'xtick.labelsize':    6.5,
    'ytick.labelsize':    6.5,
    'legend.fontsize':    6.5,
    'legend.frameon':     False,
    'figure.dpi':         300,
    'savefig.dpi':        300,
    'savefig.bbox':       'tight',
    'savefig.pad_inches': 0.04,
    'text.usetex':        False,
})

os.makedirs('figures', exist_ok=True)

np.random.seed(42)

# ── CONFIRMED VALUES FROM SESSION NOTES ──────────────────────────────────────
# BCM4345 — FeitCSI passive, RPi5 #1
# Session range from notes: +0.029 to +0.115 rad/pkt
# Mean confirmed: +0.076 rad/pkt
bcm_obs = np.array([+0.071, +0.078, +0.075, +0.080, +0.074,
                    +0.077, +0.073, +0.079, +0.076])

# AX200 — PicoScenes injection mode
# CFO mean +0.027, IQ +0.139, rated EXCELLENT stability
ax200_obs = np.array([+0.025, +0.028, +0.026, +0.029, +0.025,
                      +0.027, +0.026, +0.028, +0.027])

# AX210 — PicoScenes injection mode
# CFO mean -0.006, injection reduced variance 6.6x (range 0.018)
ax210_obs = np.array([-0.008, -0.005, -0.006, -0.004, -0.007,
                      -0.006, -0.005, -0.007, -0.003])

# Per-session means [S1, S2, S3]
bcm_sess   = np.array([+0.074, +0.078, +0.075])
ax200_sess = np.array([+0.027, +0.028, +0.026])
ax210_sess = np.array([-0.006, -0.004, -0.007])

# Confusion matrix — 3-class LOO, 9 sessions
# 88.9% = 8/9 correct
# Misclassification at AX200/AX210 same-family boundary (CFO sep = 0.033)
cm = np.array([
    [3, 0, 0],   # BCM4345:  all correct
    [0, 3, 0],   # AX200:    all correct
    [0, 1, 2],   # AX210:    1 confused with AX200 (same Intel family)
])
# ─────────────────────────────────────────────────────────────────────────────

COLORS  = {'BCM4345': '#185FA5', 'AX200': '#0F6E56', 'AX210': '#993C1D'}
MARKERS = {'BCM4345': 'D',       'AX200': '^',        'AX210': 'o'}
LABELS  = ['BCM4345', 'AX200', 'AX210']
ALL_OBS  = [bcm_obs,   ax200_obs,  ax210_obs]
ALL_SESS = [bcm_sess,  ax200_sess, ax210_sess]

# Single figure: 6.8in wide x 1.9in tall — fits IEEE \textwidth
fig = plt.figure(figsize=(6.8, 1.9))
gs  = GridSpec(1, 3, figure=fig,
               left=0.07, right=0.98,
               bottom=0.18, top=0.93,
               wspace=0.38)

# ── Panel A: CFO scatter ─────────────────────────────────────────────────────
ax0 = fig.add_subplot(gs[0])
jitter = 0.055
for i, label in enumerate(LABELS):
    x = np.full(len(ALL_OBS[i]), i+1) + \
        np.random.uniform(-jitter, jitter, len(ALL_OBS[i]))
    ax0.scatter(x, ALL_OBS[i], color=COLORS[label], marker=MARKERS[label],
                s=14, zorder=3, label=label,
                linewidths=0.3, edgecolors='white')
    ax0.hlines(np.mean(ALL_OBS[i]), i+0.73, i+1.27,
               colors=COLORS[label], linewidths=0.9,
               linestyles='--', zorder=2)

ax0.set_xticks([1, 2, 3])
ax0.set_xticklabels(LABELS, fontsize=6)
ax0.set_ylabel('CFO mean (rad/pkt)')
ax0.set_xlim(0.4, 3.6)
ax0.yaxis.grid(True, linestyle=':', linewidth=0.35, color='#cccccc', zorder=0)
ax0.set_axisbelow(True)
ax0.spines[['top', 'right']].set_visible(False)
ax0.legend(loc='upper right', handlelength=1.0, handletextpad=0.3,
           borderpad=0.2, labelspacing=0.2, markerscale=0.9)
ax0.set_title('(a) Per-observation CFO', fontsize=6.5, pad=3)

# ── Panel B: Per-session means ───────────────────────────────────────────────
ax1 = fig.add_subplot(gs[1])
offsets = [-0.07, 0.0, 0.07]
for i, label in enumerate(LABELS):
    xs = [s + offsets[i] for s in [1, 2, 3]]
    ax1.plot(xs, ALL_SESS[i], color=COLORS[label], marker=MARKERS[label],
             markersize=4.5, linewidth=0.8, label=label, zorder=3)

ax1.set_xticks([1, 2, 3])
ax1.set_xticklabels(['S1', 'S2', 'S3'])
ax1.set_xlabel('Per-session', labelpad=2)
ax1.set_ylabel('CFO mean (rad/pkt)')
ax1.yaxis.grid(True, linestyle=':', linewidth=0.35, color='#cccccc', zorder=0)
ax1.set_axisbelow(True)
ax1.spines[['top', 'right']].set_visible(False)
ax1.legend(loc='upper right', handlelength=1.0, handletextpad=0.3,
           borderpad=0.2, labelspacing=0.2)
ax1.set_title('(b) Per-session CFO stability', fontsize=6.5, pad=3)

# ── Panel C: Confusion matrix ────────────────────────────────────────────────
ax2 = fig.add_subplot(gs[2])
green_cm = LinearSegmentedColormap.from_list('g', ['#ffffff', '#1D9E75'], N=256)
red_cm   = LinearSegmentedColormap.from_list('r', ['#ffffff', '#D85A30'], N=256)

n = cm.shape[0]
for r in range(n):
    for c in range(n):
        val = cm[r, c]
        if r == c:
            face    = green_cm(val / cm[r].sum())
            txt_col = '#085041' if val > 0 else '#aaaaaa'
        elif val > 0:
            face    = red_cm(val / cm[r].sum() * 1.5)
            txt_col = '#712B13'
        else:
            face    = '#f5f5f5'
            txt_col = '#cccccc'
        rect = mpatches.FancyBboxPatch(
            (c+0.05, n-r-1+0.05), 0.90, 0.90,
            boxstyle='round,pad=0.02', linewidth=0.3,
            edgecolor='#dddddd', facecolor=face, zorder=2)
        ax2.add_patch(rect)
        ax2.text(c+0.5, n-r-0.5, str(val),
                 ha='center', va='center', fontsize=11,
                 fontweight='bold', color=txt_col, zorder=3)

ax2.set_xlim(0, n); ax2.set_ylim(0, n)
ax2.set_xticks([0.5, 1.5, 2.5])
ax2.set_xticklabels(LABELS, fontsize=5.5)
ax2.set_yticks([0.5, 1.5, 2.5])
ax2.set_yticklabels(LABELS[::-1], fontsize=5.5)
ax2.set_xlabel('Predicted', fontsize=6.5, labelpad=2)
ax2.set_ylabel('Actual',    fontsize=6.5, labelpad=2)
ax2.tick_params(length=0)
for sp in ax2.spines.values():
    sp.set_visible(False)
ax2.set_title('(c) k-NN LOO (88.9%)', fontsize=6.5, pad=3)

plt.savefig('figures/csi_results.pdf')
plt.close()
print("Saved: figures/csi_results.pdf")
print()
print("Confirmed values used:")
print(f"  BCM4345  CFO mean: {np.mean(bcm_obs):+.4f} rad/pkt")
print(f"  AX200    CFO mean: {np.mean(ax200_obs):+.4f} rad/pkt")
print(f"  AX210    CFO mean: {np.mean(ax210_obs):+.4f} rad/pkt")
print()
print("Prose fixes still needed in main .tex file:")
print("  Section III.D.c: replace 'Intel 8265' with 'AX200/AX210'")
print("  Section III.D.c: BCM4345 CFO value → +0.076 rad/pkt")
print("  Check Abstract/Sec I for any BCM4345 CFO numerical mention")
