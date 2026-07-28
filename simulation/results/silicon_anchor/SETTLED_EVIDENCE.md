# Settled burst3 evidence — scope, provenance, and disclosed defects

Committed on the bridge 210/211 boundary: **only the three burst3 cells**
(`reps/burst3__{fc,re,staticC8}/rep001–rep005`) plus the supporting evidence
artifacts listed here. The steady24h, burst4, remaining-window, and
engine-diversity tiers are complete or partial on disk but deliberately
uncommitted; they enter with the separately-scoped integration round
(bridge 199 conditions). Campaign ended 2026-07-28T10:51:56Z: auto-STOP at
15/15 steady24h reps; the daemon banked a partial burst4__staticC8 rep and
exited ("STOP mid-rep (partial banked)").

## Headline evidence (5 reps × 3 cells, tier 1)

burst3 frozen-composition retimed p99 encoder delay, mean ± sd across reps:
fc 782.455 ± 0.270 ms (PASS < 1000 ms), re 22,565.317 ± 0.935 ms,
staticC8 1,397.413 ± 1.140 ms. Banked-sim reconstruction reproduced exactly
in every rep (replayed == banked, e.g. fc p99 589.301 ms). Integrity: the
negative-gates suite (below) verifies every committed rep against all nine
gates; the full-campaign `--all-reps` sweep on 2026-07-28 was 32/32 clean.

## The 1000 ms bound (checklist item 7)

The campaign spec (queue JSON) never declares the pass/fail bound. Declared
here: **1000 ms p99 per-request encoder delay** — the same evaluation bound
used by the simulation comparator (metric-stack SLA); every PASS/BREACH
wording in campaign notes and the audit uses it. It is an evaluation
convention, not a runner gate; the runner measures and banks regardless.

## Queue provenance (item 4)

- Final queue file: `simulation/silicon_anchor_queue.json`, sha256
  `0d7b186bdac139cf5dc4e2cb919960d21dd5e0abd7a7d160296e659f686d609a`,
  committed with this evidence.
- **Defect (disclosed):** `meta.provenance.queue_sha` is `null` in every
  rep.json — the runner never pinned the queue it executed. The dispatch
  inputs it *does* pin (schedule sha, banked stats, dispatch meta) are what
  the reconstruction gate reads, so measurement provenance is unaffected;
  but the tier/ordering/extension config is only recoverable from git
  history plus this pin.
- **Mid-campaign edit (disclosed):** the queue was edited while the daemon
  ran (2026-07-27, between the ~17:37Z reload and the 18:20Z tier change):
  the campaign was EXTENDED with the tier-5 engine-diversity block
  (hf_sdpa / hf_fa2 / vllm_serving fn_sweeps) and the tier-3 steady24h
  block, tiers were REORDERED (author note "REORDER 2": tier 3 calm-day
  promoted over tier 2), `max_attempts_per_rep` 3 → 6, and the vLLM cell's
  absence handling flipped between fail and skip (final state: "preflighted,
  and SKIPPED (not failed) if absent"). **The edit also mangled the queue's
  `design` field**: the original structured object was replaced by a
  truncated stringification with the REORDER note spliced into it. This is
  a metadata-only defect — the runner reads tiers/cells, never `design` —
  and the original design text is recoverable from git history of this
  file. burst3 (tier 1) had completed all five reps before any of this;
  the edit cannot have influenced the committed evidence.

## Manifest excerpt (item 5)

`burst3_manifest_excerpt.jsonl` (307 events, sha256
`883271ba2be4c6291b7b07a2e8b8f4314ff484490f204a2e9de860578d6b3850`) is the
FROZEN burst3-only slice of the live manifest, which itself stays
untracked (it kept growing until campaign end). The excerpt preserves the
full resume history — in particular **burst3__fc rep001 resumed twice**
(from_batch 510 at 03:16:55Z, then 1044 at 03:20:33Z) while its rep.json
records only the last resume; the excerpt is the authoritative record.
`wall_s` on resumed reps is the LAST segment's wall time, not cumulative
(fc rep001 wall_s 781.81 vs busy 1142.4 s); per-batch times are unaffected.

## engine__hf_fa2 annotation (item 6, tier 5 — cells not in this commit)

The tier-5 cell labeled `engine__hf_fa2` (attn `flash_attention_2`) did
NOT engage FA2: its per-N stats are statistically identical to `hf_sdpa`
(banked FA2 is measurably faster at high N: 465.7 vs 511.3 ms at N=64),
and no FA2 kernel evidence exists in its artifacts. Per bridge 199c it
must be described as a **second SDPA measurement**, not an FA2 bound. The
vLLM rerun DOES record its backend (FLASH_ATTN eager). Noted here so the
label cannot be read at face value when tier 5 enters the integration
round.

## Clock/tenancy scope notes (item 10, carried into integration framing)

- Memory clock: both 13801 and 14001 MHz appear across in-gate snapshots
  (allowed set; earlier ledger text said "13801" alone — corrected).
- Any "zero fatal slowdowns" claim is scoped to **trace-replay cells**;
  tier-5 engine cells have no clock.jsonl (throttle evidence comes from
  their run wrappers, a weaker record).
- Calm-day framing for integration: under HF-eager retiming the steady24h
  ordering INVERTS vs burst3 — fc 1,120.875 ± 0.470 and re 1,121.014 ±
  0.163 ms BREACH while staticC8 610.580 ± 0.197 PASSES. The absolutes are
  engine-band-conditional (HF-eager runs ≈1.3–1.6× the AIC/vLLM band); the
  robust relative facts are the fc-vs-re near-tie (0.14 ms) and the
  burst3 ordering. burst4 has no discriminating power at p99 (fc 782.389
  vs re 782.576) with an extreme beyond-p99 tail (max ≈13.6 s), and its
  static cell finished 0/5 — a broken trio: disclose, claim nothing.

## Environment (item 8)

`env_snapshot_2026-07-28.json`: driver 595.84, CUDA 13.2, torch
2.12.1+cu130, transformers 5.13.0, captured from the daemon's own venv
(`eda/.venv`, verified via /proc cmdline) with clock policy and daemon
interpreter evidence.

## Negative gates (item 9, bridge 101)

`verification/silicon_negative_gates.py` — 18 corruption probes through the
runner's own functions (membership drop/dup, request drop/dup, dispatch
reorder/mismatch, schedule sha/content, gate-verdict flip, banked-headline
edit, model/engine/attn fingerprints, out-of-band clock, foreign tenant):
ALL fail loudly. Wired into `provenance/verify_all.sh`. Extractor-side
guards recommended post-campaign (gap analysis in the suite header): hash
`batches.jsonl` into meta.provenance; filter on `reconstruction_gate.pass`
(advisory today); reconcile measured rows vs dispatch log by `batch_idx`;
compare (not just record) the G2/G7 fingerprints.
