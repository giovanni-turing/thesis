"""Plotly re-designs of the trace-EDA figures.

Reads materialized series (analysis/trace_eda/series/*.parquet), the *_stats.json
sidecars, and the CPU-derived artifacts from _prep.py. No GPU.

Design changes vs the matplotlib originals are documented per-figure in the
docstrings and surfaced in figuras_new/GALLERY.md.
"""
import json, os
import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import _theme as T

SERIES = "/home/gio/tese/analysis/trace_eda/series"
STATS = "/home/gio/tese/analysis/trace_eda"
DATA = os.path.join(os.path.dirname(os.path.abspath(__file__)), "_data")


def rates(win="1min"):
    df = pd.read_parquet(f"{SERIES}/rates_{win}.parquet")
    secs = {"1s": 1, "15s": 15, "30s": 30, "45s": 45, "1min": 60}[win]
    for c in ["requests", "images", "ctx", "gen"]:
        df[c + "_ps"] = df[c] / secs
    return df


# ============================================================ a: context|images
def fig_context_vs_numimages():
    q = pd.read_parquet(f"{DATA}/ctx_by_numimages.parquet").sort_values("NumImages")
    x = q["NumImages"]
    fig = go.Figure()
    # two-level band: p10-p90 (light) + p25-p75 (darker)
    for lo, hi, op, lab in [("p10", "p90", 0.12, "p10–p90"),
                            ("p25", "p75", 0.22, "p25–p75")]:
        fig.add_trace(go.Scatter(
            x=pd.concat([x, x[::-1]]), y=pd.concat([q[hi], q[lo][::-1]]),
            fill="toself", fillcolor=f"rgba(42,120,214,{op})",
            line=dict(width=0), hoverinfo="skip", name=lab))
    fig.add_trace(go.Scatter(
        x=x, y=q["p50"], mode="lines+markers", name="median",
        line=dict(color=T.BLUE, width=2.4),
        marker=dict(size=7, color=T.BLUE, line=dict(color="white", width=1)),
        customdata=q["count"],
        hovertemplate="%{x} images<br>median %{y:,.0f} ctx tokens"
                      "<br>n=%{customdata:,}<extra></extra>"))
    # fit slope reference (~64 tok/image, from stats)
    fig.add_trace(go.Scatter(
        x=x, y=5474 + 64.4 * x, mode="lines", name="≈64 tokens / image",
        line=dict(color=T.MUTED, width=1.4, dash="dot"), hoverinfo="skip"))
    fig.update_layout(
        title="Context tokens scale with image count — the vision payload is "
              "already inside the prompt",
        xaxis_title="images per request (NumImages)",
        yaxis_title="context tokens")
    return T.save(fig, "eda_a_context_vs_numimages", w=920, h=520)


# ============================================================ c: seven-day
def fig_seven_day():
    r = rates("1min")
    p99 = float(np.percentile(r["images_ps"], 99))
    fig = make_subplots(
        rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.09,
        subplot_titles=("Language-pool arrival — requests / s (1-min windows)",
                        "Vision-pool arrival — images / s, same clock, its own bursts"))
    fig.add_trace(go.Scatter(x=r.index, y=r["requests_ps"], name="requests/s",
                             line=dict(color=T.AQUA, width=0.8),
                             hovertemplate="%{x|%a %H:%M}<br>%{y:.1f} req/s<extra></extra>"),
                  row=1, col=1)
    fig.add_trace(go.Scatter(x=r.index, y=r["images_ps"], name="images/s",
                             line=dict(color=T.BLUE, width=0.8), fill="tozeroy",
                             fillcolor="rgba(42,120,214,0.10)",
                             hovertemplate="%{x|%a %H:%M}<br>%{y:.0f} img/s<extra></extra>"),
                  row=2, col=1)
    fig.add_hline(y=p99, line=dict(color=T.MUTED, width=1, dash="dash"), row=2, col=1,
                  annotation_text=f"p99 = {p99:.0f} img/s",
                  annotation_position="top left",
                  annotation_font=dict(color=T.MUTED, size=14))
    # midnight day boundaries
    for d in pd.date_range(r.index.min().ceil("D"), r.index.max(), freq="D"):
        for rr in (1, 2):
            fig.add_vline(x=d, line=dict(color="#eef0f2", width=1), row=rr, col=1)
    fig.update_yaxes(title_text="requests/s", row=1, col=1)
    fig.update_yaxes(title_text="images/s", row=2, col=1)
    fig.update_layout(title="One shared clock: vision demand is far spikier than "
                            "the request signal", showlegend=False)
    return T.save(fig, "eda_c_seven_day_signals", w=1040, h=620)


