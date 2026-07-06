"""Holt-Winters (triple exponential smoothing) baseline predictor — Phase 4's
third cheap baseline, strengthening EWMA with trend + seasonality.

No model weights, no covariates: fits an additive level + trend + seasonal
decomposition (Hyndman & Athanasopoulos, ch. 8.3) over the bucket's own
target history and extrapolates it linearly (with the seasonal component
repeating every `seasonal_periods` steps) across the horizon — unlike
EWMAPredictor's flat forecast, this one can trend and repeat a diurnal/weekly
shape. The optional quantile band reuses Holt's linear-trend closed-form
h-step variance (same formula as a trend-only model); it does not add extra
variance for seasonal-index uncertainty, which is a deliberate cheap-baseline
simplification, not a claim of exact coverage.
"""

from __future__ import annotations

import math
from collections.abc import Sequence

from predictor import DEFAULT_HORIZON, Bucket, Forecast, Predictor, normal_quantile_bands


def _fit(series: Sequence[float], alpha: float, beta: float, gamma: float, m: int) -> tuple[float, float, list[float], float]:
    """Fit additive Holt-Winters over `series`; return (level, trend, seasonal buffer, one-step residual std).

    `seasonal[i]` holds the latest smoothed seasonal estimate for calendar
    phase `i` (i.e. time index t where t % m == i); it is a circular buffer,
    not a fixed-length forecast — see _extrapolate for how it is read forward.
    """
    n = len(series)
    season1, season2 = series[:m], series[m : 2 * m]
    level = sum(season1) / m
    trend = (sum(season2) - sum(season1)) / (m * m)
    seasonal = [season1[i] - level for i in range(m)]

    residuals = []
    for t in range(m, n):
        y = series[t]
        s_prev = seasonal[t % m]
        residuals.append(y - (level + trend + s_prev))

        new_level = alpha * (y - s_prev) + (1 - alpha) * (level + trend)
        new_trend = beta * (new_level - level) + (1 - beta) * trend
        seasonal[t % m] = gamma * (y - level - trend) + (1 - gamma) * s_prev
        level, trend = new_level, new_trend

    if len(residuals) < 2:
        return level, trend, seasonal, 0.0
    mean = sum(residuals) / len(residuals)
    var = sum((r - mean) ** 2 for r in residuals) / (len(residuals) - 1)
    return level, trend, seasonal, math.sqrt(var)


def _extrapolate(level: float, trend: float, seasonal: list[float], last_t: int, horizon: int) -> tuple[float, ...]:
    m = len(seasonal)
    return tuple(level + h * trend + seasonal[(last_t + h) % m] for h in range(1, horizon + 1))


def _trend_sigma_by_step(sigma: float, alpha: float, beta: float, horizon: int) -> list[float]:
    """Holt's linear-trend h-step forecast-error std (Hyndman ch. 8.2, eq. 8.17)."""
    acc, out = 0.0, []
    for h in range(1, horizon + 1):
        out.append(sigma * math.sqrt(1 + acc))
        acc += (alpha + h * alpha * beta) ** 2
    return out


class HoltWintersPredictor(Predictor):
    """Additive Holt-Winters: y_hat[t+h] = level_t + h*trend_t + seasonal[(t+h) % m].

    Requires at least two full seasonal cycles of context (`2 * seasonal_periods`
    points) to initialize level/trend/seasonal — buckets shorter than that
    raise ValueError rather than silently degrading to a non-seasonal fit.
    Covariates are accepted (for interface parity with the other backends)
    but ignored.
    """

    max_batch_size = 1_000_000  # pure stdlib arithmetic — no native batch-shape constraint

    def __init__(
        self,
        horizon: int = DEFAULT_HORIZON,
        *,
        freq_s: float,
        seasonal_periods: int,
        alpha: float = 0.3,
        beta: float = 0.1,
        gamma: float = 0.1,
        return_quantiles: bool = True,
    ) -> None:
        super().__init__(horizon, freq_s=freq_s, return_quantiles=return_quantiles)
        if seasonal_periods < 2:
            raise ValueError(f"seasonal_periods must be >= 2, got {seasonal_periods}")
        for pname, pval in (("alpha", alpha), ("beta", beta), ("gamma", gamma)):
            if not 0.0 < pval <= 1.0:
                raise ValueError(f"{pname} must be in (0, 1], got {pval}")
        self.seasonal_periods = seasonal_periods
        self.alpha, self.beta, self.gamma = alpha, beta, gamma

    def _predict_batch(self, buckets: Sequence[Bucket]) -> list[Forecast]:
        return [self._predict_one(b) for b in buckets]

    def _predict_one(self, bucket: Bucket) -> Forecast:
        m = self.seasonal_periods
        point: dict[str, tuple[float, ...]] = {}
        quantiles: dict[str, tuple[tuple[float, ...], ...]] | None = {} if self.return_quantiles else None

        for name, series in bucket.targets.items():
            if len(series) < 2 * m:
                raise ValueError(
                    f"{bucket.series_id}/{name}: need >= {2 * m} points for seasonal_periods={m}, got {len(series)}"
                )
            level, trend, seasonal, sigma = _fit(series, self.alpha, self.beta, self.gamma, m)
            steps = _extrapolate(level, trend, seasonal, len(series) - 1, self.horizon)
            point[name] = steps

            if quantiles is not None:
                sigma_by_step = _trend_sigma_by_step(sigma, self.alpha, self.beta, self.horizon)
                quantiles[name] = normal_quantile_bands(steps, sigma_by_step)

        return Forecast(bucket.series_id, self.horizon, point, quantiles)
