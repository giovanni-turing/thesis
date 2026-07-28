"""Shared plotly theme + save helpers for the thesis figure re-designs.

Mirrors the dataviz-skill validated palette used by the matplotlib originals
(analysis/trace_eda/_common.py) so old vs. new stay comparable, but renders via
plotly. Every figure is exported as static PDF (vector, print) + PNG (raster,
preview) + a self-contained interactive HTML (review/defense).

PRINT GEOMETRY (visual-review pass V01/V02/V03, packets 011-027)
----------------------------------------------------------------
`save(fig, name, w, h)` now takes w/h in **PostScript points** and the exported
PDF canvas is exactly w x h pt, chosen per figure to equal its `\\includegraphics`
placement width in `tex/`. Placement scale is therefore 1.0x and a nominal
N-pt font in the figure is an N-pt font on paper (V03 / packet 011 fix).

The PDF is produced as plotly -> SVG (kaleido) -> cairo, *not* by kaleido's
own PDF writer. Kaleido 0.2.1 prints through Chromium 88 / Skia, which emits
subset fonts whose text layer carries Private-Use-Area codepoints in place of
`(`, `:`, `-`, `x`, `~` (defect family V01) and writes 90-degree rotated runs
back-to-front (`snekot txetnoc`, defect family V02). Cairo writes a proper
ToUnicode CMap and forward-ordered rotated runs, so both families disappear.
This is the plotly-side equivalent of matplotlib's `pdf.fonttype = 42`; the two
matplotlib figures in the set (`sim_frontier`, `sim_metric_frontier`) set that
rcParam in their own producers.

Type sizes are print sizes: nothing below 7 pt, data strokes >= 0.7 pt.

Palette (dataviz reference, light mode, fixed slot order - never cycled):
  slot1 blue   #2a78d6   slot2 green   #008300   slot3 magenta #e87ba4
  slot4 yellow #eda100   slot5 aqua    #1baf7a   slot6 orange  #eb6834
  slot7 violet #4a3aa7   slot8 red     #e34948
Semantic continuity with the originals: vision-pool / images -> blue,
language-pool / requests -> aqua-green.
"""
from __future__ import annotations
import copy
import os
import shutil
import textwrap
import plotly.graph_objects as go
import plotly.io as pio

FIGDIR = os.path.dirname(os.path.abspath(__file__))
TESE = os.path.dirname(FIGDIR)

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

# --- print type scale (points; canvas == placement width, so pt == pt) -------
FS_TICK = 7.0      # tick numerals
FS_AXIS = 7.5      # axis titles
FS_ANNO = 7.0      # in-plot annotations / callouts
FS_LEG = 7.0       # legend entries
FS_SUB = 8.0       # subplot titles
FS_TITLE = 8.5     # figure title

LW_GRID = 0.5
LW_AXIS = 0.6

# --- template ---------------------------------------------------------------
_axis = dict(
    showgrid=True, gridcolor=GRID, gridwidth=LW_GRID,
    zeroline=False,
    showline=True, linecolor=AXIS, linewidth=LW_AXIS,
    ticks="outside", ticklen=2.5, tickwidth=0.6, tickcolor=AXIS,
    tickfont=dict(color=MUTED, size=FS_TICK),
    title=dict(font=dict(color=INK, size=FS_AXIS), standoff=4),
    automargin=True,
)
pio.templates["thesis"] = go.layout.Template(
    layout=dict(
        font=dict(family=FONT, size=FS_TICK, color=INK),
        paper_bgcolor=SURFACE,
        plot_bgcolor=SURFACE,
        colorway=CAT,
        title=dict(font=dict(size=FS_TITLE, color=INK), x=0.0, xanchor="left",
                   pad=dict(l=2, b=4)),
        xaxis=_axis, yaxis=_axis,
        legend=dict(bgcolor="rgba(255,255,255,0.0)", borderwidth=0,
                    font=dict(size=FS_LEG, color=INK),
                    itemsizing="constant", tracegroupgap=2),
        margin=dict(l=34, r=8, t=26, b=26),
        hoverlabel=dict(font=dict(family=FONT, size=11)),
        colorscale=dict(sequential=[[i / (len(BLUES) - 1), c]
                                    for i, c in enumerate(BLUES)]),
    )
)
pio.templates.default = "thesis"


def style_axes(fig, **kw):
    fig.update_xaxes(**_axis)
    fig.update_yaxes(**_axis)
    return fig


