"""Plotly re-designs of the simulation-chapter figures (sim_knees, sim_burst_queue).
Data: simulation/results/sweeps/summary.json + series/*.series.json. No GPU.
"""
import json, os
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import _theme as T

SW = "/home/gio/tese/simulation/results/sweeps"


# ===================================================== saturation knees
def fig_knees():
    d = json.load(open(f"{SW}/summary.json"))
    cur = d["curves"]
    sla = d["thresholds"]
    fig = make_subplots(rows=1, cols=2, horizontal_spacing=0.10,
        subplot_titles=("Language pool (dynamo.replay, 2 workers)",
                        "Vision pool (converter FIFO, 2 encoder workers)"))
    WCOL = {"head2k": T.BLUE, "burst1": T.AQUA}
    TDASH = {"poly": "solid", "aic": "dash"}

    def draw(key, col, lab, showlegend=True):
        c = cur[key]
        pool, window, timing = key.split("|")
        color = WCOL[window]
        fig.add_trace(go.Scatter(x=c["offered"], y=c["metric"], mode="lines+markers",
            name=lab, line=dict(color=color, width=2, dash=TDASH[timing]),
            marker=dict(size=6, color=color), showlegend=showlegend,
            hovertemplate=lab + "<br>%{x:.1f} offered<br>%{y:,.0f} ms p99<extra></extra>"),
            row=1, col=col)
        ks = c.get("knee_speedup")
        if ks is not None and ks in c["speedups"]:
            idx = c["speedups"].index(ks)
            fig.add_trace(go.Scatter(x=[c["offered"][idx]], y=[c["metric"][idx]],
                mode="markers", marker=dict(size=13, color=color,
                line=dict(color="white", width=2.5)), showlegend=False,
                hovertemplate=f"knee s={ks:g}<extra></extra>"), row=1, col=col)

    # left: LLM pool, 4 curves
    for window in ("head2k", "burst1"):
        for timing in ("poly", "aic"):
            draw(f"llm|{window}|{timing}", 1, f"{window} · {timing}")
    fig.add_hline(y=sla["llm_ttft_p99_ms"], line=dict(color=T.MUTED, width=1, dash="dot"),
        row=1, col=1, annotation_text="SLA: TTFT p99 &lt; 1000 ms (+ ITL p99 &lt; 100 ms)",
        annotation_position="bottom right", annotation_font=dict(size=14, color=T.MUTED))
    # right: vision pool, 2 curves (color+dash already keyed by left legend)
    for window in ("head2k", "burst1"):
        draw(f"vision|{window}|aic", 2, window, showlegend=False)
    fig.add_hline(y=sla["vision_encoder_delay_p99_ms"],
        line=dict(color=T.MUTED, width=1, dash="dot"), row=1, col=2,
        annotation_text="SLA: encoder delay p99 &lt; 1000 ms",
        annotation_position="bottom left", annotation_font=dict(size=14, color=T.MUTED))
    # knee text annotations
    def knee_text(key):
        c = cur[key]
        if c.get("knee_speedup") is None:
            return "saturated at s=1"
        s = f"knee s={c['knee_speedup']:g}"
        return s + ("" if c.get("saturated_in_range") else " (censored)")
    fig.add_annotation(x=np.log10(3), y=np.log10(500), xref="x1", yref="y1",
        text=knee_text("llm|head2k|poly"), showarrow=False, font=dict(size=14, color=T.BLUE))
    fig.add_annotation(x=np.log10(40), y=np.log10(230), xref="x2", yref="y2",
        text="head2k: " + knee_text("vision|head2k|aic"), showarrow=False,
        font=dict(size=14, color=T.BLUE))
    fig.add_annotation(x=np.log10(70), y=np.log10(20000), xref="x2", yref="y2",
        text="burst1: " + knee_text("vision|burst1|aic"), showarrow=False,
        font=dict(size=14, color=T.AQUA))

    fig.update_xaxes(type="log", title_text="offered load (req/s, log)", row=1, col=1)
    fig.update_yaxes(type="log", title_text="TTFT p99 (ms, log)", row=1, col=1)
    fig.update_xaxes(type="log", title_text="offered load (img/s, log)", row=1, col=2)
    fig.update_yaxes(type="log", title_text="encoder delay p99 (ms, log)", row=1, col=2)
    fig.update_layout(
        title="Saturation knees per pool — arrival-speedup sweep on the Azure LMM trace",
        legend=dict(orientation="h", y=-0.16, x=0.0))
    return T.save(fig, "sim_knees", w=1360, h=560)


# ===================================================== burst queue
def fig_burst_queue():
    s = json.load(open(f"{SW}/series/vision_burst1_s1.series.json"))
    rec = s["series"]
    t = np.array([r["t"] for r in rec]) / 3600.0
    arrived = np.array([r["img_arrived"] for r in rec], float)
    queue = np.array([r["queue_imgs_end"] for r in rec], float)
    arr1 = np.convolve(arrived, np.ones(60) / 60, mode="same")
    meta = json.load(open(f"{SW}/vision_burst1_aic_s1.json"))
    util = round(meta["encoder_utilization"] * 100)
    nw = meta["encoder_workers"]
    pk = int(queue.max()); pkt = t[queue.argmax()]

    fig = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.08,
        row_heights=[0.46, 0.54],
        subplot_titles=(f"Offered load — {nw}-worker pool at {util}% mean utilization",
                        "Head-of-line backlog — bursts, not mean load, drive it"))
    fig.add_trace(go.Scatter(x=t, y=arr1, mode="lines", fill="tozeroy",
        line=dict(color=T.AQUA, width=1), fillcolor="rgba(27,175,122,0.30)",
        name="offered images/s",
        hovertemplate="%{x:.2f} h<br>%{y:.0f} img/s<extra></extra>"), row=1, col=1)
    fig.add_trace(go.Scatter(x=t, y=queue, mode="lines", line=dict(color=T.BLUE, width=1),
        name="queued images",
        hovertemplate="%{x:.2f} h<br>%{y:,.0f} queued<extra></extra>"), row=2, col=1)
    fig.add_trace(go.Scatter(x=[pkt], y=[pk], mode="markers+text",
        marker=dict(size=11, color=T.BLUE, line=dict(color="white", width=2)),
        text=[f"  peak {pk:,} images queued"], textposition="middle right",
        textfont=dict(size=15, color=T.INK), showlegend=False, hoverinfo="skip"),
        row=2, col=1)
    fig.update_yaxes(title_text="offered images/s<br>(1-min mean)", rangemode="tozero",
                     row=1, col=1)
    fig.update_yaxes(title_text="queued images", rangemode="tozero", row=2, col=1)
    fig.update_xaxes(title_text="hours into the episode window", row=2, col=1)
    fig.update_layout(
        title="A 29%-utilized vision pool still builds a 4,701-image backlog in the "
              "largest burst", showlegend=False)
    return T.save(fig, "sim_burst_queue", w=1360, h=680)


ALL = [fig_knees, fig_burst_queue]
if __name__ == "__main__":
    import sys
    which = sys.argv[1:] or None
    for fn in ALL:
        if which and not any(w in fn.__name__ for w in which):
            continue
        try:
            fn()
        except Exception:
            import traceback; traceback.print_exc()
