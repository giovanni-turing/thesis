#!/usr/bin/env python3
"""A16 — SELF-CONSISTENT (MEAN-FIELD) ENDOGENOUS-DEMAND replay.

  *** WHAT THIS IS, IN ONE SENTENCE ***
  Abandonment and retry decisions are iterated to a FIXED POINT AROUND the
  unmodified discrete-event replay; they are NOT resolved in-clock.  There is no
  Abandon event kind in the mocker (lib/mocker/src/replay/offline/events.rs) and
  agg.rs:228-235 explicitly declines to plumb a per-request deadline.  This is a
  mean-field / user-equilibrium approximation.  Any phrasing that calls it a
  "closed loop inside the simulator", or that implies in-clock causality, is
  FALSE and must not be used in the thesis text, slides or captions.

  Correct framing: "the open-loop limitation is NARROWED from unmodelled to
  bounded-under-a-stated-client-model", not "closed".

NARROWS (does not close) the open-loop limitation stated in tex/closedloop.tex:

    "The replay is OPEN-LOOP: arrivals follow the trace regardless of
    experienced latency, so overload cannot shed or defer demand as clients
    would -- policies are compared under identical offered load ... real
    clients' abandonment, backpressure, or retries under overload could shift
    the realized demand in either direction, which this open-loop replay does
    not model."

================================================================================
1. WHAT IS MODELLED
================================================================================
Each *client* (= one original trace row i) has a patience P_i.  Its experienced
ingress->first-token wait is

    W = enc_delay_i  +  ttft_i          (encoder queue+compute, then language)

* ABANDONMENT.  If W > P_i the client gives up at ingress+P_i.  Its remaining
  work is never done: the row is deleted from the language trace.  Special case
  enc_delay_i > P_i: the client abandons *during encoding* and never reaches the
  language pool at all -- this is deterministic (independent of language load)
  and is the channel through which a collapsed encoder pool (reactive: 16 s p99)
  sheds language demand.
* RETRY.  An abandoner re-submits with probability q, after a backoff
  b_g = base * mult^(g-1) * (1 + U(-jitter,+jitter)), up to G generations.  A
  retry is the SAME prompt (same hash_ids -> the radix cache may serve its
  prefix, which is realistic) arriving later.  Retries ADD load.

(a) relieves overload, (b) amplifies it: the net sign is genuinely unknown a
priori, which is exactly why the thesis flags it as a frontier rather than
asserting a direction.

================================================================================
2. WHY THIS IS NOT DONE INSIDE THE MOCKER  (investigated; see notes below)
================================================================================
The dynamo offline replay (lib/mocker/src/replay/offline/) reads a fully
materialised `Trace` and pushes every row into a BinaryHeap of events before the
clock starts; there is no admission-time callback, no per-request deadline, and
`agg.rs` explicitly declines to plumb a deadline into the worker/engine core
("not worth it for the calibration use case this exists to serve", agg.rs:234).
Adding true in-clock abandonment would mean: a new `Abandon` event kind in
offline/events.rs, cancellation propagation through components/admission.rs +
the router's pending queue + engine.rs mid-prefill, and a retry re-injection
path -- i.e. a real feature in the scheduler core, not a reporting patch like
70c965db26.  That is a multi-day Rust change with its own correctness burden and
it would fork the ledgered engine, so every ledgered number would have to be
re-anchored against a rebuilt binary.

Instead this driver implements demand response as an OUTER MEAN-FIELD FIXED
POINT around the unmodified replay binary.  This is NOT a closed in-clock loop:
demand and congestion are made mutually consistent by iteration, and the causal
ordering WITHIN any single iteration is wrong by construction.  Only the
converged state is interpretable.  The scheme:

    R^(0) = offered composed trace                      (= the ledgered run)
    run   -> per-request waits W^(k)
    smooth-> Wbar (method of successive averages, alpha_k = 1/k)
    apply client model to Wbar -> R^(k+1)
    repeat until the abandon set stops churning

At the fixed point every client's abandon/retry decision is consistent with the
congestion of the run that decision produced.  This is the standard
self-consistent-demand (user-equilibrium / mean-field) construction.

WHAT THIS APPROXIMATION COSTS -- stated plainly, all three are reported:
  (i)  An abandoner is removed *entirely*, so the partial work it consumed
       before giving up (queue slot, possibly part of a prefill) is not charged.
       In the mocker TTFT = router queue + one prefill pass; prefill is
       O(10-100 ms) against patience thresholds of seconds, so the unbilled work
       is small.  `abandoner_entered_prefill_frac` reports the share of
       ABANDONERS whose patience exceeded the imputed router queue wait at their
       arrival bin (so they had reached prefill before giving up), and
       `unbilled_prefill_ms_ub` multiplies that count by the mean observed
       prefill duration -- an UPPER BOUND on the unbilled work.  (The previous
       `abandon_prefill_frac` was computed over SERVED requests and was 1.0 by
       construction; it measured nothing and has been removed.)
       READ THE MAGNITUDE, NOT THE FRACTION.  The fraction saturates at 1.0
       whenever patience (seconds) exceeds the router queue wait (tens of ms):
       measured on burst3/reactive/P2000 the queue wait is genuinely nonzero
       (77 % nonzero, mean 49.7 ms, p99 848.9 ms) but is dwarfed by patience, so
       essentially every abandoner had reached prefill.  What bounds the bias is
       `unbilled_prefill_ms_ub` = 6.16 s of unbilled prefill across 67 abandoners
       in a 2,857-request window -- i.e. approximation cost (i) is negligible,
       now measured rather than asserted.
  (ii) Relief is applied at whole-run granularity, not at the instant of
       abandonment.  Within-iteration causality is therefore wrong; only the
       converged state is meaningful.  Intermediate iterations are diagnostics.
       The iteration can settle into a LIMIT CYCLE rather than a point, and in
       BOTH shipped arms it does (period 2 -- see the `cycle` block of each
       cell, and defense/anim/build/a16_endogenous_report.py which detects it).
       The reported headline is therefore the BAND over the cycle, which is a
       CYCLE ENVELOPE and NOT a bound on a fixed point: the iteration located a
       cycle, and in a map with an attracting 2-cycle the fixed point is
       generically repelling and unobservable.  Its endpoints are moreover
       computed over DIFFERENT populations (2962 vs 2952 served clients in the
       reactive arm), so the envelope brackets a family of quantities rather
       than one quantity, and its midpoint is an interpolation between two
       alternating states -- NOT a point estimate, and never to be quoted as
       one.  `converged` requires BOTH the abandon-set churn AND the observable
       band to be inside tolerance; a True flag means "the observables stopped
       moving within tolerance", NOT "a fixed point was reached".
  (iii) Fixed points need not be unique.  Run the grid from both the open-loop
       start (default) and, with --seed-from-collapsed, from an all-abandon
       start; if both converge to the same demand level the point is stable.

================================================================================
3. THE METHODOLOGICAL CRUX: THE FORECAST STAYS EXOGENOUS
================================================================================
Realized demand now depends on system performance, which depends on policy.  If
the forecast were recomputed from realized demand it would become
policy-dependent and the counterfactual comparison would be destroyed (each arm
would be graded against its own, differently-shaped, demand).  The defensible
decomposition is:

    observable arrival stream = PRIMARY (exogenous) submissions + RETRIES

  * PRIMARY submissions are exogenous and, crucially, are *observed at
    submission time* -- abandonment happens strictly AFTER the client has
    submitted, so the server sees every primary arrival whether or not that
    client later gives up.  The archived rolling-origin forecast, computed
    offline from the trace, is therefore a forecast of exactly the stream a real
    forecaster would see.  It is unchanged, byte-identical, across every cell of
    this experiment.  NOTHING in this driver touches predictors/results/*.
  * RETRY load is endogenous and policy-dependent.  It is deliberately NOT
    forecast.  Retry-induced demand is precisely the component the predictive
    provisioner is blind to, and leaving it unforecast is both physically
    correct and the conservative choice for the forecast arm.

  THERE ARE TWO ASYMMETRIES AND THEY POINT IN OPPOSITE DIRECTIONS.  Both are
  stated; neither is allowed to stand in for the other.

  * ASYMMETRY 1 -- FAVOURS THE BASELINE.  The reactive arm's ARIMA predictor
    runs in-loop on observed throughput, so it *does* see retry load and adapts
    to it; the forecast arm does not.  Under endogenous demand the baseline gets
    a real (if lagged) informational advantage.

  * ASYMMETRY 2 -- FAVOURS THE FORECAST.  The archived forecast is a forecast of
    OFFERED demand, but the replayed trace is the SHED (post-abandonment) one.
    The forecast arm therefore provisions for clients that never show up: it
    receives free headroom precisely in the cells where abandonment bites, at
    unchanged forecast accuracy.

    This is NOT argued away, it is MEASURED.  The control arm `<arm>_ondemand`
    ("forecast on realized demand") replays the identical trace with the
    identical archived forecast, but deflates the capacity conversion
    FORECAST_REQ_SCALE by the realized/offered attempt ratio of that same
    iteration, so provisioning tracks the realized demand LEVEL instead of the
    offered one.  At iteration 0 the ratio is exactly 1, so the control
    reproduces the ledgered A12 anchor bit-for-bit; the gap between `fc_*` and
    `fc_*_ondemand` at the fixed point BOUNDS the size of asymmetry 2.  (It is a
    level correction, not a re-forecast -- re-forecasting realized demand would
    make the forecast policy-dependent and destroy the counterfactual, see
    above.  So it bounds, it does not eliminate.)

  NET SIGN OF THE TWO ASYMMETRIES IS NOT ESTABLISHED A PRIORI.  Do not describe
  the comparison as "conservative for the forecast arm" without qualification.

Everything endogenous stays endogenous: TTFT, queueing, replica decisions and
SLA verdicts are all computed by the unmodified discrete-event mocker from
silicon-calibrated AIC timings.  No forecast is computed in-flight anywhere.

Encoder scope: the encoder pool's provisioning schedule is held at its ledgered
per-arm trajectory (A2/A6 converter outputs); enc_delay_i is recovered from the
composed-trace seam exactly as extract_a12.py does it.  A retry carries its
client's original enc_delay (same image, same pool).  Re-provisioning the
encoder against post-abandonment demand is a second loop this driver does not
attempt.

PER-CHANNEL, NOT BLANKET.  The two encoder-scope choices have OPPOSITE signs and
the net is not established:
  * holding the encoder schedule fixed is CONSERVATIVE FOR THE FORECAST ARM
    (re-provisioning would relieve the collapsed reactive encoder);
  * re-using the client's ORIGINAL enc_delay on a retry is ANTI-CONSERVATIVE for
    the forecast arm / conservative for reactive -- a retry landing in a quiet
    period still pays the collapsed 16 s encoder delay it incurred at its first
    attempt.
Neither the blanket label "conservative for the forecast arm" nor its opposite
is earned; state both channels.

================================================================================
4. METRICS -- AND THE SURVIVORSHIP TRAP
================================================================================
Under abandonment, "p99 TTFT of served requests" is measured on survivors only:
shedding the worst-hit clients makes a collapsing system's dashboard look
BETTER.  Reporting only that number would be actively misleading.  Every
iteration therefore records:

  ttft_p99_served     p99 language TTFT over completed ATTEMPTS (dashboard view)
  e2e_p99_served      p99 (enc+ttft) over completed ATTEMPTS (dashboard view)
  e2e_p99_from_ingress p99 of the CLIENT-side wait, measured from the client's
                      ORIGINAL ingress (see below)
  abandon_rate        unique clients that never got a first token / offered
  n_primary_submitted / n_retry_attempts / n_shed_at_encode / n_realized_attempts
                      the four counters; `retry_amplification` is
                      n_retry_attempts / n_primary_submitted and is 0 when
                      retries are off (the old realized/offered ratio conflated
                      shedding with retries and read BELOW 1 with retries on)
  offered_goodput     PRIMARY HEADLINE: fraction of OFFERED clients that got a
                      first token within the E2E budget, abandoners counted as
                      failures.  Immune to survivorship.
  gpu_hours           from the mocker's own parallelism accounting

CLIENT-SIDE CLOCK -- THE COMPARISON-FAIRNESS FIX.  A retried client's wait is
measured from its ORIGINAL ingress, so the patience it burned before giving up
plus every backoff it served are ALL charged:

    W_client = (arrival_of_the_served_attempt - original_ingress) + ttft
             = sum_g (P_i + backoff_g)  +  enc_i  +  ttft

Scoring a retried client on its final attempt's own wait alone (a client that
waited 5 s, abandoned, backed off 5 s, resubmitted and got a token in 800 ms
counted as meeting a 2000 ms budget) would systematically flatter whichever arm
generates MORE retries -- i.e. the overloaded reactive arm -- and would void the
survivorship-immunity claim above.  At iteration 0 every client has g=0 and
arrival-original_ingress == enc_i, so the client clock collapses to enc+ttft and
the ledgered A12 anchors are reproduced exactly.

================================================================================
5. USAGE
================================================================================
  eda/.venv/bin/python defense/anim/build/gen_a16_endogenous.py \
      --window burst3 --arms fc_chronos,reactive \
      --patience-ms 5000 --retry-frac 0.3 --iters 6

  With the asymmetry-2 control arm (recommended -- see section 3):
      --arms fc_chronos,fc_chronos_ondemand,reactive

  Grid mode (the supervisor's run):  --grid
"""
from __future__ import annotations

