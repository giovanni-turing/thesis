"""EDA F — Fourier analysis of the arrival timestamps (GPU: cuDF + CuPy FFT).

Spectral view of the request-rate and image-rate signals over the 7 days:
  1. Periodicities — diurnal harmonics (24 h, 12 h, 8 h, …) and anything else.
  2. Spectral slope — power-law 1/f^beta decay (long-range dependence),
     the frequency-domain counterpart of the unbounded Fano growth in §E.
     Hurst exponent H = (beta + 1) / 2 for fractional-Gaussian-noise-like series.
"""
import cupy as cp
import numpy as np
import pandas as pd

from _common import C_AQUA, C_BLUE, MUTED, load_trace, plt, save_fig, save_stats

df = load_trace()

# per-second counts (zero-filled), requests and images, on GPU thereafter
c = df.assign(win=df["ts"].dt.floor("s")).groupby("win").agg(
    requests=("NumImages", "count"), images=("NumImages", "sum"),
).sort_index().to_pandas()
full = pd.date_range(c.index.min(), c.index.max(), freq="s")
c = c.reindex(full, fill_value=0)
N = len(c)
FS = 1.0  # Hz (1 sample per second)

stats = {"n_samples": N, "duration_days": N / 86400}


def spectrum(x_host):
    x = cp.asarray(x_host, dtype=cp.float64)
    x = x - x.mean()
    X = cp.fft.rfft(x)
    p = (cp.abs(X) ** 2) / N
    f = cp.fft.rfftfreq(N, d=1.0 / FS)
    return cp.asnumpy(f[1:]), cp.asnumpy(p[1:])  # drop DC


def logbin(f, p, nbins=400):
    edges = np.logspace(np.log10(f[0]), np.log10(f[-1]), nbins)
    idx = np.digitize(f, edges)
    fb, pb = [], []
    for i in range(1, nbins):
        m = idx == i
        if m.any():
            fb.append(f[m].mean())
            pb.append(p[m].mean())
    return np.array(fb), np.array(pb)


def top_peaks(f, p, fmax=1 / 600.0, k=8):
    """Strongest spectral lines below fmax (periods > 10 min), vs local median."""
    m = f < fmax
    fs, ps = f[m], p[m]
    order = np.argsort(ps)[::-1]
    peaks, taken = [], []
    for i in order:
        if len(peaks) >= k:
            break
        if any(abs(np.log(fs[i] / t)) < 0.05 for t in taken):
            continue
        taken.append(fs[i])
        peaks.append({"freq_hz": float(fs[i]), "period_hours": float(1 / fs[i] / 3600),
                      "power": float(ps[i])})
    return peaks


results = {}
figdata = {}
for name, series in [("requests", c["requests"]), ("images", c["images"])]:
    f, p = spectrum(series.to_numpy())
    fb, pb = logbin(f, p)
    # slope over the LRD band: periods 10 min .. 12 h (clear of diurnal lines & HF floor)
    band = (fb > 1 / (12 * 3600)) & (fb < 1 / 600)
    beta, logc = np.polyfit(np.log10(fb[band]), np.log10(pb[band]), 1)
    beta = -beta
    results[name] = {
        "spectral_slope_beta": float(beta),
        "hurst_from_beta": float((beta + 1) / 2),
        "top_peaks_period_gt_10min": top_peaks(f, p),
    }
    figdata[name] = (fb, pb, beta, logc)

stats.update(results)
save_stats("f_fourier_stats.json", stats)

# --- figure: two panels (small multiples, shared axes), harmonics marked ---
fig, axes = plt.subplots(1, 2, figsize=(10, 3.6), sharey=True)
harmonics = {"24h": 1 / 86400, "12h": 2 / 86400, "8h": 3 / 86400, "6h": 4 / 86400}
for ax, (name, color) in zip(axes, [("requests", C_AQUA), ("images", C_BLUE)]):
    fb, pb, beta, logc = figdata[name]
    ax.loglog(fb, pb, color=color, linewidth=1.0)
    band = (fb > 1 / (12 * 3600)) & (fb < 1 / 600)
    ax.loglog(fb[band], 10 ** (logc) * fb[band] ** (-beta), color="#eda100",
              linewidth=1.6, linestyle="--", label=f"1/f^{beta:.2f}  (H≈{(beta+1)/2:.2f})")
    for lbl, fh in harmonics.items():
        ax.axvline(fh, color=MUTED, linewidth=0.6, linestyle=":")
        ax.annotate(lbl, xy=(fh, ax.get_ylim()[0]), xytext=(2, 10),
                    textcoords="offset points", fontsize=7, color=MUTED, rotation=90)
    ax.set_xlabel("frequency (Hz)")
    ax.set_title(f"{name}/s power spectrum")
    ax.legend(frameon=False, fontsize=8)
axes[0].set_ylabel("power")
save_fig(fig, "f_fourier_spectra.png")

print("\nKey readout:")
for name in ["requests", "images"]:
    r = results[name]
    tops = ", ".join(f"{pk['period_hours']:.1f}h" for pk in r["top_peaks_period_gt_10min"][:4])
    print(f"{name}: beta={r['spectral_slope_beta']:.2f} (H≈{r['hurst_from_beta']:.2f}); "
          f"top periods: {tops}")
