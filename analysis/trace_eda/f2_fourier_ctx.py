"""EDA F2 — Fourier analysis of the ContextTokens rate signal (CuPy FFT).

Same treatment as F (requests/images): per-second ctx-tokens series over the
7 days; diurnal lines, mid-band spectral slope (LRD), noise floor. Adds the
modality decomposition: spectra of the multimodal-borne vs text-only-borne
prefill volume, to locate where the ctx signal's structure comes from.
"""
import cupy as cp
import numpy as np
import pandas as pd

from _common import C_AQUA, C_BLUE, C_YELLOW, MUTED, load_trace, plt, save_fig, save_stats

df = load_trace()
df = df.assign(win=df["ts"].dt.floor("s"), is_mm=(df["NumImages"] > 0))

def per_second(sub):
    s = sub.groupby("win")["ContextTokens"].sum().sort_index().to_pandas()
    return s

s_all = per_second(df)
full = pd.date_range(s_all.index.min(), s_all.index.max(), freq="s")
series = {
    "ctx_total": s_all.reindex(full, fill_value=0),
    "ctx_multimodal": per_second(df[df["is_mm"]]).reindex(full, fill_value=0),
    "ctx_text_only": per_second(df[~df["is_mm"]]).reindex(full, fill_value=0),
}

def spectrum_logbinned(x_host, nbins=400):
    x = cp.asarray(x_host.to_numpy(), dtype=cp.float64)
    x = x - x.mean()
    p = cp.asnumpy(cp.abs(cp.fft.rfft(x)) ** 2 / len(x))[1:]
    f = cp.asnumpy(cp.fft.rfftfreq(len(x), d=1.0))[1:]
    edges = np.logspace(np.log10(f[0]), np.log10(f[-1]), nbins)
    idx = np.digitize(f, edges)
    fb = np.array([f[idx == i].mean() for i in range(1, nbins) if (idx == i).any()])
    pb = np.array([p[idx == i].mean() for i in range(1, nbins) if (idx == i).any()])
    return fb, pb

stats = {}
curves = {}
for name, s in series.items():
    fb, pb = spectrum_logbinned(s)
    band = (fb > 1 / (12 * 3600)) & (fb < 1 / 600)
    beta, logc = np.polyfit(np.log10(fb[band]), np.log10(pb[band]), 1)
    beta = -beta
    stats[name] = {"spectral_slope_beta": float(beta),
                   "hurst_from_beta": float((beta + 1) / 2)}
    curves[name] = (fb, pb, beta, logc)
save_stats("f2_fourier_ctx_stats.json", stats)

harmonics = {"24h": 1 / 86400, "12h": 2 / 86400, "8h": 3 / 86400, "6h": 4 / 86400}
fig, axes = plt.subplots(1, 3, figsize=(12.5, 3.4), sharey=True, constrained_layout=True)
for ax, (name, color) in zip(axes, [("ctx_total", C_YELLOW),
                                    ("ctx_multimodal", C_BLUE),
                                    ("ctx_text_only", C_AQUA)]):
    fb, pb, beta, logc = curves[name]
    ax.loglog(fb, pb, color=color, linewidth=1.0)
    band = (fb > 1 / (12 * 3600)) & (fb < 1 / 600)
    ax.loglog(fb[band], 10 ** logc * fb[band] ** (-beta), color="#1f2430",
              linewidth=1.4, linestyle="--", label=f"1/f^{beta:.2f}  (H≈{(beta + 1) / 2:.2f})")
    for lbl, fh in harmonics.items():
        ax.axvline(fh, color=MUTED, linewidth=0.6, linestyle=":")
        ax.annotate(lbl, xy=(fh, ax.get_ylim()[0] if ax.get_ylim()[0] > 0 else 1),
                    xytext=(2, 10), textcoords="offset points", fontsize=7,
                    color=MUTED, rotation=90)
    ax.set_xlabel("frequency (Hz)")
    ax.set_title(name.replace("_", " "))
    ax.legend(frameon=False, fontsize=8)
axes[0].set_ylabel("power")
save_fig(fig, "f2_fourier_ctx.png")

print("\nKey readout:")
for name, s in stats.items():
    print(f"{name}: beta={s['spectral_slope_beta']:.2f}  H≈{s['hurst_from_beta']:.2f}")
