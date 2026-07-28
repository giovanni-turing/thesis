---
from: reviewer
ts: 2026-07-27T23:41:44-03:00
re: new
type: finding
thread: D67-final-pre-freeze-punchlist
---

## D67 narrow recheck: most repairs pass; final pre-freeze punch list

Snapshot: `/tmp/llm-week-d66-reaudit.EV1F4d`. Clean recomputation,
binding, and the delivery-chain selftest pass.

Verified closed since 223:

- native input/output/processed-token mutations now fail both checking and
  regeneration;
- all four requested role mutations now fail (GPU-hour roles, reactive TTFT
  p99, E2E reduction polarity, and ITL roles);
- whole-driver L=60-to-L=59 mutations fail;
- the exact table-caption L=60-to-L=59 mutation fails; and
- an artifact `lead_s=59` mutation fails both generator and binder.

### Three mechanical residuals

1. `launch.sh` contains separate forecast and reactive L=60 assignments, but
   `lead_config()` checks only the set of observed values. Removing either
   individual assignment while leaving the other at 60 still false-greens.
   Bind both arm-specific assignments or assert their expected occurrence
   count.
2. The adjacent body claim `language lead L=60` is not bound: changing that
   occurrence to L=59 leaves the binder green even though the caption is now
   protected. Bind the body role or make it mechanically derive from the
   already-bound caption.
3. The generator and artifact are still untracked. Add both to the freeze
   commit; otherwise the delivery hook cannot operate in a clean checkout.

### Four wording residuals

The data evidence is favorable. These are small consistency edits:

1. `tex/closedloop.tex:1264-1267` still says the verdict is decided on the
   aggregate alone and calls windows a diagnostic, contradicting the correct
   every-window compliance-gate language at `:1286-1290`; the caption at
   `:1303-1305` also retains the diagnostic-only formulation.
2. `tex/conclusion.tex:50-63` still says windows explain rather than decide
   and calls the grid an analysis/masking instrument. Preserve the accepted
   hierarchy: span leads magnitude and already rejects reactive; windows
   remain the declared non-masking validity/compliance gate needed to
   establish every-window forecast compliance.
3. The chapter summary at `tex/closedloop.tex:1644-1657` remains
   mechanism/window-first. Mirror the newly corrected aggregate-first
   chapter opening before compressing to mechanisms.
4. Both deck mirrors still retain:
   - “whole span decides it” / “the verdict”;
   - a mixed span/onset heading that applies best/worst-across-leads language
     to the single-L60 span row;
   - bare encoder `L=30` without its issued-forecast-lead meaning; and
   - `-37% (synthesis)` without explicitly naming post-hoc,
     threshold-integrated TTFT-mass magnitude versus the p99 contract.

The unsupported 651-ms-across-L60/120/300 claim is now correctly fixed, as
are the protocol distinction in the chapter, encoder subject reset, e13
mapping, and native-token/role gates. No new experiment is requested.
