"""Toto-2.0-2.5B backend (Datadog) — GPU multivariate foundation-model predictor.

Runs the checkpoint staged at models/toto/ via the `toto2` package. Requires
that package + a CUDA torch (it lives in models/toto/.venv — run this backend
from that venv). Import is lazy so the rest of `predictors` loads without it.

Batching: BatchExecutor hands us buckets that already share one context length
and one variate set, so a whole chunk stacks into a single
(batch, n_variates, time) tensor and one forecast() call. Within each bucket
every variate (targets first, then covariates) shares one series_id, so Toto's
variate-axis attention mixes covariates into each target — but only the target
variates' forecasts are emitted; covariate outputs are dropped. The point
forecast is the model's 0.5 quantile (median).
"""

from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path

import numpy as np

from predictor import QUANTILE_LEVELS, Bucket, Forecast, Predictor

_DEFAULT_DIR = Path(__file__).resolve().parent.parent / "models" / "toto"

MAX_CONTEXT = 4096   # Toto 2.0 trained context length
PATCH_SIZE = 32      # context must be a patch multiple; shorter inputs are left-padded, masked
DECODE_BLOCK = 768   # single-pass decode size recommended by the model card
_MEDIAN_IDX = QUANTILE_LEVELS.index(0.5)  # the level Toto's median/point forecast lives at


class TotoPredictor(Predictor):
    """Datadog Toto-2.0-2.5B, forecasting all of a bucket's targets jointly with
    its covariates as extra variates under one series id.
    """

    def __init__(
        self,
        horizon: int = 10,
        *,
        freq_s: float,
        model_dir: str | Path = _DEFAULT_DIR,
        device: str | None = None,
        batch_size: int = 64,
        return_quantiles: bool = True,
        clip_min: float | None = 0.0,
    ) -> None:
        super().__init__(horizon, freq_s=freq_s, return_quantiles=return_quantiles, clip_min=clip_min)
        import torch
        from toto2 import Toto2Model

        torch.set_float32_matmul_precision("high")
        self._torch = torch
        self._batch_size = batch_size
        self.device = torch.device(device or ("cuda" if torch.cuda.is_available() else "cpu"))
        self.model = Toto2Model.from_pretrained(str(model_dir)).to(self.device).eval()

    @property
    def max_batch_size(self) -> int:
        return self._batch_size

    def _predict_batch(self, buckets: Sequence[Bucket]) -> list[Forecast]:
        torch = self._torch
        target_names = list(buckets[0].targets)
        cov_names = list(buckets[0].covariates)
        variate_names = target_names + cov_names
        n_targets = len(target_names)

        # (B, V, T): each bucket's target variates first, then its covariates.
        # Stacked in numpy (no-op casts for float32 inputs) — torch.tensor on
        # nested python lists was a per-element copy.
        rows = np.stack(
            [
                np.stack(
                    [
                        np.asarray(({**b.targets, **b.covariates})[name], dtype=np.float32)[-MAX_CONTEXT:]
                        for name in variate_names
                    ]
                )
                for b in buckets
            ]
        )
        ctx = torch.from_numpy(rows).to(self.device)  # (B, V, T)

        pad = (-ctx.shape[-1]) % PATCH_SIZE  # left-pad to a patch multiple, masked as missing
        if pad:
            ctx = torch.cat([torch.zeros(ctx.shape[0], ctx.shape[1], pad, device=self.device), ctx], dim=2)
        mask = torch.ones_like(ctx, dtype=torch.bool)
        if pad:
            mask[..., :pad] = False
        # One series id per (bucket, variate) row, all zero: within a bucket every
        # variate is one multivariate series; the batch axis keeps buckets independent.
        series_ids = torch.zeros(ctx.shape[0], ctx.shape[1], dtype=torch.long, device=self.device)

        with torch.inference_mode():
            q = self.model.forecast(
                {"target": ctx, "target_mask": mask, "series_ids": series_ids},
                horizon=self.horizon,
                decode_block_size=DECODE_BLOCK,
                has_missing_values=pad > 0,
            )
        q = q.float().cpu()  # (9, B, V, H)

        out = []
        for bi, bucket in enumerate(buckets):
            point: dict[str, tuple[float, ...]] = {}
            quantiles: dict[str, tuple[tuple[float, ...], ...]] | None = {} if self.return_quantiles else None
            for vi, name in enumerate(target_names[:n_targets]):
                point[name] = tuple(q[_MEDIAN_IDX, bi, vi, :].tolist())
                if quantiles is not None:
                    quantiles[name] = tuple(tuple(q[li, bi, vi, :].tolist()) for li in range(len(QUANTILE_LEVELS)))
            out.append(Forecast(bucket.series_id, self.horizon, point, quantiles))
        return out
