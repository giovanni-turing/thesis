"""Naive last-value (random-walk) baseline predictor — Phase 4's cheapest baseline.

No model weights, no covariates: the point forecast repeats the target's last
observed value across the whole horizon. The optional quantile band uses the
classic random-walk prediction interval (Hyndman & Athanasopoulos,
*Forecasting: Principles and Practice*, ch. 3): the residual std of the
target's own first differences, scaled by sqrt(step) per horizon step and
converted to quantiles via the standard normal.
"""

from __future__ import annotations

import math
from collections.abc import Sequence

from predictor import Bucket, Forecast, Predictor, normal_quantile_bands


def _residual_std(series: Sequence[float]) -> float:
    diffs = [b - a for a, b in zip(series, series[1:])]
    if len(diffs) < 2:
        return 0.0
    mean = sum(diffs) / len(diffs)
    var = sum((d - mean) ** 2 for d in diffs) / (len(diffs) - 1)
    return math.sqrt(var)


class NaivePredictor(Predictor):
    """Persistence forecast: y_hat[t+k] = y[t] for every target, every k in 1..h.

    Covariates are accepted (for interface parity with the other backends) but
    ignored — this baseline is exactly the strawman the thesis's foundation-
    model backends are meant to beat.
    """

    max_batch_size = 1_000_000  # pure stdlib arithmetic — no native batch-shape constraint

    def _predict_batch(self, buckets: Sequence[Bucket]) -> list[Forecast]:
        return [self._predict_one(b) for b in buckets]

    def _predict_one(self, bucket: Bucket) -> Forecast:
        point: dict[str, tuple[float, ...]] = {}
        quantiles: dict[str, tuple[tuple[float, ...], ...]] | None = {} if self.return_quantiles else None

        for name, series in bucket.targets.items():
            last = float(series[-1])
            point[name] = tuple(last for _ in range(self.horizon))

            if quantiles is not None:
                sigma = _residual_std(series)
                sigma_by_step = [sigma * math.sqrt(step) for step in range(1, self.horizon + 1)]
                quantiles[name] = normal_quantile_bands(last, sigma_by_step)

        return Forecast(bucket.series_id, self.horizon, point, quantiles)
