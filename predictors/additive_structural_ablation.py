#!/usr/bin/env python3
"""Structural-additive LLM prefill predictor ablation (ARCHIVE-ONLY).

Roadmap IDEA (progress/thesis-roadmap.md, "structural-additive LLM predictor
ablation"): the LLM prefill demand (context-token rate, `ctx`) is currently
forecast DIRECTLY. Hypothesis: decompose ctx as a text-borne component
(a * requests) plus an image-driven component (b * images), because the
vision-borne part has higher persistence (Hurst ~0.87 vs ~0.76) and prefill
regime shifts are vision-driven, so an ADDITIVE predictor should pay at ONSETS
specifically (not pooled averages, which Ch4's covariate-null already covers).

This script is ARCHIVE-ONLY: no GPU, no simulation. It

  1. fits the linear decomposition ctx ~ a*requests + b*images (+intercept) on
     the REALIZED rate series -> reports R^2, coefficients, and the fraction of
     ctx that the image term explains (the "how image-driven is ctx" number);
  2. reconstructs an ADDITIVE ctx forecast path from the ARCHIVED `requests` and
     `images` point-forecast paths (ctx_hat = a*req_hat + b*img_hat + c);
  3. scores that against the ARCHIVED DIRECT `ctx` point-forecast path, in WAPE,
     pooled over the common forecast span AND onset-conditioned (burst windows +
     a data-driven steep-image-rise detector).

WAPE convention matches predictors/precision.py: sum|yhat - y| / sum|y|.
Stitching: benchmark.py grid_origins uses stride-H origins so every step is
covered exactly once across the h=1..12 horizons -> the "stitched rolling-origin
path" is simply every archive row (one per step). We verify that invariant.

Output: JSON to results/metrics/additive_structural_ablation.json + a printed
digest. HONEST: if the image term is a small fraction of ctx, or additive does
not beat direct even at onsets, that is the reported finding.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
RESULTS = ROOT / "predictors" / "results"
SERIES_DIR = ROOT / "analysis" / "trace_eda" / "series"
WINDOWS_JSON = ROOT / "simulation" / "windows.json"
OUT = ROOT / "predictors" / "results" / "metrics" / "additive_structural_ablation.json"

MODELS = ["chronos", "toto"]
RESOLUTIONS = ["1min", "15s"]
RES_SECONDS = {"1min": 60.0, "15s": 15.0}


# ----------------------------------------------------------------------------- helpers
def wape(y_true: np.ndarray, y_hat: np.ndarray) -> float:
    denom = np.abs(y_true).sum()
    if denom <= 0:
        return float("nan")
    return float(np.abs(y_hat - y_true).sum() / denom)


def load_series(res: str) -> pd.DataFrame:
    """Realized rate series, index = window_start (datetime64), cols req/img/ctx/gen."""
    df = pd.read_parquet(SERIES_DIR / f"rates_{res}.parquet")
    df.index = pd.to_datetime(df.index)
    return df


def stitched_point(model: str, variate: str, res: str):
    """Return (df, dup_count) for the stitched rolling-origin POINT path of one
    (model, variate, res): columns [step, ts, y_true, point], one row per step."""
    df = pd.read_parquet(
        RESULTS / f"{model}_{variate}.parquet",
        columns=["resolution", "step", "ts", "y_true", "point"],
    )
    df = df[df["resolution"] == res][["step", "ts", "y_true", "point"]].copy()
    # stride-H origins => every step appears exactly once. Verify.
    dup = int(df["step"].duplicated().sum())
    if dup:
        # defensive: keep the first (smallest-h) forecast per step
        df = df.sort_values("step").drop_duplicates("step", keep="first")
    return df.sort_values("step").reset_index(drop=True), dup


def burst_windows_in_span(span_lo: pd.Timestamp, span_hi: pd.Timestamp) -> list[dict]:
    """Parse burst [start..end) windows from windows.json notes; keep those that
    overlap the forecast span. Returns list of dicts with name/start/end/onset."""
    w = json.load(open(WINDOWS_JSON))
    out = []
    for k, v in w.items():
        if not k.startswith("burst"):
            continue
        m = re.search(r"\[(.*?) \.\. (.*?)\)", v["note"])
        onset = re.search(r"onset (\d+) min", v["note"])
        if not m:
            continue
        start = pd.Timestamp(m.group(1))
        end = pd.Timestamp(m.group(2))
        if end <= span_lo or start >= span_hi:
            continue  # no overlap with forecast span
        out.append(
            {
                "name": k,
                "start": max(start, span_lo),
                "end": min(end, span_hi),
                "onset_min": int(onset.group(1)) if onset else None,
            }
        )
    return out


# ----------------------------------------------------------------------------- main
def main() -> None:
    report: dict = {
        "what": "structural-additive LLM prefill (ctx) predictor ablation, archive-only",
        "wape_def": "sum|yhat - y| / sum|y| (matches predictors/precision.py)",
        "decomposition": {},
        "scores": [],
        "notes": [
            "ContextTokens already includes text AND image tokens (converter "
            "trace_to_two_pool.py L27); the linear b*images term is a surrogate "
            "for a non-constant, saturating per-image increment (~277 tokens/img "
            "at 1 image, ~66 at 529 per tex/trace-eda.tex).",
        ],
    }

    # --- Step 1: fit ctx ~ a*requests + b*images (+ intercept) on realized series ---
    for res in RESOLUTIONS:
        s = load_series(res)
        X = np.column_stack([np.ones(len(s)), s["requests"].to_numpy(float), s["images"].to_numpy(float)])
        y = s["ctx"].to_numpy(float)
        coef, *_ = np.linalg.lstsq(X, y, rcond=None)
        c0, a, b = coef
        yhat = X @ coef
        ss_res = float(((y - yhat) ** 2).sum())
        ss_tot = float(((y - y.mean()) ** 2).sum())
        r2 = 1.0 - ss_res / ss_tot
        img_mass = float((b * s["images"].to_numpy(float)).sum() / y.sum())
        txt_mass = float((a * s["requests"].to_numpy(float)).sum() / y.sum())
        int_mass = float((c0 * len(s)) / y.sum())
        report["decomposition"][res] = {
            "fit_span": "full_series",
            "n": int(len(s)),
            "intercept_c": float(c0),
            "a_text_ctx_per_request": float(a),
            "b_ctx_per_image": float(b),
            "R2": float(r2),
            "ctx_mass_fraction": {
                "text_a_req": txt_mass,
                "image_b_img": img_mass,
                "intercept": int_mass,
            },
            "mean_ctx": float(y.mean()),
            "mean_images": float(s["images"].mean()),
            "mean_requests": float(s["requests"].mean()),
        }

    # --- Steps 2-3: build additive vs direct ctx forecast, score pooled + onset ---
    for res in RESOLUTIONS:
        d = report["decomposition"][res]
        c0, a, b = d["intercept_c"], d["a_text_ctx_per_request"], d["b_ctx_per_image"]

        for model in MODELS:
            ctx_p, dup_c = stitched_point(model, "ctx", res)
            req_p, dup_r = stitched_point(model, "requests", res)
            img_p, dup_i = stitched_point(model, "images", res)

            m = ctx_p.merge(req_p[["step", "point"]].rename(columns={"point": "req_hat"}), on="step")
            m = m.merge(img_p[["step", "point"]].rename(columns={"point": "img_hat"}), on="step")
            m = m.rename(columns={"point": "ctx_direct", "y_true": "ctx_true"})
            m = m.sort_values("step").reset_index(drop=True)
            m["ts"] = pd.to_datetime(m["ts"])
            m["ctx_add"] = np.clip(c0 + a * m["req_hat"] + b * m["img_hat"], 0, None)

            span_lo, span_hi = m["ts"].min(), m["ts"].max()

            bwins = burst_windows_in_span(span_lo, span_hi)
            burst_mask = np.zeros(len(m), dtype=bool)
            for bw in bwins:
                burst_mask |= (m["ts"] >= bw["start"]).to_numpy() & (m["ts"] < bw["end"]).to_numpy()

            onset_ramp_mask = np.zeros(len(m), dtype=bool)
            for bw in bwins:
                if bw["onset_min"] is None:
                    continue
                ramp_end = min(bw["start"] + pd.Timedelta(minutes=bw["onset_min"] + 30), bw["end"])
                onset_ramp_mask |= (m["ts"] >= bw["start"]).to_numpy() & (m["ts"] < ramp_end).to_numpy()

            # data-driven steep-image-rise detector on REALIZED images rate
            img_true = img_p.set_index("step")["y_true"].reindex(m["step"]).to_numpy()
            win = max(1, int(round(300 / RES_SECONDS[res])))
            fwd = np.zeros(len(m))
            if len(m) > win:
                fwd[: len(m) - win] = img_true[win:] - img_true[: len(m) - win]
            pos = fwd[fwd > 0]
            thr = float(np.percentile(pos, 90)) if pos.size else float("inf")
            rise_mask = fwd >= thr

            def score_subset(mask: np.ndarray) -> dict:
                sub = m[mask]
                n = int(mask.sum())
                if n == 0:
                    return {"n": 0, "wape_direct": None, "wape_additive": None, "delta_pp": None}
                wd = wape(sub["ctx_true"].to_numpy(float), sub["ctx_direct"].to_numpy(float))
                wa = wape(sub["ctx_true"].to_numpy(float), sub["ctx_add"].to_numpy(float))
                return {
                    "n": n,
                    "wape_direct": wd,
                    "wape_additive": wa,
                    "delta_pp": (wa - wd) * 100,  # additive minus direct; <0 => additive better
                }

            entry = {
                "model": model,
                "resolution": res,
                "span": [str(span_lo), str(span_hi)],
                "n_steps": int(len(m)),
                "dup_steps": {"ctx": dup_c, "requests": dup_r, "images": dup_i},
                "burst_windows_in_span": [bw["name"] for bw in bwins],
                "image_rise_threshold": thr,
                "pooled": score_subset(np.ones(len(m), dtype=bool)),
                "onset_burst_windows": score_subset(burst_mask),
                "onset_ramp": score_subset(onset_ramp_mask),
                "onset_steep_image_rise": score_subset(rise_mask),
            }
            report["scores"].append(entry)

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(report, indent=2, default=str))

    # ---- printed digest ----
    print("=" * 82)
    print("DECOMPOSITION  ctx ~ a*requests + b*images + c   (realized series, full)")
    print("=" * 82)
    for res, d in report["decomposition"].items():
        print(
            f"[{res}] R2={d['R2']:.4f}  a(text/req)={d['a_text_ctx_per_request']:.1f}  "
            f"b(ctx/img)={d['b_ctx_per_image']:.1f}  c={d['intercept_c']:.0f}"
        )
        cm = d["ctx_mass_fraction"]
        print(
            f"       ctx mass: text={cm['text_a_req']*100:.1f}%  image={cm['image_b_img']*100:.1f}%  "
            f"intercept={cm['intercept']*100:.1f}%"
        )
    print()
    print("=" * 82)
    print("WAPE (%)  direct-ctx vs additive-ctx  (delta_pp = additive - direct; <0 = additive wins)")
    print("=" * 82)
    hdr = f"{'model':7} {'res':5} {'subset':24} {'n':>6} {'direct':>8} {'add':>8} {'delta_pp':>9}"
    print(hdr)
    print("-" * len(hdr))
    for e in report["scores"]:
        for sk in ["pooled", "onset_burst_windows", "onset_ramp", "onset_steep_image_rise"]:
            sc = e[sk]
            if sc["n"] == 0:
                print(f"{e['model']:7} {e['resolution']:5} {sk:24} {0:>6} {'-':>8} {'-':>8} {'-':>9}")
                continue
            print(
                f"{e['model']:7} {e['resolution']:5} {sk:24} {sc['n']:>6} "
                f"{sc['wape_direct']*100:>8.2f} {sc['wape_additive']*100:>8.2f} {sc['delta_pp']:>+9.2f}"
            )
    print()
    print(f"wrote {OUT}")


if __name__ == "__main__":
    main()
