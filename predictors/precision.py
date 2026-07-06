#!/usr/bin/env python
"""Precision analysis of the rolling-origin forecast benchmark (benchmark.py).

Scans results/parts/{model}/{mode}_{res}_*.parquet and keeps only COMPLETE
(model, mode) combos — for every resolution the part rows must equal
len(grid_origins(n_res, ctx)) * len(VARIATES) * H, i.e. the model's whole
origin grid. Incomplete combos (e.g. a model mid-run) are skipped with a note,
so this is safe to re-run at any time; parts are only read, never written.

Every forecast candidate column is scored against y_true: the point forecast
plus each quantile head taken as a point forecast (point, p10..p90). Quantiles
clip at 0 and y_true >= 0, so a percentile can legitimately beat the point
head on absolute error — "the most accurate percentile" is reported per cell.

Metrics per (model, mode, span, resolution, variate, candidate):
  metrics_h1.parquet       h == 1 only:           MAE, RMSE, WAPE
  metrics_overall.parquet  pooled over h = 1..12: MAE, RMSE, WAPE
  metrics_by_h.parquet     per h (adds h column): MAE, WAPE
  summary.md               common-span ranking per (resolution, variate),
                           best-percentile analysis, findings paragraph
WAPE = sum|yhat - y| / sum|y|.

Spans (every output row is labelled):
  common  origin >= 8076 (the chronos grid start; all models sit on the same
          multiples-of-12 grid, so every model predicts exactly these steps) —
          ALL cross-model comparison uses this span.
  full    every origin the model produced (per-model secondary view; for
          chronos full == common by construction).

Usage:
  /home/gio/tese/eda/.venv/bin/python precision.py             # all models
  /home/gio/tese/eda/.venv/bin/python precision.py --models chronos toto
"""

from __future__ import annotations

import argparse
import math
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq

sys.path.insert(0, str(Path(__file__).resolve().parent))

from benchmark import H, MODELS, QCOLS, RESOLUTIONS, VARIATES, grid_origins, load_series  # noqa: E402

RESULTS_DIR = Path(__file__).resolve().parent / "results"
PARTS_DIR = RESULTS_DIR / "parts"
METRICS_DIR = RESULTS_DIR / "metrics"

