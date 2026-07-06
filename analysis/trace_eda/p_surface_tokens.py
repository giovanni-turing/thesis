"""EDA P — KDE density surface colored by total token rate (plotly, GPU).

Same construction as EDA O for the surface: z = P(ctx, gen) from a Gaussian
KDE over (log10(1+ctx/s), log10(1+gen/s)). The color is NOT a conditional
expectation here — it is the deterministic total-token scale of each grid
node: ctx/s + gen/s (log-scaled color). Buttons switch resolution and
renormalize the scene axes.
"""
import os

import cupy as cp
import numpy as np
import pandas as pd
import plotly.graph_objects as go

HERE = os.path.dirname(os.path.abspath(__file__))
SERIES = os.path.join(HERE, "series")
OUT = os.path.join(HERE, "figures", "p_demand_space_tokens.html")

RESOLUTIONS = [("1s", 1, "1s"), ("15s", 15, "15s"), ("30s", 30, "30s"),
               ("45s", 45, "45s"), ("60s", 60, "1min")]
GRID = 240          # dense sampling of the smooth KDE (no noise added: bandwidth unchanged)
SUPPORT_FRAC = 3e-4  # keep more of the low-density shoulder


def kde_density_gpu(xy_host, grid=GRID, chunk=12_000):  # chunk sized for 240^2 nodes x chunk float32
    P = cp.asarray(xy_host, dtype=cp.float32)
    N = len(P)
    mu, sd = P.mean(0), P.std(0) + 1e-9
    Z = (P - mu) / sd
    h = float(N ** (-1.0 / 6.0))  # Scott's rule, d=2
    inv2h2 = 1.0 / (2.0 * h * h)

    gx = cp.linspace(P[:, 0].min(), P[:, 0].max(), grid)
    gy = cp.linspace(P[:, 1].min(), P[:, 1].max(), grid)
    GX, GY = cp.meshgrid(gx, gy)
    G = cp.stack([GX.ravel(), GY.ravel()], 1)
    Gz = (G - mu) / sd

    dens = cp.zeros(len(G), dtype=cp.float32)
    for i in range(0, N, chunk):
        d2 = ((Gz[:, None, :] - Z[i:i + chunk][None, :, :]) ** 2).sum(-1)
        dens += cp.exp(-d2 * inv2h2).sum(1)
    dens = dens / (N * 2 * np.pi * h * h * float(sd[0] * sd[1]))
    dens[dens < SUPPORT_FRAC * dens.max()] = cp.nan
    return cp.asnumpy(gx), cp.asnumpy(gy), cp.asnumpy(dens.reshape(grid, grid))


surfaces = []
cmax_log = 0.0
cmin_log = np.inf
for name, secs, fname in RESOLUTIONS:
    w = pd.read_parquet(os.path.join(SERIES, f"rates_{fname}.parquet"))
    ctx = np.log10(1.0 + w["ctx"].to_numpy(float) / secs)
    gen = np.log10(1.0 + w["gen"].to_numpy(float) / secs)
    gx, gy, dens = kde_density_gpu(np.column_stack([ctx, gen]))
    # total token rate at each grid node: deterministic function of coordinates
    GX, GY = np.meshgrid(gx, gy)
    total = (10.0 ** GX - 1.0) + (10.0 ** GY - 1.0)      # ctx/s + gen/s
    total[np.isnan(dens)] = np.nan
    surfaces.append((name, gx, gy, dens, total, total))

# shared color scale on log2(1+x): per-second units comparable across
# resolutions; caps at global p10/p99 of supported nodes (log2 domain)
_all = np.concatenate([s[4][~np.isnan(s[4])].ravel() for s in surfaces])
CMIN = float(np.log2(1.0 + np.percentile(_all, 10)))
CMAX = float(np.log2(1.0 + np.percentile(_all, 99)))
traces = []
for name, gx, gy, dens, total, total_log in surfaces:
    traces.append(go.Surface(
        x=gx, y=gy, z=dens,
        surfacecolor=np.log2(1.0 + total),
        cmin=CMIN, cmax=CMAX,
        colorscale=[[0.0, "#008300"], [0.35, "#a8d24a"], [0.6, "#eda100"],
                    [0.8, "#eb6834"], [1.0, "#c40000"]],  # green -> red, red at max
        colorbar=dict(title="log2(1 + ctx/s + gen/s)", thickness=14),
        customdata=np.stack([total], axis=-1),
        hovertemplate=("log ctx/s %{x:.2f} · log gen/s %{y:.2f}<br>"
                       "density %{z:.3g}<br>total tokens/s %{customdata[0]:,.0f}"
                       "<extra></extra>"),
        visible=False,
        name=name,
        showscale=True,
    ))
traces[-1].visible = True  # default: 60s

xt = [0, 1, 2, 3, 4, 5]
xl = ["0", "9", "99", "999", "9,999", "99,999"]

def rng(a, pad=0.03):
    lo, hi = float(np.nanmin(a)), float(np.nanmax(a))
    span = hi - lo
    return [lo - pad * span, hi + pad * span]

buttons = []
for i, (name, gx, gy, dens, total, total_log) in enumerate(surfaces):
    buttons.append(dict(
        label=name, method="update",
        args=[{"visible": [j == i for j in range(len(traces))]},
              {"scene.xaxis.range": rng(gx),
               "scene.yaxis.range": rng(gy),
               "scene.zaxis.range": [0, float(np.nanmax(dens)) * 1.05]}],
    ))

fig = go.Figure(data=traces)
fig.update_layout(
    title="KDE density surface of (ctx/s, gen/s) — height P(ctx,gen), color ctx/s + gen/s",
    scene=dict(
        xaxis=dict(title="ctx tokens/s", tickvals=xt, ticktext=xl),
        yaxis=dict(title="gen tokens/s", tickvals=xt, ticktext=xl),
        zaxis=dict(title="density"),
    ),
    updatemenus=[dict(type="buttons", direction="right", x=0.5, xanchor="center",
                      y=1.08, active=len(surfaces) - 1, buttons=buttons)],
    margin=dict(l=0, r=0, t=80, b=0),
    template="plotly_white",
)
fig.write_html(OUT, include_plotlyjs=True)
print(f"wrote {OUT} ({os.path.getsize(OUT)/1e6:.1f} MB)")
