---
from: reviewer
ts: 2026-07-28T03:51:37-03:00
re: new
type: finding
thread: D82-h100-timing-fidelity-scope
---

# D82 — “Calibrated H100 timing” overstates the physical fidelity boundary

The English abstract says the language simulator runs “under calibrated H100
timing” (`tex/tese.tex:78-82`); the Portuguese abstract mirrors “tempos H100
calibrados” (`tex/tese.tex:158-161`), and the introduction uses
“AIC-calibrated H100 timing” (`tex/intro.tex:201-204`).

The canonical fidelity statement is materially narrower: language timing is
trusted from AIC's shipped `h100_sxm` database and Dynamo's engine, was not
physically revalidated in this work, and the conclusion is sensitive to that
timing model (`tex/metodologia.tex:719-730`). Moreover, inputs beyond 16,384
tokens are extrapolated, including requests that decide the burst-window TTFT
tail (`tex/metodologia.tex:731-735`).

“Calibrated” alone can reasonably be read as local physical calibration.
Please identify the source and validation boundary in both abstracts and the
introduction, e.g. “using AIC's shipped H100 timing database, not physically
revalidated here.” The long-context extrapolation can remain at the canonical
limitation locus, but the top-level wording must not imply a physical H100
anchor.
