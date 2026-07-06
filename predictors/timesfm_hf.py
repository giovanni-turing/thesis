"""TimesFM-2.0-500m backend (Google) — GPU univariate foundation-model predictor.

Runs the checkpoint staged at models/timesfm/ through its native transformers
integration (`TimesFmModelForPrediction`) — the class the checkpoint was saved
for (config `architectures: [TimesFmModelForPrediction]`). Needs transformers
>= 5.x + torch; the eda venv (models it was validated in) has both.

Univariate only: this checkpoint has no covariate API, so covariates are
dropped — each target series is forecast independently. That is the deliberate
request-rate-blind ablation the thesis argues against, surfaced honestly rather
than hidden. Every (bucket, target) becomes one series in a single batched
forward call; results are scattered back per bucket. `full_predictions[..., 0]`
is the point head and `[..., 1:10]` the 9 quantile heads (levels 0.1..0.9) —
note the model card flags these quantile heads as experimental / uncalibrated.
"""

from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path

import numpy as np

from predictor import QUANTILE_LEVELS, Bucket, Forecast, Predictor

_DEFAULT_DIR = Path(__file__).resolve().parent.parent / "models" / "timesfm"


class TimesFMPredictor(Predictor):
    """Google TimesFM-2.0-500m via transformers; univariate, covariate-blind.

    `freq` is TimesFM's categorical frequency indicator (0 = high-frequency /
    up to daily granularity — correct for the per-minute pool signals; 1 =
    weekly/monthly; 2 = quarterly+).
    """

    def __init__(
        self,
        horizon: int = 10,
        *,
        freq_s: float,
        model_dir: str | Path = _DEFAULT_DIR,
        device: str | None = None,
        freq: int = 0,
        batch_size: int = 64,
        return_quantiles: bool = True,
        clip_min: float | None = 0.0,
    ) -> None:
        super().__init__(horizon, freq_s=freq_s, return_quantiles=return_quantiles, clip_min=clip_min)
        import torch
        from transformers import TimesFmModelForPrediction

        torch.set_float32_matmul_precision("high")
        self._torch = torch
        self._batch_size = batch_size
        self.freq = freq
        self.device = torch.device(device or ("cuda" if torch.cuda.is_available() else "cpu"))
        self.model = (
            TimesFmModelForPrediction.from_pretrained(str(model_dir), torch_dtype=torch.float32)
            .to(self.device)
            .eval()
        )
        self.model.horizon_len = horizon  # decode/truncate to exactly this many steps

    @property
    def max_batch_size(self) -> int:
        return self._batch_size

    def _predict_batch(self, buckets: Sequence[Bucket]) -> list[Forecast]:
        torch = self._torch

        # Flatten every (bucket, target) series into one batched forward call,
        # remembering which slots belong to which bucket.
        past_values, index = [], []  # index[i] = (bucket_i, target_name)
        for bi, bucket in enumerate(buckets):
            for name, series in bucket.targets.items():
                # np.asarray is a no-op for float32 arrays (the benchmark's hot
                # path); torch.tensor(list(...)) was a per-element copy.
                past_values.append(torch.as_tensor(np.asarray(series, dtype=np.float32), device=self.device))
                index.append((bi, name))

        freq = torch.full((len(past_values),), self.freq, dtype=torch.long, device=self.device)
        with torch.inference_mode():
            out = self.model(past_values=past_values, freq=freq, return_dict=True)
        mean = out.mean_predictions.float().cpu()   # (N, H) point forecast
        full = out.full_predictions.float().cpu()   # (N, H, 10): [point, q0.1..q0.9]

        points: list[dict] = [{} for _ in buckets]
        bands: list[dict | None] = [({} if self.return_quantiles else None) for _ in buckets]
        for i, (bi, name) in enumerate(index):
            points[bi][name] = tuple(mean[i].tolist())
            if bands[bi] is not None:
                bands[bi][name] = tuple(tuple(full[i, :, li + 1].tolist()) for li in range(len(QUANTILE_LEVELS)))

        return [
            Forecast(bucket.series_id, self.horizon, points[bi], bands[bi])
            for bi, bucket in enumerate(buckets)
        ]
