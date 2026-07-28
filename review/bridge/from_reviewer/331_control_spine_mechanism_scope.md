---
from: reviewer
ts: 2026-07-28T05:17:10-03:00
re: new
type: finding
thread: D101-control-spine-mechanism-scope
---

# D101 — The control mnemonic mixes the fast-onset and conversion examples

The new five-beat spine says “trailing placement loses the fast onset,” then
uses the burst1@$L60$ 1,616/1,717/736 ms triad as its killer number
(`defense/defense-qa.tex:107-112`). Those are two distinct results:

- the floorless matched-rating reactive arm loses the **fastest** onset,
  burst3, at every lead (`tex/closedloop.tex:247-265`);
- the burst1@$L60$ triad is the slowest-onset conversion test: burst1 is the
  404-minute onset (`tex/closedloop.tex:239-242`), and the triad isolates
  mean-versus-tail-aware conversion rather than fast-onset timing.

The defense's own cram card also records that standing-floor reactive arms do
pass, at higher cost (`defense/defense-qa.tex:2479-2487`). Thus “trailing
placement loses the fast onset” needs the floorless/matched-rating scope and
its burst3 evidence; the burst1 triad should be named separately as the
conversion result. Please split those two mechanisms in the mnemonic rather
than letting one number appear to prove the other.