import argparse
import collections
import json
import math
import os
import re
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from a16_endogenous_report import detect_cycle  # noqa: E402

ROOT = Path("/home/gio/tese")
OUT = ROOT / "defense/anim/data/a16_runs"
RR = ROOT / "simulation/run_replay.sh"
SRC_PY = ROOT / "ai-dynamo/dynamo/.venv/bin/python"
ENTRY = ROOT / "simulation/replay_with_forecast.py"
SMOKE = ROOT / "simulation/planner_forecast_smoke.json"
LADDER = ROOT / "simulation/results/riders44/planner_ladder_t200_20.json"
FC_CAP4 = ROOT / "simulation/results/live51/planner_fc_twin_cap4.json"
RE_CAP4 = ROOT / "simulation/results/live51/planner_re_twin_cap4.json"
A2 = ROOT / "defense/anim/data/a2_runs"
A2T = ROOT / "defense/anim/data/a2t_runs"
A6 = ROOT / "defense/anim/data/a6_runs"
AGG = ROOT / "simulation/results/aggregate44"

# Stamped into every result file and printed at the end of every run.  The claim
# this driver is allowed to support is bounded by this sentence.
MEANFIELD_NOTE = (
    "SELF-CONSISTENT (MEAN-FIELD) ENDOGENOUS-DEMAND REPLAY: abandonment/retry "
    "decisions are iterated to a self-consistent LIMIT SET AROUND the unmodified "
    "discrete-event replay, NOT resolved in-clock. NOTE: in both shipped arms the "
    "iteration settles into a PERIOD-2 LIMIT CYCLE, not a fixed point -- the "
    "reported band is the CYCLE ENVELOPE, it is not a bound on a fixed point (no "
    "fixed point is shown to lie inside it), its endpoints are computed over "
    "DIFFERENT served populations, and its midpoint is an interpolation between "
    "alternating states rather than a point estimate. The mocker has no Abandon "
    "event kind "
    "(lib/mocker/src/replay/offline/events.rs) and agg.rs:228-235 declines to "
    "plumb a per-request deadline. The open-loop limitation is NARROWED from "
    "unmodelled to bounded-under-a-stated-client-model, NOT closed. Any wording "
    "implying a closed in-clock loop is false."
)

