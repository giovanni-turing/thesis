#!/usr/bin/env python
"""MASTER end-to-end encoder anchor -- confound-free, at the 2400 MHz reference.

Uses the DENSE banked 2400 MHz f(N) curves (no fresh GPU, no clock confound):
  AIC        aic_f_n_postinfill.csv        (the cost model)
  vLLM       vllm_eager_dense.json         (the real serving path AIC composes)
  HF-eager   merged_sdpa.csv               (the slow HF-transformers stack)
  compile    vit_compile_dense.json        (torch.compile, secondary; interpolated)

Replays every burst window through the FAITHFUL multi-worker FIFO converter
(simulate_vision_pool, whole-request batching to the 64-image cap), reporting:
  - W=1 encoder-delay p99 (saturated anchor), silicon vs AIC
  - minimum feasible worker count C* (p99<1000ms, non-divergent) = worker
    inflation a real encoder demands over what AIC provisions
Run in the aiconfigurator venv (CPU). Writes anchor_master.json.
"""
import csv, json, math
from pathlib import Path
import silicon_multiworker as M

HERE = Path(__file__).resolve().parent
OUT = HERE / "anchor_master.json"
SWEEP = list(range(1, 33)) + [36, 40, 48, 64]


def load_curves():
    v = json.load(open(HERE / "vllm_eager_dense.json"))["rows"]
    vllm = {str(n): v[str(n)]["mean_ms"] for n in range(1, 65)}
    sdpa = {}
    for r in csv.reader(open(HERE / "merged_sdpa.csv")):
        if r and r[0].strip().isdigit() and int(float(r[0])) <= 64:
            sdpa[str(int(float(r[0])))] = float(r[2])
    comp = json.load(open(HERE / "vit_compile_dense.json"))
    comp = {k: comp[k]["compiled_ms"] for k in comp if int(k) <= 64}
    return vllm, sdpa, comp


def main():
    vllm, sdpa, comp = load_curves()
    enc = {"aic": M.AICEncoder(),
           "vllm": M.MeasuredEncoder(vllm),          # true serving path
           "eager": M.MeasuredEncoder(sdpa),         # HF-transformers eager
           "compile": M.MeasuredEncoder(comp)}       # torch.compile (secondary)
    a = M.AICEncoder()
    out = {"clock_mhz": 2400, "sla_ms": M.SLA_MS, "sweep": SWEEP,
           "f64_ms": {"aic": a._f(64), "vllm": vllm["64"], "eager": sdpa["64"],
                      "compile": comp["64"]},
           "f64_over_aic": {k: round((vllm["64"] if k == "vllm" else sdpa["64"] if k == "eager"
                            else comp["64"]) / a._f(64), 3) for k in ("vllm", "eager", "compile")},
           "windows": {}}
    print("f(64) @2400:", {k: round(x, 1) for k, x in out["f64_ms"].items()},
          "| /AIC:", out["f64_over_aic"])
    print(f"\n{'window':8s} {'images':>10s} | W=1 p99 (s): "
          f"{'AIC':>7s}{'vLLM':>8s}{'eager':>8s} | C*: {'AIC':>4s}{'vLLM':>5s}{'eager':>6s} "
          f"{'inflV':>6s}{'inflE':>6s}")
    for name, offset, maxr, grid in M.WINDOWS:
        reqs, total = M.build_img_reqs(offset, maxr)
        rec = {"images": int(sum(n for _, _, n in reqs)), "n_image_reqs": len(reqs)}
        # W=1 p99 + feasible C* per encoder
        p1, cstar = {}, {}
        for k, e in enc.items():
            p99_1, _, _ = M.eval_point(reqs, 1, e, total)
            p1[k] = round(p99_1, 1)
            # feasibility gate = p99 < SLA ONLY, matching baselines.tex tab:base-grid
            # ("minimizes all-request encoder-delay p99"); NOT the extra queue-
            # divergence check (which only flagged burst5's boundary-draining queue).
            cs = next((w for w in SWEEP if M.eval_point(reqs, w, e, total)[0] < M.SLA_MS), None)
            cstar[k] = cs
            rec[k] = {"w1_p99_ms": p1[k], "cstar": cs, "gate": "p99_only",
                      "p99_at_aic_cstar": None}
        ac = str(cstar["aic"]) if cstar["aic"] else None
        # p99 of each encoder at AIC's recommended worker count
        for k, e in enc.items():
            if ac:
                p99_ac, _, _ = M.eval_point(reqs, cstar["aic"], e, total)
                rec[k]["p99_at_aic_cstar"] = round(p99_ac, 1)
        rec["w1_ratio_vllm"] = round(p1["vllm"] / p1["aic"], 3) if p1["aic"] else None
        rec["w1_ratio_eager"] = round(p1["eager"] / p1["aic"], 3) if p1["aic"] else None
        rec["inflation_vllm"] = round(cstar["vllm"] / cstar["aic"], 2) if (cstar["aic"] and cstar["vllm"]) else None
        rec["inflation_eager"] = round(cstar["eager"] / cstar["aic"], 2) if (cstar["aic"] and cstar["eager"]) else None
        out["windows"][name] = rec
        json.dump(out, open(OUT, "w"), indent=1)
        print(f"{name:8s} {rec['images']:>10,d} | "
              f"{p1['aic']/1000:>7.1f}{p1['vllm']/1000:>8.1f}{p1['eager']/1000:>8.1f} | "
              f"{str(cstar['aic']):>4s}{str(cstar['vllm']):>5s}{str(cstar['eager']):>6s} "
              f"{str(rec['inflation_vllm']):>6s}{str(rec['inflation_eager']):>6s}")

    def gm(k):
        v = [out["windows"][w][k] for w in out["windows"] if out["windows"][w].get(k)]
        return round(math.exp(sum(math.log(x) for x in v) / len(v)), 3) if v else None
    out["geomean"] = {"w1_ratio_vllm": gm("w1_ratio_vllm"), "w1_ratio_eager": gm("w1_ratio_eager"),
                      "inflation_vllm": gm("inflation_vllm"), "inflation_eager": gm("inflation_eager")}
    json.dump(out, open(OUT, "w"), indent=1)
    print("\ngeomean:", out["geomean"])
    print("DONE ->", OUT)


if __name__ == "__main__":
    main()
