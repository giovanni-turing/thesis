# PROSE OVERCLAIMS — methodological-overclaim worklist

Scope: every line this session added to `tex/`, audited for the specific failure of describing
**simulation / mocker / live-validation** work as **real-hardware (H100 silicon / GPU) measurement**.
Ground-truth boundary (from the methodology): the **RTX-5090 vision encoder** collection, the
**7,817-request vLLM** vision-tower run, and the **phase-E physical anchor** ARE real silicon and may
be called "measured / on silicon / physically validated"; the **language / decode pool** is the
discrete-event **mocker on AIC timing**, and the **live validation anchor** runs the **real Dynamo
control plane with mocked engines** (never real GPUs).

Deduplicated, ordered abstract/intro/conclusion first, then by severity.

---

## 0. Result

**Surviving OVERCLAIMS: 0.** No required edit remains.

One serious overclaim existed and was already **fixed by hand this session** (logged in §2 below as
context, not as an open item). A full 14-chapter re-audit of every added line found **no sibling** of
that defect anywhere else: `n_overclaims = 0` in all of
closedloop, twopool, baselines, aiconfigurator, validation, predictors, intro, conclusion, apendice,
apendice_ecosystem, related, trace-eda, tese.

`grep -rniE "real H100 silicon" tex/*.tex` → **0**. Confirmed 2026-07-20.

---

## 1. WORKLIST — edits to make

**(empty)** — no methodological overclaim survives that requires a text change.

Every `on silicon` / `real GPU` phrase remaining in `tex/` was inspected in context and is within
method (see §3). None attributes the language pool, the mocker, or the live-validation workers to real
GPU execution.

---

## 2. Already fixed by hand this session (context, not an open item)

| # | File / line | Was (OVERCLAIM) | Now (corrected) | Severity | Proof it was wrong |
|---|---|---|---|---|---|
| H1 | tex/closedloop.tex (live-validation recap, ~L1004) | "…runs the burst3 window through Dynamo's **real H100 silicon**, in real time" | "…through Dynamo's **real control plane, in real time**. Those workers are **mocker processes on the shared AIC timing model, not GPUs**; the live anchor validates the control loop, not silicon." | **critical** | The live anchor uses `dynamo.mocker` workers on the AIC timing model — no H100 executes. Confirmed by validation.tex L156-157 ("validates the control loop, not GPU silicon"), apendice_ecosystem.tex L165-168 ("its engines are mocked … real GPU engines … remains future work"), and the run artifacts (`live_fc`/`live_re`, `profile_export_aiperf.json`). |

This fix is now the honest form and is the *only* methodological-overclaim edit the session required.

---

## 3. Inspected and CLEARED — do not "correct" these (they are within method)

These are the `on silicon` / `real GPU` occurrences the hardened gate (§4, B4b) flags for human
re-read. Each was verified against the ground-truth boundary and is **correct as written** — listed so
a future editor does not mistake a WARN for a defect and over-correct a supported claim.

| File:line | Text (abridged) | Why it is honest |
|---|---|---|
| intro.tex:39 | "cost model, collected **on silicon** for this thesis" | The **RTX-5090 encoder** cost model — real silicon, permitted. |
| intro.tex:243 | "encoder costs **validated on silicon**, language-pool timing **calibrated**" | Explicitly splits encoder (silicon) from language pool (calibrated sim). |
| intro.tex:300 | "every timing model is either **collected on silicon and validated physically, or compared against its alternative**" | Encoder = silicon; language = the "compared" alternative. Correct disjunction. |
| conclusion.tex:38 | "encoder cost model was **collected on silicon** for this thesis" | RTX-5090 encoder. Permitted. |
| conclusion.tex:124 | "full closed loop **on a real GPU serving cluster**: the honest complement to the **mocked-engine** control-loop anchor" | Explicitly **future work**, contrasted against the mocked engines. Honest. |
| related.tex:369 | "…systems above are evaluated **on real GPU clusters**, while this thesis substitutes a silicon-calibrated simulation" | Describes the **other** systems on real GPUs; this thesis is named as simulation. |
| related.tex:370 / :385 | "**silicon-calibrated** simulation, physical anchors for the encoder cost model" | Legend/positioning; "silicon-calibrated" is the encoder anchor, sim is named as sim. |
| related.tex:372 | "A closed loop **on a real GPU serving cluster** is the natural next step" | Future work. Honest. |
| apendice_ecosystem.tex:166 | "…its engines are **mocked** — a full-serving-path run with **real GPU engines** … **remains future work**" | Names the mocking, marks real GPU as future work. Strengthens the caveat. |

## 3.1 Borderline (NOT an overclaim) — optional defensive polish only

- **closedloop.tex ~L952-954** — parallel construction: the encoder GPU-hours are "derived … **not
  measured**" while the language pool's H100 GPU-hours are "**stored** quantities". A careless reader
  could read "stored" (next to "not measured") as a hardware run. It does **not** assert hardware
  execution — the simulator emits/stores the field, and the chapter states throughout that the language
  pool is the mocker/AIC-timed sim. **Within method; no fix required.** If maximally defensive, one
  could write "stored (as emitted by the simulator), not derived". Optional, not on the worklist.

