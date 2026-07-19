#!/usr/bin/env python
"""Generality figure: silicon f(N) / AIC(image_px) across 224/336/448/672px.
Reads fn_multires.json (silicon, eager+compiled) + aic_multires.json. eda venv."""
import json, sys
from pathlib import Path
sys.path.insert(0, "/home/gio/tese/figuras_new")
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import _theme as T

HERE = Path(__file__).resolve().parent
sil = json.load(open(HERE / "fn_multires.json"))
aic = json.load(open(HERE / "aic_multires.json"))
RES = [str(p) for p in sil["res"]]
GRID = [str(n) for n in sil["grid_n"]]
colors = {"224": T.AQUA, "336": T.YELLOW, "448": T.BLUE, "672": T.VIOLET}

fig = make_subplots(rows=1, cols=2, subplot_titles=(
    "serving proxy (torch.compile) ÷ AIC", "HF-eager ÷ AIC"), horizontal_spacing=0.09)
for ci, mode in enumerate(["compiled", "eager"]):
    fig.add_hrect(y0=1 - 0.128, y1=1 + 0.128, fillcolor="rgba(27,175,122,0.10)",
                  line_width=0, row=1, col=ci + 1)
    fig.add_hline(y=1.0, line=dict(color=T.MUTED, width=1.2, dash="dot"), row=1, col=ci + 1)
    for px in RES:
        y = [sil[mode][px][n] / aic[px][n] for n in GRID]
        fig.add_trace(go.Scatter(x=[int(n) for n in GRID], y=y, mode="lines+markers",
            name=f"{px}px", legendgroup=px, showlegend=(ci == 0),
            line=dict(color=colors[px], width=2.5), marker=dict(size=6)), row=1, col=ci + 1)
    fig.update_xaxes(title_text="images per forward N", row=1, col=ci + 1)
fig.update_yaxes(title_text="silicon ÷ AIC", row=1, col=1)
fig.update_layout(
    title="Generality: AIC-vs-silicon fidelity across image resolution (224–672px)",
    legend=dict(orientation="h", y=-0.16, x=0.0), width=1300, height=560)
b = str(HERE / "anchor_multires")
fig.write_image(b + ".pdf"); fig.write_image(b + ".png", scale=3)

# table
print(f"{'mode':9s} {'px':>4s} " + " ".join(f"N={n:>3s}" for n in GRID))
for mode in ["compiled", "eager"]:
    for px in RES:
        print(f"{mode:9s} {px:>4s} " + " ".join(
            f"{sil[mode][px][n]/aic[px][n]:5.2f}" for n in GRID))
print("figure ->", b + ".{pdf,png}")
