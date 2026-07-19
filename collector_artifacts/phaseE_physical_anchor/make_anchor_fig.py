#!/usr/bin/env python
"""Table + figure for the one-real-encoder burst-replay anchor.

Reads burst_anchor_all.json (per window: AIC-sim, eager-silicon, compiled-silicon
encoder-delay p99) and produces:
  - a printed summary table
  - encoder_anchor.pdf/png : per-window encoder-delay p99, AIC vs silicon
    (serving-mode compiled) vs eager, log-y, with the 1000 ms SLA line.
"""
import json, os, sys
from pathlib import Path
sys.path.insert(0, "/home/gio/tese/figuras_new")
import plotly.graph_objects as go
import _theme as T

HERE = Path(__file__).resolve().parent
d = json.load(open(HERE / "burst_anchor_all.json"))
W = d["windows"]
order = ["burst1", "burst2", "burst3", "burst4", "burst5", "burst6"]

# ---- table ----
print(f"{'window':8s} {'images':>9s} {'AIC p99':>10s} {'compiled':>10s} {'ratio':>6s} "
      f"{'eager':>10s} {'ratio':>6s}")
for w in order:
    r = W[w]
    aic = r["aic"]["p99"]
    comp = r.get("compiled", {})
    eag = r.get("eager", {})
    print(f"{w:8s} {r['images']:>9,d} {aic:>10.0f} "
          f"{comp.get('p99', float('nan')):>10.0f} {comp.get('p99_over_aic','-'):>6} "
          f"{eag.get('p99', float('nan')):>10.0f} {eag.get('p99_over_aic','-'):>6}")

# geomean ratio across windows
import math
def gm(key):
    rs = [W[w][key]["p99_over_aic"] for w in order
          if key in W[w] and W[w][key].get("p99_over_aic")]
    return math.exp(sum(math.log(x) for x in rs) / len(rs)) if rs else None
print(f"\ngeomean silicon/AIC p99  compiled={gm('compiled')}  eager={gm('eager')}")
print(f"fn(N=64): AIC {json.load(open(HERE.parent/'phaseB_batch_validation'/'aic_f_n_postinfill.csv')) if False else ''}")
if "fn_compiled" in d and "fn_eager" in d:
    print(f"f(64) ms: eager {d['fn_eager'].get('64')}  compiled {d['fn_compiled'].get('64')}")

# ---- figure ----
labels = [w.replace("burst", "b") for w in order]
series = [("AIC cost model (sim)", "aic", T.MUTED),
          ("silicon, serving-mode (compiled)", "compiled", T.BLUE),
          ("silicon, HF-eager", "eager", T.RED)]
fig = go.Figure()
for name, key, col in series:
    y = [W[w].get(key, {}).get("p99") for w in order]
    if not any(y):
        continue
    fig.add_trace(go.Bar(x=labels, y=y, name=name, marker_color=col,
        hovertemplate="%{x}: %{y:,.0f} ms<extra>" + name + "</extra>"))
fig.add_hline(y=1000, line=dict(color=T.INK, width=1.4, dash="dash"),
              annotation_text="SLA 1000 ms", annotation_position="top left",
              annotation_font=dict(size=14))
gc = gm("compiled")
sub = (f"serving-mode silicon tracks the AIC cost model to a geomean "
       f"{gc:.2f}× on encoder-delay p99" if gc else "")
fig.update_layout(
    title="One real encoder, six burst replays end-to-end: silicon vs AIC" +
          (f"<br><sub>{sub}</sub>" if sub else ""),
    yaxis_title="encoder-delay p99 (ms, log)", yaxis_type="log",
    xaxis_title="burst window", barmode="group",
    legend=dict(orientation="h", y=-0.16, x=0.0))
base = str(HERE / "encoder_anchor")
fig.update_layout(width=1100, height=600)
fig.write_image(base + ".pdf"); fig.write_image(base + ".png", scale=3)
print("figure ->", base + ".{pdf,png}")
