# POST-EDIT CROSS-REFERENCE AUDIT

Scope: every quantity touched by the 32 applied edits, traced across all 13 files in
`/home/gio/tese/tex/` (incl. `tese.tex` EN abstract + PT Resumo, `intro.tex`, `conclusion.tex`,
both appendices). Five independent tracing passes; 85 sites examined.

Every proposal below was read in the file by this pass and diffed against
`provenance/audit/ADJUDICATION.md` §0.4 (R1–R48). **No proposal matches a rejected fix.**

Result: **7 desynced sites**, 0 unmitigated scope overclaims, 78 sites verified consistent.

---

## 1. DESYNCED SITES

Ordered by reviewer visibility: intro/conclusion first, then chapter bodies, then appendices.

### D1 — `intro.tex:247` (RQ3 answer) — SEVERITY: HIGHEST

**Caused by:** the kernel-ledger weakening (ADJUDICATION line 194: *"Weaken, do not restate:
delete `fully attributed`, and the companion `closes … with no unexplained residual` at :18 and
:433"*). That instruction scoped the deletion to `aiconfigurator.tex` only; the RQ3 answer in
Chapter 1 carries the same phrase verbatim and was missed.

Current (lines 246–247):
```
measurement within ${\approx}3\%$, the end-to-end kernel ledger closes
with no unexplained residual, and a matched-engine silicon measurement of
```
Replacement:
```
measurement within ${\approx}3\%$, the end-to-end kernel ledger is attributed
term by term except for a ${\approx}0.7$\,ms remainder, and a matched-engine silicon measurement of
```

Why it matters: Ch. 1 now asserts a *complete* ledger while `aiconfigurator.tex:18`, `:436` and
`:456` all state a `≈0.7 ms` unattributed remainder. A reviewer reading only the introduction gets
the withdrawn claim. Verified: `aiconfigurator.tex:17-18` reads "attributed term by term except for
a ${\approx}0.7$\,ms remainder"; `:436` and `:456` likewise. §0.4 check: not R34 (that rejects
changing the ≈3 % figure itself, which this edit preserves); no other R touches this clause.

---

### D2 — `conclusion.tex:55` — SEVERITY: HIGH

**Caused by:** [E24], `validation.tex:72` reactive replica-seconds delta `−7.6 % → −7.7 %`.

Current:
```
replica-time within 5.3--7.6\%.
```
Replacement:
```
replica-time within 5.3--7.7\%.
```

The band's upper endpoint *is* the corrected cell. `validation.tex:74` now prints `$-7.7\%$` (read
and confirmed); the forecast leg at `:69` is `$-5.3\%$`, so the corrected range is 5.3–7.7 %.
§0.4 check: the adjacent `1.1--6.8\%` TTFT band in the same sentence is **R1** — *do not touch it*.
ADJUDICATION line 646 explicitly anticipates this printing ("See [E24] for the −7.6/−7.7 printing").

---

### D3 — `conclusion.tex:105` — SEVERITY: HIGH

**Caused by:** [E12], `twopool.tex:185` — the matched-engine bound's scope was separated from the
sweep's extent ("64 consecutive batch sizes within a dense $N{=}1$--$512$ sweep of 69 points").

Current (lines 104–105):
```
own vision-tower implementation to within $12.8\%$ (a matched-engine check over
a dense $N{=}1$--$64$ sweep on a standalone vision-tower forward; the
```
Replacement:
```
own vision-tower implementation to within $12.8\%$ (a matched-engine check over
a dense $N{=}1$--$512$ sweep on a standalone vision-tower forward, holding across
the 64 batch sizes of the $N\le64$ serving regime; the
```

This is the exact sweep-extent-vs-bound-scope conflation [E12] removed, and it **contradicts
`conclusion.tex:120` sixteen lines later**, which already reads "(69 batch sizes, $N{=}1$--$512$)"
with the bound scoped separately on `:121`. §0.4 check: no rejected fix touches the sweep extent;
R35 concerns only the ≈1.4–1.6× summary on `:106`, which this edit leaves untouched.

