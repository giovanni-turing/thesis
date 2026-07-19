#!/usr/bin/env python
"""Figures for anchor_master.json: (1) per-forward f(N)/AIC fidelity curve,
(2) provisioned worker count C* per burst (AIC vs real serving encoder vs eager).
"""
import json, csv, sys
from pathlib import Path
sys.path.insert(0, "/home/gio/tese/figuras_new")
import plotly.graph_objects as go
import _theme as T

HERE = Path(__file__).resolve().parent
d = json.load(open(HERE / "anchor_master.json"))
W = d["windows"]
order = ["burst1", "burst2", "burst3", "burst4", "burst5", "burst6"]
labels = [w.replace("burst", "b") for w in order]

# ---- fig 1: per-forward f(N)/AIC across N (fidelity) ----
aic = {int(float(r["n_images"])): float(r["aic_ms"])
       for r in csv.DictReader(open(HERE.parent / "phaseB_batch_validation" / "aic_f_n_postinfill.csv"))}
vllm = json.load(open(HERE / "vllm_eager_dense.json"))["rows"]
sdpa = {}
for r in csv.reader(open(HERE / "merged_sdpa.csv")):
    if r and r[0].strip().isdigit():
        sdpa[int(float(r[0]))] = float(r[2])
Ns = [n for n in range(1, 65) if n in aic and str(n) in vllm and n in sdpa]
fig = go.Figure()
fig.add_hrect(y0=1 - 0.128, y1=1 + 0.128, fillcolor="rgba(27,175,122,0.10)", line_width=0)
fig.add_hline(y=1.0, line=dict(color=T.MUTED, width=1.4, dash="dot"))
fig.add_trace(go.Scatter(x=Ns, y=[vllm[str(n)]["mean_ms"] / aic[n] for n in Ns], mode="lines",
    name="vLLM serving / AIC", line=dict(color=T.BLUE, width=3)))
fig.add_trace(go.Scatter(x=Ns, y=[sdpa[n] / aic[n] for n in Ns], mode="lines",
    name="HF-eager / AIC", line=dict(color=T.RED, width=3, dash="dash")))
fig.add_annotation(x=32, y=1.128, text="±12.8%", showarrow=False, font=dict(size=15, color="#1b9e6f"))
fig.update_layout(
    title="Per-forward fidelity: the real serving encoder tracks AIC to ~5%",
    xaxis_title="images per forward N", yaxis_title="silicon ÷ AIC",
    xaxis=dict(dtick=8), yaxis=dict(range=[0.9, 1.8]),
    legend=dict(orientation="h", y=-0.16, x=0.0), width=1000, height=560)
fig.write_image(str(HERE / "anchor_fidelity.pdf")); fig.write_image(str(HERE / "anchor_fidelity.png"), scale=3)

# ---- fig 2: provisioned worker count C* per burst ----
f2 = go.Figure()
for name, key, col in [("AIC cost model", "aic", T.MUTED),
                       ("real serving encoder (vLLM)", "vllm", T.BLUE),
                       ("HF-eager", "eager", T.RED)]:
    y = [W[w][key]["cstar"] for w in order]
    f2.add_trace(go.Bar(x=labels, y=y, name=name, marker_color=col,
        text=y, textposition="outside", textfont=dict(size=14), cliponaxis=False))
g = d["geomean"]
f2.update_layout(
    title="Provisioned regime: the real serving encoder needs what AIC provisions"
          f"<br><sub>worker inflation geomean {g['inflation_vllm']}× (eager would demand "
          f"{g['inflation_eager']}×) — 2400 MHz</sub>",
    xaxis_title="burst window", yaxis_title="min feasible workers C* (p99 < 1 s)",
    barmode="group", legend=dict(orientation="h", y=-0.16, x=0.0), width=1050, height=600)
f2.write_image(str(HERE / "anchor_provisioning.pdf")); f2.write_image(str(HERE / "anchor_provisioning.png"), scale=3)
print("figures -> anchor_fidelity.{pdf,png}, anchor_provisioning.{pdf,png}")
