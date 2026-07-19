"""Shared plotly theme + save helpers for the thesis figure re-designs.

Mirrors the dataviz-skill validated palette used by the matplotlib originals
(analysis/trace_eda/_common.py) so old vs. new stay comparable, but renders via
plotly. Every figure is exported as static PDF (vector, print) + PNG (raster,
preview) + a self-contained interactive HTML (review/defense).

Palette (dataviz reference, light mode, fixed slot order — never cycled):
  slot1 blue   #2a78d6   slot2 green   #008300   slot3 magenta #e87ba4
  slot4 yellow #eda100   slot5 aqua    #1baf7a   slot6 orange  #eb6834
  slot7 violet #4a3aa7   slot8 red     #e34948
Semantic continuity with the originals: vision-pool / images -> blue,
language-pool / requests -> aqua-green.
"""
from __future__ import annotations
import os
import plotly.graph_objects as go
import plotly.io as pio

FIGDIR = os.path.dirname(os.path.abspath(__file__))

# --- palette ----------------------------------------------------------------
BLUE = "#2a78d6"
GREEN = "#008300"
MAGENTA = "#e87ba4"
YELLOW = "#eda100"
AQUA = "#1baf7a"
ORANGE = "#eb6834"
VIOLET = "#4a3aa7"
RED = "#e34948"
CAT = [BLUE, GREEN, MAGENTA, YELLOW, AQUA, ORANGE, VIOLET, RED]

INK = "#0b0b0b"
MUTED = "#52514e"
GRID = "#e5e7eb"
SURFACE = "#ffffff"
AXIS = "#9aa0a6"

# sequential blue ramp (dataviz)
BLUES = ["#eaf2fd", "#cde2fb", "#9ec5f4", "#6da7ec", "#3987e5",
         "#256abf", "#184f95", "#104281", "#0d366b"]

FONT = "Inter, Helvetica, Arial, sans-serif"

# --- template ---------------------------------------------------------------
_axis = dict(
    showgrid=True, gridcolor=GRID, gridwidth=1,
    zeroline=False,
    showline=True, linecolor=AXIS, linewidth=1,
    ticks="outside", ticklen=4, tickcolor=AXIS,
    tickfont=dict(color=MUTED, size=13),
    title=dict(font=dict(color=INK, size=14)),
    automargin=True,
)
pio.templates["thesis"] = go.layout.Template(
    layout=dict(
        font=dict(family=FONT, size=13, color=INK),
        paper_bgcolor=SURFACE,
        plot_bgcolor=SURFACE,
        colorway=CAT,
        title=dict(font=dict(size=17, color=INK), x=0.0, xanchor="left",
                   pad=dict(l=4, b=8)),
        xaxis=_axis, yaxis=_axis,
        legend=dict(bgcolor="rgba(255,255,255,0.0)", borderwidth=0,
                    font=dict(size=18, color=INK)),
        margin=dict(l=70, r=24, t=64, b=56),
        hoverlabel=dict(font=dict(family=FONT, size=12)),
        colorscale=dict(sequential=[[i / (len(BLUES) - 1), c]
                                    for i, c in enumerate(BLUES)]),
    )
)
pio.templates.default = "thesis"


def style_axes(fig, **kw):
    fig.update_xaxes(**_axis)
    fig.update_yaxes(**_axis)
    return fig


def save(fig, name: str, w: int = 1000, h: int = 560, scale: int = 3):
    """Write <name>.pdf (vector), <name>.png (raster), <name>.html (interactive)."""
    base = os.path.join(FIGDIR, name)
    fig.update_layout(width=w, height=h)
    fig.write_image(base + ".pdf")
    fig.write_image(base + ".png", scale=scale)
    if os.environ.get("EMIT_SVG"):
        os.makedirs(os.path.join(FIGDIR, "svg"), exist_ok=True)
        fig.write_image(os.path.join(FIGDIR, "svg", name + ".svg"))
    fig.write_html(base + ".html", include_plotlyjs="cdn", full_html=True,
                   config={"displaylogo": False, "responsive": True})
    print("figure:", base + ".{pdf,png,html}")
    return fig
