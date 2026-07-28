---
from: reviewer
ts: 2026-07-27T19:38:21-03:00
re: 097_metric_stack_delta
type: finding
thread: D65-metric-stack-provenance-gate
---

## HIGH — A5c and the appendix do not yet protect the claims they advertise

The current artifact is correct: `metric_stack.py --check` passes, all
currently printed table values match the raw-trace recomputation, the tracked
figure regenerates byte-identically under `eda/.venv`, and a clean temporary
build is 125 pages with 0 errors and 0 undefined references. The delivery
chain nevertheless has reproducible false greens.

### 1. A5c is literal-presence checking, not table/claim checking

`provenance/verify_all.sh:102-125` recomputes the JSON, but it binds only four
values and merely asserts that each formatted literal occurs somewhere in
`tex/closedloop.tex`. Swapping the forecast/reactive 1 s counts and excess
masses between their rows leaves all four strings present and A5c passes.
Changing forecast worker-hours, either p99.99 operand, the 7.7% or 13% claims,
the M1 identity, the conclusion repetition, or the PDF also passes. Twenty-six
of the table's 30 numeric cells are not checked.

The inline Python additionally hard-codes `/home/gio/tese`
(`verify_all.sh:109-111`), so a check invoked from another checkout can read
this workspace's artifact and TeX instead of the checkout under test.

Required fix: derive paths from the suite's `TESE`, structurally bind every
printed row/column cell (or generate the table), and gate the promoted derived
claims at their exact locations. Add negative tests proving a row swap and a
relocated-checkout corruption fail.

### 2. p99.5/p99.99 are true but outside the generated/gated artifact

The manuscript promotes p99.5/p99.99 at `tex/closedloop.tex:657-660`, while
the generator stops at p99.9 (`metric_stack.py:32-33,73-76`) and the JSON
jumps from p99.9 to max (`metric_stack.json:21-27,85-91`). The values can be
recomputed and are correct (p99.99 forecast/reactive
6,705.863/14,723.995 ms), but currently live only in
`metric_stack_delay_vectors.npz`. That NPZ has no tracked generator named by
the ledger or appendix and A5c never verifies it.

Required fix: include p99.5 and p99.99 in the raw-trace-generated JSON and
bind the prose to them, or add a tracked generator and complete manifest/gate
for the vector artifact.

### 3. The figure is neither delivery-gated nor unconditionally deterministic

`make_metric_stack_figure.py:14` uses
`os.environ.setdefault("SOURCE_DATE_EPOCH", "0")`; a caller-supplied epoch
changes PDF metadata and bytes. The tracked PDF regenerates to SHA-256
`19da27040751eecf0603894052d12f28c4d7bac73562f697f217026b110e1198`
under `eda/.venv` (Matplotlib 3.11.0), but the documented aiconfigurator
environment (Matplotlib 3.10.8) produces different bytes, and the ledger gives
no executable command (`progress/results-ledger.md:3038-3049`).

Required fix: pin the interpreter/environment and epoch in an executable
ledger command, regenerate the PDF in A5c, and compare it byte-for-byte (or
verify defined semantic content).

### 4. Appendix pointers and immutable pin are incomplete

The appendix declares root-relative paths at `tex/apendice.tex:114-121`, but
the new row names nonexistent `comparator_frontier/...` paths at
`tex/apendice.tex:245-249`; the actual prefix is
`simulation/results/comparator_frontier/`. The immutable pin list at
`tex/apendice.tex:22-31` ends at `f7a64be`; none of its five commits contains
the new JSON or PDF. Add the integration pin (8ca4530 or its corrective
successor) and ensure the row identifies every load-bearing artifact.

Disposition: the present numbers are accepted, but the advertised
regeneration/provenance claim is not closed until these false-green paths and
pointers are repaired.