---

### D4 — `validation.tex:162` — SEVERITY: MEDIUM

**Caused by:** [E24], same as D2 — this is the chapter's own prose summary of its own table.

Current:
```
by 5.3--7.6\%, and the ITL SLA verdicts agree (though the forecast policy's
```
Replacement:
```
by 5.3--7.7\%, and the ITL SLA verdicts agree (though the forecast policy's
```

`tab:val-anchor` is one page earlier at `:74`; the chapter currently contradicts its own table.
§0.4 check: **R1** (1.1 %) sits on `:159` and **R2** (18.0 %) on `:161` — both inside this same
paragraph and both must be left exactly as printed. Only the `7.6 → 7.7` token changes.

---

### D5 — `aiconfigurator.tex:87` — SEVERITY: MEDIUM

**Caused by:** [E16], the SM-clock correction applied at `apendice.tex:28`. [E16]'s literal scope
was that one site; this is the cross-chapter propagation of the same fact, **not** a re-proposal of
rejected **R28** (which protects `apendice.tex:124`'s hard-lock claim — a different sentence,
untouched here).

Current (lines 86–90):
```
at locked clocks: SM \SI{2407}{\mega\hertz}, memory
\SI{14001}{\mega\hertz}
(\texttt{nvidia-smi -lgc/-lmc}, persistence mode enabled), the
clock at which the system file's throughput figures are stated.
```
Replacement:
```
at locked clocks (\texttt{nvidia-smi -lgc 2400,2400 -lmc 14001}, persistence
mode enabled; delivered SM 2377--2400\,\si{\mega\hertz}, MEM
\SI{13801}{\mega\hertz}), at the \SI{2407}{\mega\hertz} boost reference the
system file's throughput figures are stated against.
```

Evidence (from [E16], re-read): `SELECT DISTINCT sm_clock_mhz FROM provenance.collector_encoder_fn`
→ 2377, 2385, 2392, 2400, 2887. **No archived reading is 2407.** The requested lock was
`-lgc 2400,2400`; delivered memory clock 13801. `apendice.tex:28` was corrected to exactly this form
(read and confirmed); Ch. 4 is now the last place in the thesis still asserting collection *at*
2407 MHz.

---

### D6 — `aiconfigurator.tex:418` (`tab:aic-validation` caption) — SEVERITY: MEDIUM

**Caused by:** [E16], same as D5. The GEMM/encoder-validation run this caption describes is
precisely the run `apendice.tex:28` now records as `-lgc 2400,2400 … delivered SM 2377--2400`.

Current:
```
(RTX~5090, bf16, batch 1, SM clock locked to \SI{2407}{\mega\hertz}).
```
Replacement:
```
(RTX~5090, bf16, batch 1, SM clock locked via \texttt{nvidia-smi -lgc 2400,2400},
delivered 2377--2400\,\si{\mega\hertz}).
```

The table body needs no other change: `aiconfigurator.tex:400` already says only "the SM clock is
sampled after every replication".

---

### D7 — `apendice.tex:95–96` (`fig:pred-heatmap` caption) — SEVERITY: MEDIUM

**Caused by:** [E20]. **Direction inverted from the first-pass report.** The upstream tracer flagged
`predictors.tex:170` ("all twelve at 30 s and finer") as the stale site. It is not — the appendix
caption is.

[E20]'s *own* DB evidence line reads:
`1 s → toto-cov (ctx, gen, requests), toto-uni (images)` — i.e. **all four 1-second cells are
Toto-2**, split only by covariate mode. The prescribed replacement text nevertheless wrote "three of
four at \SI{1}{\second}", contradicting the evidence it cites. The applied edit propagated that slip.

