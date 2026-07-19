#!/usr/bin/env python3
"""Coverage manifest: prove every request of the trace is simulated through
both pools. Reads the verification.jsons of every fleet (no heavy data load)
and emits defense/anim/data/coverage_manifest.json + a printed table.

Coverage model (the trace has 1,000,000 requests over 7 days):
  - ENCODER pool: every request priced by the AIC converter in every fleet
    run (A2/A2t/A6/A13). The A13 full-trace runs (static C8/C2, reactive)
    cover ALL 1,000,000 on both static and reactive policies.
  - LANGUAGE pool: every request replayed through dynamo.replay. A13's
    ft_llm_static + ft_llm_reactive cover ALL 1,000,000 end-to-end
    (encoder-composed -> planner). Forecast policies cover the 749,601-req
    forecast span (A6/A11/A12); the first 250,399 requests (first 1.4 days)
    have no archived forecast BY CONSTRUCTION (thesis coverage boundary) and
    are covered on the always-defined policies (static, reactive).
"""
import json
from pathlib import Path

ROOT = Path("/home/gio/tese")
D = ROOT / "defense/anim/data"
N_TRACE = 1_000_000
N_SPAN = 749_601   # forecast-covered span (aggregate window)


def load(p):
    return json.load(open(p)) if p.exists() else {}


rows = []
# --- A13: the full-trace coverage batch (the guarantee) ---
a13 = load(D / "a13_runs/verification.json")
for tag, r in a13.items():
    rows.append({"fleet": "A13", "run": tag, "pool": r.get("stage", "?"),
                 "requests": r.get("requests"), "expect": N_TRACE,
                 "full": r.get("requests") == N_TRACE and r.get("completed", r.get("requests")) == N_TRACE,
                 "ok": "error" not in r})

# --- language covered-span fleets (forecast + reactive on the 749,601 span) ---
for fleet, vf in (("A11", "a11_runs"), ("A12", "a12_runs")):
    v = load(D / f"{vf}/verification.json")
    for tag, r in v.items():
        n = r.get("requests")
        if n is None:
            continue
        rows.append({"fleet": fleet, "run": tag, "pool": "language",
                     "requests": n, "expect": n, "full": None, "ok": "error" not in r})

# --- A14: per-model max-span forecast E2E ---
a14 = load(D / "a14_runs/verification.json")
for m, r in a14.items():
    if "lang_requests" in r:
        rows.append({"fleet": "A14", "run": f"{m} max-span E2E", "pool": "both (E2E)",
                     "requests": r.get("lang_requests"), "expect": r.get("max_requests"),
                     "full": None, "ok": "error" not in r})

manifest = {
    "trace_requests": N_TRACE, "forecast_span_requests": N_SPAN,
    "per_model_maxspan": {m: {"requests": a14[m].get("lang_requests"),
                              "pct_of_1M": a14[m].get("pct_of_1M"),
                              "ttft_p99": a14[m].get("ttft_p99")} for m in a14},
    "context_days_requests": N_TRACE - N_SPAN,
    "coverage": {
        "encoder_full_trace": {
            "policies": ["static_C8", "static_C2", "reactive"],
            "requests_each": N_TRACE,
            "runs": [t for t in a13 if t.startswith(("ft_static", "ft_reactive"))],
        },
        "language_full_trace": {
            "policies": ["static_TP2x2", "reactive"],
            "requests_each": N_TRACE,
            "runs": [t for t in a13 if t.startswith("ft_llm")],
        },
        "forecast_policies": {
            "note": "structurally undefined on the first 1.4 days (no archived "
                    "forecast) — covered on the 749,601-req forecast span only",
            "span_requests": N_SPAN,
        },
    },
    "rows": rows,
}

# ---- the guarantee check ----
ft_enc = {t: a13[t] for t in a13 if t.startswith(("ft_static", "ft_reactive"))}
ft_llm = {t: a13[t] for t in a13 if t.startswith("ft_llm")}
enc_ok = ft_enc and all(r.get("requests") == N_TRACE and "error" not in r
                        for r in ft_enc.values())
llm_ok = ft_llm and all(r.get("requests") == N_TRACE and r.get("completed") == N_TRACE
                        and "error" not in r for r in ft_llm.values())
a14_ok = bool(a14) and all("error" not in a14[m] and a14[m].get("lang_requests") == a14[m].get("max_requests") for m in a14)
manifest["guarantee"] = {
    "encoder_all_1M_covered": bool(enc_ok),
    "language_all_1M_covered": bool(llm_ok),
    "per_model_maxspan_covered": a14_ok,
    "complete": bool(enc_ok and llm_ok),
}

(D / "coverage_manifest.json").write_text(json.dumps(manifest, indent=1))

print("=" * 68)
print(f"{'fleet':5} {'run':30} {'pool':9} {'requests':>10} {'ok'}")
print("-" * 68)
for r in rows:
    mark = "OK" if r["ok"] else "ERR"
    full = " [FULL 1M]" if r.get("full") else ""
    print(f"{r['fleet']:5} {r['run']:30} {r['pool']:9} "
          f"{(r['requests'] or 0):>10,}{full}  {mark}")
print("=" * 68)
g = manifest["guarantee"]
print(f"encoder pool — all 1,000,000 requests simulated: {g['encoder_all_1M_covered']}")
print(f"language pool — all 1,000,000 requests simulated: {g['language_all_1M_covered']}")
if a14:
    print("--- per-model max-span forecast E2E (both pools) ---")
    for m in a14:
        r = a14[m]
        print(f"  {m:8} {r.get('lang_requests',0):>9,} req ({r.get('pct_of_1M')}% of 1M) "
              f"TTFT p99 {r.get('ttft_p99')} ms  {'ok' if 'error' not in r else 'ERR'}")
print(f"FULL-COVERAGE GUARANTEE MET: {g['complete']}")
print(f"wrote {D / 'coverage_manifest.json'}")
