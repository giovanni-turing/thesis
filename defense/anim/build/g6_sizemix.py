#!/usr/bin/env python3
"""G6 — image-size-mixture encoder cost model (the reprice kernel).

Closes the `tex/intro.tex` Scope caveat: *"The trace records image counts, not
sizes, so the encoder pool assumes a uniform 448^2 image."*  The trace cannot be
made to yield true sizes, so the honest substitute is a **sensitivity sweep**:
reprice the encoder under a set of plausible size distributions and re-run the
same schedules, exactly as Appendix `app:engine-sensitivity` reprices the same
schedule under a different engine's f(N).

NOTE ON PROVENANCE. Every size distribution in this module is ASSUMED. The
Azure trace records image COUNTS only; it carries no size field, and no size
information is recoverable from it. The f(N) curves the mixtures are priced
with are silicon-grounded (AIC's collected rtx_5090 / vllm 0.22.0 DB); the
WEIGHTS are not. Artifacts emitted from this module carry an explicit
`size_distribution_provenance` marker per distribution so the two cannot be
read as equally grounded, and any figure or table built on them must repeat
that label.

What resolution actually changes (AIC source of truth)
------------------------------------------------------
`BaseBackend._encoder_pre_merge_per_visual` turns (H, W) into per-image token
counts using the ViT geometry (Qwen3-VL: patch_size=16, spatial_merge_size=2):

    pre_merge_per_image  = (px // 16)^2        # patches the ViT transformer sees
    tokens_per_image     = (px // 32)^2        # post-merge tokens handed to the LLM

`_run_encoder_phase` then queries each op with
  - non-attention ops : x = n_img_pre (total pre-merge patches), batch 1
  - projector ops     : x = n_img_post (total post-merge tokens), batch 1
  - encoder_attention : varlen — eff_batch = num_images, s = pre_merge_per_image

So cost is superlinear in resolution: measured on this silicon DB (snapshot
graph, rtx_5090 / vllm 0.22.0 / Qwen3-VL-8B), f(64) is

    224^2   74.6 ms   0.24x      672^2   785.6 ms   2.48x
    336^2  169.9 ms   0.54x      896^2  1631.3 ms   5.16x
    448^2  316.4 ms   1.00x     1344^2  5169.3 ms  16.34x

(448^2 f(64) = 316.369 ms is the ledgered thesis anchor — reproduced exactly.)
Patch count grows as px^2 while cost grows a little faster still (448->896 is
4x the patches but 5.16x the cost), the attention term being the superlinear
part.

Resolution is therefore a far stronger lever than the engine-stack gap the
thesis already absorbed. To state that gap correctly (`tex/apendice.tex`
113-117, 186-197): against the engine it targets, AIC's composition stays
within 12.8% across the whole N<=64 serving regime (canonical residuals
-2.2%, +11.3%, +5.5% at N=8/32/64 on vLLM's own vision tower). The
1.4-1.6x figure is NOT the model's error bar -- it is the
HuggingFace-eager execution-stack difference, used in the thesis as an
UPPER-BOUND arm; `tex/closedloop.tex` 625-632 reprices the winning schedule
under that slower f(N) (encoder-delay p99 784 vs 588 ms) and finds the
p90/rho=15 headroom provisions 24-32 workers against the 12-16 required, so
it is absorbed with no added workers. G6 borrows that appendix's METHOD
(reprice the same schedule, re-grade), not its magnitude.

The mixture model
-----------------
A distribution is a dict {px: weight}. For a dispatched batch of T images the
composition is fixed by **largest-remainder (Hamilton) apportionment** of T
across the resolutions by weight, so the batch holds T*w_r images of resolution
r (rounded, summing to exactly T). Cost is then AIC's own op loop over that
heterogeneous image set:

    P = sum_r n_r * pre_r                 # total pre-merge patches
    Q = sum_r n_r * post_r                # total post-merge tokens
    attention  = sum_r  op.query(x = n_r*pre_r, batch_size = n_r, s = pre_r)
    projector  = op.query(x = Q, batch_size = 1, s = Q)
    all others = op.query(x = P, batch_size = 1, s = P)

For a degenerate mixture {px: 1.0} this reduces *algebraically* to
`_run_encoder_phase(num_images=T, image_height=image_width=px)` — a single
resolution class with n_r = T. `selftest_reduction()` asserts that identity
numerically against AIC itself, and the driver refuses to run if it fails.

Honest limits of the model (carried into the report)
----------------------------------------------------
1. **Mean-field composition, not per-request realization.** Images are treated
   as i.i.d. draws from the mixture, and each batch is given its *expected*
   composition. This is the right granularity for a sensitivity sweep (how does
   the verdict move with the assumed distribution) but it does not model
   per-request size variance or size/image-count correlation.
2. **Small-batch quantization.** Apportionment of a small T coarsens the
   mixture (T=1 always draws the modal class). Two diagnostics are reported so
   this can be checked empirically rather than argued:
   `small_batch_lt8_forward_fraction` (share of encoder FORWARDS with T<8, a
   count-weighted number) and `small_batch_lt8_worker_second_fraction` (the
   same share weighted by each forward's modelled latency, i.e. the share of
   encoder worker-seconds actually exposed to the quantization). The
   time-weighted figure is the load-bearing one -- sub-8 batches are by
   definition the cheap ones, so the count-weighted share overstates the
   exposure. At burst peaks the pool batches near the cap.
3. **Extrapolation beyond collected shapes.** At 896^2 a 64-image batch is
   200,704 patches, past the densest part of the collected DB — `encoder_attention`
   reports source "mixed". Per-op source tags are recorded per mixture so any
   claim resting on extrapolated cells is visible.
4. **The FIFO cap stays at 64 images.** This is deliberate: the methodology is
   "reprice the *same* schedule", as in the engine-sensitivity appendix. A
   size-aware deployment would cap batches by *patches*, not images; that is a
   different (better-provisioned) system and is not what is being tested here.
"""

