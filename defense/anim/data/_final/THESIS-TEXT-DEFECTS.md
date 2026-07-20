# Defects found IN THE THESIS TEXT (not in the new measurements)

## 1. tex/twopool.tex:76-77 — MY DIAGNOSIS IS REFUTED. **Do NOT requote 882 -> 783.**
The proposed fix is withdrawn. `simulation/results/235b/llm_head2k_aic235btp8_s{1,4,16}.json` are
all **old-schema (wheel)** files carrying the wheel `max_ttft` signature, and the published
398 / 1,402 / 14.9 / 7.9 / 87.7 all match wheel values to the digit. **The entire Family-transfer
paragraph is wheel on BOTH arms — internally consistent, not runtime-mixed.** The "307" coincides
with the source build's 307.36 only because the two runtimes agree to 0.2% at s=1. Substituting
882 -> 783 would **CREATE** the mixing defect it purports to fix. No such edit may be made.

**Two real defects instead:**
- **1a. `:69`'s "extreme tail only (identical p99)" over-generalises.** True at s=1 (+0.2%), false
  at s=2 (-5.7%), s=4 (-11.3%), s=16 (+22.1% TTFT / -61.1% ITL). Narrow the claim:
  "...inflated the extreme tail (identical p99 at $s{=}1$; the two runtimes diverge with distance
  from the knee, by up to 22\% in TTFT p99 and 61\% in ITL p99 at $s{=}16$)."
- **1b. The 4x column is indefensible** (this card missed it). The source build gives the 235B
  **20,032.8 ms** against the published **1,402 ms** — a 14.3x divergence on the same 2,000
  requests, same tokens, comparable e2e p99 (72.7 vs 69.0 s). That is systematic TTFT accounting
  divergence under queueing, not a tail effect. **Delete the 4x column; keep the 1x pair** (agrees
  within 2.7% across runtimes). Deleting rather than substituting also respects R26, since the
  source values live in post-manuscript `g3_32b/`.

The underlying pattern stands: divergence is a function of DISTANCE FROM THE KNEE, not of arm or
MoE-ness — 8B-TP1 agrees to +0.2% at s=1 and -0.3% at s=3 but diverges to +22.1% TTFT / -61.1% ITL
at s=16.

## 2. simulation/results/sweeps/reports/ is RUNTIME-MIXED — conclusion CONFIRMED, **my proof was FALSE**
The conclusion holds, but the evidence I gave for it must not be repeated. `llm_head2k_aic_s3`'s
`max_ttft` 4543.39 is **NOT** "identical to the source build" — the source build reads **4517.57**.
It matches `g3_32b/8b_tp1_s3` to the digit (74-key identical schema, 29 bit-identical fields, the
rest within 0.3%). Right conclusion, wrong comparison.
Also: there are **four** source-schema files, not one — all three `llm_burst1_aic_*` were missed.
And **mtime is not the discriminator** (`llm_head2k_poly_s3` is dated 07-08 and is old-schema);
the `gpu_hours` key set is.

**Impact:** `sweep_curve (llm, head2k, aic)` crosses the runtime boundary, and its s=3 point sets
the knee. **The knee is robust:** ITL 109.51 (ingested) and 108.48 (source rerun) **both breach**
the 100 ms bound; s=2 passes either way; the independent fine sweep brackets it at s=2.8158.
`tab:sim-knees` is affected **in provenance only** — its steady AIC row is wheel while its burst
row and the 748 ms caption figure are source.
**Required: NO NUMERIC EDIT.** (i) a caption disclosure that the sweep set is not
runtime-homogeneous, and (ii) a `runtime` column backfill on `provenance.sweep_point`.

## 3. tex/intro.tex:504 and :148 — "offered-work upper bound" is not supportable as stated
**CONFIRMED, but my headline support does not survive.** "At 15 s it understates 58% of bins" is a
`timesfm_e2e` figure and **does not reproduce**: `ft_llm_static` gives **47.7%** and
`ft_llm_reactive` **47.3%** — a *minority*. The stamp actually **overstates** about 52% of bins.
That sentence is struck.

**What does hold:** it is not a pointwise bound (55.4% / 57.9% of truth-selected top-1% bins are
short; worst 934.7 tok/s = 72.0% of its own bin); the arrival-selected top-1% bias is
**+54.48% / +55.60% at 15-second bins** (1.1 pp spread across the two ft_llm arms); volume
fidelity is 7.82e-07. **"Strongly conservative" is struck** — at the planner's 60 s interval the
figure is +2.9% and 42.6% of the flagged-hottest bins are still under-stated.
Replacement wording: the permitted sentence in A16_decode_FINAL.md, ft-arm ranges only, bin width
stated, no provisioning claim in either direction. At `:148` only the parenthetical changes — its
surrounding R^2 0.654 constant-fraction fit does not depend on the bound being pointwise.