# ============================================================ d: ACF
def _acf(x, lags):
    x = x - x.mean()
    d0 = (x * x).sum()
    return np.array([(x[:-k] * x[k:]).sum() / d0 if k else 1.0 for k in lags])


def fig_acf():
    r = rates("1min")
    lags = np.arange(0, 241)
    a_img = _acf(r["images_ps"].to_numpy(), lags)
    a_req = _acf(r["requests_ps"].to_numpy(), lags)
    hl_img = int(np.argmax(a_img < 0.5))
    hl_req = int(np.argmax(a_req < 0.5))
    fig = go.Figure()
    fig.add_hline(y=0.5, line=dict(color=T.MUTED, width=1, dash="dash"),
                  annotation_text="ACF = 0.5", annotation_position="top right",
                  annotation_font=dict(color=T.MUTED, size=14))
    for a, hl, c, name in [(a_img, hl_img, T.BLUE, "images/s"),
                           (a_req, hl_req, T.AQUA, "requests/s")]:
        fig.add_trace(go.Scatter(x=lags, y=a, mode="lines", name=name,
                                 line=dict(color=c, width=2.2),
                                 hovertemplate="lag %{x} min<br>ACF %{y:.2f}<extra>"
                                               + name + "</extra>"))
        # half-life dropline + marker
        fig.add_trace(go.Scatter(x=[hl, hl], y=[0, 0.5], mode="lines",
                                 line=dict(color=c, width=1, dash="dot"),
                                 showlegend=False, hoverinfo="skip"))
        fig.add_annotation(x=hl, y=0.5, ax=hl, ay=0.5, text=f"{name}: {hl} min",
                           showarrow=False, yshift=14, font=dict(color=c, size=14))
    fig.update_layout(
        title="Demand-signal memory — vision stays autocorrelated 8× longer",
        xaxis_title="lag (minutes)", yaxis_title="autocorrelation",
        xaxis=dict(range=[0, 240]))
    return T.save(fig, "eda_d_acf", w=920, h=520)


# ============================================================ d: img vs req (density)
def fig_img_vs_req():
    r = rates("1min")
    x, y = r["requests_ps"].to_numpy(), r["images_ps"].to_numpy()
    alpha = (x * y).sum() / (x * x).sum()
    ss_res = ((y - alpha * x) ** 2).sum()
    r2 = 1 - ss_res / ((y - y.mean()) ** 2).sum()
    fig = go.Figure()
    # cap the color scale so the origin spike doesn't wash out the mid-density trend
    fig.add_trace(go.Histogram2d(
        x=x, y=y, colorscale=[[0, "#ffffff"]] + [[i / 8, c] for i, c in
        enumerate(T.BLUES)][1:], nbinsx=120, nbinsy=120, zauto=False, zmax=30, zmin=0,
        colorbar=dict(title="1-min<br>windows", thickness=12, len=0.7,
                      tickvals=[0, 10, 20, 30], ticktext=["0", "10", "20", "30+"]),
        hovertemplate="%{x:.1f} req/s<br>%{y:.0f} img/s<br>%{z} windows<extra></extra>"))
    xr = np.linspace(0, x.max(), 50)
    fig.add_trace(go.Scatter(x=xr, y=alpha * xr, mode="lines",
                             name=f"constant fraction: {alpha:.1f} img/req",
                             line=dict(color=T.YELLOW, width=2.6)))
    fig.add_annotation(x=0.98, y=0.06, xref="paper", yref="paper",
                       text=f"R² = {r2:.2f} — request rate explains only {r2*100:.0f}%"
                            "<br>of vision-load variance",
                       showarrow=False, align="right",
                       font=dict(color=T.INK, size=14),
                       bgcolor="rgba(255,255,255,0.75)")
    fig.update_layout(
        title="Vision work is poorly explained by request rate",
        xaxis_title="requests / s (1-min windows)", yaxis_title="images / s",
        legend=dict(x=0.02, y=0.98))
    return T.save(fig, "eda_d_img_vs_req_scatter", w=940, h=560)


