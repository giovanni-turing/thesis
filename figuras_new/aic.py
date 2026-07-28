"""Plotly re-design of the AIC encoder-validation figure (aic_fn).

Left: composed AIC cost model vs measured HF-SDPA forward latency, log-log,
with measured/AIC ratio labels. Right: per-image kernel ledger for N=1 vs N=64,
hatched = categories outside AIC's analytic graph. No GPU.
Data: collector_artifacts/phaseB_batch_validation/{aic_f_n_postinfill.csv,
measured_f_n_5x50.csv, kernel_ledger_N1.json, kernel_ledger_N64.json}.
"""
import csv, json, os
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import _theme as T

PB = "/home/gio/tese/collector_artifacts/phaseB_batch_validation"

# ledger category display, color, hatched(outside AIC graph)
CATS = [
    ("gemm", "GEMM", T.BLUE, False),
    ("attention", "attention", T.AQUA, False),
    ("elementwise", "elementwise (unfused)", T.RED, True),
    ("gather_cat", "DeepStack gather/cat", T.YELLOW, True),
    ("patch_embed_conv", "patch-embed conv", T.VIOLET, False),
    ("norm", "norm", "#8a919c", False),
    ("other", "other", "#c3c3c3", True),
]


def _load():
    aic = {}
    with open(f"{PB}/aic_f_n_postinfill.csv") as f:
        for row in csv.DictReader(f):
            aic[int(row["n_images"])] = float(row["aic_ms"])
    meas = {}
    with open(f"{PB}/measured_f_n_5x50.csv") as f:
        for row in csv.DictReader(f):
            meas[int(row["batch"])] = float(row["mean_ms"])
    return aic, meas


def fig_aic():
    aic, meas = _load()
    l1 = json.load(open(f"{PB}/kernel_ledger_N1.json"))
    l64 = json.load(open(f"{PB}/kernel_ledger_N64.json"))

    fig = make_subplots(rows=1, cols=2, horizontal_spacing=0.135,
        column_widths=[0.55, 0.45],
        # wrap each panel heading to its own panel width, not to half the canvas
        subplot_titles=(
            T.wrap("Encoder f(N): composed AIC vs measured silicon", 182),
            T.wrap("Per-image kernel ledger (hatched = outside AIC's graph)", 149)))

    # --- left: f(N) ---
    aN = sorted(aic)
    fig.add_trace(go.Scatter(x=aN, y=[aic[n] for n in aN], mode="lines",
        name="composed (AIC, grid-exact)", line=dict(color=T.BLUE, width=1.4),
        hovertemplate="N=%{x}<br>%{y:.1f} ms<extra>AIC</extra>"), row=1, col=1)
    mN = sorted(meas)
    fig.add_trace(go.Scatter(x=mN, y=[meas[n] for n in mN], mode="lines+markers",
        name="measured (HF eager, 5×50)", line=dict(color=T.RED, width=1.2, dash="dash"),
        marker=dict(size=3.4, color=T.RED),
        hovertemplate="N=%{x}<br>%{y:.1f} ms<extra>measured</extra>"), row=1, col=1)
    # ratio labels at each measured N
    for i, n in enumerate(mN):
        if n in aic:
            r = meas[n] / aic[n]
            # stagger: consecutive measured N sit close together on the log axis
            # and the ratio labels collide at print scale
            fig.add_annotation(x=np.log10(n), y=np.log10(meas[n]), xref="x1", yref="y1",
                text=f"{r:.2f}×", showarrow=False,
                yshift=8 if i % 2 == 0 else 19, xshift=-5,
                font=dict(size=T.FS_ANNO - 0.5, color=T.RED))
    fig.update_xaxes(type="log", title_text="images per forward N", row=1, col=1,
                     tickvals=[1, 2, 4, 8, 16, 32, 64, 128])
    fig.update_yaxes(type="log", title_text="forward latency (ms, log)", row=1, col=1)

    # --- right: per-image stacked ledger ---
    xs = ["N = 1", "N = 64"]
    totals = [l1["total_kernel_ms"] / 1, l64["total_kernel_ms"] / 64]
    for key, disp, color, hatched in CATS:
        vals = [l1["categories_ms"].get(key, 0) / 1,
                l64["categories_ms"].get(key, 0) / 64]
        pat = (dict(shape="/", solidity=0.45, fgcolor="white", bgcolor=color, size=4)
               if hatched else dict(shape=""))
        fig.add_trace(go.Bar(x=xs, y=vals, name=disp,
            marker=dict(color=color, pattern=pat, line=dict(color="white", width=0.6)),
            hovertemplate=disp + "<br>%{y:.2f} ms/img<extra></extra>"), row=1, col=2)
    for xi, tot in zip(xs, totals):
        fig.add_annotation(x=xi, y=tot, xref="x2", yref="y2",
            text=f"<b>{tot:.1f} ms/img</b>", showarrow=False, yshift=7,
            font=dict(size=T.FS_ANNO, color=T.INK))
    fig.update_yaxes(title_text="kernel time per image (ms)", rangemode="tozero",
                     row=1, col=2)
    fig.update_layout(
        title=T.wrap("AIC anchors the encoder cost; the measured gap lives in "
                     "unmodeled elementwise + gather kernels", 427),
        barmode="stack",
        # 7 ledger categories x plotly's 30 px minimum legend item height =
        # 210 pt, taller than the whole canvas, so the vertical legend silently
        # dropped GEMM and attention. A wrapped horizontal legend fits.
        # 9 legend entries: force a fixed 3-per-row grid, otherwise plotly sizes
        # every entry to the widest label and only 2 fit per row (5 rows, which
        # overran the canvas and swallowed the x-axis title).
        # 9 legend entries. Plotly lays a horizontal legend out in uniform
        # columns sized to the widest label, which put only 2 per row (5 rows,
        # taller than the plot). entrywidth pins a 3-per-row grid instead.
        legend=dict(orientation="h", x=0.0, xanchor="left", y=-0.42,
                    yanchor="top", font=dict(size=6.2),
                    entrywidth=80, entrywidthmode="pixels", itemwidth=30),
        margin=dict(l=34, r=10, t=56, b=76))
    return T.save(fig, "aic_fn", w=427, h=214)


