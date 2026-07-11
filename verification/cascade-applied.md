# Headline cascade — applied edit log

Spec: `verification/headline-cascade.md`. Scope: `tex/*.tex` only. No git run.
Build after edits: `latexmk -pdf -interaction=nonstopmode -halt-on-error tese.tex`
→ **RC=0, 0 undefined references, 125 pages, no rerun/LaTeX warnings.**

Core correction: burst5's C=16 static denominator was an endpoint-divergence
artifact; honest AIC deployable static = **C=8** (3.869M worker-seconds, p99 644 ms).
Headline ratio 0.27–0.31× → **0.55–0.61×**. Every vs-static ratio recomputed against
the 3.869M denominator.

## tab:cl-aggregate — every ratio recomputed as Mworker-s / 3.869 (closedloop.tex)

| Row | Mworker-s | old ratio | new ratio | check (Mws/3.869) |
|---|---|---|---|---|
| Static C=8 (deployable) | 3.87 | 1.00× | 1.00× | 3.87/3.869 = 1.000 |
| Static C=2 (calm optimum) | 0.97 | 0.125× | 0.25× | 0.97/3.869 = 0.251 |
| Forecast p90, L=30s | 2.38 | 0.31× | 0.61× | 2.38/3.869 = 0.615 (spec 0.614) |
| Forecast p90, L=300s | 2.12 | 0.27× | 0.55× | 2.12/3.869 = 0.548 (spec 0.546) |
| Forecast p50, L=30s | 0.96 | 0.12× | 0.25× | 0.96/3.869 = 0.248 |
| Reactive, L=30s | 2.61 | 0.34× | 0.67× | 2.61/3.869 = 0.675 |
| Reactive, L=300s | 1.67 | 0.22× | 0.43× | 1.67/3.869 = 0.432 |

Forecast-row worker-seconds and p99 (588) unchanged, per spec (only denominator/ratio move).
Static row: p99 565→644, worker-s 7.74→3.87, C=16→C=8.

## Site-by-site (file:line → old → new)

### tese.tex (abstract + resumo)
- 59: `0.27--0.31$\times$ the deployable static` → `0.55--0.61$\times$ …`
- 97 (PT resumo): `0,27--0,31$\times$ o tempo de GPU` → `0,55--0,61$\times$ …`

### intro.tex
- 261: `…every episode at 0.27--0.31 times` → `…0.55--0.61 times`
- 442: `burst windows need 6--16 encoder workers` → `6--8` (burst5 C* 16→8)
- 453: `at a quarter to a third of the deployable static` → `at over half to two-thirds of …` (prose form of 0.55–0.61)
- 477: `the 0.27--0.31$\times$ result assume` → `the 0.55--0.61$\times$ result …`

### related.tex
- 348: `0.27--0.31 times the deployable static` → `0.55--0.61 times …`

### conclusion.tex
- 22: `6--16 encoder workers` → `6--8`
- 23: `an $8\times$/$2\times$ overprovisioning` → `a $4\times$/$2\times$ overprovisioning`
- 65: `\textbf{0.27--0.31$\times$ the deployable static…}` → `\textbf{0.55--0.61$\times$ …}`
- 76: `at roughly a quarter to a third of the best static` → `at roughly half to two-thirds of …`

### baselines.tex
- 81 (tab:base-grid burst5 row): `burst5 & 1.35 & 16 & TP2×2 & 21.6 & 5.4` → `… & 8 & TP2×2 & 10.8 & 5.4` (C* 16→8; 5090 GPU-h 21.6→10.8 = 8×1.35; H100 5.4 unchanged)
- 88–97 (the now-WRONG "C=16 / headline unchanged" para): rewritten. Kept the
  stage-conditional image-bearing note (burst optima rise 1–2 workers). Changed
  `deployable static $C{=}16$` → `$C{=}8$`; removed the "cost headline … is unchanged"
  claim and replaced with "the choice of metric reshapes only the per-window table,
  not the deployable fleet that carries the cost headline … (0.55--0.61$\times$ static)."
- 114/115: `swings from 2 workers on the calm day to 16 on burst5` → `to 8 on burst5`
- 117/118: `$C{=}16$ encoders plus TP2×2` → `$C{=}8$ encoders plus TP2×2`
- 119/120: `by $8\times$ on the vision side and $2\times$` → `by $4\times$ … and $2\times$`
- 251/252: `deployable only as 16 encoders + TP2×2, i.e. $8\times$/$2\times$` → `8 encoders …, i.e. $4\times$/$2\times$`