from __future__ import annotations

import math

import aiconfigurator.sdk.models.vit_ops as vit_ops

# ---------------------------------------------------------------------------
# Load-bearing snapshot graph — identical to defense/anim/build/a2_conv_snapshot.py.
# The aiconfigurator venv sits at a data-branch HEAD whose guarded
# `encoder_patch_embed_gemm` op POSTDATES the thesis simulation snapshot. Drop it
# so repriced runs stay comparable to the ledgered endpoints (f(64)=316.369 ms,
# encoder-delay p99 588.37 ms).
# ---------------------------------------------------------------------------
_ORIG_VIT_OPS = vit_ops._vit_transformer_ops


def _snapshot_ops(enc_cfg, tp_size):
    return [op for op in _ORIG_VIT_OPS(enc_cfg, tp_size)
            if op._name != "encoder_patch_embed_gemm"]


vit_ops._vit_transformer_ops = _snapshot_ops

from aiconfigurator.sdk import config as sdk_config          # noqa: E402
from aiconfigurator.sdk.backends.factory import get_backend  # noqa: E402
from aiconfigurator.sdk.models import get_model              # noqa: E402
from aiconfigurator.sdk.perf_database import get_database    # noqa: E402


def apportion(total: int, mix: dict[int, float]) -> dict[int, int]:
    """Largest-remainder apportionment of `total` images across resolutions.

    Deterministic, order-stable (resolutions sorted ascending), and sums to
    exactly `total`. Returns only the classes that received >=1 image.
    """
    if total <= 0:
        return {}
    pxs = sorted(mix)
    wsum = float(sum(mix[p] for p in pxs))
    quota = {p: total * mix[p] / wsum for p in pxs}
    base = {p: int(math.floor(quota[p])) for p in pxs}
    rem = total - sum(base.values())
    if rem:
        # largest fractional remainder first; ties -> smaller px first (stable)
        order = sorted(pxs, key=lambda p: (-(quota[p] - base[p]), p))
        for p in order[:rem]:
            base[p] += 1
    return {p: n for p, n in base.items() if n > 0}


