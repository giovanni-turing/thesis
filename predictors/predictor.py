"""Abstract predictor interface + batch executor for per-pool demand forecasting
(Phase 4 — the thesis's predictive-scaling contribution).

Every predictor ingests the most recent bucket of same-cadence metric history —
one or more *covariate* series (correlated regressors the model may use as
context but does not forecast, e.g. requests/s) and one or more *target*
series (the progressive values to forecast, e.g. images/s or gen tokens/s —
see analysis/trace_eda/m_gen_and_global.py) — and returns an h-step-ahead
forecast per target, sampled at the same fixed frequency f as the input. Point
forecasts are mandatory; the 9-quantile band (levels 0.1..0.9 — the
intersection of TimesFM's and Toto's native quantile heads; Chronos-2 is asked
for the same 9 levels for a like-for-like comparison) is optional per call.

Concrete backends (chronos-2, timesfm, toto) live beside this file and each
implement predict_batch() against their own native batching mechanism:
- Chronos2Predictor: one long-format DataFrame, id_column groups series,
  native past/future covariate support (chronos-forecasting>=2.0).
- TimesFMPredictor: forecast_input list-of-arrays batching; univariate only —
  this checkpoint has no covariate API, so covariates are dropped (an ablation
  the thesis argues from, not a limitation to hide).
- TotoPredictor: (batch, n_variates, time) tensor; covariates ride the variate
  axis under the same series_id as their target so cross-variate attention
  sees them, then only target rows of the output are kept.

BatchExecutor reads one row per Bucket from a parquet trace file, groups rows
into the fewest, densest calls to predict_batch(), and appends each resulting
batch's forecasts to a JSON-lines side file as soon as it returns (crash-safe,
resumable — a run interrupted mid-way leaves completed forecasts on disk
instead of losing them to an unclosed Parquet footer). Once every batch is
done, the side file is assembled into the final Parquet output and removed.
"""

from __future__ import annotations

import json
from abc import ABC, abstractmethod
from collections import defaultdict
from collections.abc import Sequence
from dataclasses import dataclass, field
from pathlib import Path
from statistics import NormalDist

import pyarrow as pa
import pyarrow.parquet as pq

QUANTILE_LEVELS: tuple[float, ...] = (0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9)
DEFAULT_HORIZON = 10  # steps ahead at the bucket's own cadence
_Z = {level: NormalDist().inv_cdf(level) for level in QUANTILE_LEVELS}


def normal_quantile_bands(
    center: float | Sequence[float], sigma_by_step: Sequence[float]
) -> tuple[tuple[float, ...], ...]:
    """(9, h) bands: level l, step k -> center[k] + z(l) * sigma_by_step[k].

    `center` is either one value broadcast across every step (a flat point
    forecast, e.g. naive/EWMA) or a per-step sequence the same length as
    `sigma_by_step` (a trending/seasonal point forecast, e.g. Holt-Winters) —
    each quantile step is centered on that step's own point forecast, not a
    single anchor value.

    Shared by stdlib statistical baselines whose forecast error is assumed
    Gaussian around a point forecast with a model-specific sigma growth curve
    over the horizon; foundation-model backends produce quantiles natively
    and don't need this.
    """
    centers = center if isinstance(center, Sequence) else [center] * len(sigma_by_step)
    return tuple(
        tuple(c + _Z[level] * s for c, s in zip(centers, sigma_by_step)) for level in QUANTILE_LEVELS
    )


@dataclass(frozen=True)
class Bucket:
    """One sliding window of same-cadence metric history feeding one forecast call.

    `targets` holds the progressive series to forecast (name -> values);
    `covariates` holds correlated regressor series over the same window that
    inform the forecast but are not themselves forecast. All arrays share one
    length, sampled at `freq_s`.
    """

    series_id: str
    freq_s: float
    targets: dict[str, Sequence[float]]
    covariates: dict[str, Sequence[float]] = field(default_factory=dict)

    def __post_init__(self) -> None:
        lengths = {len(v) for v in self.targets.values()} | {len(v) for v in self.covariates.values()}
        if len(lengths) > 1:
            raise ValueError(f"{self.series_id}: all series in a bucket must share one length, got {lengths}")
        if not self.targets:
            raise ValueError(f"{self.series_id}: bucket has no target series")

    @property
    def context_length(self) -> int:
        return len(next(iter(self.targets.values())))


@dataclass(frozen=True)
class Forecast:
    """h-step-ahead forecast for one Bucket, at the bucket's own cadence."""

    series_id: str
    horizon: int
    point: dict[str, tuple[float, ...]]  # name -> h values
    quantiles: dict[str, tuple[tuple[float, ...], ...]] | None = None  # name -> (9, h), QUANTILE_LEVELS order