FC_REQ_SCALE = 8.0            # ledgered tail-aware capacity conversion

# The `_ondemand` suffix marks the FORECAST-ON-REALIZED-DEMAND control arm: same
# trace, same archived forecast, but the capacity conversion is deflated by the
# realized/offered attempt ratio so provisioning tracks the realized demand
# level.  It bounds the "forecast provisions against offered demand while
# replaying a shed trace" asymmetry.  See section 3 of the module docstring.
ONDEMAND = "_ondemand"


def base_arm(arm: str) -> str:
    return arm[:-len(ONDEMAND)] if arm.endswith(ONDEMAND) else arm


SLA_TTFT_MS = 1000.0          # thesis language-pool SLA
E2E_BUDGET_MS = 2000.0        # thesis union budget (a12_data meta.union_budget_ms)

# Composed (encoder-folded) trace per (window, arm) -- the ledgered A2/A6/A12
# converter outputs.  READ ONLY; never rewritten in place.
TRACES = {
    ("burst3", "fc_chronos"): A2 / "burst3_forecast_L30.jsonl",
    ("burst3", "fc_toto"): A2T / "burst3_forecast_toto_L30.jsonl",
    ("burst3", "reactive"): A2 / "burst3_reactive_L30.jsonl",
    ("burst5", "fc_chronos"): A2 / "burst5_forecast_L30.jsonl",
    ("burst5", "fc_toto"): A2T / "burst5_forecast_toto_L30.jsonl",
    ("burst5", "reactive"): A2 / "burst5_reactive_L30.jsonl",
    ("burst4", "fc_chronos"): A2 / "burst4_forecast_L30.jsonl",
    ("burst4", "fc_toto"): A2T / "burst4_forecast_toto_L30.jsonl",
    ("burst4", "reactive"): A2 / "burst4_reactive_L30.jsonl",
    ("burst1", "fc_chronos"): A2 / "burst1_forecast_L30.jsonl",
    ("burst1", "fc_toto"): A2T / "burst1_forecast_toto_L30.jsonl",
    ("burst1", "reactive"): A2 / "burst1_reactive_L30.jsonl",
    ("week", "fc_chronos"): AGG / "fc_p90_L30_issuetime.jsonl",
    ("week", "fc_toto"): A6 / "toto_p90_L30.jsonl",
    ("week", "reactive"): A6 / "react_L30.jsonl",
}
T0 = {"burst3": "2024-10-18 10:18:00", "burst5": "2024-10-18 14:32:00",
      "burst4": "2024-10-18 15:37:00", "burst1": "2024-10-21 12:59:00",
      "week": "2024-10-16 21:39:00"}
# planner configs: A12 (the run this driver extends) uses the smoke/ladder pair
# for every window -- keep it identical so iteration 0 reproduces A12 exactly.
CFG: dict = {}
# open-loop (iteration 0) anchors from the ledger, asserted so a broken harness
# cannot silently pass.
# NOTE: these are the A12 *composed-trace* anchors (defense/anim/data/a12_runs/
# verification.json), NOT the A11 grid-trace ones -- this driver replays the
# per-arm encoder-composed traces, so iteration 0 must reproduce A12 exactly.
ANCHOR = {("burst3", "fc_chronos"): 651.1, ("burst3", "fc_toto"): 651.1,
          ("burst3", "reactive"): 10573.7,
          ("burst5", "fc_chronos"): 651.1, ("burst5", "fc_toto"): 651.1,
          ("burst5", "reactive"): 2181.6,
          ("burst4", "fc_chronos"): 651.1, ("burst4", "fc_toto"): 651.1,
          ("burst4", "reactive"): 2807.0,
          ("burst1", "fc_chronos"): 651.1, ("burst1", "fc_toto"): 671.6,
          ("burst1", "reactive"): 1664.7,
          ("week", "fc_chronos"): 651.1, ("week", "fc_toto"): 651.1,
          ("week", "reactive"): 1191.6}


