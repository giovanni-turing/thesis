# Cross-Chapter Consistency Pass

Scope: `/home/gio/tese/tex/*.tex` (13 files, 5,212 lines). All line numbers refer to those files.
This pass establishes **what disagrees with what**. No edits proposed.

Method note: every quantity below was located by exhaustive grep over all 13 chapter files, and
each site's surrounding sentence was read to determine its *subject* and *scope* before being
called a restatement. Where two phrasings turn out to be equivalent, that is stated explicitly
rather than filed as a defect.

---

## 1. Restatement consistency table

### 1.1 The 0.62x cost ratio — VALUE consistent, WORDING drifts

The numeric value is consistent at **every** site. Source of truth is
`closedloop.tex:465-469` (Tab. `tab:cl-aggregate`): 2.41M worker-seconds / 3.87M = 0.6227 -> 0.62x.

| # | Site | Value | Denominator phrasing |
|---|---|---|---|
| 1 | `tese.tex:67` (EN abstract) | 0.62x | "the deployable static encoder fleet's **GPU-time**" |
| 2 | `tese.tex:112` (PT resumo) | 0,62x | "o tempo de **GPU** da **menor frota estatica viavel** de codificadores" |
| 3 | `intro.tex:50` | "a fraction of" | "the deployable static encoder fleet's provisioned **GPU-time** over the covered week" |
| 4 | `intro.tex:271-272` | 0.62 | "the deployable static encoder fleet's provisioned **worker-time**" |
| 5 | `intro.tex:481` | 0.62x | "the deployable static encoder fleet's **worker-time**" |
| 6 | `intro.tex:514` | 0.62x | (no denominator; handoff caveat) |
| 7 | `baselines.tex:98` | 0.62x | "**static**" (bare) |
| 8 | `closedloop.tex:242` | 0.62x | "week" (table shorthand) |
| 9 | `closedloop.tex:265` | 0.62 | col. header "$\times$**static**" |
| 10 | `closedloop.tex:465-469` | 0.62x | col. header "vs. **static**", row "Static $C{=}8$ (deployable)" = 1.00x |
| 11 | `closedloop.tex:481-482` | 0.62 | "the deployable static encoder fleet's provisioned **worker-time**" |
| 12 | `closedloop.tex:500` | 0.62x | "the conservative figure across both readiness models" |
| 13 | `closedloop.tex:530` | 0.62x | rho=15 operating point |
| 14 | `closedloop.tex:630-634` | 0.62x | "the static $C{=}8$ **denominator**" |
| 15 | `closedloop.tex:666-667` | 0.62 | "the deployable static encoder fleet's **worker-time**" |
| 16 | `conclusion.tex:81-82` | 0.62x | "the deployable static encoder fleet's provisioned **worker-time**" |
| 17 | `conclusion.tex:95-96` | "roughly two-thirds" | "the best static ... encoder fleet's **GPU-time**" |
| 18 | `related.tex:361` | 0.62 | "the deployable static encoder fleet's provisioned **worker-time**" |
| 19 | `apendice.tex:11`, `apendice.tex:333` | 0.62x | provenance pointers only |

Sensitivity band **0.59--0.62x** (strict re-warm) restated at `intro.tex:274`,
`closedloop.tex:124`, `closedloop.tex:446`, `closedloop.tex:498-499`, `closedloop.tex:669`,
`conclusion.tex:84`. **Consistent at all six sites**, and all six carry the "strict re-warm"
qualifier. No defect.

rho-frontier **0.89 / 0.62 / 0.48 / 0.40x**: `closedloop.tex:242` vs `closedloop.tex:522-533`
(0.89x at rho=10, 0.40x at rho=25, 0.48--0.89x for rho in {10,15,20}, "aggregate 0.46--0.48x" for
rho=20). **Consistent**; the 0.46--0.48 is explicitly the across-readiness-model range for the
single 0.48 cell, not a competing value.