# ============================================================ e: arrival process
def fig_arrival_process():
    ia = pd.read_parquet(f"{DATA}/interarrival.parquet")
    c1 = pd.read_parquet(f"{SERIES}/rates_1s.parquet")["requests"].to_numpy()
    st = json.load(open(f"{STATS}/e_comprehensive_stats.json"))
    lam = st["arrivals"]["mean_rate_req_per_s"]
    fano = st["fano_factor_by_window"]
    fkeys = ["s", "10s", "min", "10min", "h"]
    flab = ["1s", "10s", "1min", "10min", "1h"]

    fig = make_subplots(rows=1, cols=3, horizontal_spacing=0.075,
        subplot_titles=("Inter-arrival survival", "Counts vs Poisson",
                        "Overdispersion grows with scale"))
    # (a) survival
    fig.add_trace(go.Scatter(x=ia["x"], y=ia["surv"], mode="lines", name="empirical",
                             line=dict(color=T.BLUE, width=2)), row=1, col=1)
    xr = np.linspace(0, ia["x"].max(), 100)
    fig.add_trace(go.Scatter(x=xr, y=np.exp(-lam * xr), mode="lines",
                             name=f"exponential (λ={lam:.2f}/s)",
                             line=dict(color=T.YELLOW, width=2, dash="dash")), row=1, col=1)
    # (b) counts vs poisson
    from scipy.special import gammaln
    kmax = int(np.quantile(c1, 0.9999))
    ks = np.arange(0, kmax + 1)
    vc = pd.Series(c1).value_counts(normalize=True)
    emp = np.array([vc.get(k, 0) for k in ks])
    pois = np.exp(ks * np.log(lam) - lam - gammaln(ks + 1))
    fig.add_trace(go.Scatter(x=ks[emp > 0], y=emp[emp > 0], mode="markers",
                             name="empirical", marker=dict(color=T.BLUE, size=7),
                             showlegend=False), row=1, col=2)
    fig.add_trace(go.Scatter(x=ks, y=pois, mode="markers", name=f"Poisson({lam:.2f})",
                             marker=dict(color=T.YELLOW, size=6, symbol="square"),
                             showlegend=False), row=1, col=2)
    # (c) fano
    fv = [fano[k] for k in fkeys]
    fig.add_trace(go.Scatter(x=flab, y=fv, mode="lines+markers", name="Fano",
                             line=dict(color=T.BLUE, width=2),
                             marker=dict(size=8, color=T.BLUE), showlegend=False),
                  row=1, col=3)
    fig.add_hline(y=1.0, line=dict(color=T.MUTED, width=1, dash="dash"), row=1, col=3,
                  annotation_text="Poisson = 1", annotation_position="bottom left",
                  annotation_font=dict(color=T.MUTED, size=14))
    fig.update_yaxes(type="log", title_text="P(X > x)", row=1, col=1)
    fig.update_xaxes(title_text="inter-arrival (s)", row=1, col=1)
    fig.update_yaxes(type="log", title_text="probability", row=1, col=2)
    fig.update_xaxes(title_text="requests in 1 s", row=1, col=2)
    fig.update_yaxes(type="log", title_text="Fano factor (var/mean)", row=1, col=3)
    fig.update_xaxes(title_text="aggregation window", row=1, col=3)
    fig.update_layout(
        title="Arrivals are non-Poisson and increasingly overdispersed at coarse scales",
        legend=dict(orientation="h", y=1.02, x=0.0))
    return T.save(fig, "eda_e_arrival_process", w=1180, h=440)


