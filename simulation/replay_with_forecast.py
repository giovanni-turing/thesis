#!/usr/bin/env python
"""Phase 4.3 LLM-side hook: dynamo.replay with a `forecast_file` predictor.

Registers a TSFM-forecast-replaying predictor into the planner's
LOAD_PREDICTORS registry, then delegates to ``dynamo.replay``'s main —
so the predictive policy runs through the SAME planner actuation path as
the reactive baseline; the only difference between policies is the
prediction source.

Predictor identity: the local planner constructs three instances from one
factory in a fixed order (local_planner.py: _num_req_predictor,
_isl_predictor, _osl_predictor) — the factory hands out variate bindings
in that sequence. Clocking: the planner feeds one observation per
throughput tick; the predictor counts add_data_point calls and returns
a SINGLE archived bin sampled one control-minute ahead (the bin at index
4*ticks at 15-s resolution) -- it does NOT aggregate the minute's four
15-s bins, and the series starts at T0-1min. Run with the throughput
adjustment interval equal to the forecast bin (60 s for 1-min bins) so
per-bin totals map 1:1 onto per-interval counts. The language-pool result
is therefore a same-input conversion comparison on a held, sampled
signal (a synthetic sampled-signal experiment), not a timing or
anticipation instrument (see tex/closedloop.tex language-pool caveat).

Configuration (env — PlannerConfig has no extension fields):
  FORECAST_DIR        predictors/results (chronos_*.parquet live here)
  FORECAST_MODEL      chronos | toto | timesfm | naive | ewma
  FORECAST_QUANTILE   point | p10..p90         (default p50)
  FORECAST_RESOLUTION 1min                     (default)
  FORECAST_T0         window start timestamp (ISO, converter-normalized)

isl/osl are derived per bin: isl = ctx_total/req_total, osl =
gen_total/req_total (guarded). All other args pass through to
dynamo.replay unchanged:
  REPLAY_PY=.../dynamo/.venv/bin/python \\
  FORECAST_T0="2024-10-21 12:59:00.180" ... \\
  python -m? no — run_replay.sh with REPLAY_MODULE=simulation/replay_with_forecast.py
"""
from __future__ import annotations

import os
import sys

import pandas as pd

from dynamo.planner.core.load import predictors as P


def _load_series() -> dict[str, "pd.Series"]:
    d = os.environ.get("FORECAST_DIR", "/home/gio/tese/predictors/results")
    model = os.environ.get("FORECAST_MODEL", "chronos")
    q = os.environ.get("FORECAST_QUANTILE", "p50")
    res = os.environ.get("FORECAST_RESOLUTION", "1min")
    t0 = pd.Timestamp(os.environ["FORECAST_T0"])
    out: dict[str, pd.Series] = {}
    for variate, fname in (("requests", f"{model}_requests.parquet"),
                           ("ctx", f"{model}_ctx.parquet"),
                           ("gen", f"{model}_gen.parquet")):
        df = pd.read_parquet(os.path.join(d, fname))
        df = df[df.resolution == res]
        if "variate" in df.columns and df.variate.nunique() > 1:
            df = df[df.variate == variate]
        df = df[df.ts >= t0 - pd.Timedelta(minutes=1)]
        df = df.sort_values("ts").drop_duplicates("ts")
        s = df.set_index("ts")[q].clip(lower=0.0)
        # Units: parquet quantiles are PER-BIN totals, and the planner reads a
        # predicted value as a per-60s count (its adjustment interval).
        # Normalize per-bin -> per-60s so demand is resolution-independent
        # (x1 at 1min: burst1 runs byte-identical; x4 at 15s: demand was
        # silently understated 4x). ISL/OSL are ratios c/r, g/r — unaffected.
        bin_s = pd.Timedelta(res.replace("min", "m")).total_seconds()
        s = s * (60.0 / bin_s)
        if s.empty:
            raise SystemExit(f"forecast_file: no rows for {variate} at/after {t0}")
        # Alignment guard: the forecast span must actually COVER the window
        # start (at coarse resolutions the models' context pushes the first
        # forecastable bin days into the trace — serving later rows for an
        # earlier window is silent garbage).
        gap_s = (s.index[0] - t0).total_seconds()
        if gap_s > 2 * pd.Timedelta(res.replace("min", "m")).total_seconds():
            raise SystemExit(
                f"forecast_file: window start {t0} is OUTSIDE the {res} "
                f"forecast span (first bin {s.index[0]}, {gap_s/3600:.1f} h "
                f"later) — use a finer resolution or an in-span window")
        out[variate] = s
    return out


class _ForecastFilePredictor(P.BasePredictor):
    """Replays an archived stitched forecast path; observation-driven clock."""

    def __init__(self, kind: str, series: dict[str, pd.Series]) -> None:
        super().__init__(minimum_data_points=1)
        self.kind = kind          # "req" | "isl" | "osl"
        self.series = series
        self.ticks = 0

    def add_data_point(self, value: float) -> None:  # always advances the clock
        super().add_data_point(value)
        self.ticks += 1

    def _bin(self, idx: int) -> tuple[float, float, float]:
        # Clock: one planner tick = 60 s of sim time, but the series is at
        # FORECAST_RESOLUTION bins — advance round(60/bin_s) bins per tick
        # (1 at 1min, unchanged; 4 at 15s, else the path is read 4x too
        # slowly and sticks near the window start).
        res = os.environ.get("FORECAST_RESOLUTION", "1min")
        bin_s = pd.Timedelta(res.replace("min", "m")).total_seconds()
        # NOTE: this SAMPLES the single bin at index 4*idx (one bin per control
        # minute at 15-s resolution); it does NOT aggregate the minute's four
        # 15-s bins. The language-pool experiment is therefore a conversion test
        # on this held, sampled signal -- a synthetic sampled-signal experiment,
        # not a timing/anticipation instrument (see the language-pool caveat in
        # tex/closedloop.tex). The series also starts at T0-1min (load_series).
        idx = int(idx * max(1, round(60.0 / bin_s)))
        req = self.series["requests"]
        i = min(idx, len(req) - 1)
        ts = req.index[i]
        r = float(req.iloc[i])
        c = float(self.series["ctx"].reindex([ts]).fillna(0.0).iloc[0])
        g = float(self.series["gen"].reindex([ts]).fillna(0.0).iloc[0])
        return r, c, g

    def predict_next(self) -> float:
        r, c, g = self._bin(self.ticks)  # next bin = one past the observed ones
        if self.kind == "req":
            # FORECAST_REQ_SCALE: tail-aware capacity mapping through the
            # planner's mean-based conversion — scale the predicted request
            # rate so mean-throughput sizing lands on tail-adequate replicas
            # (knee-derived; e.g. 2.0 for the TP2 burst shape).
            return max(r, 0.0) * float(os.environ.get("FORECAST_REQ_SCALE", "1.0"))
        if r <= 0.0:
            return 0.0
        return max((c if self.kind == "isl" else g) / r, 1.0)


def _factory_maker():
    series = _load_series()
    order = iter(("req", "isl", "osl"))  # local_planner construction order

    def factory(_config) -> _ForecastFilePredictor:
        kind = next(order)
        print(f"[forecast_file] constructed {kind} predictor", flush=True)
        return _ForecastFilePredictor(kind, series)

    return factory


P.LOAD_PREDICTORS["forecast_file"] = _factory_maker()

if __name__ == "__main__":
    from dynamo.replay.main import main  # noqa: E402

    sys.exit(main())
