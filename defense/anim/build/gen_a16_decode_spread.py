#!/usr/bin/env python3
"""A16 — Decode-series upper-bound audit ("how loose is the arrival stamp?").

THE GAP (tex/intro.tex Scope, trace-eda)
----------------------------------------
The thesis forecasts four demand signals (requests / images / ctx / gen) that
are materialized by `analysis/trace_eda/n_materialize_series.py` as

    gen[bin] = sum of GeneratedTokens of every request whose ARRIVAL falls in bin

i.e. a request's *entire* generated-token volume is stamped at the minute it
arrived.  That is faithful for encoder and prefill work (both happen at
admission) but decode does NOT happen at arrival: it spreads over the
request's generation lifetime.  The thesis therefore calls the decode series
an "offered-work UPPER BOUND" without ever saying how loose the bound is.

WHAT THIS SCRIPT DOES
---------------------
It reconstructs the TRUE temporal decode demand from the per-request records
produced by the discrete-event mocker (the `--report-jsonl` patch, dynamo
70c965db26).  Each record carries

    arrival_time_ms, first_token_ms, last_token_ms, itl_ms, output_length

so the request's real decode occupancy is the interval

    [first_token_ms, last_token_ms + itl_ms)      (width = output_length*itl)

over which `output_length` tokens are emitted at a constant rate 1/itl.
Spreading every request's mass over its own interval and re-binning gives
D_true(t) — the decode tokens actually *emitted* in bin t.  Three series are
built on the identical bin grid:

  arr_trace   mass stamped at the RAW TRACE arrival second   <- the series the
              thesis actually forecasts (rates_*.parquet `gen`)
  arr_comp    mass stamped at the COMPOSED arrival second (encoder delay folded
              in) -- isolates the decode-spread effect from the encoder shift
  spread      mass spread over the true generation interval  <- ground truth

and every comparison is reported at 1s / 15s / 30s / 60s bins (15s is the
planner's FORECAST_RESOLUTION; 1min is the EDA/forecast-archive grid).

METHODOLOGY NOTES
-----------------
* Nothing is simulated here.  This is a pure re-binning of already-ledgered
  per-request records; no forecast is computed, no replay is run.
* Spreading only *moves* mass in time, so every difference reported is a purely
  TEMPORAL displacement and the totals agree to float precision on the 1-s grid.
  (The coarser grids used to lose a ragged tail of up to 59 one-second bins in
  rebin(); the horizon is now padded to a whole minute so 1/15/30/60 all divide
  evenly and mass_conservation_rel_err is ~machine zero at every resolution.)
* CONSTANT-RATE ASSUMPTION.  `itl_ms` is the request's MEAN inter-token latency,
  so each request's mass is spread at a uniform rate 1/itl across its window.
  Real per-token spacing varies with batch occupancy, so the D_true built here
  is itself SMOOTHED relative to the true instant-by-instant decode rate.
  Direction matters: smoothing flattens D_true's peaks, which INFLATES any
  peak-overstatement figure — i.e. this assumption biases the analysis TOWARD
  the "the arrival stamp is conservative" conclusion.  The verdict is therefore
  read off the mass-weighted busiest-1% signed bias, which is far less
  sensitive to within-window shape than a ratio of maxima.
* The generation interval measured by the mocker already contains whatever
  queueing/batching slowdown the policy caused, so decode duration is
  policy-dependent.  BOTH arms are therefore run and reported, because the two
  questions point in opposite directions:
    - "how LOOSE is the bound?"  -> ft_llm_static (2 fixed TP2 replicas, least
      congested) is the conservative arm: shorter windows => less spreading =>
      a *smaller* measured gap.  Congested arms only widen it.
    - "is the bound ever VIOLATED?" -> static is ANTI-conservative for this
      question.  The congested reactive arm is short at the very top tiers
      (+3.63% at top-0.1% of bins) where static is not (-0.08%), so any
      violation claim must be read off the CONGESTED arm, not the default one.

OUTPUTS (all NEW files, nothing existing is touched)
----------------------------------------------------
  <out>/a16_stats.json          every number quoted below, machine readable
  <out>/a16_series_60s.csv      arr_primary, arr_comp, spread @ 1min
  <out>/a16_series_15s.csv      arr_primary, arr_comp, spread @ 15s
  <out>/a16_series_1s.csv.gz    ditto @ 1s   (so the 1-s JSON block is checkable)
  <out>/a16_series_30s.csv.gz   ditto @ 30s  (so the 30-s JSON block is checkable)
  <out>/a16_decode_spread.png   4-panel figure (week, worst onset, ratio CDF,
                                replica-count disagreement)
  <out>/a16_summary.txt         the printed verdict

USAGE
-----
  python3 defense/anim/build/gen_a16_decode_spread.py                  # full, default arm
  python3 defense/anim/build/gen_a16_decode_spread.py --max-requests 2000   # smoke
  python3 defense/anim/build/gen_a16_decode_spread.py --records <f> --tag <name>
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

import numpy as np

try:
    import orjson as _fastjson

    def _loads(b):
        return _fastjson.loads(b)
except ImportError:  # pragma: no cover
    def _loads(b):
        return json.loads(b)

ROOT = Path("/home/gio/tese")
TRACE = ROOT / "data/AzureLMMInferenceTrace_multimodal.csv.gz"
DEFAULT_RECORDS = ROOT / "defense/anim/data/a13_runs/ft_llm_static.requests.jsonl"
DEFAULT_OUT = ROOT / "defense/anim/data/a16_decode_spread"
THESIS_SERIES = ROOT / "analysis/trace_eda/series"
PLANNER_CFG = ROOT / "simulation/planner_forecast_smoke.json"

RESOLUTIONS = [1, 15, 30, 60]  # seconds per bin
# Per-replica decode capacity sweep (generated tokens/s sustained by one TP2
# replica).  Used only to translate a demand series into a replica count; the
# conclusion is reported across the whole sweep so it never rests on one value.
CAP_SWEEP = [200.0, 400.0, 800.0, 1600.0, 3200.0]
# positional trace join is accepted only above this per-column match fraction
MIN_MATCH = 0.99


# --------------------------------------------------------------------------- #
# record ingest
# --------------------------------------------------------------------------- #
def read_records(path: Path, limit: int | None) -> dict[str, np.ndarray]:
    """Stream the per-request jsonl into flat arrays, preserving FILE ORDER.

    Two record flavours exist:
      * planner path (a15) -- session_id "request_<n>", n 1-based within the run
        window;
      * non-planner path (a13 ft_llm_static) -- session_id is null.
    Neither is trusted for the trace join: the join is done positionally and
    then VERIFIED against ContextTokens/GeneratedTokens (see verify_trace_join).
    """
    arr, ft, lt, itl, out, inp = [], [], [], [], [], []
    with open(path, "rb") as fh:
        for n, line in enumerate(fh):
            if limit is not None and n >= limit:
                break
            r = _loads(line)
            arr.append(r["arrival_time_ms"])
            ft.append(r["first_token_ms"])
            lt.append(r["last_token_ms"])
            itl.append(r["itl_ms"] if r["itl_ms"] is not None else 0.0)
            out.append(r["output_length"])
            inp.append(r["input_length"])
    return dict(
        arrival_ms=np.asarray(arr, dtype=np.float64),
        first_ms=np.asarray(ft, dtype=np.float64),
        last_ms=np.asarray(lt, dtype=np.float64),
        itl_ms=np.asarray(itl, dtype=np.float64),
        gen=np.asarray(out, dtype=np.float64),
        inp=np.asarray(inp, dtype=np.float64),
    )


def read_trace_rows(offset: int, count: int) -> dict[str, np.ndarray]:
    """RAW trace arrival offsets (ms from the FLOORED trace t0, the grid
    `n_materialize_series.py` bins on) + ContextTokens/GeneratedTokens."""
    import pandas as pd

    df = pd.read_csv(TRACE, nrows=offset + count,
                     usecols=["TIMESTAMP", "ContextTokens", "GeneratedTokens"])
    ts = pd.to_datetime(df["TIMESTAMP"], format="ISO8601", utc=True)
    t0f = ts.iloc[0].floor("s")  # bin 0 starts at floor(t0), not at t0
    off_ms = (ts - t0f).dt.total_seconds().to_numpy() * 1000.0
    return dict(
        arrival_ms=off_ms[offset:offset + count],
        ctx=df["ContextTokens"].to_numpy(dtype=np.float64)[offset:offset + count],
        gen=df["GeneratedTokens"].to_numpy(dtype=np.float64)[offset:offset + count],
    )


def verify_trace_join(rec: dict, tr: dict) -> dict:
    """Establish that the record stream and the trace slice are THE SAME SET of
    requests.

    No per-row join is needed anywhere in this analysis: the raw-trace arrival
    series is built from the trace alone and the true-decode series from the
    records alone, then the two aggregate series are compared.  What must hold
    for that comparison to be meaningful is set identity, so that is what is
    checked — as a sorted-multiset equality on both token columns.  (The mocker
    emits records in completion order, which is a local permutation of arrival
    order, so a positional row-by-row match would spuriously fail.)
    """
    n = min(len(rec["gen"]), len(tr["gen"]))
    ctx_ok = float((np.sort(rec["inp"][:n]) == np.sort(tr["ctx"][:n])).mean())
    gen_ok = float((np.sort(rec["gen"][:n]) == np.sort(tr["gen"][:n])).mean())
    pos_ok = float((rec["gen"][:n] == tr["gen"][:n]).mean())
    return {"n_compared": int(n),
            "ctx_multiset_match_frac": ctx_ok,
            "gen_multiset_match_frac": gen_ok,
            "gen_positional_match_frac": pos_ok,
            "gen_total_rel_err": abs(float(rec["gen"][:n].sum()) - float(tr["gen"][:n].sum()))
                                 / max(float(tr["gen"][:n].sum()), 1e-12),
            "usable": bool(min(ctx_ok, gen_ok) >= MIN_MATCH)}


# --------------------------------------------------------------------------- #
# binning kernels
# --------------------------------------------------------------------------- #
def stamp_bins(t_ms: np.ndarray, mass: np.ndarray, nbins: int, bin_ms: float) -> np.ndarray:
    """Point-stamp every request's whole mass into the bin containing t_ms."""
    b = np.floor(t_ms / bin_ms).astype(np.int64)
    np.clip(b, 0, nbins - 1, out=b)
    return np.bincount(b, weights=mass, minlength=nbins).astype(np.float64)


