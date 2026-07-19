#!/usr/bin/env python
"""Figure for the provisioned-regime anchor: per-window minimum feasible worker
count C* under AIC vs real silicon (serving-mode compiled, and eager for
contrast) -- the worker inflation a real encoder demands over what AIC provisions.
"""
import json, sys
from pathlib import Path
sys.path.insert(0, "/home/gio/tese/figuras_new")
import plotly.graph_objects as go
import _theme as T

HERE = Path(__file__).resolve().parent
d = json.load(open(HERE / "multiworker_anchor.json"))
W = d["windows"]
order = [w for w in ["burst1", "burst2", "burst3", "burst4", "burst5", "burst6"] if w in W]
labels = [w.replace("burst", "b") for w in order]

series = [("AIC cost model", "aic", T.MUTED),
          ("silicon, serving-mode (compiled)", "compiled", T.BLUE),
          ("silicon, HF-eager", "eager", T.RED)]
fig = go.Figure()
for name, key, col in series:
    y = [W[w][key]["cstar"] for w in order]
    fig.add_trace(go.Bar(x=labels, y=y, name=name, marker_color=col,
        text=y, textposition="outside", textfont=dict(size=13), cliponaxis=False,
        hovertemplate="%{x}: %{y} workers<extra>" + name + "</extra>"))
gc = d.get("geomean_inflation_compiled"); ge = d.get("geomean_inflation_eager")
fig.update_layout(
    title="Provisioned regime: workers a real encoder needs vs. what AIC provisions"
          + (f"<br><sub>serving-mode inflation geomean {gc}× (eager would demand {ge}×)</sub>"
             if gc else ""),
    yaxis_title="min feasible workers C* (p99 < 1000 ms)",
    xaxis_title="burst window", barmode="group",
    legend=dict(orientation="h", y=-0.16, x=0.0))
base = str(HERE / "encoder_anchor_multiworker")
fig.update_layout(width=1100, height=600)
fig.write_image(base + ".pdf"); fig.write_image(base + ".png", scale=3)

# table
print(f"{'window':8s} {'AIC C*':>7s} {'comp C*':>8s} {'eag C*':>7s} "
      f"{'inflC':>6s} {'inflE':>6s}  {'comp p99@AIC':>13s}")
for w in order:
    r = W[w]
    print(f"{w:8s} {r['aic']['cstar']:>7} {r['compiled']['cstar']:>8} "
          f"{r['eager']['cstar']:>7} {str(r['inflation_compiled']):>6} "
          f"{str(r['inflation_eager']):>6}  {str(r['compiled_p99_at_aic_cstar']):>13}")
print(f"\ngeomean inflation: compiled {gc}x  eager {ge}x")
print("figure ->", base + ".{pdf,png}")
