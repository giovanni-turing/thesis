"""Chronos-2 backend (Amazon) — foundation-model predictor with native covariates.

Runs the checkpoint staged at models/chronos/ via `Chronos2Pipeline` from
`chronos-forecasting>=2.0`, through the pipeline's tensor `predict()` API (not
`predict_df` — building million-row DataFrames per batch costs more than the
GPU forward itself). Two input forms, chosen per call:

- No covariates: every (bucket, target) series stacks into one (tasks, 1, T)
  float32 tensor — a single univariate batch; the pipeline sub-batches it
  internally at `batch_size` series per forward.
- With covariates: a list of {"target", "past_covariates"} dicts, one per
  (bucket, target) — Chronos-2's native covariate mechanism. Covariates are
  supplied as *past-only* (no future values are known at forecast time).
  Note the pipeline counts batch_size in *series* (targets + covariates), so
  a task with k covariates packs batch_size/(k+1) tasks per forward.

The checkpoint emits 21 quantile levels; the 9 shared QUANTILE_LEVELS are
selected by index and the 0.5 quantile is taken as the point forecast.
"""

from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path

import numpy as np

from predictor import QUANTILE_LEVELS, Bucket, Forecast, Predictor

_DEFAULT_DIR = Path(__file__).resolve().parent.parent / "models" / "chronos"


class Chronos2Predictor(Predictor):
    """Amazon Chronos-2 (120M encoder-decoder) with native past covariates."""

    def __init__(
        self,
        horizon: int = 10,
        *,
        freq_s: float,
        model_dir: str | Path = _DEFAULT_DIR,
        device: str | None = None,
        batch_size: int = 256,
        return_quantiles: bool = True,
        clip_min: float | None = 0.0,
    ) -> None:
        super().__init__(horizon, freq_s=freq_s, return_quantiles=return_quantiles, clip_min=clip_min)
        import torch
        from chronos import Chronos2Pipeline

        torch.set_float32_matmul_precision("high")
        self._torch = torch
        self._batch_size = batch_size
        device = device or ("cuda" if torch.cuda.is_available() else "cpu")
        self.pipeline = Chronos2Pipeline.from_pretrained(str(model_dir), device_map=device)

        qlevels = [float(q) for q in self.pipeline.quantiles]
        self._q_idx = [qlevels.index(level) for level in QUANTILE_LEVELS]  # raises if unsupported
        self._point_idx = qlevels.index(0.5)

    @property
    def max_batch_size(self) -> int:
        # predict() sub-batches internally at self._batch_size series per
        # forward, so one call can carry many batches' worth of tasks.
        return 16 * self._batch_size

    def _predict_batch(self, buckets: Sequence[Bucket]) -> list[Forecast]:
        torch = self._torch
        target_names = list(buckets[0].targets)
        cov_names = list(buckets[0].covariates)

        # One prediction task per (bucket, target), in a fixed scatter order.
        index = [(bi, name) for bi in range(len(buckets)) for name in target_names]
        if cov_names:
            inputs: list | torch.Tensor = [
                {
                    "target": np.asarray(buckets[bi].targets[name], dtype=np.float32),
                    "past_covariates": {
                        cov: np.asarray(buckets[bi].covariates[cov], dtype=np.float32) for cov in cov_names
                    },
                }
                for bi, name in index
            ]
        else:
            rows = np.stack([np.asarray(buckets[bi].targets[name], dtype=np.float32) for bi, name in index])
            inputs = torch.from_numpy(rows).unsqueeze(1)  # (tasks, 1, T)

        preds = self.pipeline.predict(inputs, prediction_length=self.horizon, batch_size=self._batch_size)

        points: list[dict] = [{} for _ in buckets]
        bands: list[dict | None] = [({} if self.return_quantiles else None) for _ in buckets]
        for (bi, name), pred in zip(index, preds):
            q = pred.squeeze(0).float().cpu().numpy()  # (n_quantiles, H)
            points[bi][name] = tuple(q[self._point_idx].tolist())
            if bands[bi] is not None:
                bands[bi][name] = tuple(tuple(q[qi].tolist()) for qi in self._q_idx)

        return [
            Forecast(bucket.series_id, self.horizon, points[bi], bands[bi])
            for bi, bucket in enumerate(buckets)
        ]
