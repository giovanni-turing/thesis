---
from: claude
ts: 2026-07-28T08:15:00-03:00
re: new
type: question
---

# Silicon campaign ended; settled burst3 evidence commit landed (2daa383)

The physical-replay campaign auto-STOPped at 15/15 steady24h reps
(daemon exited 10:51:56Z banking a partial burst4 rep). The settled
evidence commit agreed on the 210/211 boundary is in: `2daa383`, burst3
cells ONLY --- 5 reps x 3 arms, retimed p99 fc 782.455 +/- 0.270 ms (PASS
under the now-declared 1000 ms bound), re 22,565.317 +/- 0.935, staticC8
1,397.413 +/- 1.140; banked reconstruction exact in every rep.

Evidence hygiene in the commit, full detail in
`simulation/results/silicon_anchor/SETTLED_EVIDENCE.md`: the half-finished
rep003 at old HEAD replaced; daemon files and the live manifest untracked
in favor of a frozen burst3-only excerpt preserving the fc/rep001
double-resume history; the final queue content-pinned with the
mid-campaign edit fully documented (including a design-field mangling the
audit had not caught) and the queue_sha:null defect disclosed; the
engine__hf_fa2 mislabel annotated as a second SDPA measurement per 199c;
the environment snapshot committed; and the bridge-101 negative gate
tests now exist as code (18 corruption probes, all failing loudly; a
read-only full-campaign sweep verified 32/32 completed reps against all
nine gates), wired into provenance/verify_all.sh.

steady24h and burst4 tiers are deliberately NOT in this commit. Next: the
metodologia physical-anchor integration delta under the 199 conditions ---
calm-day absolutes presented as engine-band-conditional (the steady24h
ordering inverts vs burst3 under HF-eager retiming; the robust facts are
the fc-vs-re near-tie and the burst3 ordering), burst4 disclosed as
non-discriminating with a broken static trio, no claim attached. That
arrives as its own separately-scoped round for your review.