# ---------------------------------------------------------------- window load
def load_window(window: str, arm: str, cache: dict) -> dict:
    """Composed-trace rows + per-row ingress time and encoder delay.

    Encoder delay is recovered from the seam exactly as extract_a12.py does:
    FIFO key-match of (input_length, output_length) between the composed trace
    and the raw CSV window slice, then enc = composed_ts - raw_rel_ts.
    """
    arm = base_arm(arm)   # the control arm replays the identical composed trace
    key = (window, arm)
    if key in cache:
        return cache[key]
    cf = OUT / f"_seam_{window}_{arm}.npz"
    rows = [json.loads(l) for l in open(TRACES[key])]
    if cf.exists():
        z = np.load(cf)
        w = {"rows": rows, "ts": z["ts"], "enc": z["enc"], "ingress": z["ingress"]}
        cache[key] = w
        return w
    wins = json.load(open(ROOT / "defense/anim/data/windows_ext.json"))
    wm = wins["aggregate" if window == "week" else window]
    raw = pd.read_csv(ROOT / "data/AzureLMMInferenceTrace_multimodal.csv.gz")
    tsr = raw["TIMESTAMP"].str.replace("Z", "", regex=False).str.pad(23, "right", "0")
    raw["ts"] = pd.to_datetime(tsr, format="%Y-%m-%dT%H:%M:%S.%f")
    raw = raw.sort_values("ts").reset_index(drop=True)
    sl = raw.iloc[wm["offset"]:wm["offset"] + wm["max_requests"]].reset_index(drop=True)
    rel = ((sl.ts - sl.ts.iloc[0]).dt.total_seconds() * 1000.0).to_numpy()
    key2idx = collections.defaultdict(collections.deque)
    for i, (ci, gi) in enumerate(zip(sl["ContextTokens"], sl["GeneratedTokens"])):
        key2idx[(max(1, int(ci)), max(1, int(gi)))].append(i)
    ts = np.array([r["timestamp"] for r in rows], dtype=float)
    enc = np.empty(len(rows))
    ingress = np.empty(len(rows))
    for li, r in enumerate(rows):
        i = key2idx[(r["input_length"], r["output_length"])].popleft()
        enc[li] = ts[li] - rel[i]
        ingress[li] = rel[i]
    assert (enc >= -1e-6).all(), f"{window}/{arm}: negative encoder delay at seam"
    enc = np.maximum(enc, 0.0)
    OUT.mkdir(parents=True, exist_ok=True)
    np.savez(cf, ts=ts, enc=enc, ingress=ingress)
    w = {"rows": rows, "ts": ts, "enc": enc, "ingress": ingress}
    cache[key] = w
    return w


# --------------------------------------------------------------- client model
class ClientModel:
    """Per-client patience + retry draws.  Common random numbers across arms and
    iterations: every draw is a pure function of (seed, client index, generation),
    so two policies face the SAME clients, and a decision flips only because the
    latency changed -- never because the RNG advanced differently."""

    def __init__(self, a):
        self.a = a
        self.n = None

    def _u(self, salt: int, idx: np.ndarray, gen: int) -> np.ndarray:
        # splitmix-style deterministic hash -> U[0,1); vectorised, order-free.
        with np.errstate(over="ignore"):  # uint64 wraparound is the point
            x = (idx.astype(np.uint64) * np.uint64(0x9E3779B97F4A7C15)
                 ^ np.uint64(self.a.seed) * np.uint64(0xBF58476D1CE4E5B9)
                 ^ np.uint64(gen + 1) * np.uint64(0x94D049BB133111EB)
                 ^ np.uint64(salt) * np.uint64(0xD6E8FEB86659FD93))
            x ^= x >> np.uint64(30); x *= np.uint64(0xBF58476D1CE4E5B9)
            x ^= x >> np.uint64(27); x *= np.uint64(0x94D049BB133111EB)
            x ^= x >> np.uint64(31)
        return (x >> np.uint64(11)).astype(np.float64) / float(1 << 53)

    def patience(self, n: int) -> np.ndarray:
        idx = np.arange(n)
        if self.a.patience_dist == "const":
            return np.full(n, float(self.a.patience_ms))
        u = np.clip(self._u(1, idx, 0), 1e-9, 1 - 1e-9)
        if self.a.patience_dist == "lognormal":
            # median = patience_ms, log-sd = patience_sigma
            z = math.sqrt(2.0) * _erfinv(2 * u - 1)
            return float(self.a.patience_ms) * np.exp(self.a.patience_sigma * z)
        if self.a.patience_dist == "exp":
            return -float(self.a.patience_ms) / math.log(2.0) * np.log(1 - u)
        raise SystemExit(f"unknown patience dist {self.a.patience_dist}")

    def retries(self, n: int, gen: int) -> np.ndarray:
        return self._u(2, np.arange(n), gen) < float(self.a.retry_frac)

    def backoff_ms(self, n: int, gen: int) -> np.ndarray:
        j = (self._u(3, np.arange(n), gen) * 2 - 1) * float(self.a.retry_jitter)
        return (float(self.a.retry_backoff_ms)
                * float(self.a.retry_mult) ** (gen - 1) * (1.0 + j))


def _erfinv(y):
    """Winitzki approximation; adequate for drawing patience (no scipy dep)."""
    a = 0.147
    ln = np.log(1 - y * y)
    t = 2 / (math.pi * a) + ln / 2
    return np.sign(y) * np.sqrt(np.sqrt(t * t - ln / a) - t)