def spread_bins(a_ms: np.ndarray, b_ms: np.ndarray, mass: np.ndarray,
                nbins: int, bin_ms: float) -> np.ndarray:
    """Spread each request's mass uniformly over [a_ms, b_ms) onto the bin grid.

    Exact (no sampling): the two partial edge bins get their fractional share
    and the fully-covered interior bins are filled with a cumsum of a rate-
    difference array, so the result is the true integral of the piecewise-
    constant emission rate over each bin.  Mass is conserved to float precision.
    """
    out = np.zeros(nbins, dtype=np.float64)
    a = a_ms / bin_ms
    b = b_ms / bin_ms
    np.clip(a, 0.0, nbins - 1e-9, out=a)
    np.clip(b, 0.0, nbins - 1e-9, out=b)
    b = np.maximum(b, a)

    ia = np.floor(a).astype(np.int64)
    ib = np.floor(b).astype(np.int64)

    # (1) requests confined to a single bin (incl. zero-width) -> point stamp
    same = ia == ib
    if same.any():
        out += np.bincount(ia[same], weights=mass[same], minlength=nbins)

    m = ~same
    if not m.any():
        return out
    am, bm, iam, ibm = a[m], b[m], ia[m], ib[m]
    rate = mass[m] / (bm - am)  # mass per bin-width

    # (2) leading partial bin and trailing partial bin
    out += np.bincount(iam, weights=rate * (iam + 1.0 - am), minlength=nbins)
    out += np.bincount(ibm, weights=rate * (bm - ibm), minlength=nbins)

    # (3) fully covered interior bins [iam+1, ibm) -- rate each, via diff+cumsum
    interior = ibm > iam + 1
    if interior.any():
        d = np.zeros(nbins + 1, dtype=np.float64)
        d += np.bincount(iam[interior] + 1, weights=rate[interior], minlength=nbins + 1)
        d -= np.bincount(ibm[interior], weights=rate[interior], minlength=nbins + 1)
        out += np.cumsum(d)[:nbins]
    return out


