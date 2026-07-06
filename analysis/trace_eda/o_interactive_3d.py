"""EDA O — interactive 3D view of the demand space (plotly + GPU KDE smoothing).

Each point is one time window at coordinates (ctx tokens/s, gen tokens/s,
images/s) in log10(1+x) space. Point color is the request rate smoothed by a
Gaussian-KDE (Nadaraya–Watson) regression over the 3D neighborhood — the KDE
runs on GPU (CuPy, chunked pairwise kernels, Scott's-rule bandwidth).
A button group switches the window resolution (1s / 15s / 30s / 45s / 60s;
large series are subsampled to 15k points). Output: self-contained HTML.
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
MAX_POINTS = 15_000
SEED = 0


def kde_smooth_gpu(X_host, y_host, chunk=2048):
    """Nadaraya–Watson regression of y on X with a Gaussian kernel (GPU).

    Bandwidth: Scott's rule per dimension on standardized coordinates.
    """
    X = cp.asarray(X_host, dtype=cp.float32)
    y = cp.asarray(y_host, dtype=cp.float32)
    n, d = X.shape
    mu, sd = X.mean(0), X.std(0) + 1e-9
    Z = (X - mu) / sd
    h = float(n ** (-1.0 / (d + 4)))  # Scott's rule on standardized coords
    inv2h2 = 1.0 / (2.0 * h * h)
    out = cp.empty(n, dtype=cp.float32)
    for i in range(0, n, chunk):
        zi = Z[i:i + chunk]                       # (c, d)
        d2 = ((zi[:, None, :] - Z[None, :, :]) ** 2).sum(-1)  # (c, n)
        w = cp.exp(-d2 * inv2h2)
        out[i:i + chunk] = (w @ y) / w.sum(1)
    return cp.asnumpy(out)


rng = np.random.default_rng(SEED)
traces, labels = [], []
for name, secs, fname in RESOLUTIONS:
    w = pd.read_parquet(os.path.join(SERIES, f"rates_{fname}.parquet"))
    if len(w) > MAX_POINTS:
        w = w.iloc[np.sort(rng.choice(len(w), MAX_POINTS, replace=False))]
    rates = w[["ctx", "gen", "images", "requests"]].to_numpy(dtype=float) / secs
    L = np.log10(1.0 + rates[:, :3])              # ctx/s, gen/s, img/s in log space
    color = kde_smooth_gpu(L, rates[:, 3])        # KDE-smoothed requests/s
    labels.append(f"{name}" + (" (15k sample)" if len(w) == MAX_POINTS else ""))
    traces.append(go.Scatter3d(
        x=L[:, 0], y=L[:, 1], z=L[:, 2],
        mode="markers",
        marker=dict(
            size=2.5,
            color=color,
            colorscale=[[0, "#f7f9fc"], [0.5, "#2a78d6"], [1, "#123c74"]],
            colorbar=dict(title="req/s<br>(KDE-smoothed)", thickness=14),
            opacity=0.75,
        ),
        customdata=np.column_stack([rates[:, :3], color]),
        hovertemplate=("ctx/s %{customdata[0]:,.0f} · gen/s %{customdata[1]:,.0f}"
                       " · img/s %{customdata[2]:,.1f}<br>req/s (smoothed)"
                       " %{customdata[3]:.2f}<extra></extra>"),
        visible=False,
        name=name,
    ))
traces[-1].visible = True  # default: 60s

def axis(title):
    ticks = [0, 1, 2, 3, 4, 5]
    return dict(title=title, tickvals=ticks,
                ticktext=[f"{10**t - 1:,.0f}" for t in ticks])

buttons = [dict(label=lbl,
                method="update",
                args=[{"visible": [j == i for j in range(len(traces))]}])
           for i, lbl in enumerate(labels)]
buttons_default = len(labels) - 1

fig = go.Figure(data=traces)
fig.update_layout(
    title="Demand space: (ctx/s, gen/s, img/s), color = KDE-smoothed request rate",
    scene=dict(xaxis=axis("ctx tokens/s"), yaxis=axis("gen tokens/s"),
               zaxis=axis("images/s")),
    updatemenus=[dict(type="buttons", direction="right", x=0.5, xanchor="center",
                      y=1.08, active=buttons_default, buttons=buttons)],
    margin=dict(l=0, r=0, t=80, b=0),
    template="plotly_white",
)
fig.write_html(OUT, include_plotlyjs=True)
print(f"wrote {OUT} ({os.path.getsize(OUT)/1e6:.1f} MB)")