# ------------------------------------------------------------------ the replay
def run_replay(trace: Path, arm: str, window: str, t0: pd.Timestamp,
               tag: str, outdir: Path, req_scale: float = FC_REQ_SCALE) -> dict:
    rep = outdir / f"{tag}.report.json"
    jl = outdir / f"{tag}.requests.jsonl"
    fc_cfg, re_cfg = CFG.get(window, (SMOKE, LADDER))
    env = {**os.environ, "RUST_LOG": "warn", "AIC_TP": "2", "AIC_VER": "0.19.0",
           "REPLAY_PY": str(SRC_PY), "STARTUP_TIME": "60"}
    cfg = re_cfg
    barm = base_arm(arm)
    if barm.startswith("fc_"):
        cfg = fc_cfg
        env.update(REPLAY_ENTRY=str(ENTRY),
                   FORECAST_T0=t0.strftime("%Y-%m-%d %H:%M:%S.%f"),
                   FORECAST_MODEL=barm.split("_", 1)[1], FORECAST_QUANTILE="p90",
                   FORECAST_RESOLUTION="15s",
                   FORECAST_REQ_SCALE=f"{req_scale:.6f}")
    elif arm.endswith(ONDEMAND):
        raise SystemExit(f"{arm}: the _ondemand control is only defined for "
                         f"forecast arms (the reactive planner has no offered-"
                         f"demand forecast to deflate)")
    cmd = ["bash", str(RR), str(trace), "aic", str(rep), "2",
           "--planner-config", str(cfg), "--report-jsonl", str(jl)]
    with open(outdir / f"{tag}.log", "w") as log:
        r = subprocess.run(cmd, stdout=log, stderr=subprocess.STDOUT, env=env)
    if r.returncode != 0:
        raise SystemExit(f"{tag}: replay rc={r.returncode} (see {tag}.log)")
    d = json.load(open(rep))
    n = sum(1 for _ in open(trace))
    ttft = np.full(n, np.nan)
    qwait = np.full(n, np.nan)
    for line in open(jl):
        rr = json.loads(line)
        li = int(re.match(r"request_(\d+)", rr["session_id"]).group(1)) - 1
        if rr.get("ttft_ms") is None:
            continue
        ttft[li] = rr["ttft_ms"]
        fa, ar = rr.get("first_admit_ms"), rr.get("arrival_time_ms")
        qwait[li] = (fa - ar) if (fa is not None and ar is not None) else 0.0
    return {"report": d, "ttft": ttft, "qwait": qwait}


# ------------------------------------------------------------- the outer loop
def pctl(x, q=99.0):
    x = np.asarray(x, dtype=float)
    x = x[~np.isnan(x)]
    if x.size == 0:
        return None
    x = np.sort(x)
    return float(x[min(x.size - 1, int(x.size * q / 100.0))])


def build_realized(w, What, P, cm, a, span_ms):
    """Deterministic rebuild of the realized trace from the smoothed wait field.

    Returns (rows, prov, stats).  prov[j] = (orig_line, generation) for realized
    line j.  A client abandons if its smoothed E2E wait exceeds its patience;
    abandonment during encoding (enc > P) is unconditional.
    """
    n = len(w["rows"])
    rows_out, prov = [], []
    abandoned = np.zeros(n, dtype=bool)
    enc_only = np.zeros(n, dtype=bool)
    attempts = np.zeros(n, dtype=int)
    dropped_tail = 0
    retry_ok = [cm.retries(n, g) for g in range(a.max_retries + 1)]
    boff = [cm.backoff_ms(n, g) if g else np.zeros(n) for g in range(a.max_retries + 1)]
    for li in range(n):
        ing, enc = w["ingress"][li], w["enc"][li]
        g = 0
        while True:
            arr = ing + enc
            if arr > span_ms:
                dropped_tail += 1
                abandoned[li] = True
                break
            if enc > P[li]:
                enc_only[li] = True
                abandoned[li] = True
                break
            Wi = What.get((li, g))
            if Wi is None:
                Wi = enc + What["_field"](arr)
            if Wi <= P[li]:
                rows_out.append((arr, li, g))
                attempts[li] = g + 1
                break
            # abandoned this attempt
            attempts[li] = g + 1
            if g >= a.max_retries or not retry_ok[g][li]:
                abandoned[li] = True
                break
            ing = ing + P[li] + boff[g + 1][li]
            g += 1
    rows_out.sort(key=lambda t: t[0])
    trace_rows, prov = [], []
    for arr, li, g in rows_out:
        r = dict(w["rows"][li])
        r["timestamp"] = round(arr, 3)
        trace_rows.append(r)
        prov.append((li, g))
    return trace_rows, prov, {"abandoned": abandoned, "enc_only": enc_only,
                              "attempts": attempts, "dropped_tail": dropped_tail}


def field_fn(arr_ms, wait, bin_s, span_ms):
    """Binned congestion field tau(t): mean observed language wait by arrival
    bin, used to IMPUTE the wait of clients absent from the current run (they
    were abandoned, so the run cannot observe them).  Nearest non-empty bin
    fallback."""
    nb = max(1, int(span_ms / (bin_s * 1000.0)) + 1)
    b = np.clip((arr_ms / (bin_s * 1000.0)).astype(int), 0, nb - 1)
    ok = ~np.isnan(wait)
    s = np.zeros(nb); c = np.zeros(nb)
    np.add.at(s, b[ok], wait[ok]); np.add.at(c, b[ok], 1)
    tau = np.where(c > 0, s / np.maximum(c, 1), np.nan)
    if np.isnan(tau).all():
        tau[:] = 0.0
    idx = np.arange(nb)
    good = idx[~np.isnan(tau)]
    tau = tau[good[np.abs(idx[:, None] - good[None, :]).argmin(1)]]

    def f(t):
        return float(tau[min(nb - 1, max(0, int(t / (bin_s * 1000.0))))])
    return f


BAND_KEYS = ("ttft_p99_served", "offered_goodput", "abandon_rate",
             "retry_amplification", "gpu_hours", "e2e_p99_served",
             "e2e_p99_from_ingress")


def _band(hist, keys=BAND_KEYS):
    """min/max of each observable over the last 3 completed iterations."""
    tail = [h for h in hist[1:][-3:] if "ttft_p99_served" in h]
    if not tail:
        return {}
    return {k: [min(h[k] for h in tail), max(h[k] for h in tail)]
            for k in keys if all(k in h for h in tail)}


def _band_ok(hist, a) -> bool:
    """True when the OBSERVABLES have stopped moving, not merely the abandon set.

    Guards against declaring convergence on a limit cycle: churn can read ~0
    while ttft_p99/goodput oscillate between two phases.  Needs >=3 iterations
    of history to mean anything.
    """
    tail = [h for h in hist[1:][-3:] if "ttft_p99_served" in h]
    if len(tail) < 3:
        return False
    for k in ("ttft_p99_served", "e2e_p99_from_ingress"):
        v = [h[k] for h in tail if k in h]
        if len(v) == 3 and max(v) > 0 and (max(v) - min(v)) / max(v) > a.band_tol:
            return False
    v = [h["offered_goodput"] for h in tail]
    return (max(v) - min(v)) <= a.band_tol