Language-pool companion **0.96x**: `tese.tex:68`, `tese.tex:114`, `closedloop.tex:375`,
`conclusion.tex:85`. **Consistent.**

**Findings:**

- **[1a] `conclusion.tex:95` rounds 0.62 to "roughly two-thirds".** Two-thirds = 0.667. This is the
  only site that states the headline as a fraction rather than a ratio, and it rounds *away* from
  the measured value in the direction that understates the saving. Same paragraph states 0.62x
  fourteen lines earlier (`conclusion.tex:81`).
- **[1b] `related.tex:361` and `tese.tex:67` quote 0.62x with no span or readiness-model
  qualifier.** Every other prose site carries either "over the 5.60-day covered span"
  (`intro.tex:270`, `conclusion.tex:79`), "over the aggregate and inside every in-span episode"
  (`closedloop.tex:480`), or the warm-pool/strict-re-warm pair. Abstract compression is defensible;
  `related.tex:361` is body text making a positioning claim and is unqualified.

### 1.2 588 ms encoder floor — TWO VALUES IN CIRCULATION (588 and 589)

Derivation, `closedloop.tex:452-457`: f(64)=316.4 ms + p99 handoff 272 ms = **588.4 ms**.

**Sites reading 588:** `intro.tex:265`, `intro.tex:479`, `intro.tex:514`; `conclusion.tex:68`,
`conclusion.tex:101`; `twopool.tex:215`; `baselines.tex:221-227` (per-window table, six rows);
`closedloop.tex:80, 92, 113, 121, 142, 202, 452, 468, 469, 472, 483, 499, 523, 531, 543, 593, 627`.

**Sites reading 589:** `closedloop.tex:241` ("burst3 589 ms"), `closedloop.tex:254` (caption:
"clears the aggregate p99 at the **589 ms** service floor"), `closedloop.tex:265` (Tab.
`tab:cl-ewma`, four cells), `closedloop.tex:606` ("the vLLM reprice, 606 vs. **589 ms**"),
`closedloop.tex:622` ("606 ms versus **589 ms** under AIC"), `apendice.tex:211` ("606 ms (from
**589 ms** under AIC)").

- **[1c] The same "zero-queueing service floor" is called 588 ms in Tab. `tab:cl-aggregate`
  (`closedloop.tex:452-458`, where it is *derived* as 316.4+272) and 589 ms in Tab. `tab:cl-ewma`
  (`closedloop.tex:254, 265`) — both in Chapter closedloop, both labelled "service floor".**
- **[1d] The AIC-priced week-scale encoder-delay p99 baseline is quoted inconsistently within a
  single paragraph of `closedloop.tex`:** the vLLM reprice compares "606 versus **589** under AIC"
  (`:622`), while the HuggingFace-eager reprice five lines later compares "784 versus **588** under
  AIC" (`:627`). These are the same AIC schedule replay. One of the two AIC baselines is misquoted,
  or the two reprice harnesses differ and the text does not say so (contrast `:636-638`, where an
  analogous 647-vs-644 harness gap *is* explicitly called out as "<0.5% harness difference").

### 1.3 734 ms calm-day bound — CONSISTENT

