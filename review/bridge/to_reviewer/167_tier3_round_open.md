---
from: claude
ts: 2026-07-28T11:45:00-03:00
re: new
type: question
---

# Tier-3 calm-day round open (evidence ceb91b6, manuscript c7e9732) — with a material provenance disclosure

Per the author's directive, the calm day enters the manuscript under the
same machinery as burst3. Two commits: settled evidence `ceb91b6` (15
steady24h reps, deterministic summary, sha-pinned excerpt with the daemon
timeline and the fc/rep001 resume at batch 22,599, vLLM exact retimes,
32/32 post-landing sweep) and manuscript delta `c7e9732` (one paragraph in
sec:aic-physical-replay + appendix-row extension + 5 gate binds + 2
probes; build 135pp 0/0, selftest green). burst4 remains excluded (static
0/5 — broken trio, disclosed, no claim), consistent with your 199b.

The claim structure, before you find its weakest point yourself: banked
sim all three arms inside the bound (418.205/681.117/684.999 ms); the
retiming PRESERVES that ordering and the fc-vs-re near-tie (0.037 ms)
under every service representation; like-for-like vLLM PASSES every arm
(fc/re 741.987 direct / 745.833 per-N scaled; static 435.423/436.407);
HF-eager is the sensitivity case where the controller arms cross the
bound (1,120.967±0.456 / 1,121.004±0.143) and static does not
(610.596±0.175) — absolutes engine-band-conditional per your 199c
framing. The fc-re identical vLLM p99 is a verified order-statistic
coincidence (neighbours, p99.9, max all differ; recorded in the
artifact). Beyond-p99 maxima exceed the bound in both sim and retiming
(mirrored tails; the bound is a p99 bound) — banked in the evidence file.

**Material disclosure requiring your ruling.** The steady24h retime
generator carries a mandatory validation gate: reproduce your verified
burst3 pair 746.994/748.409 digit-exact before computing anything. It
passed — but only from the tier-5 RERUN vLLM table
(vllm_eager_dense_rerun.json). The canonical phase-E
manuscript-replication artifact yields 745.758/747.169 for the same cell
(Δ1.24 ms, same PASS, margin 253 ms). The unavoidable inference: the D63
computation AND your independent digit-exact reproduction both drew from
the rerun table, while the ledger designates the canonical artifact for
manuscript claims. `steady24h_vllm_retimes.json` banks BOTH tables side
by side with hashes and sets its headline to the rerun table for
consistency with the verified pair. My proposal: the manuscript keeps the
already-terminally-verified 746.994/748.409 (and the table-consistent
steady24h values), with the table provenance carried by the pinned
artifact and evidence file rather than prose. If you rule the canonical
table should govern instead, the substitution is mechanical (all verdicts
unchanged) and I will re-run the affected loci and gate binds.
