"""Plotly re-designs of the predictor-chapter figures.

Data: predictors/results/metrics/*.parquet, predictors/results/*.parquet,
predictors/results_dynamo/consolidated.json, simulation/results/live51/*.json,
and the reassembled covariate parquets in _data/. No GPU.
"""
import json, os, re
import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import _theme as T

ROOT = "/home/gio/tese"
MET = f"{ROOT}/predictors/results/metrics"
RES = f"{ROOT}/predictors/results"
DATA = os.path.join(os.path.dirname(os.path.abspath(__file__)), "_data")
LIVE = f"{ROOT}/simulation/results/live51"

VARIATES = ["requests", "images", "ctx", "gen"]
VLAB = {"requests": "requests", "images": "images",
        "ctx": "context tokens", "gen": "generated tokens"}
RES_ORDER = ["1min", "45s", "30s", "15s", "1s"]
FM = [("timesfm", "uni", "TimesFM"), ("chronos", "uni", "Chronos-2"),
      ("toto", "uni", "Toto-2")]
BASE = [("naive", "naive", T.MUTED, "dot"),
        ("ewma", "EWMA", "#8a919c", "dashdot"),
        ("holt_winters", "Holt–Winters", "#4b5563", "dash")]


# ===================================================== 1. horizon WAPE (2x2)
def fig_horizon():
    m = pd.read_parquet(f"{MET}/metrics_by_h.parquet")
    m = m[(m.span == "common") & (m.resolution == "1min") & (m.candidate == "point")]
    fig = make_subplots(rows=2, cols=2, subplot_titles=[VLAB[v] for v in VARIATES],
                        shared_xaxes=True, vertical_spacing=0.14, horizontal_spacing=0.11)
    for i, v in enumerate(VARIATES):
        r, c = i // 2 + 1, i % 2 + 1
        mv = m[m.variate == v]
        # foundation-model envelope (min-max across the 3 FMs at each h)
        fmc = []
        for mod, mode, _ in FM:
            s = mv[(mv.model == mod) & (mv["mode"] == mode)].sort_values("h")
            fmc.append(s.set_index("h")["wape"] * 100)
        fmdf = pd.concat(fmc, axis=1)
        hs = fmdf.index
        show = (i == 0)
        fig.add_trace(go.Scatter(
            x=list(hs) + list(hs[::-1]),
            y=list(fmdf.max(axis=1)) + list(fmdf.min(axis=1)[::-1]),
            fill="toself", fillcolor="rgba(42,120,214,0.18)", line=dict(width=0),
            name="foundation models (min–max)", legendgroup="fm", showlegend=show,
            hoverinfo="skip"), row=r, col=c)
        fig.add_trace(go.Scatter(x=hs, y=fmdf.mean(axis=1), mode="lines",
            line=dict(color=T.BLUE, width=1.4), name="foundation models",
            legendgroup="fm", showlegend=False,
            hovertemplate="h=%{x}<br>%{y:.1f}% WAPE<extra>foundation</extra>"),
            row=r, col=c)
        for mod, lab, col, dash in BASE:
            s = mv[(mv.model == mod)].sort_values("h")
            fig.add_trace(go.Scatter(x=s.h, y=s.wape * 100, mode="lines", name=lab,
                line=dict(color=col, width=0.9, dash=dash), legendgroup=lab,
                showlegend=show,
                hovertemplate="h=%{x}<br>%{y:.1f}% WAPE<extra>" + lab + "</extra>"),
                row=r, col=c)
        fig.update_yaxes(rangemode="tozero", row=r, col=c)
    fig.update_xaxes(tickvals=[1, 3, 6, 9, 12], title_text="horizon step h", row=2)
    fig.update_yaxes(title_text="WAPE (%)", col=1)
    fig.update_layout(
        title=T.wrap("Point-forecast error across the horizon — foundation "
                     "models stay a tight pack below every baseline", 367),
        legend=dict(orientation="h", y=-0.14, x=0.0),
        margin=dict(l=34, r=8, t=44, b=44))
    return T.save(fig, "pred_horizon_wape", w=367, h=252)


# ===================================================== 2. forecast band
def _ensure_covariates(model):
    """Reassemble the split+gzipped covariate parquet on demand."""
    out = f"{DATA}/{model}_covariates.parquet"
    if not os.path.exists(out):
        import glob, gzip
        parts = sorted(glob.glob(f"{RES}/{model}_covariates.parquet.gz.part*"))
        with open(out, "wb") as w:
            w.write(gzip.decompress(b"".join(open(p, "rb").read() for p in parts)))
    return out