CANDIDATES = ["point", *QCOLS]
READ_COLS = ["resolution", "variate", "origin", "h", "y_true", *CANDIDATES]
#: First origin of the tightest-context model (chronos → 8076). Every model's
#: grid starts at ceil(ctx/H)*H and strides H, so origins >= COMMON_FIRST are
#: forecast by every model at every resolution.
COMMON_FIRST = max(-(-cfg["ctx"] // H) * H for cfg in MODELS.values())
CELL_KEYS = ["model", "mode", "resolution", "variate"]


def _modes(model: str) -> list[str]:
    return ["uni"] + (["cov"] if MODELS[model].get("cov") else [])


def discover(models: list[str]) -> tuple[list[tuple[str, str, list[Path]]], list[str]]:
    """-> ([(model, mode, part_paths)] for complete combos, [skip notes])."""
    included, skipped = [], []
    for model in models:
        for mode in _modes(model):
            paths: list[Path] = []
            gaps = []
            for res in RESOLUTIONS:
                res_paths = sorted((PARTS_DIR / model).glob(f"{mode}_{res}_*.parquet"))
                got = sum(pq.read_metadata(p).num_rows for p in res_paths)
                want = len(grid_origins(len(load_series(res)[1]), MODELS[model]["ctx"])) * len(VARIATES) * H
                if got != want:
                    gaps.append(f"{res}:{got}/{want}")
                paths += res_paths
            if gaps:
                skipped.append(f"{model}/{mode} incomplete ({', '.join(gaps)})")
            else:
                included.append((model, mode, paths))
    return included, skipped


def read_combo(paths: list[Path]) -> pd.DataFrame:
    return pa.concat_tables([pq.read_table(p, columns=READ_COLS) for p in paths]).to_pandas()


def per_h_sums(df: pd.DataFrame) -> pd.DataFrame:
    """One vectorized groupby: per (resolution, variate, h) error sums for every
    candidate — n, sum|y|, and sum|e| / sum e² per candidate (float64)."""
    y = df["y_true"].to_numpy(dtype=np.float64)
    cols: dict = {
        "resolution": pd.Categorical(df["resolution"], categories=list(RESOLUTIONS)),
        "variate": pd.Categorical(df["variate"], categories=list(VARIATES)),
        "h": df["h"].to_numpy(),
        "ay": np.abs(y),
    }
    for c in CANDIDATES:
        e = df[c].to_numpy(dtype=np.float64) - y
        cols[f"ae_{c}"] = np.abs(e)
        cols[f"se_{c}"] = e * e
    g = pd.DataFrame(cols).groupby(["resolution", "variate", "h"], observed=True, sort=True)
    sums = g.sum()
    sums["n"] = g.size()
    return sums.reset_index()


def metric_frames(
    per_h: pd.DataFrame, model: str, mode: str, span: str
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """per-h sums -> (h1, overall, by_h) long metric frames for one combo+span."""
    val_cols = ["n", "ay"] + [f"ae_{c}" for c in CANDIDATES] + [f"se_{c}" for c in CANDIDATES]
    overall = per_h.groupby(["resolution", "variate"], observed=True, sort=True)[val_cols].sum().reset_index()
    h1 = per_h[per_h["h"] == 1].reset_index(drop=True)

    def rows(src: pd.DataFrame, with_h: bool, with_rmse: bool) -> pd.DataFrame:
        out = []
        for c in CANDIDATES:
            d = pd.DataFrame(
                {
                    "model": model,
                    "mode": mode,
                    "span": span,
                    "resolution": src["resolution"].astype(str),
                    "variate": src["variate"].astype(str),
                    "candidate": c,
                }
            )
            if with_h:
                d["h"] = src["h"].to_numpy(dtype=np.int8)
            d["mae"] = (src[f"ae_{c}"] / src["n"]).to_numpy()
            if with_rmse:
                d["rmse"] = np.sqrt(src[f"se_{c}"] / src["n"]).to_numpy()
            d["wape"] = (src[f"ae_{c}"] / src["ay"]).to_numpy()
            out.append(d)
        return pd.concat(out, ignore_index=True)

    return rows(h1, False, True), rows(overall, False, True), rows(per_h, True, False)


def _ordered(df: pd.DataFrame, by_h: bool = False) -> pd.DataFrame:
    d = df.copy()
    d["resolution"] = pd.Categorical(d["resolution"], list(RESOLUTIONS))
    d["variate"] = pd.Categorical(d["variate"], list(VARIATES))
    d["candidate"] = pd.Categorical(d["candidate"], CANDIDATES)
    keys = ["model", "mode", "span", "resolution", "variate", "candidate"] + (["h"] if by_h else [])
    d = d.sort_values(keys, ignore_index=True)
    for c in ("resolution", "variate", "candidate"):
        d[c] = d[c].astype(str)
    return d


def best_pct(metrics: pd.DataFrame) -> pd.DataFrame:
    """Per cell: the p10..p90 candidate with lowest MAE, joined with the point
    forecast's MAE and the relative delta (negative = percentile better)."""
    q = metrics[metrics["candidate"] != "point"]
    best = q.loc[q.groupby(CELL_KEYS)["mae"].idxmin()].set_index(CELL_KEYS)
    pt = metrics[metrics["candidate"] == "point"].set_index(CELL_KEYS)
    best = best.assign(point_mae=pt["mae"], delta_pct=100.0 * (best["mae"] / pt["mae"] - 1.0))
    return best


def _fmt(x: float) -> str:
    if not np.isfinite(x) or x == 0:
        return f"{x:g}"
    if 0.01 <= abs(x) < 1e6:
        return f"{x:,.{max(0, 3 - int(math.floor(math.log10(abs(x)))))}f}"
    return f"{x:.3g}"


def compute_findings(h1: pd.DataFrame, overall: pd.DataFrame, included: list) -> dict:
    """Common-span facts reused by summary.md and the printed digest."""
    c_over = overall[overall["span"] == "common"]
    c_h1 = h1[h1["span"] == "common"]
    over_pt = c_over[c_over["candidate"] == "point"]
    f: dict = {
        "over_pt": over_pt,
        "h1_pt": c_h1[c_h1["candidate"] == "point"].set_index(CELL_KEYS),
        "best_over": best_pct(c_over),
        "best_h1": best_pct(c_h1),
    }
    # 1) which model/mode wins each (resolution, variate) cell on overall point MAE
    f["winners"] = over_pt.loc[over_pt.groupby(["resolution", "variate"])["mae"].idxmin()]
    f["win_counts"] = f["winners"].groupby(["model", "mode"]).size().sort_values(ascending=False)
    # 2) covariates: uni vs cov for models that completed both
    have = {(m, mo) for m, mo, _ in included}
    f["cov_effect"] = {}
    for model in sorted({m for m, mo in have if mo == "cov" and (m, "uni") in have}):
        piv = over_pt[over_pt["model"] == model].pivot_table(
            index=["resolution", "variate"], columns="mode", values="mae"
        )
        rel = 100.0 * (piv["cov"] / piv["uni"] - 1.0)
        f["cov_effect"][model] = (rel.mean(), int((rel < 0).sum()), len(rel))
    # 3) best-percentile pattern
    b = f["best_over"].reset_index()
    beats = b[b["delta_pct"] < 0]
    lv = beats["candidate"].str[1:].astype(int)
    f["pct"] = dict(
        n=len(b),
        n_beat=len(beats),
        modal=beats["candidate"].mode().iat[0] if len(beats) else "-",
        below=int((lv < 50).sum()),
        at=int((lv == 50).sum()),
        above=int((lv > 50).sum()),
        median_impr=beats["delta_pct"].median() if len(beats) else float("nan"),
    )
    return f


def write_summary(f: dict, included: list, skipped: list[str], path: Path) -> None:
    over_pt, h1_pt = f["over_pt"], f["h1_pt"]
    best_over, best_h1 = f["best_over"], f["best_h1"]
    md = [
        "# Forecast precision summary",
        "",
        f"Generated {time.strftime('%Y-%m-%d %H:%M:%S')} by precision.py.",
        f"All tables below use the **common span** (origin >= {COMMON_FIRST} — the steps every "
        "model forecasts; per-model full-span metrics are in the parquet files with `span='full'`). "
        "Rows are ranked by point-forecast overall MAE (pooled over h=1..12). "
        "`best pct` = the p10..p90 quantile head with lowest MAE when used as a point forecast "
        "(delta vs the point forecast in parentheses; negative = percentile better).",
        "",
        "Included: " + ", ".join(f"{m}/{mo}" for m, mo, _ in included) + ".",
        ("Skipped (incomplete, re-run later): " + "; ".join(skipped) + ".") if skipped else "Skipped: none.",
    ]
    for res in RESOLUTIONS:
        md.append(f"\n## {res}")
        for var in VARIATES:
            rows = over_pt[(over_pt["resolution"] == res) & (over_pt["variate"] == var)].sort_values("mae")
            md += [
                f"\n### {res} / {var}",
                "",
                "| # | model | mode | h1 MAE | overall MAE | overall WAPE | best pct overall (MAE / WAPE, Δ vs point) | best pct h=1 (MAE, Δ) |",
                "|--:|:--|:--|--:|--:|--:|:--|:--|",
            ]
            for i, r in enumerate(rows.itertuples(), 1):
                key = (r.model, r.mode, res, var)
                bo, bh = best_over.loc[key], best_h1.loc[key]
                md.append(
                    f"| {i} | {r.model} | {r.mode} | {_fmt(h1_pt.loc[key, 'mae'])} | {_fmt(r.mae)} "
                    f"| {r.wape:.3f} | {bo['candidate']}: {_fmt(bo['mae'])} / {bo['wape']:.3f} ({bo['delta_pct']:+.1f}%) "
                    f"| {bh['candidate']}: {_fmt(bh['mae'])} ({bh['delta_pct']:+.1f}%) |"
                )
    # findings
    md.append("\n## Findings (common span)\n")
    md += ["Winner per cell (overall point MAE):", "", "| resolution | " + " | ".join(VARIATES) + " |",
           "|:--|" + ":--|" * len(VARIATES)]
    win_ix = f["winners"].set_index(["resolution", "variate"])
    for res in RESOLUTIONS:
        cells = [f"{win_ix.loc[(res, v), 'model']}/{win_ix.loc[(res, v), 'mode']}" for v in VARIATES]
        md.append(f"| {res} | " + " | ".join(cells) + " |")
    wc = ", ".join(f"{m}/{mo}: {n}" for (m, mo), n in f["win_counts"].items())
    n_cells = len(f["winners"])
    md.append(f"\nWin counts over the {n_cells} (resolution, variate) cells — {wc}.")
    for model, (mean_rel, n_better, n) in f["cov_effect"].items():
        verb = "helps" if mean_rel < -0.5 else ("hurts" if mean_rel > 0.5 else "is roughly neutral")
        md.append(
            f"\nCovariates ({model}): cov vs uni changes overall point MAE by {mean_rel:+.1f}% on average "
            f"and improves {n_better}/{n} cells — covariate conditioning {verb} overall."
        )
    missing_cov = [m for m in MODELS if MODELS[m].get("cov") and m not in f["cov_effect"]]
    if missing_cov:
        md.append(f"\nCovariate comparison pending for: {', '.join(missing_cov)} (incomplete runs).")
    p = f["pct"]
    md.append(
        f"\nBest percentile: a quantile head beats the point forecast in {p['n_beat']}/{p['n']} "
        f"(model, mode, resolution, variate) cells (median improvement {p['median_impr']:.1f}%); "
        f"modal winner {p['modal']}; winners below/at/above the median: {p['below']}/{p['at']}/{p['above']}."
    )
    if p["below"] > max(p["above"], p["at"]):
        md.append(
            "The winning quantiles sit **below the median**: these rate series are bursty and "
            "right-skewed (many quiet bins, few large spikes), so a deliberately low forecast tracks "
            "the typical bin and sheds the penalty a spike-inflated point forecast pays on quiet bins "
            "— at the price of never anticipating bursts."
        )
    elif p["above"] > max(p["below"], p["at"]):
        md.append(
            "The winning quantiles sit **above the median**: absolute error is dominated by "
            "under-forecast bursts, so an optimistic quantile pays on these bursty rate series."
        )
    else:
        md.append(
            "Winning quantiles cluster **at the median (p50)** — consistent with MAE being minimized "
            "at the conditional median; the point head behaves like a mean and overshoots on bursty data."
        )
    path.write_text("\n".join(md) + "\n")


def print_digest(f: dict, included: list, skipped: list[str]) -> None:
    print("\n=== DIGEST ===")
    print("included:", ", ".join(f"{m}/{mo}" for m, mo, _ in included))
    print("skipped:", "; ".join(skipped) if skipped else "none")
    over_pt = f["over_pt"]
    for res in ("1min", "1s"):
        for var in VARIATES:
            top = over_pt[(over_pt["resolution"] == res) & (over_pt["variate"] == var)].nsmallest(3, "mae")
            ranked = " | ".join(f"{r.model}/{r.mode} {_fmt(r.mae)}" for r in top.itertuples())
            print(f"top3 {res:>4} {var:<8}: {ranked}")
    p = f["pct"]
    print(
        f"best-pct: beats point in {p['n_beat']}/{p['n']} cells (median {p['median_impr']:+.1f}%), "
        f"modal {p['modal']}, below/at/above p50 = {p['below']}/{p['at']}/{p['above']}"
    )
    for model, (mean_rel, n_better, n) in f["cov_effect"].items():
        print(f"covariates {model}: cov vs uni {mean_rel:+.1f}% mean ΔMAE, better in {n_better}/{n} cells")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n", 1)[0])
    ap.add_argument("--models", nargs="+", default=list(MODELS), choices=list(MODELS))
    args = ap.parse_args()

    included, skipped = discover(args.models)
    for note in skipped:
        print(f"[skip] {note}")
    if not included:
        print("no complete (model, mode) combos found — nothing to do")
        return

    h1_parts, over_parts, byh_parts = [], [], []
    for model, mode, paths in included:
        t0 = time.time()
        df = read_combo(paths)
        for span in ("common", "full"):
            sub = df[df["origin"] >= COMMON_FIRST] if span == "common" else df
            f1, fo, fh = metric_frames(per_h_sums(sub), model, mode, span)
            h1_parts.append(f1)
            over_parts.append(fo)
            byh_parts.append(fh)
        print(f"[scored] {model}/{mode}: {len(df):,} rows in {time.time() - t0:.1f}s")
        del df

    h1 = _ordered(pd.concat(h1_parts, ignore_index=True))
    overall = _ordered(pd.concat(over_parts, ignore_index=True))
    by_h = _ordered(pd.concat(byh_parts, ignore_index=True), by_h=True)

    METRICS_DIR.mkdir(parents=True, exist_ok=True)
    for name, frame in [("metrics_h1", h1), ("metrics_overall", overall), ("metrics_by_h", by_h)]:
        out = METRICS_DIR / f"{name}.parquet"
        pq.write_table(pa.Table.from_pandas(frame, preserve_index=False), out)
        print(f"[write] {out} ({len(frame):,} rows)")

    f = compute_findings(h1, overall, included)
    write_summary(f, included, skipped, METRICS_DIR / "summary.md")
    print(f"[write] {METRICS_DIR / 'summary.md'}")
    print_digest(f, included, skipped)


if __name__ == "__main__":
    main()
