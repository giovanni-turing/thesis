"""EWMA (simple exponential smoothing) baseline predictor — Phase 4's second
cheap baseline, alongside naive last-value.

No model weights, no covariates: the point forecast is the exponentially
smoothed level at the end of the bucket, held flat across the horizon (SES has
no trend component). SES is equivalent to ARIMA(0,1,1), so the optional
quantile band uses that model's closed-form h-step forecast-error variance
(Hyndman & Athanasopoulos, ch. 8.1): sigma_h^2 = sigma^2 * (1 + alpha^2 (h-1)),
where sigma^2 is the one-step-ahead residual variance of the smoothed level.
"""

from __future__ import annotations

import math
from collections.abc import Sequence

from predictor import DEFAULT_HORIZON, Bucket, Forecast, Predictor, normal_quantile_bands


def _update(level: float, alpha: float, observed: float) -> float:
    return alpha * observed + (1 - alpha) * level


def _smooth(series: Sequence[float], alpha: float) -> tuple[float, float]:
    """Return (final level, one-step residual std) for simple exponential smoothing."""
    level = float(series[0])
    residuals = []
    for y in series[1:]:
        residuals.append(y - level)
        level = _update(level, alpha, y)

    if len(residuals) < 2:
        return level, 0.0
    mean = sum(residuals) / len(residuals)
    var = sum((r - mean) ** 2 for r in residuals) / (len(residuals) - 1)
    return level, math.sqrt(var)


def _extrapolate(level: float, alpha: float, horizon: int) -> tuple[float, ...]:
    """Recursive strategy: emit the current level, then feed it back in as the
    next "observed" point and re-apply the SES update to get the next step.

    For plain SES this is provably a fixed point — _update(level, alpha,
    level) == level for any alpha, since it's a convex combination of level
    with itself — so every step of the loop below emits the same value and
    the horizon is flat. That flatness is a property of the model (no trend
    term), not a shortcut being taken: recursing here (instead of repeating
    the level h times) is what makes this correct-by-construction if a trend
    term is ever added, rather than by cancellation.
    """
    steps = []
    state = level
    for _ in range(horizon):
        steps.append(state)
        state = _update(state, alpha, state)
    return tuple(steps)


class EWMAPredictor(Predictor):
    """Simple exponential smoothing: y_hat[t+k] = level_t for every k in 1..h.

    Covariates are accepted (for interface parity with the other backends) but
    ignored, same as NaivePredictor.
    """

    max_batch_size = 1_000_000  # pure stdlib arithmetic — no native batch-shape constraint

    def __init__(
        self, horizon: int = DEFAULT_HORIZON, *, freq_s: float, alpha: float = 0.3, return_quantiles: bool = True
    ) -> None:
        super().__init__(horizon, freq_s=freq_s, return_quantiles=return_quantiles)
        if not 0.0 < alpha <= 1.0:
            raise ValueError(f"alpha must be in (0, 1], got {alpha}")
        self.alpha = alpha

    def _predict_batch(self, buckets: Sequence[Bucket]) -> list[Forecast]:
        return [self._predict_one(b) for b in buckets]

    def _predict_one(self, bucket: Bucket) -> Forecast:
        point: dict[str, tuple[float, ...]] = {}
        quantiles: dict[str, tuple[tuple[float, ...], ...]] | None = {} if self.return_quantiles else None

        for name, series in bucket.targets.items():
            level, sigma = _smooth(series, self.alpha)
            point[name] = _extrapolate(level, self.alpha, self.horizon)

            if quantiles is not None:
                sigma_by_step = [
                    sigma * math.sqrt(1 + self.alpha**2 * (step - 1)) for step in range(1, self.horizon + 1)
                ]
                quantiles[name] = normal_quantile_bands(level, sigma_by_step)

        return Forecast(bucket.series_id, self.horizon, point, quantiles)