---

## 4. Gate hardening — verify_all.sh B4 (added this session)

Added as a new **Gate-B** block (`B4`), after B3, inside the `WANT_THESIS` section of
`/home/gio/tese/provenance/verify_all.sh`. It is a grep-level REPORT-don't-hide gate: false positives
(WARN) are acceptable, misses are not.

- **B4a (HARD FAIL if any hit):** the caught defect and its per-line siblings must be 0 occurrences —
  `real H100 silicon`, `real H100 GPU`, `real H100s`, `on real H100`, `H100 silicon`,
  `mocker…on…silicon`, `mock(ed|er)…on real…GPU`, `live-valid…on real…GPU`, `live-valid…on silicon`.
- **B4b (manual-review WARN):** any `on silicon` / `on real … GPU` / `real GPU` / `silicon-*` phrase
  sitting **within 3 lines** of a language-pool / mocker / live-validation cue
  (`mocker|mocked|language-pool|live-valid|live-runtime|control-plane replay|discrete-event`) is
  surfaced for a human re-read. It does **not** fail the gate.

Exact lines added (verbatim):

```bash
# B4 methodological-overclaim gate -- REPORT, don't hide (false positives OK, misses are not).
# Simulation / mocker / live-validation must never be written as real-H100-silicon execution.
# The only physically-measured pool is the RTX-5090 encoder (its "on silicon" is legitimate);
# the language pool is the discrete-event mocker on AIC timing and the live anchor runs mocked
# engines. This audit already hand-fixed one defect (closedloop "real H100 silicon" -> mocker
# control plane); B4a asserts that class can never reappear, B4b surfaces new near-misses.
cd "$TESE"
# B4a HARD -- the caught defect and its per-line siblings. Each must be 0 or the gate FAILS.
for pat in \
    'real H100 silicon' 'real H100 GPU' 'real H100s' 'on real H100' 'H100 silicon' \
    'mocker[^.]*on[^.]*silicon' 'mock(ed|er)[^.]*on real[^.]*GPU' \
    'live[- ]valid[a-z]*[^.]*on real[^.]*GPU' 'live[- ]valid[a-z]*[^.]*on silicon'; do
  hits=$(grep -rniE "$pat" tex/*.tex 2>/dev/null)
  n=$(printf '%s' "$hits" | grep -c .)
  if [ "$n" -eq 0 ]; then ok "no methodological overclaim matching /$pat/"
  else bad "METHODOLOGICAL OVERCLAIM (hard): /$pat/ -- $n line(s)"
       printf '%s\n' "$hits" | sed 's/^/        /'; fi
done
# B4b MANUAL-REVIEW WARN -- any silicon/real-GPU phrasing sitting within 3 lines of a
# language-pool / mocker / live-validation cue. Deliberately over-broad: a WARN here is an
# instruction to a human to re-read the passage, not a failure. Legitimate encoder-silicon and
# other-systems-on-real-GPU passages are expected to trip it; that is the point of a REPORT gate.
SIL='on silicon|on real [A-Za-z0-9]* ?GPU|real GPU|silicon-(validated|measured|collected|calibrated)'
CUE='mocker|mocked|language[ -]pool|live[- ]valid|live-runtime|control[- ]plane replay|discrete-event'
NEAR=0
while IFS= read -r line; do
  [ -n "$line" ] && { warn "manual-review (silicon/GPU phrase <=3 lines from a sim/mocker/live cue): $line"; NEAR=$((NEAR+1)); }
done < <(
  for f in tex/*.tex; do
    awk -v S="$SIL" -v C="$CUE" -v F="$f" '
      { L[NR]=$0 }
      END { for (i=1;i<=NR;i++) if (L[i] ~ S)
              for (j=i-3;j<=i+3;j++)
                if (j>=1 && j<=NR && L[j] ~ C) { printf "%s:%d: %s\n", F, i, substr(L[i],1,88); break } }' "$f"
  done)
[ $NEAR -eq 0 ] && ok "no silicon/real-GPU phrase within 3 lines of a sim/mocker/live cue" \
                || printf "        (%d near-miss(es) above are for human re-read, not gate failures)\n" "$NEAR"
```

**Run result on corrected text (2026-07-20):** B4a = **9 PASS, 0 FAIL**; B4b = **9 WARN** near-misses,
all in §3 above and all within method. The gate is green (no FAIL). The corrected text passes.

---

## 5. Cross-check against ADJUDICATION §0.4 (rejected fixes)

None of the above re-introduces a rejected fix. The 44 rejected fixes (§0.4) are all numeric/scope
corrections computed from rounded cells or the wrong artifact; **none** concerns the sim-vs-silicon
methodological boundary, and the empty worklist here proposes **no** number or wording change, so there
is no possible collision. The hand-fix H1 (silicon→mocker) is a methodological correction outside the
scope of §0.4 and is not among the rejected set. No claim the method actually supports is weakened:
the RTX-5090 encoder collection and the 7,817-request vLLM run remain described as real silicon.