# ============================================================ i: burst onsets
def _episodes():
    r = rates("1min")
    s = r["images_ps"].to_numpy()
    st = json.load(open(f"{STATS}/i_burst_anatomy_stats.json"))
    p50 = st["thresholds"]["p50_img_per_s"]
    p99 = st["thresholds"]["p99_img_per_s"]
    above = s > p99
    runs = []
    i = 0
    while i < len(s):
        if above[i]:
            j = i
            while j < len(s) and above[j]:
                j += 1
            lo = i
            while lo > 0 and s[lo] > p50:
                lo -= 1
            hi = j
            while hi < len(s) and s[hi] > p50:
                hi += 1
            runs.append([lo, hi])
            i = j
        else:
            i += 1
    merged = []
    for a, b in runs:
        if merged and a <= merged[-1][1]:
            merged[-1][1] = max(merged[-1][1], b)
        else:
            merged.append([a, b])
    onsets, peaks = [], []
    for a, b in merged:
        seg = s[a:b]
        pk = seg.argmax()
        onsets.append(max(pk, 1))       # minutes baseline->peak (>=1)
        peaks.append(seg.max())
    return np.array(onsets, float), np.array(peaks, float)


def fig_burst_onsets():
    onsets, peaks = _episodes()
    p10, p50 = np.percentile(onsets, 10), np.percentile(onsets, 50)
    fig = make_subplots(rows=1, cols=2, horizontal_spacing=0.11,
        subplot_titles=(f"Onset time ECDF — p10 {p10:.0f} min, p50 {p50:.0f} min "
                        f"({len(onsets)} episodes)", "Fast-onset bursts are not small"))
    # left: ECDF (better than a 25-bin histogram over ~18 points)
    xs = np.sort(onsets)
    ys = np.arange(1, len(xs) + 1) / len(xs)
    fig.add_trace(go.Scatter(x=xs, y=ys, mode="lines+markers", name="ECDF",
                             line=dict(color=T.BLUE, width=2, shape="hv"),
                             marker=dict(size=6, color=T.BLUE), showlegend=False,
                             hovertemplate="%{x:.0f} min<br>%{y:.0%} of episodes<extra></extra>"),
                  row=1, col=1)
    for p, v in [("p10", p10), ("p50", p50)]:
        fig.add_vline(x=v, line=dict(color=T.MUTED, width=1, dash="dot"), row=1, col=1)
    # right: peak vs onset
    fig.add_trace(go.Scatter(x=onsets, y=peaks, mode="markers", name="episode",
                             marker=dict(size=10, color=T.BLUE,
                                         line=dict(color="white", width=1)),
                             showlegend=False,
                             hovertemplate="onset %{x:.0f} min<br>peak %{y:.0f} img/s<extra></extra>"),
                  row=1, col=2)
    import math
    lr = [math.log10(0.8), math.log10(300)]
    fig.update_xaxes(type="log", range=lr, dtick=1,
                     title_text="onset time, baseline→peak (min)", row=1, col=1)
    fig.update_yaxes(title_text="fraction of episodes", range=[0, 1.05], row=1, col=1)
    fig.update_xaxes(type="log", range=lr, dtick=1, title_text="onset time (min)", row=1, col=2)
    fig.update_yaxes(title_text="peak images/s", row=1, col=2)
    fig.update_layout(title="Burst onsets are short and the fastest ones are the biggest")
    return T.save(fig, "eda_i_burst_onsets", w=1080, h=480)