Arithmetic check against the same DB line — Toto column wins: 15 s ×4, 30 s ×4, 1 s ×4 = 12; plus
45 s (gen, images) = 2; plus 1 min (gen) = 1. **Total 15 of 20.** Non-Toto: 45 s ctx + requests
(chronos-uni), 1 min ctx (timesfm-uni), 1 min images (chronos-cov), 1 min requests (chronos-uni) =
Chronos ×4 + TimesFM ×1. This reproduces `predictors.tex:170-172` *exactly* ("takes 15 of the 20
cells, including all twelve at 30 s and finer; Chronos-2 takes four of the five remaining … and
TimesFM the fifth"). `predictors.tex:170` is CONFIRMED and must not be edited.

Current (lines 95–97):
```
these margins is within $2\%$ of the column best.
Toto-2 carries every column win at
\SI{15}{\second} and \SI{30}{\second} and three of four at \SI{1}{\second}
(with covariates except on images); Chronos-2 and TimesFM take three of
four at \SI{1}{\minute} and two of four at \SI{45}{\second}.
```
Replacement:
```
Toto-2 carries every column win at
\SI{15}{\second}, \SI{30}{\second} and \SI{1}{\second}
(with covariates except on images at \SI{1}{\second}); Chronos-2 and TimesFM take three of
four at \SI{1}{\minute} and two of four at \SI{45}{\second}.
```

§0.4 check: **R43** rejected "p30 in the last" at `predictors.tex:282` — a different quantity
(TimesFM's quantile-win level, correctly written as p10 by the applied edit). R22/R24 cover
`predictors.tex:175` and `:191`, both untouched here. Nothing in §0.4 defends the "three of four"
wording; [E20] is classed DEFINITIONAL ("no number is wrong; the second clause over-scopes"), and
this correction serves that intent rather than contradicting it.

**Caveat, stated honestly:** the per-cell winners were taken from [E20]'s recorded `argmin`
query, not re-derived from `forecast_metrics` by this pass. The internal consistency is strong
(three independent tallies agree: predictors' 15/20, predictors' 4+1 coarse split, and the
argmin listing), but a DB re-run is cheap insurance before applying D7.

---

## 2. SCOPE OVERCLAIMS

**None requiring an edit.** Every narrowed claim was checked for a surviving broad restatement:

| Narrowed claim | Site of narrowing | Broad restatement elsewhere? |
| --- | --- | --- |
| Sub-minute margin `8–32 %`, "one-third on the image signal" | `predictors.tex:154-157`, `:414-416` | No. Grep for `8--32`, "one-third", "terço" returns nothing outside `predictors.tex`. Abstract/Resumo state forecastability qualitatively with no digits; `conclusion.tex:28-31` and `intro.tex:233` claim only "beat every classical baseline in all twenty cells". |
| TimesFM quantile wins → "p50 head in 17 of 18, p10 in the last" | `predictors.tex:283-286` | No. No other chapter attributes the wins to a level. `intro.tex:429` ("no fixed quantile beats a median point forecast") remains true under the narrowed attribution. |
| poly-vs-AIC knee shift: "one octave" → "one sweep step (s=3→2, ×1.5)" | `twopool.tex:404-405` | No. The three surviving "octave" statements are different quantities — see §4. |
| torch.compile `1.2–1.4×` → scoped to `N≥8` | `apendice.tex:191` | No. The only other mention, `aiconfigurator.tex:372`, carries no magnitude. |
| `+21.8 %` residual → "past the FIFO cap at N=64" | `apendice.tex:196` | No. `twopool.tex:185`, `closedloop.tex:634`, `conclusion.tex:120-121`, `intro.tex:508-510` all now speak of the `N≤64` regime inside an `N=1–512` sweep. (`conclusion.tex:105` was the sole holdout — that is D3.) |
| EWMA rating claim → "only at ρ≥20 does it come under static" | `closedloop.tex:230-231` | No. `conclusion.tex:71` and `intro.tex:492` quote only the ρ=15 operating-point cost (1.09×) and make no frontier claim. |
| Re-verification "to the digit" → "within run noise (<1 %)" | `closedloop.tex:241` | No. The reproduction language in `conclusion.tex:51`, `intro.tex:534` and `tese.tex:69/:115` describes the *live-stack* validation with its own published 1.1–6.8 % band. |
| Reproduction fraction "fast half of bursts" → "a third of episodes" | `related.tex:311-317` | No. Surviving statements are `trace-eda.tex:289-291` ("10th percentile 2 minutes") and `predictors.tex:335`, the latter protected by **R17**. No "half"-language remains. |
| Fano factor + explicit scope | `related.tex:206` ([E25]) | No conflicting-scope Fano statement; `trace-eda.tex` is the source. |

**Four optional-only (pre-existing, not edit-induced) looseness sites**, flagged for the author, *not*
proposed as errata: `conclusion.tex:41`, `closedloop.tex:615`, `aiconfigurator.tex:250` and `:264`
state the 12.8 % bound with no `N`-scope. All four predate the 32 edits and all four sit adjacent to
an `\ref` to `app:engine-sensitivity`. Since the residual grows to +21.8 % past N=64, appending
"across the $N\le64$ serving regime" would tighten them — but this is polish, not a desync.

---

## 3. VERIFIED CONSISTENT

Quantities confirmed to agree at every site that states them. This is the evidence the edit pass did
not break anything.

**Single-site quantities** (stated exactly once thesis-wide; exhaustive grep across all 13 files in
bare / `\SI` / `\num` / comma-grouped / rounded / percent / Portuguese renderings returned no other
occurrence):

- Per-forecast GPU cost `4–51 ms` (`predictors.tex:96`). Old 65/90 ms extinct.
- Onset-decomposition WAPE `73–100 / 57–72 / 33–38 %` (`predictors.tex:253`). Old 75–100/58–72 extinct.
- p10 coverage `0.14–0.21` vs `0.07–0.14` (`predictors.tex:307`).
- Quantile attribution p50/p10 (`predictors.tex:283`).
- Week-replay TTFT p99 agreement `8.5 %` (`twopool.tex:217`).
- Encoder-vs-TTFT tail correlation `r=0.53` (`twopool.tex:229`). Old 0.52 extinct.
- Image-vs-request-rate Pearson `r=0.35` (`trace-eda.tex:246`). Old 0.36 extinct; direction confirmed by **R5**.
- Poly-vs-AIC knee shift, one sweep step (`twopool.tex:404`).
- Protocol batch count "eight" (`aiconfigurator.tex:352`); no "twelve batch sizes" survives anywhere.
- Dynamo pre-1.0 `-rc` tagging wording (`apendice_ecosystem.tex:122`); sole discussion in the thesis.

**Multi-site quantities confirmed in agreement:**

- **`248` steady TTFT p99** — `twopool.tex:103` (`tab:sim-poly-aic`) and `:276` (`tab:sim-knees`) now
  agree after [E14]. No occurrence of `249` remains in `tex/`. Dependent ratio `1.24×`
  (`twopool.tex:61`) and its mirror `+24 %` (`intro.tex:253`) are consistent (307.36448/248.46453 =
  1.23699) and are protected by **R4/R12**.
- **`12.8 %` bound + `N≤64` scope** — correctly scoped at `twopool.tex:185`, `aiconfigurator.tex:319`,
  `:321-323`, `:354`, `:522`, `intro.tex:249`, `:508-510`, `apendice.tex:204`, `conclusion.tex:120-121`,
  `closedloop.tex:633`. One holdout = D3.
- **`1.36–1.62×` HuggingFace ratio** — `apendice.tex:187` now matches `aiconfigurator.tex:245/:276/:283`
  after [E17]. The 1.61/1.62 split is resolved.
- **`≈1.4–1.6×` summaries** at `intro.tex:249`, `:510`, `conclusion.tex:42`, `:106`,
  `closedloop.tex:618`, `twopool.tex:180`, `aiconfigurator.tex:316`, `:520`, `apendice.tex:202` —
  **not stale**: 1.62 rounds into "1.6" at one decimal and all nine carry `${\approx}$`. **R35**
  explicitly upheld these and rejected harmonisation.
- **`2,735 ms` p50-arm encoder-delay p99** — `closedloop.tex:244` prose now matches `:471`
  (`tab:cl-aggregate`). Only two occurrences thesis-wide; no headline chapter quotes this magnitude.
- **`≈0.7 ms` ledger remainder** — consistent at `aiconfigurator.tex:18`, `:436`, `:456`. One holdout = D1.
- **`5.3–7.7 %` replica-time band** — `tab:val-anchor` corrected. Two prose holdouts = D2, D4.
- **`3 % / 6 % / 22 %` heatmap margins** — stated only in the `apendice.tex:91-93` caption
  ([E19]); `predictors.tex:110` points at the figure without restating a margin.
- **TP2×2 burst-window spot-check** — the widened scope at `twopool.tex:391-393` agrees with the
  in-chapter evidence at `twopool.tex:265` (TP2×2 passes at 748 ms) and with `intro.tex:524-526`,
  which already named the TP2×2 shape and the 235B-TP8 spot-check. **R15/R26** protect this material.
- **`cap:validation` cross-reference** — `apendice_ecosystem.tex:144` verified: `\label{cap:validation}`
  is defined at `validation.tex:8`, and that chapter is indeed the home of the `live_fc`/`live_re`
  aiperf runs.
- **`tese.tex` (EN abstract + PT Resumo)** — contains **no restatement of any edited quantity**.
  Confirmed by grep across all 32 edits. Correctly untouched.
- **`baselines.tex`** — no restatement of any edited quantity. Correctly untouched.

---

## 4. DELIBERATE DIFFERENCES

Sites that differ from an edited value but describe a **different quantity**. A later pass must not
"harmonise" these.

| Site | Looks like | Actually is |
| --- | --- | --- |
| `closedloop.tex:565` | the 4–51 ms GPU forecast cost | A *deployed re-forecaster* priced per control tick on **CPU-class** hardware. Different hardware, different unit. Never derived from the old 65/90 ms (also GPU). |
| `predictors.tex:279` | the p40 quantile attribution | An illustrative enumeration of levels a scaler *could* provision against ("p60, p40, or whatever level tracks the signal best"). Not a claim about which quantile won. |
| `intro.tex:539`, `validation.tex:84` | the 8.5 % week-replay agreement | Live-vs-offline **provisioned replica-time** in the `cap:validation` anchor (1,799 vs 1,948). **Must not become 8.5 %.** |
| `closedloop.tex:365` (`651--706 ms`) | the twopool modelled-vs-replayed pair | Per-episode p99 **range** across onsets of 1–220 min under the p90 forecast. Numeral coincidence only. |
| `trace-eda.tex:285` (`r=0.89`) | the corrected Pearson | Window-level **images-vs-context** correlation. |
| `twopool.tex:229` (`r=0.53`) vs `trace-eda.tex:246` (`0.35`) | same statistic | Encoder-delay-vs-prefill-TTFT **tail** correlation vs image-vs-request-rate Pearson. |
| The `R²=0.123 / 0.12` family (`trace-eda.tex:241,257,482`; `intro.tex:146,406`; `related.tex:188,227,339`; `tese.tex:51,92`; `conclusion.tex:17`; `predictors.tex:233`) | the 0.36→0.35 Pearson edit | A **coefficient of determination**, not a Pearson r. Untouched by [E22]. **R32** forbids logging 0.12→0.123 as an erratum. |
| `twopool.tex:387` ("one to two octaves higher") | the narrowed knee shift | A genuinely octave-spaced region above s=4 under a **lax TTFT-only** bound. [E13] protects it explicitly. |
| `twopool.tex:310` ("octave-spaced above s=4") | ditto | Describes the sweep **grid geometry**. |
| `intro.tex:382` ("one swept octave below") | ditto | The **235B-vs-8B** knee (s=1 vs s=2), an exact factor 2. Corroborated at `twopool.tex:82-83`; **R13** protects it. |
| `twopool.tex:266` (`589`) vs `:242` (`588`) | an unharmonised pair | `:266` is `tab:cl-ewma`'s **measured verification** run; `:242` quotes the **committed** floor (316.4+272=588.4). Gap = +0.10 %, exactly what the new "<1 % run noise" wording licenses. Tracked as `[C7]`. |
| `closedloop.tex:467` (`2,953`) | the p50 arm's 2,735 | The **static C=2** fleet row. |
| `closedloop.tex:596` ("exactly") | the "to the digit" retraction | An analytic **rescaling identity** for handoff bandwidth, not a re-run agreement. |
| `apendice.tex:251` ("preserved exactly") | ditto | AIC data-branch **table rows** preserved across a collector correction. |
| `closedloop.tex:64,184,533,538` (ρ≥20) | the EWMA frontier narrowing | The **Foundation** policy's frontier (0.89/0.62/0.48/0.40×), not EWMA's (1.32/1.09/0.94/0.83×). |
| `validation.tex:103` (`cap:closedloop`) | the [E28] `cap:validation` retarget | Points at the **offline** p50 leg of the burst3 split, established in the closed-loop chapter. Correct as-is, as are all 18 other `cap:closedloop` refs. |
| `aiconfigurator.tex:61`, `:90` (2407 MHz) | the D5/D6 clock desync | The AIC **parameterisation reference** (the boost spec the `rtx_5090` system file's throughput figures are stated against) — exactly what the corrected `apendice.tex:28` preserves. Correct. |
| `apendice.tex:124` (target 2400/14001) | ditto | States the **literal lock command**. **R28** protects it. |
| `aiconfigurator.tex:144`, `:199` (`+4.3 % / −5.8 %`) | the `−4.2 %/+6.2 %` band | The **per-N infill shifts**; `:199` prints both and says "equivalently". **R42** confirms −4.2 as the band endpoint. |
| `conclusion.tex:40` ("an attributed residual ledger") | the D1 ledger claim | Claims attribution, **not** exhaustiveness. Compatible with the ≈0.7 ms remainder. No edit. |
| `related.tex:168`, `tese.tex:256` (`v1.3.0 source build`) | the `-rc` tagging edit | The **pinned-snapshot** claim. **R41** rejected re-tagging as `v1.3.0-rc1`. |
| `apendice.tex:223` (224²–896²) | the `N=1–512` sweep | A **resolution** sweep. |

---

## 5. §0.4 CROSS-CHECK

All seven proposals diffed against R1–R48. **None is a rejected fix.**

| Proposal | Nearest rejected entry | Disposition |
| --- | --- | --- |
| D1 `intro.tex:247` | R34 (`≈3 %` figure) | Different clause; D1 preserves the ≈3 % verbatim. Clear. |
| D2 `conclusion.tex:55` | R1 (`1.1 %`, same sentence) | R1's token is untouched; only `7.6→7.7`. ADJUDICATION:646 anticipates it. Clear. |
| D3 `conclusion.tex:105` | R35 (`≈1.4–1.6×`, line 106) | R35's token is untouched; only the sweep extent. Clear. |
| D4 `validation.tex:162` | R1 (:159), R2 (:161) | Both untouched; only `7.6→7.7`. Clear. |
| D5 `aiconfigurator.tex:87` | R28 (`apendice.tex:124`) | Different file, different sentence. R28's own note says the 2407 defect "does survive — see [E16]". Clear. |
| D6 `aiconfigurator.tex:418` | R28 | Same reasoning as D5. Clear. |
| D7 `apendice.tex:95` | R43 (`p30`), R22/R24 | Different quantity and different file; D7 leaves `predictors.tex` entirely alone. Clear. |

Explicitly **not** touched, per §0.4: R1 (1.1 %), R2 (18.0 %), R4/R12 (`tab:sim-poly-aic` 248/67.3 and
the 1.24×/+24 % ratios), R13 (235B knee), R15/R16 (235B spot-check, ITL metric), R17 (18-episode
population), R18 (0.96×), R20 (~14 %), R22/R23/R24 (`predictors.tex:175/:382/:191`), R25 (2.25×),
R26 (32B clause), R27 (26 parquet files), R28 (`apendice.tex:124`), R29 (21.4 M rows), R30, R31,
R32 (0.12), R33, R35 (≈1.4–1.6×), R41 (v1.3.0), R43 (p30), R44 (onset fraction), R46, R48.