def run_cell(window: str, arm: str, a) -> dict:
    cache = {}
    w = load_window(window, arm, cache)
    n = len(w["rows"])
    span_ms = float(w["ts"].max()) + a.tail_grace_s * 1000.0
    cm = ClientModel(a)
    P = cm.patience(n)
    base_t0 = pd.Timestamp(T0[window])
    ts0 = float(w["ts"].min())
    cellid = (f"{window}_{arm}_P{a.patience_ms}_{a.patience_dist}"
              f"_q{a.retry_frac}_b{a.retry_backoff_ms}_G{a.max_retries}_s{a.seed}")
    outdir = OUT / cellid
    outdir.mkdir(parents=True, exist_ok=True)

    What: dict = {}
    hist, prev_ab = [], None
    stable = 0
    t0_shifts = []
    for k in range(a.iters + 1):
        if k == 0:
            trace = TRACES[(window, base_arm(arm))]
            prov = [(li, 0) for li in range(n)]
            st = {"abandoned": np.zeros(n, bool), "enc_only": np.zeros(n, bool),
                  "attempts": np.ones(n, int), "dropped_tail": 0}
            t0 = base_t0
            arr = w["ts"].copy()
        else:
            rows, prov, st = build_realized(w, What, P, cm, a, span_ms)
            if not rows:
                hist.append({"iter": k, "collapsed": True})
                break
            trace = outdir / f"iter{k}.trace.jsonl"
            with open(trace, "w") as f:
                for r in rows:
                    f.write(json.dumps(r) + "\n")
            arr = np.array([r["timestamp"] for r in rows])
            # the replay re-zeroes to the first arrival; shift FORECAST_T0 by the
            # same delta so the archived forecast stays aligned to wall time.
            t0 = base_t0 + pd.Timedelta(milliseconds=float(arr.min()) - ts0)
        # fix9: record the forecast-alignment shift so a reviewer can confirm the
        # archived forecast's phase did not move materially with policy.  It is a
        # compensation for the replay re-zeroing to its first arrival, not a leak.
        shift_ms = round(float(arr.min()) - ts0, 3)
        t0_shifts.append(shift_ms)

        # fix6: the forecast-on-realized-demand control deflates the capacity
        # conversion by THIS iteration's realized/offered attempt ratio.  ratio==1
        # at k=0, so the ledgered anchor is reproduced exactly.
        req_scale = FC_REQ_SCALE
        if arm.endswith(ONDEMAND):
            req_scale = FC_REQ_SCALE * (len(prov) / n)

        res = run_replay(Path(trace), arm, window, t0, f"iter{k}", outdir,
                         req_scale=req_scale)
        ttft = res["ttft"]
        served = ~np.isnan(ttft)

        # ---- observed E2E wait per realized line, mapped back to clients ----
        encl = np.array([w["enc"][li] for li, _ in prov])
        Wobs = encl + ttft
        fld = field_fn(arr, ttft, a.field_bin_s, span_ms)
        What = {(li, g): float(Wobs[j]) for j, (li, g) in enumerate(prov)
                if served[j]}
        What["_field"] = fld
        # MSA damping on the smoothed field, applied to keys seen before
        if hist:
            al = 1.0 / (k) if a.damping == "msa" else a.damping_alpha
            prevW = hist[-1]["_What"]
            for key in set(What) | set(prevW):
                if key == "_field":
                    continue
                new = What.get(key)
                old = prevW.get(key)
                if new is None or old is None:
                    continue
                What[key] = old + al * (new - old)

        # ---------------------------- metrics -----------------------------
        # fix1 (COMPARISON FAIRNESS): a retried client's wait is measured from its
        # ORIGINAL ingress, so the patience it burned before abandoning and every
        # backoff it served are charged.  Scoring the final attempt's own wait
        # alone structurally rewards the retry-heavy (overloaded) arm.
        #   W_client = (arrival_of_served_attempt - original_ingress) + ttft
        # At k=0 every g==0 and arr-ingress == enc, so this collapses to enc+ttft
        # and the ledgered A12 anchors are reproduced exactly.
        client_first = {}
        for j, (li, g) in enumerate(prov):
            if served[j]:
                w_client = (float(arr[j]) - float(w["ingress"][li])) + float(ttft[j])
                if li not in client_first or w_client < client_first[li]:
                    client_first[li] = w_client
        n_served_clients = len(client_first)
        ab_rate = 1.0 - n_served_clients / n
        good = sum(1 for v in client_first.values() if v <= a.e2e_budget_ms)
        rep = res["report"]

        # fix2: a REAL probe of approximation cost (i).  An abandoner that had
        # already left the router queue when it gave up had begun prefill, and
        # that work is not charged.  Impute its queue wait from the binned qwait
        # field (it is absent from this run by construction, so it cannot be
        # observed directly) and compare against its patience.
        qw = res["qwait"]
        qfld = field_fn(arr, qw, a.field_bin_s, span_ms)
        ab_idx = np.where(st["abandoned"] & ~st["enc_only"])[0]
        if ab_idx.size:
            qimp = np.array([qfld(float(w["ingress"][li] + w["enc"][li]))
                             for li in ab_idx])
            entered = P[ab_idx] > qimp
            ab_prefill_frac = float(np.mean(entered))
            n_entered = int(entered.sum())
        else:
            ab_prefill_frac, n_entered = 0.0, 0
        pf = (ttft[served] - qw[served])
        mean_prefill_ms = float(np.mean(pf[pf > 0])) if np.any(pf > 0) else 0.0

        n_primary = int((st["attempts"] > 0).sum())
        n_retry_attempts = int(max(0, st["attempts"].sum() - n_primary))
        ab_set = set(np.where(st["abandoned"])[0]) if k else set()
        churn = (len(ab_set ^ prev_ab) / n) if prev_ab is not None else 1.0
        rec = {
            "iter": k,
            "n_offered_clients": n,
            "n_realized_attempts": len(prov),
            # fix8: the old len(prov)/n conflated shedding with retries and read
            # BELOW 1 with retries on.  Split the counters; amplification is now
            # retries per primary submission and is 0 when retries are off.
            "n_primary_submitted": n_primary,
            "n_retry_attempts": n_retry_attempts,
            "n_shed_at_encode": int(st["enc_only"].sum()),
            "retry_amplification": round(n_retry_attempts / max(1, n_primary), 4),
            "realized_over_offered": round(len(prov) / n, 4),
            "n_served_requests": int(served.sum()),
            "abandon_rate": round(ab_rate, 4),
            "abandon_during_encode": int(st["enc_only"].sum()),
            "dropped_past_span": int(st["dropped_tail"]),
            "ttft_p99_served": round(rep["p99_ttft_ms"], 1),
            "itl_p99_served": round(rep["p99_itl_ms"], 1),
            "e2e_p99_served": round(pctl(Wobs[served]) or 0.0, 1),
            "e2e_p99_from_ingress": round(
                pctl(np.array(list(client_first.values()))) or 0.0, 1),
            "offered_goodput": round(good / n, 4),
            "gpu_hours": round(rep["gpu_hours"], 3),
            "abandon_set_churn": round(churn, 4),
            "abandoner_entered_prefill_frac": round(ab_prefill_frac, 4),
            "unbilled_prefill_ms_ub": round(n_entered * mean_prefill_ms, 1),
            "forecast_t0_shift_ms": shift_ms,
            "forecast_req_scale": round(req_scale, 4),
        }
        prev_ab = ab_set
        print(f"  [{cellid}] iter{k}: n={rec['n_realized_attempts']} "
              f"ab={rec['abandon_rate']:.3f} amp={rec['retry_amplification']:.3f} "
              f"ttft_p99={rec['ttft_p99_served']} goodput={rec['offered_goodput']:.4f} "
              f"churn={rec['abandon_set_churn']:.4f}", flush=True)
        rec["_What"] = What
        hist.append(rec)
        if k == 0 and (window, base_arm(arm)) in ANCHOR:
            exp = ANCHOR[(window, base_arm(arm))]
            got = rec["ttft_p99_served"]
            rec["open_loop_anchor"] = exp
            if abs(got - exp) > max(0.5, exp * 0.05):
                raise SystemExit(f"{cellid}: OPEN-LOOP ANCHOR MISMATCH {got} vs {exp}")
        # fix3: churn alone is NOT convergence -- the observables were seen in a
        # visible 2-cycle (e2e_p99 swinging 48 %) while churn read ~0.  Require
        # the OBSERVABLE band over the last 3 iterations to be tight as well.
        if k and churn < a.eps and _band_ok(hist, a):
            stable += 1
            if stable >= 2:
                break
        else:
            stable = 0

    for h in hist:
        h.pop("_What", None)
    ol, fp = hist[0], hist[-1]
    # The iteration settles into a small limit cycle rather than a point
    # (removing clients relieves load, which re-admits some of them) -- period 2
    # in both shipped arms.  The BAND over the cycle is the headline, but it is
    # a CYCLE ENVELOPE, not a bound on a fixed point, and its midpoint is an
    # interpolation between alternating states, NOT a point estimate.  A single
    # iterate is never quoted at all.
    band = _band(hist)
    cyc = detect_cycle(hist)
    mid = {k: round((v[0] + v[1]) / 2.0, 4) for k, v in band.items()}
    converged = bool(fp.get("abandon_set_churn", 1) < a.eps
                     and not fp.get("collapsed") and _band_ok(hist, a))
    out = {"cell": cellid, "window": window, "arm": arm,
           "is_ondemand_control": arm.endswith(ONDEMAND),
           "approximation": "mean-field self-consistent limit set around the "
                            "unmodified discrete-event replay; abandonment/retry "
                            "is NOT resolved in-clock. The iteration settles into "
                            "a period-2 limit cycle, NOT a fixed point (see "
                            "`cycle`); quote the envelope, never a single iterate "
                            "and never the midpoint as a point estimate.",
           "params": {k: v for k, v in vars(a).items() if not callable(v)},
           "fixed_assumptions": {k: getattr(a, k) for k in
                                 ("retry_mult", "retry_jitter", "patience_sigma",
                                  "patience_dist", "max_retries",
                                  "retry_backoff_ms", "field_bin_s", "seed")},
           "forecast_t0_shift_ms": t0_shifts,
           "iterations": hist,
           "converged": converged,
           "converged_churn_only": bool(fp.get("abandon_set_churn", 1) < a.eps),
           "collapsed": bool(fp.get("collapsed", False)),
           "open_loop": {k: ol.get(k) for k in
                         ("ttft_p99_served", "offered_goodput", "gpu_hours",
                          "n_realized_attempts")},
           # headline: the CYCLE ENVELOPE.  `last_iterate` is retained for
           # traceability ONLY -- it is one phase of a 2-cycle and must never be
           # quoted, alone or as a point estimate.
           "cycle": cyc,
           "headline_band": band,
           "headline_band_semantics":
               "CYCLE ENVELOPE over the reported tail. NOT a bound on a fixed "
               "point and NOT a confidence interval; endpoints come from "
               "different served populations (see cycle.phases).",
           "headline_midpoint": mid,
           "headline_midpoint_semantics":
               "Interpolation between alternating cycle phases. NOT a point "
               "estimate; do not quote it as one.",
           "last_iterate": {k: fp.get(k) for k in
                            ("ttft_p99_served", "offered_goodput", "abandon_rate",
                             "retry_amplification", "gpu_hours",
                             "n_realized_attempts")},
           "last_iterate_semantics":
               "One phase of the limit cycle, kept for traceability only. Never "
               "quotable, alone or as a point estimate.",
           # deprecated aliases: the run never located a fixed point.
           "fixed_point__DEPRECATED_no_fixed_point_was_located":
               {k: fp.get(k) for k in
                ("ttft_p99_served", "offered_goodput", "abandon_rate",
                 "retry_amplification", "gpu_hours", "n_realized_attempts")},
           "fixed_point_band__DEPRECATED_this_is_a_cycle_envelope": band}
    (outdir / "cell.json").write_text(json.dumps(out, indent=1, default=str))
    return out


