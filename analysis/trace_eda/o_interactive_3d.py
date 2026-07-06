"""EDA O — KDE density surface of the (ctx, gen) demand plane (plotly, GPU).

Construction (per resolution):
  1. Points: one per time window, coordinates (log10(1+ctx/s), log10(1+gen/s)).
  2. Gaussian KDE on the plane (Scott's-rule bandwidth, CuPy, chunked)
     evaluated on a grid  ->  z = P(ctx, gen)   (the density surface).
  3. Surface color = E[img/s | ctx, gen], the Nadaraya-Watson ratio of the
     image-weighted KDE to the marginal KDE:
         E[n | x] = sum_i K(x, x_i) n_i / sum_i K(x, x_i)
     (equivalently: marginalizing the joint KDE of (ctx, gen, n_img) over n).
  4. Grid nodes with negligible density support are masked (holes, not
     extrapolation).
A button group switches the window resolution (1s / 15s / 30s / 45s / 60s).
Output: self-contained HTML.
"""
import os

import cupy as cp
import numpy as np
import pandas as pd
import plotly.graph_objects as go

HERE = os.path.dirname(os.path.abspath(__file__))
SERIES = os.path.join(HERE, "series")
OUT = os.path.join(HERE, "figures", "o_demand_space_3d.html")

# (button label, seconds, parquet name)
RESOLUTIONS = [("1s", 1, "1s"), ("15s", 15, "15s"), ("30s", 30, "30s"),
               ("45s", 45, "45s"), ("60s", 60, "1min")]
GRID = 90
SUPPORT_FRAC = 1e-3  # mask grid nodes with density below this fraction of max


def kde_surface_gpu(xy_host, n_host, grid=GRID, chunk=100_000):
    """2D Gaussian KDE density + Nadaraya-Watson E[n|x] on a grid (GPU)."""
    P = cp.asarray(xy_host, dtype=cp.float32)          # (N, 2)
    nval = cp.asarray(n_host, dtype=cp.float32)        # (N,)
    N = len(P)
    mu, sd = P.mean(0), P.std(0) + 1e-9
    Z = (P - mu) / sd
    h = float(N ** (-1.0 / 6.0))                       # Scott's rule, d=2
    inv2h2 = 1.0 / (2.0 * h * h)

    gx = cp.linspace(P[:, 0].min(), P[:, 0].max(), grid)
    gy = cp.linspace(P[:, 1].min(), P[:, 1].max(), grid)
    GX, GY = cp.meshgrid(gx, gy)                       # (g, g)
    G = cp.stack([GX.ravel(), GY.ravel()], 1)          # (g*g, 2)
    Gz = (G - mu) / sd

    dens = cp.zeros(len(G), dtype=cp.float32)
    wsum_n = cp.zeros(len(G), dtype=cp.float32)
    for i in range(0, N, chunk):
        Zi = Z[i:i + chunk]                            # (c, 2)
        d2 = ((Gz[:, None, :] - Zi[None, :, :]) ** 2).sum(-1)   # (g*g, c)
        K = cp.exp(-d2 * inv2h2)
        dens += K.sum(1)
        wsum_n += K @ nval[i:i + chunk]

    cond = wsum_n / cp.maximum(dens, 1e-12)            # E[n | x]
    dens = dens / (N * 2 * np.pi * h * h * float(sd[0] * sd[1]))  # pdf normalize
    mask = dens < SUPPORT_FRAC * dens.max()
    dens[mask] = cp.nan
    cond[mask] = cp.nan
    g = grid
    return (cp.asnumpy(gx), cp.asnumpy(gy),
            cp.asnumpy(dens.reshape(g, g)), cp.asnumpy(cond.reshape(g, g)))


surfaces, labels = [], []
cmax_log = 0.0
for name, secs, fname in RESOLUTIONS:
    w = pd.read_parquet(os.path.join(SERIES, f"rates_{fname}.parquet"))
    ctx = np.log10(1.0 + w["ctx"].to_numpy(float) / secs)
    gen = np.log10(1.0 + w["gen"].to_numpy(float) / secs)
    img = w["images"].to_numpy(float) / secs
    gx, gy, dens, cond = kde_surface_gpu(np.column_stack([ctx, gen]), img)
    cond_log = np.log10(1.0 + cond)
    cmax_log = max(cmax_log, float(np.nanmax(cond_log)))
    surfaces.append((name, gx, gy, dens, cond, cond_log))
    labels.append(name)

traces = []
ctick_vals = [0, 1, 2]
ctick_txt = ["0", "9", "99"]
for name, gx, gy, dens, cond, cond_log in surfaces:
    traces.append(go.Surface(
        x=gx, y=gy, z=dens,
        surfacecolor=cond_log,
        cmin=0.0, cmax=cmax_log,
        colorscale=[[0, "#f7f9fc"], [0.5, "#2a78d6"], [1, "#123c74"]],
        colorbar=dict(title="E[img/s | ctx,gen]", thickness=14,
                      tickvals=ctick_vals, ticktext=ctick_txt),
        customdata=np.stack([cond], axis=-1),
        hovertemplate=("log ctx/s %{x:.2f} · log gen/s %{y:.2f}<br>"
                       "density %{z:.3g}<br>E[img/s] %{customdata[0]:,.1f}"
                       "<extra></extra>"),
        visible=False,
        name=name,
        showscale=True,
    ))
traces[-1].visible = True  # default: 60s

xt = [0, 1, 2, 3, 4, 5]
xl = ["0", "9", "99", "999", "9,999", "99,999"]
# per-resolution axis renormalization: each button also updates scene ranges
def rng(a, pad=0.03):
    lo, hi = float(np.nanmin(a)), float(np.nanmax(a))
    span = hi - lo
    return [lo - pad * span, hi + pad * span]

buttons = []
for i, (name, gx, gy, dens, cond, cond_log) in enumerate(surfaces):
    buttons.append(dict(
        label=name, method="update",
        args=[{"visible": [j == i for j in range(len(traces))]},
              {"scene.xaxis.range": rng(gx),
               "scene.yaxis.range": rng(gy),
               "scene.zaxis.range": [0, float(np.nanmax(dens)) * 1.05]}],
    ))

fig = go.Figure(data=traces)
fig.update_layout(
    title="KDE density surface of (ctx/s, gen/s) — height P(ctx,gen), color E[img/s | ctx,gen]",
    scene=dict(
        xaxis=dict(title="ctx tokens/s", tickvals=xt, ticktext=xl),
        yaxis=dict(title="gen tokens/s", tickvals=xt, ticktext=xl),
        zaxis=dict(title="density"),
    ),
    updatemenus=[dict(type="buttons", direction="right", x=0.5, xanchor="center",
                      y=1.08, active=len(labels) - 1, buttons=buttons)],
    margin=dict(l=0, r=0, t=80, b=0),
    template="plotly_white",
)
fig.write_html(OUT, include_plotlyjs=True)
print(f"wrote {OUT} ({os.path.getsize(OUT)/1e6:.1f} MB)")