# ============================================================ l: request clusters
def fig_request_clusters():
    pts = pd.read_parquet(f"{DATA}/clusters_40k.parquet")
    meta = json.load(open(f"{DATA}/cluster_meta.json"))
    k = meta["best_k"]
    sil = meta["silhouette"][str(k)]
    colors = [T.BLUE, T.GREEN, T.MAGENTA, T.YELLOW, T.AQUA, T.ORANGE][:k]
    order = sorted(range(k), key=lambda c: meta[str(c)]["req_share"], reverse=True)
    fig = make_subplots(rows=1, cols=2, horizontal_spacing=0.11,
        column_widths=[0.62, 0.38],
        subplot_titles=(f"Semantic request groups (k={k}, silhouette={sil:.2f})",
                        "A tiny cluster carries most of the images"))
    for c in order:
        m = pts["cluster"] == c
        nm = f"{c}: {meta[str(c)]['semantic_name']}"
        fig.add_trace(go.Scattergl(
            x=pts.loc[m, "ContextTokens"], y=pts.loc[m, "GeneratedTokens"].clip(lower=1),
            mode="markers", name=nm,
            marker=dict(size=2.6, color=colors[c], opacity=0.35),
            hovertemplate=nm + "<extra></extra>"), row=1, col=1)
    fig.update_xaxes(type="log", title_text="context tokens", row=1, col=1)
    fig.update_yaxes(type="log", title_text="generated tokens", row=1, col=1)
    # right: request-share vs image-share disproportion (the headline stat)
    labs = [f"{c}: {meta[str(c)]['semantic_name'].split(':')[0]}" for c in order]
    fig.add_trace(go.Bar(y=labs, x=[meta[str(c)]["req_share"] for c in order],
                         orientation="h", name="share of requests",
                         marker_color=T.MUTED, opacity=0.55,
                         hovertemplate="%{x:.1%} of requests<extra></extra>"), row=1, col=2)
    fig.add_trace(go.Bar(y=labs, x=[meta[str(c)]["img_share"] for c in order],
                         orientation="h", name="share of images",
                         marker_color=T.BLUE,
                         hovertemplate="%{x:.1%} of images<extra></extra>"), row=1, col=2)
    fig.update_xaxes(title_text="share", tickformat=".0%", row=1, col=2)
    fig.update_layout(title="Four request archetypes — and vision load is "
                            "concentrated in one small group",
                      barmode="group", legend=dict(orientation="h", y=-0.16))
    return T.save(fig, "eda_l_request_clusters", w=1200, h=560)


# ============================================================ q: multires tails
def fig_multires():
    st = json.load(open(f"{STATS}/q_multires_tails_stats.json"))
    mr = st["multi_resolution"]
    pa = st["peak_attenuation_vs_1s"]
    wins = sorted({int(kk[:-1]) for kk in mr.keys()})
    sig = [("requests", T.AQUA), ("images", T.BLUE), ("ctx", T.YELLOW), ("gen", T.VIOLET)]
    fig = make_subplots(rows=1, cols=2, horizontal_spacing=0.09,
        subplot_titles=("Burstiness vs binning window", "Peak attenuation under aggregation"))
    for name, c in sig:
        cv = [mr[f"{w}s"][name]["cv2"] for w in wins]
        fig.add_trace(go.Scatter(x=wins, y=cv, mode="lines+markers", name=name,
                                 line=dict(color=c, width=2), marker=dict(size=5, color=c),
                                 legendgroup=name,
                                 hovertemplate=name + "<br>%{x}s window<br>CV² %{y:.2f}<extra></extra>"),
                      row=1, col=1)
        at = [pa[name][f"{w}s"] for w in wins]
        fig.add_trace(go.Scatter(x=wins, y=at, mode="lines+markers", name=name,
                                 line=dict(color=c, width=2), marker=dict(size=5, color=c),
                                 legendgroup=name, showlegend=False,
                                 hovertemplate=name + "<br>%{x}s window<br>peak %{y:.0%} of 1s<extra></extra>"),
                      row=1, col=2)
    for w in (1, 15, 60):
        for col in (1, 2):
            fig.add_vline(x=w, line=dict(color="#e9ebee", width=1), row=1, col=col)
    fig.update_xaxes(type="log", title_text="window (s)", row=1, col=1)
    fig.update_yaxes(type="log", title_text="CV² of rate", row=1, col=1)
    fig.update_xaxes(type="log", title_text="window (s)", row=1, col=2)
    fig.update_yaxes(title_text="observed peak / 1s peak", tickformat=".0%", row=1, col=2)
    fig.update_layout(title="Images are the burstiest signal and attenuate hardest "
                            "under coarse monitoring",
                      legend=dict(orientation="h", y=-0.16))
    return T.save(fig, "eda_q_multires", w=1180, h=520)