# ------------------------------------------------------------------------ CLI
# (patience_ms, retry_frac, retry_backoff_ms, max_retries).
# Backoff is LOAD-BEARING: retries land at ing + P_i + backoff, so whether they
# re-enter inside or outside the congestion episode determines the SIGN of the
# net effect -- the exact quantity the thesis says is unknown a priori.  Sweeping
# only patience x retry_frac would leave that question unasked.  The backoff and
# max_retries legs are anchored at the (5000, 0.3) centre point.
_B, _G = 5000, 2
GRID = [
    (2000, 0.0, _B, _G), (2000, 0.3, _B, _G), (2000, 0.6, _B, _G),
    (5000, 0.0, _B, _G), (5000, 0.3, _B, _G), (5000, 0.6, _B, _G),
    (15000, 0.0, _B, _G), (15000, 0.3, _B, _G), (15000, 0.6, _B, _G),
    (60000, 0.3, _B, _G),
    # backoff leg at the centre point (5000 is the centre cell above)
    (5000, 0.3, 1000, _G), (5000, 0.3, 30000, _G),
    # max_retries leg at the centre point
    (5000, 0.3, _B, 1), (5000, 0.3, _B, 4),
]


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--window", default="burst3")
    p.add_argument("--arms", default="fc_chronos,reactive")
    p.add_argument("--patience-ms", type=float, default=5000)
    p.add_argument("--patience-dist", default="lognormal",
                   choices=["const", "lognormal", "exp"])
    p.add_argument("--patience-sigma", type=float, default=0.6)
    p.add_argument("--retry-frac", type=float, default=0.3)
    p.add_argument("--retry-backoff-ms", type=float, default=5000)
    p.add_argument("--retry-mult", type=float, default=2.0)
    p.add_argument("--retry-jitter", type=float, default=0.25)
    p.add_argument("--max-retries", type=int, default=2)
    p.add_argument("--iters", type=int, default=6)
    p.add_argument("--eps", type=float, default=0.005)
    p.add_argument("--band-tol", type=float, default=0.05,
                   help="relative band width over the last 3 iterations that "
                        "the observables must be inside before `converged` is "
                        "reported (churn alone is not enough -- see _band_ok)")
    p.add_argument("--damping", default="msa", choices=["msa", "fixed", "none"])
    p.add_argument("--damping-alpha", type=float, default=0.5)
    p.add_argument("--field-bin-s", type=float, default=60.0)
    p.add_argument("--tail-grace-s", type=float, default=600.0)
    p.add_argument("--e2e-budget-ms", type=float, default=E2E_BUDGET_MS)
    p.add_argument("--seed", type=int, default=20260719)
    p.add_argument("--conc", type=int, default=3)
    p.add_argument("--grid", action="store_true")
    p.add_argument("--out-name", default="verification.json")
    a = p.parse_args()
    if a.damping == "none":
        a.damping, a.damping_alpha = "fixed", 1.0
    OUT.mkdir(parents=True, exist_ok=True)
    arms = a.arms.split(",")
    cells = []
    if a.grid:
        for pm, q, bo, gmax in GRID:
            for arm in arms:
                b = argparse.Namespace(**vars(a))
                b.patience_ms, b.retry_frac = pm, q
                b.retry_backoff_ms, b.max_retries = bo, gmax
                cells.append((a.window, arm, b))
    else:
        cells = [(a.window, arm, a) for arm in arms]
    # warm the seam cache serially (pandas CSV read is not worth parallelising)
    cache = {}
    for wnd, arm, _ in cells:
        load_window(wnd, arm, cache)
    results = {}
    with ThreadPoolExecutor(max_workers=a.conc) as ex:
        for out in ex.map(lambda c: run_cell(*c), cells):
            results[out["cell"]] = out
    payload = {"_note": MEANFIELD_NOTE, "cells": results}
    (OUT / a.out_name).write_text(json.dumps(payload, indent=1, default=str))
    print(f"\n{len(results)} cells -> {OUT / a.out_name}")
    print(f"\n{MEANFIELD_NOTE}\n")
    print_summary(results)