PE = "/home/gio/tese/collector_artifacts/phaseE_physical_anchor"


def fig_engines():
    import math
    # AIC merged curve (provenance CSV already merged postinfill + model tail)
    aic = {}
    with open("/home/gio/tese/figuras/aic/aic_fn_engines_aiccurve.csv") as f:
        for row in csv.DictReader(f):
            aic[int(row["N"])] = float(row["aic_ms"])

    def from_csv(p):  # col0=N, col2=mean_ms
        d = {}
        for line in open(p):
            c = line.split(",")
            if c and c[0].strip().isdigit():
                d[int(c[0])] = float(c[2])
        return d
    sdpa = from_csv(f"{PE}/merged_sdpa.csv")
    fa2 = from_csv(f"{PE}/merged_fa2.csv")
    vll = {int(k): v["mean_ms"] for k, v in
           json.load(open(f"{PE}/vllm_eager_dense.json"))["rows"].items()}
    comp = {int(k): v["compiled_ms"] for k, v in
            json.load(open(f"{PE}/vit_compile_dense.json")).items()}

    ENG = [("AIC composition", aic, T.INK, "solid"),
           ("HF-SDPA", sdpa, T.RED, "dash"),
           ("HF-FA2", fa2, T.ORANGE, "dot"),
           ("vLLM-flash", vll, T.AQUA, "solid"),
           ("torch.compile", comp, T.VIOLET, "dashdot")]

    fig = make_subplots(rows=1, cols=2, horizontal_spacing=0.12,
        subplot_titles=T.subtitles(
            ("Encoder f(N) by execution engine",
             "vLLM tracks AIC to the FIFO cap; HF is the outlier"), 393, ncols=2))
    for name, d, color, dash in ENG:
        xs = sorted(d)
        fig.add_trace(go.Scatter(x=xs, y=[d[n] for n in xs], mode="lines",
            name=name, line=dict(color=color, width=1.2, dash=dash),
            hovertemplate=name + "<br>N=%{x}<br>%{y:.1f} ms<extra></extra>"), row=1, col=1)
    # ratio panel
    for name, d, color, dash in ENG[1:]:
        xs = sorted(set(d) & set(aic))
        fig.add_trace(go.Scatter(x=xs, y=[d[n] / aic[n] for n in xs], mode="lines",
            name=name, line=dict(color=color, width=1.2, dash=dash), showlegend=False,
            hovertemplate=name + "/AIC<br>N=%{x}<br>%{y:.2f}×<extra></extra>"), row=1, col=2)
    fig.add_hrect(y0=1 - 0.128, y1=1 + 0.128, fillcolor="rgba(27,175,122,0.10)",
                  line_width=0, row=1, col=2)
    fig.add_hline(y=1.0, line=dict(color=T.MUTED, width=0.7, dash="dot"), row=1, col=2)
    for col in (1, 2):
        fig.add_vline(x=64, line=dict(color="#cbd0d6", width=0.7, dash="dot"),
                      row=1, col=col)
    # packet 025: the rotated "FIFO cap" stream extracted backwards under the
    # Skia writer; the cairo route emits it forward. Keep it rotated (it labels
    # a vertical rule) but at print size.
    fig.add_annotation(x=math.log10(64), y=1.50, xref="x2", yref="y2", text="FIFO cap",
                       showarrow=False, textangle=-90, xshift=-4,
                       font=dict(size=T.FS_ANNO - 0.5, color=T.MUTED))
    fig.add_annotation(x=math.log10(2), y=1.14, xref="x2", yref="y2", text="±12.8%",
                       showarrow=False, font=dict(size=T.FS_ANNO - 0.5, color="#1b9e6f"))
    fig.update_xaxes(type="log", title_text="images per forward N", row=1, col=1,
                     tickvals=[1, 2, 4, 8, 16, 32, 64, 128, 256, 512])
    # dtick=1: plotly's automatic "2"/"5" minor log labels render at 0.75x the
    # tick font (5.25 pt on paper), under the 6 pt print floor
    fig.update_yaxes(type="log", title_text="ViT forward (ms, log)", row=1, col=1,
                     dtick=1)
    fig.update_xaxes(type="log", title_text="images per forward N", row=1, col=2,
                     tickvals=[1, 2, 4, 8, 16, 32, 64, 128, 256, 512])
    fig.update_yaxes(title_text="engine / AIC", range=[0.9, 1.75], row=1, col=2)
    fig.update_layout(
        title=T.wrap("Encoder cost across execution engines — vLLM validates "
                     "the AIC anchor", 393),
        legend=dict(orientation="h", y=-0.36, x=0.0),
        margin=dict(l=34, r=8, t=56, b=46))
    return T.save(fig, "aic_fn_engines", w=393, h=184)


if __name__ == "__main__":
    fig_aic()
    fig_engines()