`baselines.tex:228` (source, steady 24h row, p99 column = 734), `closedloop.tex:80` ("the calm day
548--734 ms"), `closedloop.tex:115`, `intro.tex:266` ("the calm day below 734 ms"),
`intro.tex:480`. The 548 lower end (`baselines.tex:228`, `closedloop.tex:80`) also agrees.
**No disagreement.** Note `closedloop.tex:265` gives the calm-day ("steady") figure as 681 ms and
`:268` as 736 ms — those are *EWMA-variant* rows, not the foundation policy, and are correctly
scoped by that table's caption.

### 1.4 Live-vs-simulated agreement band — CONSISTENTLY SCOPED TO TTFT (see also Sec. 2)

| Site | Quoted band | Metric it is attached to |
|---|---|---|
| `validation.tex:67,72` (source table) | +6.8% / +1.1% | TTFT p99 |
| `validation.tex:97` | 1.1--6.8% | "client-observed **TTFT** tails" |
| `validation.tex:159` | 1.1--6.8% | "**TTFT** differs by" |
| `intro.tex:535` | 1.1--6.8% | "**TTFT p99** within" |
| `conclusion.tex:53` | 1.1--6.8% | "**TTFT p99** within" |
| `closedloop.tex:421` | 1.1--6.8% | "both policies' online **TTFT** tails" |

**All five restatements name TTFT.** This is *not* an overclaim — stated explicitly per the brief.

Replica-time band: `validation.tex:69,74` (source: -5.3%, -7.6%); restated as "within 8%"
(`validation.tex:84`, `intro.tex:538-539`) and as "5.3--7.6%" (`validation.tex:160`,
`conclusion.tex:55`). **Consistent** — "within 8%" is a correct loose bound on 5.3--7.6%.

### 1.5 R^2 = 0.123 vs 0.12 — SAME QUANTITY, TWO ROUNDINGS, MIXED WITHIN CHAPTERS

| Value | Sites |
|---|---|
| **0.123** | `intro.tex:146`; `trace-eda.tex:241`; `trace-eda.tex:482`; `related.tex:188`; `related.tex:335` |
| **0.12** | `tese.tex:51` (EN abstract); `tese.tex:92` (PT, "0,12"); `intro.tex:406`; `trace-eda.tex:257`; `predictors.tex:232`; `related.tex:225`; `conclusion.tex:17` |

- **[1e]** 0.123 rounds correctly to 0.12, so no site is *wrong*. But the two roundings are mixed
  **inside the same chapter** three times: `trace-eda.tex:241`/`:482` (0.123) vs `trace-eda.tex:257`
  (0.12); `related.tex:188`/`:335` (0.123) vs `related.tex:225` (0.12); `intro.tex:146` (0.123) vs
  `intro.tex:406` (0.12). A reader cross-referencing within one chapter sees two numbers.
- The paired decode figure **R^2 = 0.654** is quoted only as 0.654 (`intro.tex:147`,
  `trace-eda.tex:245`, `related.tex:335`). **Consistent** — note the asymmetry: the decode figure
  is never rounded to 0.65, only the image figure is rounded.
- `predictors.tex:242` "R^2 = 0.94" and `predictors.tex:232` "R^2 = 0.12" are different regressions
  (additive reconstruction vs cross-signal); not a conflict.

### 1.6 Covered span: 7-day vs 5.60-day vs 1,000,000 requests — CONSISTENT, ONE WORDING SLIP

The thesis maintains a clean two-level distinction:

- **Trace extent** (7 days, 1,000,000 requests): `tese.tex:49-50`, `tese.tex:90`,
  `trace-eda.tex:22-23`, `intro.tex:128-129`, `intro.tex:337` (figure node "1M requests / 7 days"),
  `intro.tex:500`, `predictors.tex:36`, `predictors.tex:405`, `conclusion.tex:98`,
  `trace-eda.tex:133, 142, 455`.
- **Graded closed-loop span** (5.60 days, 749,601 requests, after 1.4 days consumed as forecast
  context): `closedloop.tex:47-53` (the definition), `closedloop.tex:175`, `:369`, `:430`, `:437`,
  `:517`, `:645`; `intro.tex:270`; `conclusion.tex:79`.

**No site claims closed-loop results over all 1,000,000 requests or over the full 7 days.**
The "full 1,000,000-request coverage" language appears only in the git history / `defense/`
materials, **not in `tex/`.** Reported as consistent.

- **[1f] Minor wording slip:** `closedloop.tex:665` "Priced over the covered **week**",
  `closedloop.tex:437` caption "**Week-scale** aggregate (5.60-day covered span...)",
  `intro.tex:50` "over the covered **week**", `tese.tex:71` "the **week-scale** economics".
  5.60 days is not a week. The caption at `:437` disambiguates immediately; `intro.tex:50` and
  `closedloop.tex:665` do not.

### 1.7 Encoder utilization 29% — FULLY CONSISTENT

`tese.tex:60`, `tese.tex:104` (PT), `intro.tex:179`, `intro.tex:460`, `twopool.tex:340`,
`twopool.tex:362`, `twopool.tex:375`, `conclusion.tex:21`. Same value, same subject (mean encoder
utilization during the burst window), same accompanying claim (invisible to rate- and
mean-utilization monitors). **No disagreement.** (`predictors.tex:308` "degrades to 29% at 1-second
bins" is an unrelated WAPE-adjacent figure that happens to share the number.)

### 1.8 Engine ratio 1.62x vs "~1.4--1.6x" — RANGE EXCLUDES ITS OWN ENDPOINTS

Source measurements, `aiconfigurator.tex:269-274` (Tab. `tab:aic-fn`), HF-eager / composed ratio:
N=1 **1.38**, N=6 1.37, N=8 **1.36**, N=16 1.50, N=32 1.58, N=64 **1.62**.

| Phrasing | Sites |
|---|---|
| "**1.36--1.61x**, rising with N" | `apendice.tex:180` |
| "from **~1.37** at small batches to **1.62** at the 64-image dispatch cap" | `aiconfigurator.tex:281`; `aiconfigurator.tex:243-244` (adds "easing to **1.43x** at the largest dispatch") |
| "the earlier **~1.4--1.6x** figure/gap" | `intro.tex:249`; `intro.tex:510`; `apendice.tex:194`; `conclusion.tex:106` |

- **[1g]** The "~1.4--1.6x" band, used at all four *summary* sites, contains neither measured
  endpoint: the low end is 1.36--1.37 and the high end is 1.62. The tilde covers this, but the
  three precise statements disagree with each other too: `apendice.tex:180` says the top of the
  HF-eager range is **1.61**, while `aiconfigurator.tex:274`/`:281` say **1.62**.
  (`apendice.tex:180` is scoped to "SDPA attention", `aiconfigurator` Tab. `tab:aic-fn` to the
  default HF stack — plausibly two different backends, but the text does not reconcile 1.61 vs
  1.62.)
- The **12.8%** vLLM-agreement figure is by contrast quoted consistently and with its `N<=64`
  qualifier at `intro.tex:249`, `intro.tex:509`, `twopool.tex:185`, `closedloop.tex:614`,
  `closedloop.tex:632`, `aiconfigurator.tex:317`, `aiconfigurator.tex:352`, `apendice.tex:196`,
  `apendice.tex:214`, `conclusion.tex:104`, `conclusion.tex:121`. **No overclaim.** The companion
  **11.4%** at `apendice.tex:186` is the three-canonical-shape residual (N=8/32/64), a *narrower*
  scope, correctly distinguished; the two figures are not in conflict.
  Two figure/table captions state "within 12.8%" with no N-scope: `aiconfigurator.tex:248` and
  `aiconfigurator.tex:262`. Low severity (the body 12 lines away carries the scope).

### 1.9 WAPE headline figures — CONSISTENT, ONE LOOSE RESTATEMENT

- Images @ 1 s: **98.8%** best model vs **146.1%** EWMA vs 156.9% naive — `predictors.tex:155`,
  matching Tab. `tab:pred-wape` rows at `predictors.tex:127, 132, 133`. Restated as "~99% on
  1-second bins" at `predictors.tex:214`. **Consistent.**
- Images @ 1 min: **~53%** (`predictors.tex:213`), table value 53.0 (`predictors.tex:132`).
  **Consistent.**
- Horizon degradation: `predictors.tex:206-207` "~52% at h=1 to ~53--54% at h=12" = a cost of
  **1--2 points**. `intro.tex:428` restates this as "twelve steps of lead cost only **~2 WAPE
  points**".
  - **[1h]** Not wrong, but `intro.tex:428` quotes the *worst* end of a 1--2 point range as the
    single figure, which is the conservative direction — noted for completeness, not as a defect.
- The h=1 comparison `predictors.tex:191-193` (ARIMA 0.521 vs best foundation 0.515, "by about a
  WAPE point") is internally inconsistent in *units* (0.521 vs 0.515 is 0.6 percentage points, or
  ~1.2% relative), but that is intra-chapter and belongs to the predictors report.
- No WAPE number is restated in `tese.tex` or `conclusion.tex` at all. Nothing to cross-check.

### 1.10 C* values — CONSISTENT

- Deployable static **C=8** encoders + TP2x2: `baselines.tex:94`, `:118`, `:252`;
  `closedloop.tex:253`, `:465`, `:634`; `aiconfigurator.tex:367`.
- Calm-day optimum **C=2**: `closedloop.tex:466`; restated as "4x/2x calm-day overprovisioning"
  (`baselines.tex:253`, `closedloop.tex:643`) — 8/2 = 4x encoders, TP2/TP1 = 2x language.
  **Arithmetically consistent.**
- Per-window range **6--8 encoder workers**: `intro.tex:467-468`, `conclusion.tex:24`.
  **Consistent** with the C=8 max-over-windows definition.
- **No disagreement found.**

---

## 2. Scope / overclaim

### 2.1 Live-vs-simulated band: is it TTFT-only at source but quoted broadly? — NO

Answered in Sec. 1.4: all five restatement sites (`validation.tex:97`, `validation.tex:159`,
`intro.tex:535`, `conclusion.tex:53`, `closedloop.tex:421`) explicitly bind 1.1--6.8% to **TTFT
p99**. **This is not an overclaim.** State plainly: the band is correctly scoped everywhere it
appears.

### 2.2 Does any ITL pair fall outside the quoted band? — YES, and it is disclosed

From Tab. `tab:val-anchor`, `validation.tex:67-74`:

| Policy | Metric | Live | Offline twin | Relative delta |
|---|---|---|---|---|
| Forecast p90 | TTFT p99 | 695 | 651 | **+6.76%** (in band) |
| Forecast p90 | **ITL p99** | **11.5** | **9.7** | **+18.56%** — **OUTSIDE the 1.1--6.8% band** |
| Forecast p90 | replica-seconds | 6,063 | 6,400 | -5.27% (in band) |
| Reactive | TTFT p99 | 3,531 | 3,495 | +1.03% (in band; text says 1.1%) |
| Reactive | ITL p99 | 150.7 | 152.7 | -1.31% (in band) |
| Reactive | replica-seconds | 1,799 | 1,948 | -7.65% (in band) |

- The outlier **is disclosed**, at `validation.tex:160-162` ("though the forecast policy's ITL
  differs by 1.8 ms, **18.0%**, both far under the 100 ms bound") and at `intro.tex:536-538`
  (gives the raw pair 11.5 vs 9.7 rather than a percentage). `conclusion.tex:53-54` gives only the
  verdict agreement, no magnitude — acceptable given the space, but it is the one site where a
  reader could infer the 1.1--6.8% band covers ITL.
- **[2a] The disclosed percentage is wrong.** `validation.tex:161` states **18.0%**; the table's own
  values give **(11.5 - 9.7)/9.7 = 18.56%**, i.e. 18.6%. Even taken against the live value,
  1.8/11.5 = 15.7%. 18.0% matches neither. Either the table is rounded from unrounded values that
  do give 18.0% (e.g. 11.45/9.70 = 18.0% requires 11.446/9.700), or the text figure is stale.
- **[2b] Related rounding:** `validation.tex:72` reactive TTFT is quoted as **+1.1%** but
  (3531-3495)/3495 = **+1.03%**, which rounds to 1.0%. The band's *lower* endpoint, restated at
  five sites, is therefore built on a figure that rounds the wrong way. Small, but it propagates to
  `intro.tex:535`, `conclusion.tex:53`, `closedloop.tex:421`, `validation.tex:97`,
  `validation.tex:159`.

### 2.3 Other bound-widening checks

- **`twopool.tex:216-217` "validated against the week replay to within 8% at p99: 706 modelled
  versus 651 ms replayed."** (706-651)/651 = **8.45%**; 55/706 = 7.79%. **[2c] The claim "within 8%"
  holds only if the modelled value is used as the denominator.** Flagged here rather than in the
  twopool internal report because a *different* "within 8%" (replica-time, `validation.tex:84`,
  `intro.tex:539`) circulates in the same thesis with a different subject; a reader meeting both
  will conflate them. The two 8% figures are **not the same claim** — say so explicitly.
- **12.8%**: correctly scoped everywhere (Sec. 1.8). The `+21.8%` residual past the FIFO cap at
  N=512 is disclosed at `apendice.tex:197-198` and never omitted from a restatement, because every
  restatement carries "across the whole N<=64 serving regime".
- **Resolution scope**: `apendice.tex:213-217` limits 12.8% to 448^2 and below, with 15.5% at
  640^2/896^2. `twopool.tex:185` correctly says "At 448^2 the cost model matches to within 12.8%".
  `conclusion.tex:104` and `intro.tex:509` state 12.8% without a resolution qualifier — defensible,
  since `intro.tex:505-506` establishes the uniform-448^2 assumption for the whole encoder pool.
  **Not filed as an overclaim.**

---

## 3. Denominator drift on the 0.62x headline

Five distinct phrasings are in circulation for what 0.62x is measured *against*:

| Phrasing | Sites |
|---|---|
| A. "the deployable static encoder fleet's **provisioned worker-time**" | `intro.tex:272`, `closedloop.tex:482`, `conclusion.tex:81`, `related.tex:361` |
| B. "the deployable static encoder fleet's **worker-time**" | `intro.tex:481`, `closedloop.tex:667` |
| C. "the deployable static encoder fleet's **(provisioned) GPU-time**" | `tese.tex:67`, `intro.tex:50`, `conclusion.tex:96` |
| D. (PT) "o tempo de **GPU** da **menor frota estatica viavel** de codificadores" | `tese.tex:112` |
| E. bare "**static**" | `baselines.tex:98`, `closedloop.tex:263`, `closedloop.tex:465` (col. header), `closedloop.tex:242` |

**Verdict: all five denote the same denominator.** Justification, in order:

1. **A == B.** "provisioned worker-time" vs "worker-time" — the closedloop source
   (`closedloop.tex:483`) gives the denominator as **3.87M worker-seconds** of the static C=8
   fleet, which *is* provisioned (standing) time, not busy time. Dropping "provisioned" loses a
   disambiguation but does not change the referent. **Equivalent.**
2. **A/B == C.** `baselines.tex:17-19` settles it explicitly: costs are "scored ... with
   provisioned **GPU-time** *per hardware class* (**RTX 5090-class worker-seconds for the encoder
   pool**, H100 GPU-hours for the language pool; never summed across classes)". The thesis thereby
   *defines* encoder worker-seconds as the encoder pool's GPU-time. `baselines.tex:75` carries a
   "5090 GPU-h" column against a `C*` (worker-count) column, and `baselines.tex:93` reports
   "58.2/3.6/25.2/10.9 **5090-hours**" for worker-count changes. **Equivalent** — one GPU per
   encoder worker. Not a defect; noted because the equivalence is established once, in
   `baselines.tex:17-19`, and is never restated where C is used.
3. **C == D (PT).** "menor frota estatica viavel" = "smallest feasible static fleet". The EN term
   is "**deployable** static", defined at `baselines.tex:118-119` as the single static
   configuration feasible across *all* windows (C=8 + TP2x2), i.e. the max over per-window C* of
   6--8. "Smallest feasible across all windows" and "deployable" denote the same fleet.
   **Equivalent** — the PT is arguably the clearer wording.
4. **E == A.** Tab. `tab:cl-aggregate` (`closedloop.tex:465`) pins the bare "static" to the row
   "Static C=8 (deployable) ... 3.87 Mworker-s ... 1.00x". **Equivalent.**

**No denominator drift.** The only residual risk is presentational: a reader meeting C
(`tese.tex:67`, GPU-time) before reaching `baselines.tex:17-19` has no basis to know that encoder
worker-time and encoder GPU-time are the same, and the abstract does not say so. That is a
readability gap, not an inconsistency.

**One genuine denominator-adjacent issue:** `closedloop.tex:634-638` reports that the C=8
denominator, repriced at measured vLLM cost, gives encoder-delay p99 **692 ms vs 647 ms under AIC
in that reprice harness**, while Tab. `tab:cl-aggregate` reads **644 ms** for the same static row
(`closedloop.tex:465`). The text calls this "a <0.5% harness difference within run noise" —
647/644 = +0.47%, so the arithmetic checks out and this is correctly disclosed. **Not a defect.**

---

## 4. Stale limitations

Checked every `\section{Limitations}` / "Scope" / "future work" block:
`intro.tex:497-540`, `trace-eda.tex:450+`, `predictors.tex:367-392`, `twopool.tex:381-434`,
`closedloop.tex:558-646`, `validation.tex:148-166`, `apendice.tex:200-219`,
`apendice_ecosystem.tex:162-168`, `conclusion.tex:98-140`.

**Most limitation wording is current.** Specifically verified as *not* stale:

- **"Modelled reconstruction" language survives correctly.** `twopool.tex:218-219` calls the
  ~1.30 s ingress-to-first-token figure "a modelled reconstruction rather than a request-linked
  replay measurement". Nowhere else is the end-to-end figure described as measured — the only other
  mentions (`tese.tex:134`, `apendice.tex:11`) list "end-to-end latency" as an archived re-run,
  which is provenance language, not a measurement claim. **No contradiction.**
- **Encoder-pool live-loop gap.** `validation.tex:153-154` ("the encoder pool's controller exists
  only in simulation") and `conclusion.tex:108-109` ("the vision-pool control loop is exercised in
  simulation and against the measured silicon cost, not yet as a live serving loop") agree.
- **Physical anchor.** `intro.tex:539-540` ("the physical encoder-worker anchor remains future
  work") is consistent with `conclusion.tex:118-122` ("What remains is one real encoder worker
  serving a burst replay end to end") and `apendice.tex:218-219` ("A live-worker confirmation over
  the full serving path ... remains future work"). All three scope the gap to a *live worker*, not
  to physical measurement generally — which would have contradicted `aiconfigurator.tex` and
  `intro.tex:245-249`. **Correctly worded.** Residual risk: `intro.tex:539-540` says "the physical
  encoder-worker anchor" with no further qualifier, which can be misread as "there is no physical
  anchor"; the sentence 290 lines earlier (`intro.tex:245`) establishes otherwise.
- **Language-pool timing.** `twopool.tex:397-400` ("not -- and within this work cannot be --
  re-validated against physical H100 measurement") vs `intro.tex:242` ("language-pool timing
  calibrated"). "Calibrated" and "physically validated" are distinct and the thesis keeps them
  distinct. **No contradiction.**
- **Coverage.** No limitation says coverage is partial while another claims full-trace coverage —
  see Sec. 1.6. The 1.4-day forecast-context exclusion is stated identically at
  `closedloop.tex:47-53`, `closedloop.tex:598-600`, and `trace-eda.tex:176`.

**Findings:**

- **[4a] `apendice_ecosystem.tex:141-144` mis-cites the chapter.** "the live closed-loop validation
  drives a real Dynamo control plane with **aiperf** as the client (the `live_fc` / `live_re` runs
  and their `profile_export_aiperf.json` exports, **Chapter~\ref{cap:closedloop}**)". Those runs are
  Chapter `cap:validation` (`validation.tex:2-4` names `live_runs/{live_fc,live_re,...}` as its own
  artifacts; `validation.tex:31` names aiperf as its client). The cross-reference points at the
  wrong chapter. This is the clearest cross-chapter defect in this pass.
- **[4b] `apendice_ecosystem.tex:166-167` "a full-serving-path run with real GPU engines behind
  **aiperf** remains future work"** — ambiguous parse. aiperf is *already* used, live, at
  `validation.tex:31` and `apendice_ecosystem.tex:142`. The intended reading ("real GPU engines,
  driven via aiperf") is recoverable, but the surface reading ("running aiperf at all") is
  contradicted two paragraphs above in the same file. Wording, not substance.
- **[4c] `closedloop.tex:571-575`** states language-pool closed-loop evidence covers "the full
  evaluation span (the week-scale run above)" while the immediately preceding limitation says the
  remaining windows "are priced by the grid and the knee formula rather than replayed end-to-end".
  Both are true at different granularities (aggregate span replayed; individual non-triad windows
  not), but "full evaluation span" and "the remaining windows are priced rather than replayed" sit
  in adjacent clauses without a connective marking the shift. Low severity; flagged because the
  0.62x per-episode claim rests on which windows were replayed.

---

## Summary of findings, by severity

| ID | Severity | Finding |
|---|---|---|
| **1d** | **High** | AIC week-scale encoder-delay p99 quoted as 589 (`closedloop.tex:622`) and 588 (`closedloop.tex:627`) in adjacent reprice comparisons |
| **1c** | **High** | "Service floor" = 588 ms in Tab. `tab:cl-aggregate` (derived 316.4+272) vs 589 ms in Tab. `tab:cl-ewma` |
| **2a** | **High** | `validation.tex:161` states ITL delta 18.0%; table values give 18.56% |
| **4a** | **High** | `apendice_ecosystem.tex:144` cites `cap:closedloop` for live runs belonging to `cap:validation` |
| **2c** | Medium | `twopool.tex:217` "within 8%" is 8.45% against the replayed value; distinct from the unrelated replica-time "within 8%" |
| **1g** | Medium | "~1.4--1.6x" excludes both measured endpoints (1.36/1.37 and 1.62); `apendice.tex:180` says 1.61, `aiconfigurator.tex:274` says 1.62 |
| **2b** | Medium | Band endpoint 1.1% is really 1.03%; propagates to five sites |
| **1e** | Medium | R^2 printed as both 0.123 and 0.12, mixed within intro, trace-eda, and related |
| **1a** | Low | `conclusion.tex:95` "roughly two-thirds" for 0.62 |
| **1b** | Low | `related.tex:361` quotes 0.62x with no span/readiness qualifier |
| **1f** | Low | "covered week" / "week-scale" for a 5.60-day span (`intro.tex:50`, `closedloop.tex:665`) |
| **1h** | Low | `intro.tex:428` quotes "~2 WAPE points" for a 1--2 point range |
| **4b** | Low | `apendice_ecosystem.tex:167` aiperf "future work" wording |
| **4c** | Low | `closedloop.tex:571-575` "full evaluation span" adjacent to "priced rather than replayed" |

**Explicitly checked and found consistent** (no action): the 0.62x denominator across all five
phrasings (Sec. 3); the live-vs-simulated band's TTFT scoping across all five restatements
(Sec. 2.1); the 734/548 ms calm-day bounds; 29% encoder utilization; the 5.60-day vs 7-day
coverage distinction and the absence of any full-1M-request grading claim; C* = 8 / 2 and the
4x/2x derivation; 0.96x language-pool companion; the 0.59--0.62x strict-re-warm band; the
rho-frontier 0.89/0.62/0.48/0.40x; the 12.8% figure's N<=64 scoping at all eleven sites; the
"modelled reconstruction" limitation language.