### closedloop.tex
- 136: `$\rho$-frontier already prices (0.27--0.44$\times$ static)` → `(0.55--0.88$\times$ static)`
- 314 (tab caption): `Rows above it (905 ms and up) carry queueing` → `(644 ms and up)` — static C=8 now sits at 644 (above the 588 floor), so 644 is the lowest queueing-bearing row.
- 321–330 (tab:cl-aggregate): all rows per table above (static C/p99/worker-s + 6 ratio cells).
- 337: headline `…every in-span episode at 0.27--0.31 times` → `0.55--0.61 times`
- 339: `versus 7.74M worker-seconds` → `versus 3.87M worker-seconds`
- 340: `static fleet's 565` → `static fleet's 644`
- 343 (cross-model): `Toto … 0.28--0.31$\times$, TimesFM … 0.26--0.30$\times$` → `Toto … 0.56--0.62$\times$, TimesFM … 0.52--0.60$\times$` (denominator halved ⇒ every vs-static ratio doubled; the "≤4%" cross-model spread is relative and scale-invariant, unchanged).
- 357: frontier `from 0.44$\times$ static at … $\rho{=}10$` → `from 0.88$\times$ …`
- 358: `down to 0.18$\times$ at … $\rho{=}25$` → `down to 0.36$\times$ …`
- 365: `Only $\rho\in\{10,15\}$ (0.44--0.31$\times$)` → `(0.88--0.58$\times$)` (per spec's exact map string)
- 366: `the quoted 0.27--0.31$\times$ sits at $\rho{=}15$` → `0.55--0.61$\times$`
- 382: p50 prose `an excellent cost policy (0.12$\times$)` → `(0.25$\times$)`
- 415/416 (4×-payload sensitivity): `including the static $C{=}16$ fleet (p99 1{,}311 ms), because…` → `including the deployable static fleet, because…` — dropped the C=16 label and its C=16-specific 1,311 ms p99 (not recomputable for C=8, whose 4× tail would differ; qualitative "every policy violates" claim preserved via the common 1,087 ms handoff floor).
- 434–441 (silicon-scope reframe): removed the "0.27--0.31$\times$ ratio is preserved on
  silicon" claim. New framing (spec's "framing note"): the winning schedule's provisioned
  worker-time (numerator) is unchanged on silicon (headroom absorbs the underprice with no
  added workers), so **0.55--0.61$\times$ is the AIC-model headline**; a fully silicon-costed
  comparison would enlarge the static *denominator* — on silicon the deployable static fleet
  is bound by burst2's genuine batching knee (≈2×), not burst5's endpoint artifact — so the
  silicon ratio would fall between that AIC headline and the lower value the larger fleet
  implies; that accounting + a live-worker non-eager confirmation remain future work.
  (Kept "24--32 … far above the 12--16 the silicon fleet requires" — silicon quantity, unchanged.)
- 442/449: `every quantity here (the $8\times$/$2\times$ over-provisioning, … the 0.27--0.31$\times$)` → `($4\times$/$2\times$ …, … 0.55--0.61$\times$)`
- 461/468 (summary): `…in aggregate and per-episode at 0.27--0.31 times` → `0.55--0.61 times`

### aiconfigurator.tex
- 336–349 (burst5 constraint para): reframed. `Five of the six are sized at the p99 latency
  knee` → `All six …`. Removed "The sole exception, burst5, is alone sized by the
  sustained-volume divergence bound (16 workers, far above its p99 knee), and that headroom
  absorbs the underprice … (p99 588 to 784 …)". New: "Burst5 is no exception: its honest AIC
  size is 8 workers, set by the same p99 knee, not the 16 an earlier sustained-volume
  divergence flag reported. That flag was an endpoint artifact — backlog slope ≈0 over the
  arrival window, tiled-trace backlog constant, C=8 feasible at week scale (p99 644 ms) — so
  burst5 too amplifies ≈2× on silicon rather than absorbing the underprice from spare
  headroom." Closing sentence: "corrected by up to ≈2× at the latency knee **across every
  window**" (was "…and absorbed where divergence-sized").

## Untouched look-alikes (verified NOT the headline; left as-is)
- Language-pool 0.96× near-break-even (tese:60, closedloop:242/249, conclusion:67).
- R² values 0.12 / 0.123 (intro, trace-eda, related, predictors, conclusion, tese).
- Coverage 0.88–0.90 (predictors, closedloop, intro, conclusion) and image-rate correlation 0.36 (trace-eda:246).
- closedloop:155 "cuts its p99 up to 8× below the point reactive" — headroom tail reduction, not overprovisioning.
- twopool:287 "overprovision the encoder fleet by that factor" — the >10× knee-separation, not the 4×/2× calm-day factor.
- closedloop:438 "12--16 the silicon fleet requires" and aiconfigurator "1,420--1,846 ms" silicon-fail range — silicon quantities, unchanged.
- arXiv:2401.17644 (tese bib) — coincidental "644".