def fig_band():
    ch = pd.read_parquet(_ensure_covariates("chronos"))
    ch = ch[(ch.resolution == "1min") & (ch.variate == "images")].sort_values("step")
    nv = pd.read_parquet(f"{RES}/naive_images.parquet")
    nv = nv[nv.resolution == "1min"]
    peak = ch["y_true"].idxmax()
    ploc = ch.index.get_loc(peak)
    w = ch.iloc[max(0, ploc - 150):ploc + 150]
    s = 1 / 60.0
    ts = pd.to_datetime(w.ts)
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=list(ts) + list(ts[::-1]),
        y=list(w.p90 * s) + list((w.p10 * s)[::-1]), fill="toself",
        fillcolor="rgba(42,120,214,0.18)", line=dict(width=0),
        name="p10–p90 band", hoverinfo="skip"))
    nvw = nv[nv.step.isin(w.step)]
    fig.add_trace(go.Scatter(x=pd.to_datetime(nvw.ts), y=nvw.point * s, mode="lines",
        name="naive", line=dict(color="#8a919c", width=0.8, dash="dash")))
    fig.add_trace(go.Scatter(x=ts, y=w.y_true * s, mode="lines", name="observed",
        line=dict(color=T.INK, width=0.8),
        hovertemplate="%{x|%H:%M}<br>%{y:.0f} img/s<extra>observed</extra>"))
    fig.add_trace(go.Scatter(x=ts, y=w.point * s, mode="lines", name="point forecast",
        line=dict(color=T.BLUE, width=1.3),
        hovertemplate="%{x|%H:%M}<br>%{y:.0f} img/s<extra>forecast</extra>"))
    # coverage: fraction of observed bins above p90
    cov = float((w.y_true > w.p90).mean())
    fig.add_annotation(x=0.5, y=0.99, xref="paper", yref="paper", yanchor="top",
        text=f"p90 band pierced by {cov*100:.0f}% of bins — honest ~90% coverage",
        showarrow=False, font=dict(size=T.FS_ANNO, color=T.MUTED))
    fig.update_layout(
        title=T.wrap("Chronos-2 (cov): a calibrated 12-step forecast tracks "
                     "the burst plateau", 376),
        yaxis_title="images/s", yaxis=dict(rangemode="tozero"), xaxis_title=None,
        legend=dict(orientation="h", y=1.02, x=0.0, yanchor="bottom"),
        margin=dict(l=34, r=8, t=40, b=22))
    return T.save(fig, "pred_forecast_band", w=376, h=148)


# ===================================================== 3. WAPE heatmap (facet)
def fig_heatmap():
    m = pd.read_parquet(f"{MET}/metrics_overall.parquet")
    m = m[(m.span == "common") & (m.candidate == "point")]
    ROWS = [("naive", "uni", "naive"), ("ewma", "uni", "EWMA"),
            ("holt_winters", "uni", "Holt–Winters"), ("timesfm", "uni", "TimesFM"),
            ("chronos", "uni", "Chronos-2"), ("chronos", "cov", "Chronos-2 (cov)"),
            ("toto", "uni", "Toto-2"), ("toto", "cov", "Toto-2 (cov)")]
    rlabs = [r[2] for r in ROWS]
    fig = make_subplots(rows=1, cols=4, subplot_titles=[VLAB[v] for v in VARIATES],
                        horizontal_spacing=0.022, shared_yaxes=True)
    for ci, v in enumerate(VARIATES):
        M = np.full((len(ROWS), len(RES_ORDER)), np.nan)
        for i, (mod, mode, _) in enumerate(ROWS):
            for j, rr in enumerate(RES_ORDER):
                q = m[(m.model == mod) & (m["mode"] == mode) & (m.variate == v) &
                      (m.resolution == rr)]
                if len(q):
                    M[i, j] = q["wape"].iloc[0] * 100
        rel = np.clip(M / np.nanmin(M, axis=0), 1, 2)
        best = M == np.nanmin(M, axis=0)
        fig.add_trace(go.Heatmap(z=rel, x=RES_ORDER, y=rlabs,
            colorscale=[[i / 8, c] for i, c in enumerate(T.BLUES)],
            zmin=1, zmax=2, showscale=(ci == 3),
            colorbar=dict(title=dict(text="WAPE ÷<br>col best",
                                     font=dict(size=T.FS_ANNO - 0.5)),
                          thickness=5, len=0.82, x=1.004, xpad=2,
                          tickfont=dict(size=T.FS_ANNO - 0.5)),
            xgap=1, ygap=1, hoverinfo="skip"), row=1, col=ci + 1)
        for i in range(len(ROWS)):
            for j in range(len(RES_ORDER)):
                val = M[i, j]
                txt = f"{val:.0f}" if val >= 9.95 else f"{val:.1f}"
                # packet 026: the 200+ cell numerals were the worst legibility in
                # the set (2.65 pt on paper). Canvas == placement width now, so
                # this nominal 7 pt IS 7 pt on paper.
                fig.add_annotation(x=RES_ORDER[j], y=rlabs[i],
                    text=f"<b>{txt}</b>" if best[i, j] else txt,
                    showarrow=False, xref=f"x{ci+1}", yref=f"y{ci+1}",
                    font=dict(size=7, color=T.INK if rel[i, j] < 1.6 else "white"))
    fig.update_yaxes(autorange="reversed")
    fig.update_layout(
        title=T.wrap("Foundation models are the column-best in every target × "
                     "resolution cell (bold = best); classical rows run darker",
                     427),
        margin=dict(l=58, r=36, t=44, b=22))
    return T.save(fig, "pred_wape_heatmap", w=427, h=196)