def rebin(x1s: np.ndarray, secs: int) -> np.ndarray:
    """Aggregate a 1-s series into `secs`-wide bins (drop a ragged tail)."""
    if secs == 1:
        return x1s
    n = (len(x1s) // secs) * secs
    return x1s[:n].reshape(-1, secs).sum(axis=1)


# --------------------------------------------------------------------------- #
# metrics
# --------------------------------------------------------------------------- #
def series_stats(x: np.ndarray, bin_s: int) -> dict:
    """Level statistics, reported as tokens/s so resolutions are comparable."""
    r = x / bin_s
    nz = r[r > 0]
    return {
        "total_tokens": float(x.sum()),
        "mean_tok_s": float(r.mean()),
        "p50_tok_s": float(np.percentile(r, 50)),
        "p90_tok_s": float(np.percentile(r, 90)),
        "p99_tok_s": float(np.percentile(r, 99)),
        "p999_tok_s": float(np.percentile(r, 99.9)),
        "max_tok_s": float(r.max()),
        "nonzero_bins": int(nz.size),
    }


def compare(arr: np.ndarray, spread: np.ndarray, bin_s: int) -> dict:
    """Everything that quantifies HOW LOOSE the arrival-stamped bound is."""
    tot = float(spread.sum())
    absdiff = np.abs(arr - spread)
    # Total-variation / earth-mover style headline: the fraction of all decode
    # token mass that the arrival stamp puts in the WRONG bin.
    displaced = 0.5 * float(absdiff.sum()) / tot if tot > 0 else 0.0

    sa, ss = series_stats(arr, bin_s), series_stats(spread, bin_s)
    peak_over = sa["max_tok_s"] / ss["max_tok_s"] if ss["max_tok_s"] > 0 else float("nan")

    # per-bin ratio, restricted to bins that carry real load (>= p50 of spread
    # among nonzero bins) so near-zero bins can't manufacture huge ratios
    live = spread > max(np.percentile(spread[spread > 0], 50) if (spread > 0).any() else 0.0, 1.0)
    ratio = np.where(live, arr / np.maximum(spread, 1e-12), np.nan)
    rl = ratio[live]

    over = arr > spread   # arrival stamp OVERSTATES this bin -> conservative
    under = spread > arr  # arrival stamp UNDERSTATES this bin -> anti-conservative
    over_mass = float((arr - spread)[over].sum())
    under_mass = float((spread - arr)[under].sum())

    # Signed error concentrated where it matters: the busiest 1% of bins.
    # TWO SELECTION CONVENTIONS, both reported, because the headline FLIPS SIGN
    # between them and that flip is the finding:
    #   truth-selected    -- conditions on `spread`, which NO controller can
    #                        observe ex ante.  Regression-to-the-mean pulls the
    #                        stamp below truth on this set.
    #   arrival-selected  -- conditions on `arr`, the series a controller
    #                        actually sees.  This is the provisioning-relevant
    #                        population.
    # SIGN CONVENTION (identical everywhere in this file):
    #   +  =  stamp exceeds truth  =  CONSERVATIVE
    hot_t = spread >= np.percentile(spread, 99)
    hot_a = arr >= np.percentile(arr, 99)
    hot_bias = float((arr[hot_t] - spread[hot_t]).sum() / max(spread[hot_t].sum(), 1e-12))
    hot_bias_a = float((arr[hot_a] - spread[hot_a]).sum() / max(spread[hot_a].sum(), 1e-12))

    # lag: does the true decode series trail the arrival stamp?
    lag = cross_corr_lag(arr, spread, max_lag=max(1, int(round(120 / bin_s))))

    return {
        "bin_s": bin_s,
        "arrival_stamped": sa,
        "true_spread": ss,
        "mass_conservation_rel_err": abs(float(arr.sum()) - tot) / max(tot, 1e-12),
        "displaced_mass_fraction": displaced,
        "peak_overstatement_x": peak_over,
        "p999_overstatement_x": sa["p999_tok_s"] / ss["p999_tok_s"] if ss["p999_tok_s"] > 0 else float("nan"),
        "p99_overstatement_x": sa["p99_tok_s"] / ss["p99_tok_s"] if ss["p99_tok_s"] > 0 else float("nan"),
        "p90_overstatement_x": sa["p90_tok_s"] / ss["p90_tok_s"] if ss["p90_tok_s"] > 0 else float("nan"),
        "bin_ratio": {
            "n_live_bins": int(live.sum()),
            "p10": float(np.percentile(rl, 10)) if rl.size else float("nan"),
            "p50": float(np.percentile(rl, 50)) if rl.size else float("nan"),
            "p90": float(np.percentile(rl, 90)) if rl.size else float("nan"),
            "p99": float(np.percentile(rl, 99)) if rl.size else float("nan"),
            "max": float(rl.max()) if rl.size else float("nan"),
            "frac_bins_overstated": float(over.mean()),
            "frac_bins_understated": float(under.mean()),
        },
        "overstated_mass_frac": over_mass / tot if tot > 0 else 0.0,
        "understated_mass_frac": under_mass / tot if tot > 0 else 0.0,
        "hot_bin_signed_bias": hot_bias,                     # truth-selected top 1%
        "hot_bin_signed_bias_truth_selected": hot_bias,      # explicit alias
        "hot_bin_signed_bias_arrival_selected": hot_bias_a,  # OBSERVABLE selection
        "hot_bin_sign_convention": "+ = stamp exceeds truth = CONSERVATIVE",
        "lag_bins": lag["lag_bins"],
        "lag_seconds": lag["lag_bins"] * bin_s,
        "lag_corr": lag["corr"],
    }


def cross_corr_lag(a: np.ndarray, b: np.ndarray, max_lag: int) -> dict:
    """Lag (in bins) that best aligns `a` shifted forward onto `b`."""
    a0 = a - a.mean()
    b0 = b - b.mean()
    den = math.sqrt(float((a0 * a0).sum()) * float((b0 * b0).sum())) or 1.0
    best, bl = -2.0, 0
    for L in range(0, max_lag + 1):
        c = float((a0[: len(a0) - L] * b0[L:]).sum()) / den if L else float((a0 * b0).sum()) / den
        if c > best:
            best, bl = c, L
    return {"lag_bins": bl, "corr": best}


def onset_analysis(arr: np.ndarray, spread: np.ndarray, bin_s: int, top_frac=0.01) -> dict:
    """Onsets = the steepest positive jumps of the ARRIVAL series (that is what
    the forecaster reacts to).  At an onset the arrival stamp front-loads mass
    that decode has not yet performed, so it should OVERSTATE.  Decays are the
    mirror case and are where an upper bound could turn anti-conservative."""
    d = np.diff(arr, prepend=arr[0])
    k = max(1, int(len(d) * top_frac))
    onset = np.argsort(d)[-k:]
    decay = np.argsort(d)[:k]

    def blk(sel):
        a, s = arr[sel], spread[sel]
        live = s > 1.0
        r = a[live] / s[live] if live.any() else np.array([np.nan])
        sb = float((a.sum() - s.sum()) / max(s.sum(), 1e-12))
        return {
            "n_bins": int(len(sel)),
            # UNWEIGHTED median of per-bin ratios.  Kept as a diagnostic ONLY:
            # this file's own doctrine is that direction-of-bias claims are read
            # off the MASS-WEIGHTED ratio below.  Do not quote ratio_p50.
            "ratio_p50_unweighted_diagnostic": float(np.nanpercentile(r, 50)),
            "ratio_p90_unweighted_diagnostic": float(np.nanpercentile(r, 90)),
            "ratio_max_unweighted_diagnostic": float(np.nanmax(r)),
            # THE load-bearing figure: sum(arr)/sum(spread) over the block.
            "ratio_mass_weighted": 1.0 + sb,
            "signed_bias": sb,
            "mass_frac_of_series": float(a.sum() / max(arr.sum(), 1e-12)),
        }

    # worst single onset bin (largest absolute overstatement)
    err = arr - spread
    w = int(np.argmax(err))
    return {
        "onset_bins": blk(onset),
        "decay_bins": blk(decay),
        "worst_overstated_bin": {
            "bin": w, "t_s": w * bin_s,
            "arrival_tok_s": float(arr[w] / bin_s),
            "true_tok_s": float(spread[w] / bin_s),
            "ratio": float(arr[w] / max(spread[w], 1e-12)),
        },
        "worst_understated_bin": {
            "bin": int(np.argmin(err)), "t_s": int(np.argmin(err)) * bin_s,
            "arrival_tok_s": float(arr[int(np.argmin(err))] / bin_s),
            "true_tok_s": float(spread[int(np.argmin(err))] / bin_s),
            "ratio": float(arr[int(np.argmin(err))] / max(spread[int(np.argmin(err))], 1e-12)),
        },
    }


def hot_tiers(arr: np.ndarray, spread: np.ndarray, bin_s: int,
              select: str = "truth") -> list[dict]:
    """Signed error as a function of HOW BUSY the bin is — the WHOLE tier curve.

    The curve is NOT monotone in busyness, so no single tier characterises the
    series and quoting one tier is a cherry-pick.  All four are always emitted.

    `select` chooses the population:
      "truth"    busiest bins of the TRUE spread series (unobservable ex ante)
      "arrival"  busiest bins of the ARRIVAL-stamped series (what a controller
                 can actually identify).  The headline flips sign between them.

    SIGN CONVENTION, identical to every other block in this file:
        bias_frac  +  =  stamp exceeds truth  =  CONSERVATIVE
    `shortfall_*` are the mirror tail statistics (truth minus stamp, so + =
    the stamp is SHORT); they are named so they cannot be confused with bias.
    """
    ra, rs = arr / bin_s, spread / bin_s
    basis = rs if select == "truth" else ra
    out = []
    for q in (90.0, 99.0, 99.9, 99.99):
        hot = basis >= np.percentile(basis, q)
        if not hot.any():
            continue
        sh = rs[hot] - ra[hot]                       # + = stamp short
        true_sum = float(rs[hot].sum())
        # mass-weighted signed bias; algebraically -shortfall_mean/true_mean
        bias = float((ra[hot].sum() - true_sum) / max(true_sum, 1e-12))
        short_frac_of_bin = sh / np.maximum(rs[hot], 1e-12)
        out.append({
            "selection": select,
            "top_pct": round(100.0 - q, 4),
            "n_bins": int(hot.sum()),
            "true_mean_tok_s": float(rs[hot].mean()),
            "bias_frac": bias,                       # + = CONSERVATIVE
            # --- tail, because a MEAN cannot license a tail claim (D6) ---
            "frac_bins_short": float((sh > 0).mean()),
            "shortfall_mean_tok_s": float(sh.mean()),
            "shortfall_p90_tok_s": float(np.percentile(sh, 90)),
            "shortfall_max_tok_s": float(sh.max()),
            "shortfall_max_frac_of_own_bin": float(short_frac_of_bin.max()),
        })
    return out


def controller_sampled_bias(arr: np.ndarray, spread: np.ndarray, bin_s: int,
                            interval_s: float) -> dict:
    """The population the PROVISIONING CONTROLLER actually reads.

    The planner's throughput adjustment interval is `interval_s`
    (simulation/planner_forecast_smoke.json: throughput_adjustment_interval_seconds),
    and simulation/replay_with_forecast.py:106-119 advances the archived path by
    `round(60/bin_s)` bins per tick — a STRIDE POINT SAMPLE, not an aggregate.
    At 15-s bins that is stride 4: three of every four bins are NEVER read.
    Line 75-76 then rescales the sampled bin by 60/bin_s, i.e. the controller's
    demand model for one control interval is "stride x one sampled bin".

    Two views, both per phase offset (the phase is not controllable):
      sampled_bins  bias over the sampled subpopulation only, at bin resolution
      decision      the controller's actual estimator (stride * sampled bin) vs
                    the TRUE decode mass in that whole control interval
    Both use the busiest 1% (truth-selected) of the relevant population, mass
    weighted, with the file-wide sign convention (+ = stamp exceeds truth).

    CAVEAT recorded in the output: the decode series enters the planner only as
    osl = gen/req (replay_with_forecast.py:138), never as a decode rate, so a
    bin-level decode bias is NOT shown to propagate to a replica decision.
    """
    stride = max(1, int(round(interval_s / bin_s)))
    res: dict = {"planner_interval_s": interval_s, "bin_s": bin_s,
                 "stride": stride,
                 "frac_bins_never_read": 1.0 - 1.0 / stride,
                 "consumed_as": "osl = gen/req ratio, not a decode rate",
                 "sampled_bins": [], "decision": []}
    n_ticks = len(arr) // stride
    if n_ticks < 100:
        return res
    for phase in range(stride):
        a = arr[phase:phase + n_ticks * stride:stride]
        s = spread[phase:phase + n_ticks * stride:stride]
        hot = s >= np.percentile(s, 99)
        res["sampled_bins"].append({
            "phase": phase, "n_bins": int(len(a)),
            "hot_bin_signed_bias": float((a[hot] - s[hot]).sum()
                                         / max(s[hot].sum(), 1e-12)),
        })
        # controller estimator for the control interval: stride * sampled bin
        est = a * stride
        truth = spread[:n_ticks * stride].reshape(n_ticks, stride).sum(axis=1)
        hot2 = truth >= np.percentile(truth, 99)
        res["decision"].append({
            "phase": phase, "n_intervals": int(n_ticks),
            "hot_interval_signed_bias": float((est[hot2] - truth[hot2]).sum()
                                              / max(truth[hot2].sum(), 1e-12)),
        })
    b = [d["hot_bin_signed_bias"] for d in res["sampled_bins"]]
    c = [d["hot_interval_signed_bias"] for d in res["decision"]]
    res["sampled_bins_bias_range"] = [min(b), max(b)]
    res["decision_bias_range"] = [min(c), max(c)]
    res["decision_bias_spans_zero"] = bool(min(c) < 0.0 < max(c))
    return res


def under_run_durations(arr: np.ndarray, spread: np.ndarray, bin_s: int, cap: float) -> dict:
    """How LONG does a stretch of under-provisioning last?  A single-bin blip
    is absorbed by the replica floor and by startup lead; a sustained deficit
    is not."""
    u = (np.ceil(arr / bin_s / cap) < np.ceil(spread / bin_s / cap)).astype(np.int8)
    if not u.any():
        return {"capacity_tok_s_per_replica": cap, "n_runs": 0}
    # run-length encode the 1s
    pad = np.concatenate(([0], u, [0]))
    starts = np.flatnonzero((pad[1:] == 1) & (pad[:-1] == 0))
    ends = np.flatnonzero((pad[1:] == 0) & (pad[:-1] == 1))
    runs = (ends - starts).astype(np.float64)
    return {
        "capacity_tok_s_per_replica": cap,
        "n_runs": int(len(runs)),
        "median_s": float(np.median(runs) * bin_s),
        "p90_s": float(np.percentile(runs, 90) * bin_s),
        "max_s": float(runs.max() * bin_s),
        "frac_runs_single_bin": float((runs == 1).mean()),
    }


def replica_disagreement(arr: np.ndarray, spread: np.ndarray, bin_s: int) -> list[dict]:
    """Translate both series into a replica count (ceil(rate / capacity)) and
    count how often provisioning off the arrival stamp differs from truth.

    Reported across a capacity sweep so no single capacity value carries the
    conclusion.  over = arrival stamp buys MORE replicas than truth needs
    (conservative: costs money, protects SLA); under = fewer (anti-conservative)."""
    out = []
    peak_true = float((spread / bin_s).max()) or 1e-12
    for cap in CAP_SWEEP:
        ra = np.ceil(arr / bin_s / cap)
        rs = np.ceil(spread / bin_s / cap)
        diff = ra - rs
        u = diff < 0
        # DOES the anti-conservative direction matter?  A bin can only hurt if
        # its ABSOLUTE demand is high; under-provisioning a trough is harmless.
        # Report where the under-provisioned bins actually sit on the load range.
        lvl = (spread[u] / bin_s / peak_true) if u.any() else np.array([np.nan])
        out.append({
            "capacity_tok_s_per_replica": cap,
            "mean_replicas_arrival": float(ra.mean()),
            "mean_replicas_true": float(rs.mean()),
            "replica_seconds_excess_frac": float((ra.sum() - rs.sum()) / max(rs.sum(), 1e-12)),
            "frac_bins_over": float((diff > 0).mean()),
            "frac_bins_under": float((diff < 0).mean()),
            "max_under_replicas": float(max((-diff).max(), 0.0)),
            "peak_replicas_arrival": float(ra.max()),
            "peak_replicas_true": float(rs.max()),
            "under_bins_level_vs_peak": {
                "p50": float(np.nanpercentile(lvl, 50)),
                "p90": float(np.nanpercentile(lvl, 90)),
                "max": float(np.nanmax(lvl)),
            },
            # the decisive one: is the arrival stamp ever short AT the peak?
            "under_at_top1pct_bins": float(
                (diff[spread >= np.percentile(spread, 99)] < 0).mean()),
        })
    return out


# --------------------------------------------------------------------------- #
def sanity_vs_thesis_series(arr_trace_1s: np.ndarray, out: dict) -> None:
    """Confirm the arrival-stamped series we rebuilt IS the thesis's `gen`."""
    p = THESIS_SERIES / "rates_1min.parquet"
    if not p.exists():
        out["thesis_series_check"] = {"status": "series file absent"}
        return
    import pyarrow.parquet as pq

    g = pq.read_table(p)["gen"].to_numpy().astype(np.float64)
    ours = rebin(arr_trace_1s, 60)
    n = min(len(g), len(ours))
    g, ours = g[:n], ours[:n]
    denom = max(float(g.sum()), 1e-12)
    out["thesis_series_check"] = {
        "status": "compared",
        "n_bins": int(n),
        "thesis_total": float(g.sum()),
        "rebuilt_total": float(ours.sum()),
        "total_rel_err": abs(float(ours.sum()) - float(g.sum())) / denom,
        "mean_abs_bin_err_frac": float(np.abs(ours - g).sum()) / denom,
        "max_abs_bin_err": float(np.abs(ours - g).max()),
    }


def make_figure(series: dict, stats: dict, path: Path) -> None:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    a60, s60 = series["arr_trace_60"], series["spread_60"]
    a15, s15 = series["arr_trace_15"], series["spread_15"]
    fig, ax = plt.subplots(2, 2, figsize=(13, 7.5))

    t = np.arange(len(a60)) / 60.0  # hours
    ax[0, 0].plot(t, a60 / 60, lw=0.4, color="#c44", label="arrival-stamped (thesis `gen`)")
    ax[0, 0].plot(t, s60 / 60, lw=0.4, color="#357", label="true decode emission")
    ax[0, 0].set_xlabel("hours from trace start"); ax[0, 0].set_ylabel("decode tokens/s")
    ax[0, 0].set_title("Full week @ 1-min bins"); ax[0, 0].legend(fontsize=7)

    w = stats["by_resolution"]["15"]["onsets"]["worst_overstated_bin"]["bin"]
    lo, hi = max(0, w - 60), min(len(a15), w + 60)
    ax[0, 1].step(np.arange(lo, hi) * 15 / 60, a15[lo:hi] / 15, color="#c44", lw=1,
                  label="arrival-stamped")
    ax[0, 1].step(np.arange(lo, hi) * 15 / 60, s15[lo:hi] / 15, color="#357", lw=1,
                  label="true decode")
    ax[0, 1].set_xlabel("minutes from trace start"); ax[0, 1].set_ylabel("decode tokens/s")
    ax[0, 1].set_title("Worst overstatement, ±15 min @ 15-s bins"); ax[0, 1].legend(fontsize=7)

    for res, c in zip(["1", "15", "60"], ["#888", "#c44", "#357"]):
        a = series[f"arr_trace_{res}"]; s = series[f"spread_{res}"]
        live = s > max(np.percentile(s[s > 0], 50), 1.0)
        r = np.sort(a[live] / s[live])
        ax[1, 0].plot(r, np.linspace(0, 1, len(r)), color=c, lw=1.2, label=f"{res}s bins")
    ax[1, 0].axvline(1.0, color="k", ls=":", lw=0.8)
    ax[1, 0].set_xlim(0, 3); ax[1, 0].set_xlabel("arrival-stamped / true decode (per bin)")
    ax[1, 0].set_ylabel("CDF over live bins"); ax[1, 0].set_title("Per-bin overstatement ratio")
    ax[1, 0].legend(fontsize=7)

    rows = stats["by_resolution"]["15"]["replica_disagreement"]
    x = np.arange(len(rows))
    ax[1, 1].bar(x - 0.2, [r["frac_bins_over"] for r in rows], 0.4, color="#357",
                 label="over-provisioned (conservative)")
    ax[1, 1].bar(x + 0.2, [r["frac_bins_under"] for r in rows], 0.4, color="#c44",
                 label="under-provisioned (anti-conservative)")
    ax[1, 1].set_xticks(x); ax[1, 1].set_xticklabels([f'{int(r["capacity_tok_s_per_replica"])}' for r in rows])
    ax[1, 1].set_xlabel("per-replica decode capacity (tok/s)")
    ax[1, 1].set_ylabel("fraction of 15-s bins"); ax[1, 1].set_title("Replica-count disagreement")
    ax[1, 1].legend(fontsize=7)

    fig.tight_layout()
    fig.savefig(path, dpi=130)
    plt.close(fig)


# --------------------------------------------------------------------------- #
def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--records", type=Path, default=DEFAULT_RECORDS,
                    help="per-request jsonl (a13/a15 *_e2e.requests.jsonl)")
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--tag", default=None, help="output filename prefix (default: from --records)")
    ap.add_argument("--max-requests", type=int, default=None, help="SMOKE ONLY: read first N records")
    ap.add_argument("--trace-offset", type=int, default=0,
                    help="0-based trace row the records start at (0 for the a13 full-trace arms)")
    ap.add_argument("--no-figure", action="store_true")
    args = ap.parse_args()

    tag = args.tag or args.records.name.split(".")[0]
    args.out.mkdir(parents=True, exist_ok=True)

    # The controller's decision cadence is read from the planner config, never
    # assumed to equal FORECAST_RESOLUTION (they are different things: 60 s vs
    # 15 s).  Any controller-relevant statistic is computed on that cadence.
    planner_interval_s = 60.0
    if PLANNER_CFG.exists():
        planner_interval_s = float(json.loads(PLANNER_CFG.read_text())
                                   .get("throughput_adjustment_interval_seconds", 60))
    print(f"[a16] planner throughput_adjustment_interval_seconds = {planner_interval_s:g}"
          f"  (from {PLANNER_CFG})", flush=True)

    print(f"[a16] reading {args.records} ...", flush=True)
    rec = read_records(args.records, args.max_requests)
    n = len(rec["gen"])
    print(f"[a16] {n:,} records", flush=True)

    print("[a16] reading raw-trace rows ...", flush=True)
    tr = read_trace_rows(args.trace_offset, n)
    join = verify_trace_join(rec, tr)
    print(f"[a16] trace set-identity: ctx {join['ctx_multiset_match_frac']:.4%} / gen "
          f"{join['gen_multiset_match_frac']:.4%} -> "
          f"{'USABLE' if join['usable'] else 'REJECTED'}", flush=True)
    trace_arr_ms, trace_gen = tr["arrival_ms"], tr["gen"]

    # decode occupancy interval: L tokens at 1/itl each => width L*itl, so the
    # emitted-token RATE inside the window is exactly 1/itl (correct by
    # construction).  For itl==0 / single-token requests the window degenerates
    # to a point, which spread_bins handles as a point stamp.
    a_ms = rec["first_ms"]
    b_ms = rec["last_ms"] + rec["itl_ms"]

    horizon_ms = float(max(b_ms.max(), rec["arrival_ms"].max(), trace_arr_ms.max())) + 1000.0
    nbins1 = int(math.ceil(horizon_ms / 1000.0))
    # pad the 1-s horizon up to a whole minute so EVERY resolution in
    # RESOLUTIONS (1/15/30/60) divides it evenly.  Without this, rebin() drops a
    # ragged tail of up to 59 one-second bins, and because spreading pushes mass
    # LATER than the arrival stamp the drop is asymmetric -> a spurious
    # mass_conservation_rel_err (1.5e-5 at 15 s).  Padding sends it to ~0.
    if nbins1 % 60:
        nbins1 += 60 - (nbins1 % 60)
    print(f"[a16] 1-s grid: {nbins1:,} bins (padded to a whole minute)", flush=True)

    gen = rec["gen"]
    arr_comp_1 = stamp_bins(rec["arrival_ms"], gen, nbins1, 1000.0)
    spread_1 = spread_bins(a_ms, b_ms, gen, nbins1, 1000.0)
    if join["usable"]:
        arr_trace_1 = stamp_bins(trace_arr_ms, trace_gen, nbins1, 1000.0)
    else:
        # Positional trace join not trustworthy for this record file: fall back
        # to the composed arrival, which needs no join and still answers the
        # gap (it isolates the decode-spread effect on its own).
        print("[a16] trace join rejected -> primary series = COMPOSED arrival", file=sys.stderr)
        arr_trace_1 = arr_comp_1

    stats: dict = {
        "tag": tag,
        "records": str(args.records),
        "n_requests": n,
        "smoke": args.max_requests is not None,
        "trace_offset": args.trace_offset,
        "trace_join": join,
        "primary_arrival_series": "raw_trace" if join["usable"] else "composed",
        "totals": {
            "trace_generated_tokens": float(trace_gen.sum()),
            "replay_output_tokens": float(gen.sum()),
            "output_vs_trace_rel_err": abs(float(gen.sum()) - float(trace_gen.sum()))
                                       / max(float(trace_gen.sum()), 1e-12),
        },
        "generation_window": {
            "mean_ms": float((b_ms - a_ms).mean()),
            "median_ms": float(np.median(b_ms - a_ms)),
            "p90_ms": float(np.percentile(b_ms - a_ms, 90)),
            "p99_ms": float(np.percentile(b_ms - a_ms, 99)),
            "max_ms": float((b_ms - a_ms).max()),
            # THE headline smoothing scale: the width of the kernel that the
            # arrival stamp implicitly sets to zero.
            "token_weighted_mean_ms": float(((b_ms - a_ms) * gen).sum() / max(gen.sum(), 1e-12)),
        },
        "capacity_sweep_tok_s": CAP_SWEEP,
        "mass_error_keys": {
            # D3: keep these two straight.  The ~1e-14 figure below is a
            # CONSTRUCTION IDENTITY (the spreading kernel conserves what it was
            # handed, guaranteed by the whole-minute horizon padding at the
            # `nbins1 % 60` block above) and is NOT evidence of trace fidelity.
            "construction_identity": "by_resolution.<r>.vs_primary_arrival."
                                     "mass_conservation_rel_err  (~1e-14, vacuous)",
            "trace_fidelity": "totals.output_vs_trace_rel_err  (QUOTE THIS ONE)",
        },
        "planner_interval_s": planner_interval_s,
        "planner_interval_source": str(PLANNER_CFG),
        "by_resolution": {},
    }
    if join["usable"]:
        # quantile shift of the arrival distribution (valid at set level; the
        # records are a local permutation so a per-row difference is not)
        sh = np.sort(rec["arrival_ms"]) - np.sort(trace_arr_ms)
        stats["encoder_shift"] = {"mean_ms": float(sh.mean()),
                                  "p50_ms": float(np.median(sh)),
                                  "p99_ms": float(np.percentile(sh, 99)),
                                  "max_ms": float(sh.max())}
    # identity check only meaningful for the full-trace, offset-0 arms
    if join["usable"] and args.trace_offset == 0 and args.max_requests is None:
        sanity_vs_thesis_series(arr_trace_1, stats)

    series: dict[str, np.ndarray] = {}
    for res in RESOLUTIONS:
        at = rebin(arr_trace_1, res)
        ac = rebin(arr_comp_1, res)
        sp = rebin(spread_1, res)
        series[f"arr_trace_{res}"] = at
        series[f"arr_comp_{res}"] = ac
        series[f"spread_{res}"] = sp
        stats["by_resolution"][str(res)] = {
            # PRIMARY arrival series vs the truth.  The key is NOT called
            # "vs_trace_arrival": when trace_join.usable is False the primary
            # series IS the composed arrival (identical to the block below), and
            # a key named after the trace would license a sentence claiming a
            # comparison that never happened.  `primary_arrival_series` at the
            # top level says which one this is.
            "vs_primary_arrival": compare(at, sp, res),
            # SECONDARY: composed arrival vs truth -- isolates decode spread
            # from the encoder-delay shift.  Byte-identical to the block above
            # whenever primary_arrival_series == "composed".
            "vs_composed_arrival": compare(ac, sp, res),
            "primary_is_composed_duplicate": not join["usable"],
            "onsets": onset_analysis(at, sp, res),
            "replica_disagreement": replica_disagreement(at, sp, res),
            "hot_tiers_truth_selected": hot_tiers(at, sp, res, "truth"),
            "hot_tiers_arrival_selected": hot_tiers(at, sp, res, "arrival"),
            "controller_sampled": controller_sampled_bias(at, sp, res, planner_interval_s),
            "under_runs": [under_run_durations(at, sp, res, c) for c in CAP_SWEEP],
        }
        print(f"[a16] {res:>3}s bins: displaced={stats['by_resolution'][str(res)]['vs_primary_arrival']['displaced_mass_fraction']:.4f} "
              f"peak_x={stats['by_resolution'][str(res)]['vs_primary_arrival']['peak_overstatement_x']:.3f}",
              flush=True)

    # ---- verdict -------------------------------------------------------- #
    stats["verdict"] = build_verdict(stats)

    sj = args.out / f"{tag}_a16_stats.json"
    sj.write_text(json.dumps(stats, indent=1))
    # EVERY resolution reported in the JSON is shipped as a series, so every
    # number in this file is independently recomputable (D7).  The 1-s and 30-s
    # series are gzipped because the 1-s grid is ~600k rows at full float64.
    for res in RESOLUTIONS:
        suffix = ".csv" if res in (15, 60) else ".csv.gz"
        p = args.out / f"{tag}_a16_series_{res}s{suffix}"
        arrt, arrc, sp = series[f"arr_trace_{res}"], series[f"arr_comp_{res}"], series[f"spread_{res}"]
        m = min(len(arrt), len(arrc), len(sp))
        np.savetxt(p, np.column_stack([np.arange(m) * res, arrt[:m], arrc[:m], sp[:m]]),
                   delimiter=",", header="t_s,arr_primary_tokens,arr_composed_tokens,true_decode_tokens",
                   # full float64 round-trip: at ~1e5 tokens/bin, %.4f (and even
                   # %.10g) collapses the ~1e-6 differences between the arrival
                   # stamp and the spread series into spurious exact ties, so
                   # the shipped CSV could not re-derive the per-bin over/under
                   # fractions reported in the JSON.  %.17g reproduces them.
                   comments="", fmt="%.17g")
    txt = render_summary(stats)
    (args.out / f"{tag}_a16_summary.txt").write_text(txt)
    print(txt)

    if not args.no_figure:
        try:
            make_figure(series, stats, args.out / f"{tag}_a16_decode_spread.png")
        except Exception as e:  # figure is a nicety, never fail the analysis
            print(f"[a16] figure skipped: {e}", file=sys.stderr)

    print(f"[a16] wrote {sj}")
    return 0