def wrap(text: str, width_pt: float, size_pt: float = FS_TITLE,
         indent_pt: float = 0.0) -> str:
    """Hard-wrap a plotly title/annotation to <br> lines that fit `width_pt`.

    Plotly never auto-wraps text; on the compact print canvases an unwrapped
    headline silently overflows the page box. Character budget uses 0.50 em as
    the mean advance width of the Inter/Helvetica sans stack.
    """
    ncols = max(12, int((width_pt - indent_pt) / (0.50 * size_pt)))
    return "<br>".join(textwrap.wrap(text, ncols)) or text


def subtitles(texts, width_pt, size_pt: float = FS_SUB, ncols: int = 1):
    """Wrap a tuple of subplot titles to the per-column width."""
    per = width_pt / max(1, ncols)
    return [wrap(t, per - 12, size_pt) for t in texts]


# --- font scaling for the interactive HTML ----------------------------------
def _scale_fonts(obj, k):
    if isinstance(obj, dict):
        for key, val in obj.items():
            if key == "size" and isinstance(val, (int, float)):
                obj[key] = round(val * k, 2)
            elif key in ("width", "height") and not isinstance(val, dict):
                continue
            else:
                _scale_fonts(val, k)
    elif isinstance(obj, list):
        for v in obj:
            _scale_fonts(v, k)
    return obj


def _html_variant(fig, w, h):
    """Screen copy: same data, canvas and type scaled up for a browser."""
    d = fig.to_dict()
    layout = d.get("layout", {})
    for key in ("font", "title", "legend", "annotations", "hoverlabel"):
        if key in layout:
            _scale_fonts(layout[key], 1.75)
    for key in list(layout):
        if key.startswith(("xaxis", "yaxis", "coloraxis")):
            _scale_fonts(layout[key], 1.75)
    for tr in d.get("data", []):
        for key in ("textfont", "marker", "insidetextfont", "outsidetextfont"):
            if key in tr:
                _scale_fonts(tr[key], 1.0 if key == "marker" else 1.75)
    layout["width"] = int(w * 2.4)
    layout["height"] = int(h * 2.4)
    layout["margin"] = {k: v * 2.0 for k, v in
                        (layout.get("margin") or dict(l=34, r=8, t=26, b=26)).items()
                        if isinstance(v, (int, float))}
    return go.Figure(d)


# --- export -----------------------------------------------------------------
GROUPS = {"eda_": "eda", "pred_": "pred", "sim_": "sim", "aic_": "aic"}


def promote(name: str):
    """Copy the exported PDF+PNG into the manuscript's figuras/<group>/ tree."""
    for pre, grp in GROUPS.items():
        if name.startswith(pre):
            dst = os.path.join(TESE, "figuras", grp)
            os.makedirs(dst, exist_ok=True)
            for ext in (".pdf", ".png"):
                src = os.path.join(FIGDIR, name + ext)
                if os.path.exists(src):
                    shutil.copyfile(src, os.path.join(dst, name + ext))
            return dst
    return None


def save(fig, name: str, w: float = 265, h: float = 150, scale: int = 4):
    """Write <name>.pdf (vector, w x h POINTS), <name>.png, <name>.html.

    w/h are points: the PDF canvas is built to match the figure's
    \\includegraphics placement width so the placement scale is 1.0x.
    PDF route is SVG -> cairo (see module docstring); cairo maps SVG px to pt
    at 96 dpi, so `scale=4/3` restores a 1 px == 1 pt canvas and the plotly
    font sizes (px) come out as the same number of points.
    """
    import cairosvg

    base = os.path.join(FIGDIR, name)
    # plotly's make_subplots hard-codes font size 16 on its subplot-title
    # annotations and ignores the template, which is ~2x the print scale used
    # here (it is what rendered the panel headings clipped and colliding on the
    # compact canvases). Normalise anything still sitting on a plotly default.
    for an in fig.layout.annotations:
        if an.font.size is None:
            an.font.size = FS_ANNO
        elif an.font.size == 16:
            an.font.size = FS_SUB
    fig.update_layout(width=w, height=h)
    svgdir = os.path.join(FIGDIR, "svg")
    os.makedirs(svgdir, exist_ok=True)
    svg = os.path.join(svgdir, name + ".svg")
    fig.write_image(svg)
    cairosvg.svg2pdf(url=svg, write_to=base + ".pdf", scale=4 / 3)
    fig.write_image(base + ".png", scale=scale)
    _html_variant(fig, w, h).write_html(
        base + ".html", include_plotlyjs="cdn", full_html=True,
        config={"displaylogo": False, "responsive": True})
    promote(name)
    print(f"figure: {name}  {w:g}x{h:g} pt")
    return fig
