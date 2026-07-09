"""Live-vs-offline FPM parity patch (Phase 5.1 validation anchor).

The OFFLINE replay feeds EVERY engine forward-pass metric into the
planner's perf-model regression (replay_adapter.py
``_feed_extra_fpm_to_regression`` — "Feed ALL non-idle snapshots directly
to the regression models for a representative fit"). The LIVE planner
instead samples only the LAST FPM per worker per load tick
(``FpmEventSubscriber`` tracking mode -> ``get_recent_stats``). At calm
load, mixed prefill+decode iterations are rare events, so the aggregated
(Mixed) sample store starves and throughput scaling reports
``model_not_ready`` indefinitely — measured here: zero mixed samples in
5 minutes at 2 req/s, while the offline twin is ready at its first tick.
This is an upstream live-path gap (candidate issue/PR), not a policy
choice; this patch restores offline semantics at the harness level.

Mechanism: alongside the planner's own tracking-mode subscriber, start a
second recv-mode subscriber per component whose blocking ``recv()``
(GIL-released) drains every published FPM into a buffer; each
``_collect_fpm()`` tick hands the buffer to the agg regression through
its list API (``load_benchmark_fpms`` — the same ``_tune`` path the
offline extra-feed uses). The ``FpmObservations`` returned to the policy
plugins remain the stock last-per-worker dict: control-law inputs are
unchanged; only the perf-model sample stream gains the passes the stock
live path drops.
"""
from __future__ import annotations

import logging
import threading

from dynamo.common.forward_pass_metrics import decode as decode_fpm
from dynamo.planner.core import base as _base

logger = logging.getLogger("planner_live_patch")

_BUF: list = []
_LOCK = threading.Lock()
_DIAG_N = 0
_KEEP: list = []  # (thread, subscriber) — keep refs alive

_orig_init = _base.NativePlannerBase._init_fpm_subscriber
_orig_collect = _base.NativePlannerBase._collect_fpm


async def _init_fpm_subscriber(self, component: str) -> None:
    await _orig_init(self, component)
    from dynamo.llm import FpmEventSubscriber

    worker_info = (
        self.prefill_worker_info
        if component == "prefill"
        else self.decode_worker_info
    )
    if not worker_info.component_name or not worker_info.endpoint:
        return
    assert self.runtime is not None
    ep = self.runtime.endpoint(
        f"{self.runtime_namespace}.{worker_info.component_name}."
        f"{worker_info.endpoint}"
    )
    sub = FpmEventSubscriber(ep)

    def drain() -> None:
        while True:
            try:
                payload = sub.recv()  # blocking; releases the GIL
            except Exception:
                return
            if payload is None:
                return
            fpm = decode_fpm(payload)
            if fpm is not None:
                with _LOCK:
                    _BUF.append(fpm)

    t = threading.Thread(target=drain, daemon=True,
                         name=f"fpm-drain-{component}")
    t.start()
    _KEEP.append((t, sub))
    logger.info("[parity patch] drain-all FPM subscriber started (%s)",
                component)


def _collect_fpm(self):
    obs = _orig_collect(self)
    with _LOCK:
        snap = list(_BUF)
        _BUF.clear()
    if snap:
        try:
            eng = getattr(self, "_engine", None)
            state = getattr(eng, "_scaling_state", None)
            reg = getattr(state, "_agg_regression", None)
            if reg is not None:
                # Mirror replay_adapter._feed_extra_fpm_to_regression
                # exactly: per-FPM add_observations keyed by the real
                # worker (counts as OBSERVATIONS — load_benchmark_fpms
                # seeds do not advance the readiness counter), excluding
                # the last snapshot per worker (that one arrives via the
                # stock tracking-mode obs, avoiding a double count).
                last_idx: dict = {}
                for i, fpm in enumerate(snap):
                    last_idx[(fpm.worker_id, fpm.dp_rank)] = i
                exclude = set(last_idx.values())
                fed = 0
                for i, fpm in enumerate(snap):
                    if i in exclude or fpm.wall_time <= 0.0:
                        continue
                    reg.add_observations({(fpm.worker_id, fpm.dp_rank): fpm})
                    fed += 1
                logger.info("[parity patch] fed %d drained FPMs", fed)
                global _DIAG_N
                _DIAG_N += 1
                if _DIAG_N % 6 == 1:  # every ~30 s at 5-s ticks
                    logger.info("[parity patch] diag=%s limits=%s",
                                reg._rust_diagnostics(),
                                reg._limit_values())
        except Exception as e:  # never take the planner down
            logger.warning("[parity patch] drain feed failed: %s", e)
    return obs


_base.NativePlannerBase._init_fpm_subscriber = _init_fpm_subscriber
_base.NativePlannerBase._collect_fpm = _collect_fpm
logger.info("[parity patch] installed (drain-all FPM -> agg regression)")