class Predictor(ABC):
    """One time-series foundation-model backend, batched over independent buckets.

    `clip_min` (default 0.0) floors every point and quantile value on return —
    every target this package forecasts (images/s, gen tokens/s, ...) is a
    non-negative rate, and extrapolating stdlib baselines (trend/seasonal
    components in particular) can otherwise predict a physically impossible
    negative rate. Clipping lives here, once, so it applies to every backend
    automatically instead of each subclass having to remember it. Pass
    `clip_min=None` to disable, e.g. for a target that can genuinely go
    negative.
    """

    def __init__(
        self,
        horizon: int = DEFAULT_HORIZON,
        *,
        freq_s: float,
        return_quantiles: bool = True,
        clip_min: float | None = 0.0,
    ) -> None:
        self.horizon = horizon
        self.freq_s = freq_s
        self.return_quantiles = return_quantiles
        self.clip_min = clip_min

    @property
    @abstractmethod
    def max_batch_size(self) -> int:
        """Largest number of Buckets this backend can forecast in one native call."""

    def predict_batch(self, buckets: Sequence[Bucket]) -> list[Forecast]:
        """Forecast every bucket in as few native batched calls as possible, then
        apply `clip_min`. Preserves input order; returns one Forecast per Bucket.
        """
        forecasts = self._predict_batch(buckets)
        if self.clip_min is None:
            return forecasts
        return [self._clip(f) for f in forecasts]

    @abstractmethod
    def _predict_batch(self, buckets: Sequence[Bucket]) -> list[Forecast]:
        """Backend-specific batched inference — see predict_batch for the contract.

        Callers (BatchExecutor, via predict_batch) already group `buckets` by
        shape and chunk to `max_batch_size`, so implementations should not
        need to sub-batch further except where their own SDK forces an even
        smaller unit.
        """

    def _clip(self, forecast: Forecast) -> Forecast:
        lo = self.clip_min
        point = {name: tuple(max(lo, v) for v in vals) for name, vals in forecast.point.items()}
        quantiles = None
        if forecast.quantiles is not None:
            quantiles = {
                name: tuple(tuple(max(lo, v) for v in band) for band in bands)
                for name, bands in forecast.quantiles.items()
            }
        return Forecast(forecast.series_id, forecast.horizon, point, quantiles)

    def _check_freq(self, buckets: Sequence[Bucket]) -> None:
        bad = {b.series_id for b in buckets if b.freq_s != self.freq_s}
        if bad:
            raise ValueError(f"buckets sampled at a different cadence than {self.freq_s}s: {sorted(bad)}")


class BatchExecutor:
    """Runs one Predictor over every Bucket row in a parquet trace file and
    writes forecasts to a parquet output file once the run completes.

    `in_file` must have a `series_id` (str), `freq_s` (float) column, and one
    list<double> column per name in `targets`/`covariates` — one row per
    Bucket. Rows are grouped by context length (list column length) so every
    native call is one dense tensor/DataFrame — no padding wasted across
    buckets that don't share a shape — then chunked to
    `predictor.max_batch_size`. Each batch's forecasts are appended to a
    `{out_file}.tmp.jsonl` side file immediately after `predict_batch`
    returns (so a crash mid-run loses nothing already computed); once every
    batch is done, that side file is read back and written out as `out_file`
    in one `pq.write_table` call, then removed.
    """

    def __init__(self, predictor: Predictor, targets: Sequence[str], covariates: Sequence[str] = ()) -> None:
        self.predictor = predictor
        self.targets = tuple(targets)
        self.covariates = tuple(covariates)

    def _read_buckets(self, in_file: str | Path) -> list[Bucket]:
        table = pq.read_table(in_file, columns=["series_id", "freq_s", *self.targets, *self.covariates])
        return [
            Bucket(
                series_id=row["series_id"],
                freq_s=row["freq_s"],
                targets={name: row[name] for name in self.targets},
                covariates={name: row[name] for name in self.covariates},
            )
            for row in table.to_pylist()
        ]

    @staticmethod
    def _forecast_row(forecast: Forecast) -> dict:
        row = {"series_id": forecast.series_id, "horizon": forecast.horizon}
        for name, values in forecast.point.items():
            row[f"point_{name}"] = list(values)
            if forecast.quantiles is not None:
                for idx, band in zip(range(1, len(QUANTILE_LEVELS) + 1), forecast.quantiles[name]):
                    row[f"q{idx:02d}_{name}"] = list(band)
        return row

    def run(self, in_file: str | Path, out_file: str | Path) -> None:
        buckets = self._read_buckets(in_file)
        self.predictor._check_freq(buckets)

        groups: dict[int, list[Bucket]] = defaultdict(list)
        for b in buckets:
            groups[b.context_length].append(b)

        max_batch = self.predictor.max_batch_size
        tmp_path = Path(f"{out_file}.tmp.jsonl")
        with tmp_path.open("w") as f:
            for group in groups.values():
                for i in range(0, len(group), max_batch):
                    chunk = group[i : i + max_batch]
                    for forecast in self.predictor.predict_batch(chunk):
                        f.write(json.dumps(self._forecast_row(forecast)) + "\n")
                        f.flush()

        with tmp_path.open() as f:
            rows = [json.loads(line) for line in f]
        pq.write_table(pa.Table.from_pylist(rows), out_file)
        tmp_path.unlink()
