---
from: reviewer
ts: 2026-07-26T21:08:10-03:00
re: 009_rereview_request
type: finding
thread: D14-freeze-scope-not-calibration-frozen
---

## Moderate — "frozen protocol" is not equivalent to the plan's freeze-on-calibration requirement

The governing plan requires all parameters to be frozen on the calibration
split before one evaluation (`thesis_shortening_plan_v3.md:161-168`). The
chapter itself discloses that the forecast arm's headline `rho=15` was chosen
ex post from the evaluation surface (`tex/closedloop.tex:303-320`).
Therefore the forecast arm is frozen before this comparator replay, but it is
not a policy selected solely on burst2/burst6.

The audit trail also cannot independently prove the freeze chronology through
version history: the calibration script, `FROZEN.json`, evaluation outputs,
and adversarial repairs all first appear in commit `4babe1c`. Filesystem mtimes
are consistent with `FROZEN.json` preceding `EVAL_RESULTS.json` by about
11 minutes, but both are mutable before the common commit.

This does not falsify the numerical result, and the ex-post `rho` disclosure is
good. It does mean the abstract/conclusion's unqualified "one frozen protocol"
cannot imply a calibration-selected, independently held-out forecast policy.
The manuscript should define the narrower sense: arm mechanics frozen before
the frontier replay, with `rho=15` previously selected ex post; the freeze
itself is timestamp-audited rather than commit-separated. Otherwise the
claimed protocol exceeds the available audit evidence.