class MixtureEncoderCostModel:
    """Drop-in replacement for `trace_to_two_pool.EncoderCostModel`.

    Exposes exactly the surface the converter uses: `latency_ms`,
    `chunked_service_ms`, `post_merge_tokens`, `tokens_per_image`, `memo_hits`,
    `distinct_sizes_costed`.
    """

    def __init__(
        self,
        mix: dict[int, float],
        *,
        system: str = "rtx_5090",
        backend: str = "vllm",
        version: str = "0.22.0",
        model_name: str = "Qwen/Qwen3-VL-8B-Instruct",
    ) -> None:
        wsum = float(sum(mix.values()))
        if wsum <= 0:
            raise ValueError("mixture weights must sum to > 0")
        self.mix = {int(px): float(w) / wsum for px, w in mix.items() if w > 0}
        self._db = get_database(system=system, backend=backend, version=version)
        self._model = get_model(model_name, sdk_config.ModelConfig(), backend)
        self._backend = get_backend(backend)
        self._enc_cfg = self._model.encoder_config
        self._ops = self._model.encoder_ops
        self._cache: dict[int, tuple[float, int]] = {0: (0.0, 0)}
        self.memo_hits = 0
        self.op_sources: dict[str, str] = {}
        # batch-size accounting, for the small-batch quantization diagnostic
        self.batch_hist: dict[int, int] = {}

        stride = self._enc_cfg.patch_size * self._enc_cfg.spatial_merge_size
        self.pre_per: dict[int, int] = {
            px: (px // self._enc_cfg.patch_size) ** 2 for px in self.mix}
        self.post_per: dict[int, int] = {
            px: (px // stride) ** 2 for px in self.mix}
        # mixture-mean post-merge tokens per image (handoff sizing + ctx delta)
        self._tokens_per_image = int(round(
            sum(self.mix[px] * self.post_per[px] for px in self.mix)))

    # -- properties the converter reads ------------------------------------
    @property
    def tokens_per_image(self) -> int:
        return self._tokens_per_image

    def post_merge_tokens(self, num_images: int) -> int:
        return self._tokens_per_image * max(0, int(num_images))

    @property
    def distinct_sizes_costed(self) -> int:
        return len(self._cache) - 1

    def small_batch_fractions(self, threshold: int = 8) -> dict[str, float]:
        """Small-batch quantization exposure, count- AND time-weighted.

        The count-weighted share overstates the exposure: batches with T<8 are
        by definition the cheap forwards. The worker-second share is the number
        that actually bounds how much of the encoder's modelled cost was priced
        under a coarsened mixture. Both are emitted; the time-weighted one is
        the load-bearing figure.
        """
        counts = self.batch_hist
        tot_n = sum(counts.values())
        small_n = sum(c for n, c in counts.items() if n < threshold)
        tot_ms = small_ms = 0.0
        for n, c in counts.items():
            ms = self._cache.get(n, (0.0, 0))[0] * c
            tot_ms += ms
            if n < threshold:
                small_ms += ms
        return {
            "small_batch_lt8_forward_fraction": round(small_n / tot_n, 4) if tot_n else 0.0,
            "small_batch_lt8_worker_second_fraction": (
                round(small_ms / tot_ms, 4) if tot_ms else 0.0),
            "total_forwards": tot_n,
            "total_encoder_ms_modelled": round(tot_ms, 1),
        }

    # -- the cost kernel ----------------------------------------------------
    def _cost(self, comp: dict[int, int]) -> tuple[float, int]:
        """AIC op-loop cost of ONE forward over a heterogeneous image set."""
        P = sum(n * self.pre_per[px] for px, n in comp.items())
        Q = sum(n * self.post_per[px] for px, n in comp.items())
        total_ms = 0.0
        for op in self._ops:
            name = op._name
            if "encoder_attention" in name:
                # varlen over the image axis: each resolution class is its own
                # (eff_batch = n_r, s = pre_r) query, exactly as AIC does it.
                for px, n in comp.items():
                    s = self.pre_per[px]
                    r = op.query(self._db, x=n * s, batch_size=n, beam_width=1,
                                 s=s, prefix=0,
                                 model_name=getattr(self._model, "model_name", ""))
                    total_ms += float(r)
                    self.op_sources[name] = _merge_src(
                        self.op_sources.get(name), getattr(r, "source", "silicon"))
            else:
                x = Q if "encoder_projector" in name else P
                r = op.query(self._db, x=x, batch_size=1, beam_width=1, s=x,
                             prefix=0,
                             model_name=getattr(self._model, "model_name", ""))
                total_ms += float(r)
                self.op_sources[name] = _merge_src(
                    self.op_sources.get(name), getattr(r, "source", "silicon"))
        return total_ms, Q

    def latency_ms(self, total_images: int) -> tuple[float, int]:
        total_images = int(total_images)
        if total_images <= 0:
            return 0.0, 0
        self.batch_hist[total_images] = self.batch_hist.get(total_images, 0) + 1
        hit = self._cache.get(total_images)
        if hit is not None:
            self.memo_hits += 1
            return hit
        out = self._cost(apportion(total_images, self.mix))
        self._cache[total_images] = out
        return out

    def chunked_service_ms(self, num_images: int, cap: int) -> float:
        full, rem = divmod(int(num_images), cap)
        total = full * self.latency_ms(cap)[0] if full else 0.0
        if rem:
            total += self.latency_ms(rem)[0]
        return total

    # -- correctness gate ---------------------------------------------------
    def selftest_reduction(self, sizes=(1, 3, 8, 17, 32, 64), tol_ms=1e-9) -> None:
        """Assert the mixture kernel reduces EXACTLY to AIC's own encoder phase
        for every single-resolution mixture. This is what licenses reading the
        mixed-distribution numbers as AIC numbers rather than as a re-derivation."""
        for px in sorted(set(list(self.mix) + [448])):
            probe = MixtureEncoderCostModel({px: 1.0})
            for n in sizes:
                mine = probe._cost({px: n})[0]
                rc = sdk_config.RuntimeConfig(batch_size=1, isl=1024, osl=128)
                rc.num_images_per_request = n
                rc.image_height = px
                rc.image_width = px
                lat, _e, _s, _post = self._backend._run_encoder_phase(
                    self._model, self._db, rc, batch_size=1)
                theirs = float(sum(lat.values()))
                if abs(mine - theirs) > tol_ms:
                    raise AssertionError(
                        f"mixture kernel != _run_encoder_phase at px={px} N={n}: "
                        f"{mine!r} vs {theirs!r}")


def _merge_src(existing: str | None, new: str) -> str:
    if existing is None or existing == new:
        return new
    return "mixed"


# ---------------------------------------------------------------------------
# The distribution catalogue.
#   Uniform arms bracket the assumption; mixed arms are the plausible-world
#   arms; the `esc*` ladder is the monotone break-point search (fraction of
#   896^2 "frames"-class images mixed into the 448^2 baseline).
#
# *** EVERY WEIGHT BELOW IS ASSUMED, NOT MEASURED. ***
# The Azure trace has no size field. These are hypotheses about what a
# deployment's image population COULD look like, chosen to bracket and to
# stress the 448^2 assumption; they are not an estimate of any real
# population. Only the f(N) cost of a given mixture is grounded (AIC silicon
# DB). SIZE_PROVENANCE below is emitted verbatim into every artifact.
# ---------------------------------------------------------------------------
SIZE_PROVENANCE = ("ASSUMED - the Azure trace records image counts only; "
                   "no measured size basis. Weights are hypothesised, not "
                   "estimated; only the f(N) cost of each mixture is "
                   "silicon-grounded.")

# One line per catalogue entry: what world the mixture is meant to represent.
DISTRIBUTION_RATIONALE: dict[str, str] = {
    "u224": "Lower bracket: thumbnail-class uniform input; the optimistic end "
            "of the assumption.",
    "u336": "Uniform intermediate between thumbnail and the assumed 448.",
    "u448": "CONTROL: the thesis's own uniform-448 assumption. Reproduces the "
            "ledgered endpoints exactly and anchors every multiplier.",
    "u672": "Uniform 1.5x-linear-scale input; the thesis's own back-of-envelope "
            "at tex/twopool.tex:437-441 guesses ~2.25x dearer here (model: 2.48x).",
    "u896": "Upper bracket: HD-class uniform input; the pessimistic end. Note "
            "encoder_attention is EXTRAPOLATED at 64x896^2 (200,704 patches).",
    "mix_web": "Hypothetical consumer/web-chat world: mostly screenshots and "
               "photos near the assumed size, a long thumbnail tail, a few HD "
               "uploads. Chosen so its mean sits close to 448 -- the arm that "
               "asks whether the assumption survives realistic dispersion.",
    "mix_uniform3": "Maximum-ignorance arm: equal mass on the three bracket "
                    "resolutions. Deliberately uninformative -- it encodes no "
                    "belief about the population, only the spread.",
    "mix_heavytail": "Adversarial/document-and-frames world: mass shifted to "
                     "672-896 (55% combined). The stress arm -- what a "
                     "size-unaware planner faces when the assumption is wrong "
                     "in the expensive direction.",
    **{f"esc{int(q * 100):03d}":
       f"Break-point ladder rung: fraction q={q:.2f} of 896^2 images mixed "
       f"into a 448^2 body. The ladder is a monotone search for where the SLA "
       f"verdict flips, not a claim that q={q:.2f} occurs."
       for q in (0.05, 0.10, 0.15, 0.20, 0.25, 0.30, 0.40, 0.50, 0.75)},
}
DISTRIBUTIONS: dict[str, dict[int, float]] = {
    # --- uniform brackets ---
    "u224":  {224: 1.0},          # thumbnail-class
    "u336":  {336: 1.0},
    "u448":  {448: 1.0},          # BASELINE = the thesis assumption (control)
    "u672":  {672: 1.0},
    "u896":  {896: 1.0},          # HD-class
    # --- plausible mixed worlds ---
    "mix_web":       {224: 0.30, 448: 0.50, 672: 0.15, 896: 0.05},
    "mix_uniform3":  {224: 1 / 3, 448: 1 / 3, 896: 1 / 3},
    "mix_heavytail": {224: 0.10, 448: 0.35, 672: 0.30, 896: 0.25},
    # --- break-point ladder: fraction q of 896^2 against a 448^2 body ---
    **{f"esc{int(q * 100):03d}": {448: 1.0 - q, 896: q}
       for q in (0.05, 0.10, 0.15, 0.20, 0.25, 0.30, 0.40, 0.50, 0.75)},
}

BASELINE = "u448"