# ============================================================ eval windows
def fig_eval_windows():
    r = rates("1min")
    BURSTS = {
        "b1": ("2024-10-21 12:59", "2024-10-21 21:18"),
        "b2": ("2024-10-15 21:16", "2024-10-15 23:10"),
        "b3": ("2024-10-18 10:18", "2024-10-18 10:45"),
        "b4": ("2024-10-18 15:37", "2024-10-18 18:46"),
        "b5": ("2024-10-18 14:32", "2024-10-18 15:53"),
        "b6": ("2024-10-15 23:26", "2024-10-16 00:48"),
    }
    T0 = pd.Timestamp("2024-10-16 21:39")
    fig = go.Figure()
    # band type: forecast context
    fig.add_vrect(x0=r.index.min(), x1=T0, fillcolor=T.MUTED, opacity=0.08,
                  line_width=0, layer="below")
    fig.add_vrect(x0="2024-10-19", x1="2024-10-20", fillcolor=T.AQUA, opacity=0.12,
                  line_width=0, layer="below")
    # stagger labels of near-overlapping bursts onto two rows
    row2 = {"b6", "b5"}
    for b, (a, z) in BURSTS.items():
        fig.add_vrect(x0=a, x1=z, fillcolor=T.YELLOW, opacity=0.22, line_width=0,
                      layer="below")
        mid = pd.Timestamp(a) + (pd.Timestamp(z) - pd.Timestamp(a)) / 2
        fig.add_annotation(x=mid, y=1.0, yref="paper", text=b, showarrow=False,
                           yshift=-34 if b in row2 else -6,
                           font=dict(color="#8a6d00", size=14))
    fig.add_trace(go.Scatter(x=r.index, y=r["images_ps"], mode="lines",
                             line=dict(color=T.BLUE, width=0.9), name="images/s",
                             hovertemplate="%{x|%a %H:%M}<br>%{y:.0f} img/s<extra></extra>"))
    fig.add_annotation(x=pd.Timestamp("2024-10-16 07:00"), y=0.86, yref="paper",
                       text="forecast context (never graded)", showarrow=False,
                       xanchor="left", font=dict(color=T.MUTED, size=14))
    fig.add_annotation(x=pd.Timestamp("2024-10-19 12:00"), y=0.93, yref="paper",
                       text="calm day", showarrow=False,
                       font=dict(color="#0e7a55", size=14))
    fig.update_layout(
        title="Stratified evaluation harness — 6 burst episodes, 1 calm day, "
              "leading forecast context",
        xaxis_title=None, yaxis_title="images/s (1-min mean)",
        yaxis=dict(range=[0, 460]), showlegend=False)
    return T.save(fig, "eda_eval_windows", w=1180, h=440)


ALL = [fig_context_vs_numimages, fig_seven_day, fig_acf, fig_img_vs_req,
       fig_arrival_process, fig_burst_onsets, fig_request_clusters,
       fig_multires, fig_eval_windows]

if __name__ == "__main__":
    import sys
    which = sys.argv[1:] if len(sys.argv) > 1 else None
    for fn in ALL:
        if which and not any(w in fn.__name__ for w in which):
            continue
        try:
            fn()
        except Exception as e:
            print("FAIL", fn.__name__, repr(e))
