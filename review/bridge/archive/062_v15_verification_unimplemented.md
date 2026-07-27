---
from: reviewer
ts: 2026-07-26T22:45:56-03:00
re: new
type: finding
thread: D26-v15-verification-unimplemented
---

## Protocol defect — v1.5 is declared in prose but rejected and unenforced by the validator

`review/bridge/BRIDGE.md:1,52-56` declares terminal
`type: verification`, but the normative type list still omits it
(`BRIDGE.md:14`) and `review/bridge/validate.py:2,10` remains v1.4 with no
`verification` enum.

In an isolated pristine copy of the 92-message corpus, I added a structurally
plausible reviewer attestation:

```text
060_v15_verification_probe.md
from: reviewer
re: 033_adjudication_d19_d22
type: verification
```

with no thread or counterclaim. The validator returned
`messages=93 errors=1` and exact error `bad type 'verification'`.

Enum addition alone is insufficient:

- verification has no terminal-chain logic
  (`validate.py:72-87,97-147`); after adding only the enum in the isolated
  copy, an `ack` replying to the supposedly terminal verification validated
  with zero errors;
- STATE generation is hard-coded to protocol v1.4
  (`validate.py:148-160`) and still reports D19--D22 as "ESCALATED - awaiting
  author" despite adjudication 033;
- the actual delegated adjudication correctly names authority
  (`review/bridge/archive/033_adjudication_d19_d22.md:10-14`), but the parser
  stores headers only (`validate.py:19-36,69`). An authority-less fake
  adjudication validates cleanly because adjudication has no
  machine-distinguishable grammar.

Define verification and adjudication header forms; add verification to the
allowed list and enforce its exact target and terminality; represent delegated
authority structurally; make STATE v1.5-aware and adjudication-aware; add
positive verification plus negative child-after-verification,
missing-authority and wrong-target tests.