# ===================================================== 4. framework diff (3 panel)
def _p99(path, key="p99_ttft_ms"):
    return json.load(open(path))[key]


def fig_framework_diff():
    # panel a: accuracy
    m1 = pd.read_parquet(f"{MET}/metrics_h1.parquet")
    m1 = m1[(m1.variate == "images") & (m1.resolution == "1min") &
            (m1.candidate == "point") & (m1.span == "common")]
    def wape(mod, mode="uni"):
        return float(m1[(m1.model == mod) & (m1["mode"] == mode)]["wape"].iloc[0])
    dp = json.load(open(f"{ROOT}/predictors/results_dynamo/consolidated.json"))["dynamo_predictors"]
    found = sorted([("toto", wape("toto")), ("timesfm", wape("timesfm")),
                    ("chronos", wape("chronos"))], key=lambda t: t[1])
    shipped = sorted([("arima*", dp["arima_1min"]["wape"]),
                      ("prophet*", dp["prophet_1min"]["wape"]),
                      ("kalman*", dp["kalman_1min"]["wape"])], key=lambda t: t[1])
    classical = sorted([("ewma", wape("ewma")), ("holt-winters", wape("holt_winters")),
                        ("naive", wape("naive"))], key=lambda t: t[1])
    # panel b/c
    re_ = _p99(f"{LIVE}/twin_re.report.json")
    fc = _p99(f"{LIVE}/twin_fc.report.json")
    fc90 = _p99(f"{LIVE}/twin_fc_p90.report.json")
    live_fc = json.load(open(f"{LIVE}/live_runs/live_fc/profile_export_aiperf.json"))["time_to_first_token"]["p99"]
    live_re = json.load(open(f"{LIVE}/live_runs/live_re/profile_export_aiperf.json"))["time_to_first_token"]["p99"]

    fig = make_subplots(rows=1, cols=3, horizontal_spacing=0.105,
        subplot_titles=("(a) forecast accuracy — nearly identical",
                        "(b) closed-loop verdict", "(c) online fidelity"),
        column_widths=[0.34, 0.33, 0.33])
    # (a)
    groups = [("foundation", found, T.BLUE), ("Dynamo-shipped*", shipped, T.YELLOW),
              ("classical", classical, "#8a919c")]
    for gname, items, col in groups:
        fig.add_trace(go.Bar(x=[n for n, _ in items], y=[v for _, v in items],
            marker_color=col, name=gname, text=[f"{v:.3f}" for _, v in items],
            textposition="outside", textfont=dict(size=T.FS_ANNO - 0.8),
            cliponaxis=False,
            hovertemplate="%{x}: %{y:.3f} WAPE<extra></extra>"), row=1, col=1)
    fig.update_yaxes(title_text="WAPE (image signal, 1-min)", rangemode="tozero",
                     title_font=dict(size=6.5), row=1, col=1)
    # (b) packet 024: on the 1125 pt canvas these labels were force-wrapped by
    # plotly into single-character vertical stacks. Re-broken to lines that fit
    # the panel at 7 pt; the categories themselves are unchanged.
    bx = ["Dynamo<br>(arima,<br>kalman,<br>prophet)",
          "forecast<br>p50 (mean<br>conv.)",
          "forecast<br>p90 (tail<br>conv.)"]
    bv = [re_, fc, fc90]
    bc = [T.RED, T.RED, "#1b9e6f"]
    fig.add_trace(go.Bar(x=bx, y=bv, marker_color=bc, showlegend=False,
        text=[f"{v:.0f}" for v in bv], textposition="outside",
        textfont=dict(size=T.FS_ANNO - 0.8),
        cliponaxis=False, hovertemplate="%{y:.0f} ms<extra></extra>"), row=1, col=2)
    fig.add_hline(y=1000, line=dict(color=T.INK, width=0.8, dash="dash"), row=1, col=2,
        annotation_text="SLA 1000 ms", annotation_position="top right",
        annotation_font=dict(size=T.FS_ANNO - 0.8))
    fig.update_yaxes(title_text="burst3 TTFT p99 (ms)", range=[0, 3900], row=1, col=2)
    # (c)
    cats = ["forecast<br>p90", "reactive"]
    fig.add_trace(go.Bar(x=cats, y=[live_fc, live_re], marker_color=T.BLUE,
        name="live runtime", text=[f"{live_fc:.0f}", f"{live_re:.0f}"],
        textposition="outside", textfont=dict(size=T.FS_ANNO - 0.8), cliponaxis=False,
        hovertemplate="live %{y:.0f} ms<extra></extra>"), row=1, col=3)
    fig.add_trace(go.Bar(x=cats, y=[fc90, re_], marker_color="#8a919c",
        name="offline twin", text=[f"{fc90:.0f}", f"{re_:.0f}"],
        textposition="outside", textfont=dict(size=T.FS_ANNO - 0.8), cliponaxis=False,
        hovertemplate="twin %{y:.0f} ms<extra></extra>"), row=1, col=3)
    fig.add_hline(y=1000, line=dict(color=T.INK, width=0.8, dash="dash"), row=1, col=3,
        annotation_text="SLA 1000 ms", annotation_position="top left",
        annotation_font=dict(size=T.FS_ANNO - 0.8))
    fig.update_yaxes(range=[0, 3900], row=1, col=3)
    # pin tickangle=0 on (b)/(c): left to itself plotly rotates these multi-line
    # category labels 90 deg the moment they are a hair too wide, which is the
    # vertical-label corruption packet 024 flagged.
    fig.update_xaxes(tickangle=0, tickfont=dict(size=6.5), row=1, col=2)
    fig.update_xaxes(tickangle=0, tickfont=dict(size=6.5), row=1, col=3)
    fig.update_layout(
        title=T.wrap("Accuracy does not explain the verdict — conversion policy "
                     "does, and it holds live", 427),
        barmode="group",
        legend=dict(orientation="h", y=-0.46, x=0.0, yanchor="top"),
        margin=dict(l=36, r=6, t=44, b=62))
    # -45 keeps the 9 model names on one line each (14.7 pt of x per label vs a
    # 9.9 pt rotated footprint) instead of plotly's per-character wrap.
    fig.update_xaxes(tickangle=-45, row=1, col=1)
    return T.save(fig, "pred_framework_diff", w=427, h=222)