# fix4: the collapse path (build_realized returned no rows) leaves every
# observable None; format defensively instead of raising TypeError after the
# results have already been written.
def print_summary(results):
    def _n(v, w=8):
        return f"{v:>{w}}" if v is not None else f"{'n/a':>{w}}"

    def _f(v, fmt=".4f"):
        return format(v, fmt) if v is not None else "n/a"

    for cid, o in results.items():
        ol, fp = o["open_loop"], o["last_iterate"]
        bd, cy = o.get("headline_band", {}), o.get("cycle", {})
        if o.get("collapsed"):
            print(f"{cid}\n    COLLAPSED (no realized rows in the limit set) "
                  f"-- open-loop ttft_p99={_n(ol.get('ttft_p99_served'))}")
            continue
        tb = bd.get("ttft_p99_served"); gb = bd.get("offered_goodput")
        per = cy.get("period")
        lab = ("PERIOD-%s LIMIT CYCLE" % per if per and per > 1 else
               "FIXED POINT (period 1)" if per == 1 else
               "NO PERIOD <= 3 DETECTED (limit set unresolved)")
        print(f"{cid}\n    limit set  {lab}")
        for ph in cy.get("phases", []):
            print(f"      phase {ph['phase']} (iterates {ph['iterates']}): "
                  f"n_served={ph.get('n_realized_attempts')} "
                  f"ttft_p99={ph.get('ttft_p99_served')} "
                  f"goodput={ph.get('offered_goodput')} "
                  f"ab={ph.get('abandon_rate')}")
        print(f"    open-loop  ttft_p99={_n(ol.get('ttft_p99_served'))} "
              f"goodput={_f(ol.get('offered_goodput'))} "
              f"n={ol.get('n_realized_attempts')}"
              f"\n    headline   ttft_p99 envelope={tb} goodput envelope={gb}"
              f"\n               ENVELOPE over the cycle -- NOT a bound on a "
              f"fixed point (none was located); endpoints come from DIFFERENT "
              f"served populations; the midpoint is an interpolation between "
              f"phases and is NOT a point estimate; no single iterate is "
              f"quotable."
              f"\n    last iter  (traceability only, NOT quotable) "
              f"ttft_p99={_n(fp.get('ttft_p99_served'))} "
              f"goodput={_f(fp.get('offered_goodput'))} "
              f"n={fp.get('n_realized_attempts')} "
              f"ab={_f(fp.get('abandon_rate'), '.3f')}"
              f"\n    conv={o['converged']} "
              f"(churn-only={o.get('converged_churn_only')}) -- 'converged' "
              f"means the observables stopped moving within tolerance, NOT that "
              f"a fixed point was reached")


if __name__ == "__main__":
    main()