def build_verdict(stats: dict) -> dict:
    """Mechanically derive the direction-of-bias claim from the numbers."""
    v = {}
    for res in ("1", "15", "30", "60"):
        c = stats["by_resolution"][res]["vs_primary_arrival"]
        o = stats["by_resolution"][res]["onsets"]
        rd = stats["by_resolution"][res]["replica_disagreement"]
        ht = stats["by_resolution"][res]["hot_tiers_truth_selected"]
        ha = stats["by_resolution"][res]["hot_tiers_arrival_selected"]
        cs = stats["by_resolution"][res]["controller_sampled"]
        worst_under = max(r["frac_bins_under"] for r in rd)
        v[f"res_{res}s"] = {
            "sign_convention": "+ = stamp exceeds truth = CONSERVATIVE",
            "displaced_mass_fraction": c["displaced_mass_fraction"],
            "peak_overstatement_x": c["peak_overstatement_x"],
            "p99_overstatement_x": c["p99_overstatement_x"],
            # MASS-WEIGHTED onset/decay ratios decide direction; the unweighted
            # medians are carried alongside but explicitly labelled diagnostic.
            "onset_ratio_mass_weighted": o["onset_bins"]["ratio_mass_weighted"],
            "decay_ratio_mass_weighted": o["decay_bins"]["ratio_mass_weighted"],
            "onset_ratio_p50_unweighted_diagnostic": o["onset_bins"]["ratio_p50_unweighted_diagnostic"],
            "decay_ratio_p50_unweighted_diagnostic": o["decay_bins"]["ratio_p50_unweighted_diagnostic"],
            "onset_decay_mass_frac_of_series": (o["onset_bins"]["mass_frac_of_series"]
                                                + o["decay_bins"]["mass_frac_of_series"]),
            # BOTH selection conventions, and the whole tier curve, never one tier
            "hot_bin_signed_bias": c["hot_bin_signed_bias"],
            "hot_bin_signed_bias_arrival_selected": c["hot_bin_signed_bias_arrival_selected"],
            "tier_curve_truth_selected": {str(h["top_pct"]): h["bias_frac"] for h in ht},
            "tier_curve_arrival_selected": {str(h["top_pct"]): h["bias_frac"] for h in ha},
            "tier_curve_monotone_in_busyness": bool(
                all(x >= y for x, y in zip([h["bias_frac"] for h in ht],
                                           [h["bias_frac"] for h in ht][1:]))
                or all(x <= y for x, y in zip([h["bias_frac"] for h in ht],
                                              [h["bias_frac"] for h in ht][1:]))),
            # tail, so no mean can be mistaken for a tail claim
            "top1pct_frac_bins_short": next(h["frac_bins_short"] for h in ht if h["top_pct"] == 1.0),
            "top1pct_shortfall_p90_tok_s": next(h["shortfall_p90_tok_s"] for h in ht if h["top_pct"] == 1.0),
            "top1pct_shortfall_max_tok_s": next(h["shortfall_max_tok_s"] for h in ht if h["top_pct"] == 1.0),
            "top1pct_shortfall_max_frac_of_own_bin": next(
                h["shortfall_max_frac_of_own_bin"] for h in ht if h["top_pct"] == 1.0),
            "max_frac_bins_under_provisioned": worst_under,
            # the population the controller actually reads
            "controller_sampled_bins_bias_range": cs.get("sampled_bins_bias_range"),
            "controller_decision_bias_range": cs.get("decision_bias_range"),
            # DIRECTION OF BIAS -- decided by the MASS-WEIGHTED signed error over
            # the busiest 1% of true bins, not by the ratio of the two series'
            # maxima.  peak_overstatement_x is max(arr)/max(spread): those two
            # maxima fall in DIFFERENT bins, it is unweighted, and it flips
            # sign across bin width (1.243 / 0.999 / 1.026 at 15/30/60 s on the
            # static arm).  It is kept below as a labelled diagnostic only.
            "conservative_at_peaks_truth_selected": bool(c["hot_bin_signed_bias"] >= 0.0),
            "conservative_at_peaks_arrival_selected": bool(
                c["hot_bin_signed_bias_arrival_selected"] >= 0.0),
            "headline_flips_sign_by_selection": bool(
                (c["hot_bin_signed_bias"] >= 0.0)
                != (c["hot_bin_signed_bias_arrival_selected"] >= 0.0)),
            "conservative_at_peaks_basis": "hot_bin_signed_bias (mass-weighted, top 1%)",
            "peak_overstatement_x_diagnostic_only": True,
            "conservative_at_onsets": bool(o["onset_bins"]["ratio_mass_weighted"] >= 1.0),
            "anti_conservative_at_decays": bool(o["decay_bins"]["ratio_mass_weighted"] < 1.0),
        }
    return v


