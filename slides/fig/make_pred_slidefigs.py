"""Slide-scale variants of the two dense predictor figures (readable from the back
of a room): reuses predictors/figures_tex.py's data + constants, replots with big
fonts. Heatmap -> colour pattern + large labels (numbers kept but secondary);
horizon -> the two provisioning-relevant panels (vision images, language gen tokens)."""
import sys; sys.path.insert(0, '/home/gio/tese/predictors')
import matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt; import numpy as np
import figures_tex as F                       # runs module load: F.by_h, F.overall, constants
OUT = '/home/gio/tese/slides/fig'

# ---------- HEATMAP (colour pattern, big labels) ----------
plt.rcParams.update({'font.size': 13, 'axes.grid': False,
                     'axes.spines.top': False, 'axes.spines.right': False})
d = F.overall.query("candidate == 'point'")
cols = [(v, r) for v in F.VARIATES for r in F.RES_ORDER]
M = np.full((len(F.ROW_ORDER), len(cols)), np.nan)
for i, (model, mode) in enumerate(F.ROW_ORDER):
    s = d.query("model == @model and mode == @mode").set_index(['variate', 'resolution']).wape
    for j, key in enumerate(cols):
        M[i, j] = 100 * s.get(key, np.nan)
rel = M / np.nanmin(M, axis=0, keepdims=True)
fig, ax = plt.subplots(figsize=(12.5, 4.7))
im = ax.imshow(np.clip(rel, 1, 2), cmap='Blues', vmin=1, vmax=2, aspect='auto')
for i in range(M.shape[0]):
    for j in range(M.shape[1]):
        best = rel[i, j] <= 1 + 1e-9
        ax.text(j, i, f"{M[i, j]:.0f}" if M[i, j] >= 9.95 else f"{M[i, j]:.1f}",
                ha='center', va='center', fontsize=9.5,
                color=('#0b3d2e' if best else F.INK), fontweight='bold' if best else 'normal')
ax.set_yticks(range(len(F.ROW_ORDER)),
              [F.ROW_LABEL[k].replace('--', '–') for k in F.ROW_ORDER], fontsize=13)
ax.set_xticks(range(len(cols)), [r for _, r in cols], fontsize=10)
for k, v in enumerate(F.VARIATES):
    ax.text(k * 5 + 2, -0.85, F.VLABEL[v], ha='center', fontsize=13.5, color=F.INK, fontweight='bold')
    if k:
        ax.axvline(k * 5 - 0.5, color='white', linewidth=3)
cb = fig.colorbar(im, ax=ax, fraction=0.02, pad=0.01)
cb.set_label('WAPE  ÷  column best  (bold = best)', fontsize=12); cb.ax.tick_params(labelsize=10)
fig.tight_layout(); fig.savefig(f'{OUT}/pred_heatmap_slide.pdf', bbox_inches='tight'); plt.close(fig)

# ---------- HORIZON (2 provisioning-relevant panels; shared legend BELOW, off the data) ----------
plt.rcParams.update({'font.size': 15})
dh = F.by_h.query("resolution == '1min' and candidate == 'point'")
fig, axes = plt.subplots(1, 2, figsize=(11.5, 5.1))
for ax, v in zip(axes, ['images', 'gen']):
    for (model, mode), (label, color, ls) in F.STYLE.items():
        z = 4 if model in ('chronos', 'toto', 'timesfm') else 2   # FMs on top of baselines
        s = dh.query("model == @model and mode == @mode and variate == @v").sort_values('h')
        ax.plot(s.h, 100 * s.wape, ls, color=color, label=label, lw=3.0, zorder=z)
    ax.set_title(F.VLABEL[v], loc='left', fontsize=18, color=F.INK)
    ax.set_xticks([1, 3, 6, 9, 12]); ax.set_ylim(bottom=0)
    ax.set_xlabel('horizon step $h$  (minutes ahead)'); ax.grid(alpha=0.3)
axes[0].set_ylabel('point WAPE (%)')
h, l = axes[0].get_legend_handles_labels()
fig.legend(h, l, ncol=6, frameon=False, fontsize=14, loc='lower center', bbox_to_anchor=(0.5, -0.015),
           handlelength=2.6, columnspacing=1.4)
fig.tight_layout(rect=(0, 0.10, 1, 1))
fig.savefig(f'{OUT}/pred_horizon_slide.pdf', bbox_inches='tight'); plt.close(fig)
print('saved pred_heatmap_slide.pdf, pred_horizon_slide.pdf')