# ===================================================== 5. models over burst
def fig_models_burst():
    obs = None
    fig = go.Figure()
    day0, day1 = pd.Timestamp("2024-10-21 00:00"), pd.Timestamp("2024-10-21 23:00")
    styles = [("timesfm", "TimesFM", T.VIOLET), ("chronos", "Chronos-2", T.BLUE),
              ("toto", "Toto-2", T.AQUA)]
    for mod, lab, col in styles:
        d = pd.read_parquet(f"{RES}/{mod}_images.parquet")
        d = d[d.resolution == "1min"].sort_values("step")
        d = d[(pd.to_datetime(d.ts) >= day0) & (pd.to_datetime(d.ts) <= day1)]
        if obs is None:
            obs = d[["ts", "y_true"]]
            fig.add_trace(go.Scatter(x=pd.to_datetime(obs.ts), y=obs.y_true / 60,
                mode="lines", name="observed", line=dict(color="#9aa0a6", width=0.7),
                hovertemplate="%{x|%H:%M}<br>%{y:.0f} img/s<extra>observed</extra>"))
        fig.add_trace(go.Scatter(x=pd.to_datetime(d.ts), y=d.point / 60, mode="lines",
            name=lab, line=dict(color=col, width=1.1),
            hovertemplate="%{x|%H:%M}<br>%{y:.0f} img/s<extra>" + lab + "</extra>"))
    fig.update_layout(
        title=T.wrap("Three foundation models trace nearly coincident paths "
                     "over the week's largest image burst", 376),
        yaxis_title="images/s (1-min bins)", yaxis=dict(rangemode="tozero"),
        xaxis_title="2024-10-21 (UTC)",
        legend=dict(orientation="h", y=1.02, x=0.0, yanchor="bottom"),
        margin=dict(l=34, r=8, t=52, b=30))
    return T.save(fig, "pred_models_burst", w=376, h=160)


ALL = [fig_horizon, fig_band, fig_heatmap, fig_framework_diff, fig_models_burst]

if __name__ == "__main__":
    import sys
    which = sys.argv[1:] or None
    for fn in ALL:
        if which and not any(w in fn.__name__ for w in which):
            continue
        try:
            fn()
        except Exception as e:
            import traceback; traceback.print_exc()
            print("FAIL", fn.__name__, repr(e))