def render_summary(s: dict) -> str:
    L = []
    A = L.append
    A("=" * 78)
    A("A16 — decode-series upper-bound audit")
    A("=" * 78)
    A(f"records: {s['records']}")
    A(f"requests: {s['n_requests']:,}" + ("   [SMOKE]" if s["smoke"] else ""))
    g = s["generation_window"]
    A(f"generation window: median {g['median_ms']:.0f} ms, mean {g['mean_ms']:.0f} ms, "
      f"p99 {g['p99_ms']:.0f} ms, max {g['max_ms']:.0f} ms")
    A(f"TOKEN-WEIGHTED mean generation window = {g['token_weighted_mean_ms']:.0f} ms "
      f"<- the smoothing the arrival stamp erases")
    A("")
    A("SIGN CONVENTION (identical in EVERY block of this file):")
    A("    +  =  arrival stamp EXCEEDS truth  =  CONSERVATIVE")
    A("    -  =  arrival stamp is SHORT of truth  =  ANTI-conservative")
    A("")
    j = s["trace_join"]
    A(f"primary arrival series: {s['primary_arrival_series'].upper()}   "
      f"(trace_join.usable={j['usable']}, positional match {j['gen_positional_match_frac']:.4f})")
    if s["primary_arrival_series"] != "raw_trace":
        A("  !! NO TRACE COMPARISON WAS MADE.  The primary series IS the composed")
        A("     arrival; `vs_primary_arrival` is byte-identical to `vs_composed_arrival`.")
        A("     No sentence may claim a comparison against the trace's arrival stamps.")
    t = s["totals"]
    A(f"TRACE FIDELITY (the mass error that matters): trace GeneratedTokens="
      f"{t['trace_generated_tokens']:.0f}  replay output={t['replay_output_tokens']:.0f}  "
      f"rel-err={t['output_vs_trace_rel_err']:.2e}   <- QUOTE THIS")
    mc = s["by_resolution"]["15"]["vs_primary_arrival"]["mass_conservation_rel_err"]
    A(f"CONSTRUCTION IDENTITY: mass_conservation_rel_err={mc:.2e} @15s — the spreading")
    A("      kernel conserves what it was handed, guaranteed by the whole-minute horizon")
    A("      padding.  It is NOT evidence of trace fidelity; that is the line above.")
    if s["primary_arrival_series"] == "raw_trace":
        A("      (On this arm the two series come from different sources — trace stamps vs")
        A("      replay records — so the figure coincides with the trace-fidelity error and")
        A("      is meaningful.  It is still not a validation of the spreading model.)")
    else:
        A(f"      NEAR-VACUOUS on this arm: both series are redistributions of the SAME "
          f"replay\n      records, so ~1e-14 is machine epsilon, "
          f"{t['output_vs_trace_rel_err'] / max(mc, 1e-300):.0e}x smaller than the error that")
        A("      matters.  Do NOT quote it as 'exact in total volume'.")
    tc = s.get("thesis_series_check", {})
    if tc.get("status") == "compared":
        A(f"rebuilt-vs-thesis `gen` series @1min: total rel-err={tc['total_rel_err']:.2e}, "
          f"per-bin L1/total={tc['mean_abs_bin_err_frac']:.2e}  (identity check)")
    else:
        A("rebuilt-vs-thesis `gen` identity check: SKIPPED (trace join not usable)")
    A("")
    A(f"{'bin':>5} {'displaced':>10} {'peak x':>8} {'p999 x':>8} {'p99 x':>8} {'p90 x':>8} "
      f"{'onset x*':>9} {'decay x*':>9} {'lag s':>6}   (* = MASS-WEIGHTED)")
    for res in ("1", "15", "30", "60"):
        c = s["by_resolution"][res]["vs_primary_arrival"]
        o = s["by_resolution"][res]["onsets"]
        A(f"{res+'s':>5} {c['displaced_mass_fraction']:>10.4f} {c['peak_overstatement_x']:>8.3f} "
          f"{c['p999_overstatement_x']:>8.3f} {c['p99_overstatement_x']:>8.3f} "
          f"{c['p90_overstatement_x']:>8.3f} {o['onset_bins']['ratio_mass_weighted']:>9.3f} "
          f"{o['decay_bins']['ratio_mass_weighted']:>9.3f} {c['lag_seconds']:>6.0f}")
    A("")
    A("replica disagreement @15-s bins (provisioning off arrival stamp vs truth):")
    A(f"  {'cap tok/s':>10} {'excess rep-s':>13} {'bins over':>10} {'bins under':>11} "
      f"{'max under':>10} {'under@top1%':>12} {'under-bin lvl p90':>18}")
    for r in s["by_resolution"]["15"]["replica_disagreement"]:
        A(f"  {r['capacity_tok_s_per_replica']:>10.0f} {r['replica_seconds_excess_frac']:>12.2%} "
          f"{r['frac_bins_over']:>10.3%} {r['frac_bins_under']:>11.3%} "
          f"{r['max_under_replicas']:>10.0f} {r['under_at_top1pct_bins']:>12.3%} "
          f"{r['under_bins_level_vs_peak']['p90']:>17.1%}")
    A("")
    A("THE WHOLE TIER CURVE @15-s, BOTH SELECTION CONVENTIONS (+ = stamp exceeds truth =")
    A("CONSERVATIVE).  The headline FLIPS SIGN between the two selections; that flip is the")
    A("finding.  Truth-selected conditions on a series no controller can observe ex ante;")
    A("arrival-selected is the population a controller can actually identify.")
    for sel, key in (("TRUTH-selected  (unobservable)", "hot_tiers_truth_selected"),
                     ("ARRIVAL-selected (OBSERVABLE)", "hot_tiers_arrival_selected")):
        A(f"  {sel}")
        A(f"  {'tier':>10} {'n bins':>8} {'true tok/s':>11} {'bias':>9} {'bins short':>11} "
          f"{'short p90':>10} {'short max':>10} {'max/bin':>8}")
        for h in s["by_resolution"]["15"][key]:
            A(f"  top {h['top_pct']:>5.2f}% {h['n_bins']:>8d} {h['true_mean_tok_s']:>11.0f} "
              f"{h['bias_frac']:>+9.2%} {h['frac_bins_short']:>11.1%} "
              f"{h['shortfall_p90_tok_s']:>10.1f} {h['shortfall_max_tok_s']:>10.1f} "
              f"{h['shortfall_max_frac_of_own_bin']:>8.1%}")
    A("  (`bias` is mass-weighted and signed as above; `short *` are the mirror tail")
    A("   statistics truth-minus-stamp, positive = the stamp fell SHORT in that bin.)")
    A("")
    cs = s["by_resolution"]["15"]["controller_sampled"]
    A(f"POPULATION THE CONTROLLER ACTUALLY READS (planner interval "
      f"{s['planner_interval_s']:g} s, {s['planner_interval_source']}):")
    A(f"  stride {cs['stride']} point sample of the 15-s bins -> "
      f"{cs['frac_bins_never_read']:.0%} of bins are NEVER read by the provisioning decision.")
    A("  busiest-1% mass-weighted bias over the SAMPLED bins, by phase offset:")
    A("      " + "  ".join(f"p{d['phase']} {d['hot_bin_signed_bias']:+.2%}"
                           for d in cs["sampled_bins"]))
    A(f"  and over the CONTROL INTERVAL estimator (stride x sampled bin vs true "
      f"{s['planner_interval_s']:g}-s mass):")
    A("      " + "  ".join(f"p{d['phase']} {d['hot_interval_signed_bias']:+.2%}"
                           for d in cs["decision"]))
    A(f"  spans zero across phase: {cs['decision_bias_spans_zero']}  -- the phase is not")
    A("  controllable, so no single-signed provisioning claim survives this population.")
    A(f"  CAVEAT: the decode series enters the planner only as {cs['consumed_as']},")
    A("  so a bin-level decode-rate bias is NOT shown to propagate to a replica decision.")
    A("")
    A("duration of under-provisioned stretches @15-s bins:")
    for r in s["by_resolution"]["15"]["under_runs"]:
        if r["n_runs"]:
            A(f"  cap {r['capacity_tok_s_per_replica']:>6.0f} tok/s: {r['n_runs']:>5d} runs, "
              f"median {r['median_s']:>4.0f}s, p90 {r['p90_s']:>4.0f}s, max {r['max_s']:>5.0f}s, "
              f"{r['frac_runs_single_bin']:.1%} are a single bin")
    A("")
    v = s["verdict"]["res_15s"]
    A("VERDICT @15-s (FORECAST_RESOLUTION — note this is NOT the controller's cadence):")
    A("  signed bias, busiest 1% of bins, MASS-WEIGHTED   [+ = stamp exceeds truth]")
    A(f"      truth-selected   {v['hot_bin_signed_bias']:+.3%}  "
      f"({'CONSERVATIVE' if v['conservative_at_peaks_truth_selected'] else 'ANTI-CONSERVATIVE'}"
      f"; unobservable ex ante)")
    A(f"      arrival-selected {v['hot_bin_signed_bias_arrival_selected']:+.3%}  "
      f"({'CONSERVATIVE' if v['conservative_at_peaks_arrival_selected'] else 'ANTI-CONSERVATIVE'}"
      f"; OBSERVABLE)")
    A(f"      headline flips sign by selection convention: {v['headline_flips_sign_by_selection']}")
    A("      truth-selected across bin width: " + "  ".join(
        f"{r}s {s['verdict'][f'res_{r}s']['hot_bin_signed_bias']:+.3%}"
        for r in ("1", "15", "30", "60")))
    A("  tier curve, truth-selected (NOT monotone -> no single tier characterises it):")
    A("      " + "  ".join(f"top{k}% {val:+.2%}"
                           for k, val in v["tier_curve_truth_selected"].items()))
    A("  tier curve, arrival-selected:")
    A("      " + "  ".join(f"top{k}% {val:+.2%}"
                           for k, val in v["tier_curve_arrival_selected"].items()))
    A(f"  onset bins MASS-WEIGHTED ratio  {v['onset_ratio_mass_weighted']:.3f}x  "
      f"({'CONSERVATIVE' if v['conservative_at_onsets'] else 'ANTI-CONSERVATIVE'} at onsets)"
      f"   [unweighted median {v['onset_ratio_p50_unweighted_diagnostic']:.3f}x = DIAGNOSTIC ONLY]")
    A(f"  decay bins MASS-WEIGHTED ratio  {v['decay_ratio_mass_weighted']:.3f}x  "
      f"({'anti-conservative' if v['anti_conservative_at_decays'] else 'conservative'} at decays)"
      f"   [unweighted median {v['decay_ratio_p50_unweighted_diagnostic']:.3f}x = DIAGNOSTIC ONLY]")
    A(f"  onset+decay carry {v['onset_decay_mass_frac_of_series']:.2%} of stamped mass, so")
    A("      neither figure characterises the series as a whole.")
    A("  TAIL within the truth-selected busiest 1% (a MEAN cannot license a tail claim):")
    A(f"      {v['top1pct_frac_bins_short']:.1%} of those bins are SHORT; shortfall p90 "
      f"{v['top1pct_shortfall_p90_tok_s']:.1f} tok/s, max {v['top1pct_shortfall_max_tok_s']:.1f} "
      f"tok/s = {v['top1pct_shortfall_max_frac_of_own_bin']:.1%} of that bin's own true rate")
    A(f"      worst under-provisioned bin share across capacity sweep: "
      f"{v['max_frac_bins_under_provisioned']:.3%}")
    A("  CONTROLLER-CADENCE population (the one a provisioning claim must use):")
    A(f"      sampled-bin bias range across phase   "
      f"[{v['controller_sampled_bins_bias_range'][0]:+.2%}, "
      f"{v['controller_sampled_bins_bias_range'][1]:+.2%}]")
    A(f"      control-interval bias range across phase "
      f"[{v['controller_decision_bias_range'][0]:+.2%}, "
      f"{v['controller_decision_bias_range'][1]:+.2%}]")
    A("")
    A("DIAGNOSTIC (not the verdict) — ratio of maxima (different bins), unweighted:")
    A("      " + "  ".join(
        f"{r}s {s['verdict'][f'res_{r}s']['peak_overstatement_x']:.3f}x"
        for r in ("1", "15", "30", "60")))
    A("      max(arr_primary)/max(spread); the two maxima do NOT occur in the same")
    A("      bin and the ratio crosses 1.0 as bin width changes, so it cannot")
    A("      support a direction-of-bias claim.  Use the mass-weighted bias above.")
    A("=" * 78)
    return "\n".join(L)


if __name__ == "__main__":
    sys.exit(main())
