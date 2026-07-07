#!/usr/bin/env python3
"""Phase 3.1 — derive converter row-windows for the baseline experiments.

Turns the EDA burst-episode definitions (analysis/trace_eda/
i_burst_anatomy_stats.json, top6_by_peak: baseline-start/end timestamps)
into (offset, max_requests) row windows for workload/trace_to_two_pool.py,
using EXACTLY the converter's trace normalization (pad 2-digit millis to
3, sort by ts) so row offsets are converter-exact. Each episode is padded
+/-10 min, matching how sweep_load.py's `burst1` window was derived —
episode 1 here MUST reproduce burst1's known offset=843072, count=64804
(hard assertion; the anchor that proves the normalization matches).

Also selects one steady 24 h window: the calendar day with the lowest
peak 1-min image rate (data-driven "calm day"), for the static baseline's
GPU-hours accounting on non-burst traffic.

Output: simulation/windows.json — a registry sweep_grid.py consumes:
  {"burst1": {"offset":..., "max_requests":..., "note":...}, ...,
   "steady24h": {...}}

Run in the aiconfigurator venv (needs pandas, same as the converter):
  /home/gio/tese/ai-dynamo/aiconfigurator/.venv/bin/python \
      simulation/derive_windows.py
"""
from __future__ import annotations

import json
from datetime import timedelta
from pathlib import Path

import pandas as pd

HERE = Path(__file__).resolve().parent
TRACE = "/home/gio/tese/data/AzureLMMInferenceTrace_multimodal.csv.gz"
EPISODES = Path("/home/gio/tese/analysis/trace_eda/i_burst_anatomy_stats.json")
OUT = HERE / "windows.json"
PAD = timedelta(minutes=10)

# The anchor derived for Phase 2.3 (sweep_load.py burst1) — episode 1 padded.
ANCHOR = {"offset": 843072, "max_requests": 64804}


def load_normalized() -> pd.DataFrame:
    """Mirror trace_to_two_pool.load_window()'s normalization exactly."""
    df = pd.read_csv(TRACE)
    ts = df["TIMESTAMP"].str.replace("Z", "", regex=False).str.pad(23, "right", "0")
    df["ts"] = pd.to_datetime(ts, format="%Y-%m-%dT%H:%M:%S.%f")
    return df.drop(columns=["TIMESTAMP"]).sort_values("ts").reset_index(drop=True)


def window_rows(df: pd.DataFrame, start: pd.Timestamp, end: pd.Timestamp) -> tuple[int, int]:
    """[start, end) as (offset, count) over the ts-sorted frame."""
    lo = int(df["ts"].searchsorted(start, side="left"))
    hi = int(df["ts"].searchsorted(end, side="left"))
    return lo, hi - lo


def describe(df: pd.DataFrame, lo: int, n: int) -> dict:
    w = df.iloc[lo:lo + n]
    span = (w["ts"].iloc[-1] - w["ts"].iloc[0]).total_seconds()
    per_min = w.set_index("ts")["NumImages"].resample("1min").sum() / 60.0
    return {
        "requests": int(n),
        "span_s": round(span, 1),
        "mean_req_per_s": round(n / span, 3),
        "mean_img_per_s": round(float(w["NumImages"].sum()) / span, 3),
        "peak_1min_img_per_s": round(float(per_min.max()), 2),
        "text_only_fraction": round(float((w["NumImages"] == 0).mean()), 3),
    }


def main() -> None:
    df = load_normalized()
    episodes = json.loads(EPISODES.read_text())["top6_by_peak"]

    windows: dict[str, dict] = {}
    for i, ep in enumerate(episodes, start=1):
        start = pd.Timestamp(ep["start_baseline"]) - PAD
        end = pd.Timestamp(ep["end_baseline"]) + PAD
        lo, n = window_rows(df, start, end)
        windows[f"burst{i}"] = {
            "offset": lo, "max_requests": n,
            "note": (f"episode {i} of top6_by_peak +/-10min pad: "
                     f"[{start} .. {end}) UTC, peak {ep['peak_img_per_s']:.1f} img/s "
                     f"@ {ep['peak']}, onset {ep['onset_minutes']} min"),
            **describe(df, lo, n),
        }

    # Anchor check: burst1 must reproduce the Phase-2.3 window exactly.
    b1 = windows["burst1"]
    assert (b1["offset"], b1["max_requests"]) == (ANCHOR["offset"], ANCHOR["max_requests"]), (
        f"burst1 anchor mismatch: got offset={b1['offset']} n={b1['max_requests']}, "
        f"expected {ANCHOR} — normalization drift, do NOT trust the other windows")

    # Steady 24 h window: full UTC calendar day with the lowest peak 1-min
    # image rate among complete days (first/last day of the trace excluded
    # if partial).
    per_min_all = df.set_index("ts")["NumImages"].resample("1min").sum() / 60.0
    days = per_min_all.groupby(per_min_all.index.date)
    full_days = {d: g for d, g in days if len(g) == 1440}
    calm_day = min(full_days, key=lambda d: float(full_days[d].max()))
    start = pd.Timestamp(calm_day)
    lo, n = window_rows(df, start, start + timedelta(days=1))
    windows["steady24h"] = {
        "offset": lo, "max_requests": n,
        "note": (f"calmest full UTC day (lowest peak 1-min img rate among "
                 f"{sorted(full_days)}): {calm_day}"),
        **describe(df, lo, n),
    }

    OUT.write_text(json.dumps(windows, indent=1))
    print(f"wrote {OUT}")
    for name, w in windows.items():
        print(f"  {name:9s} offset={w['offset']:>7d} n={w['max_requests']:>6d} "
              f"span={w['span_s']/3600:5.2f}h mean {w['mean_req_per_s']:.2f} req/s "
              f"{w['mean_img_per_s']:7.2f} img/s peak1min {w['peak_1min_img_per_s']:7.1f} img/s")


if __name__ == "__main__":
    main()
