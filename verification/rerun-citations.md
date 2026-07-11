# Rerun: citation + precedence material for P0-7 and P2-10

Date: 2026-07-10. Author: research/verification pass (READ-only; no `.tex` edited).
Scope: fix (P0-7) three "first"/precedence claims at `tex/related.tex:303--309` that do
not survive prior art, and (P2-10) the missing queueing/staffing lineage for the
tail-aware capacity conversion.

Sources used: local RAG corpus (`rag` collection via raggae), `/home/gio/tese/papers`,
and web (titles/venues/specs only; no thesis content sent to any query).

---

## 0. The three claims as currently worded (`tex/related.tex:303--309`)

> The thesis makes three precedence claims, each deliberately narrow: to our
> knowledge, the first **per-pool demand-signal characterization of a production
> multimodal inference trace**; the first **provisioning-framed, zero-shot benchmark
> of time-series foundation models on serving demand signals**; and the first
> **silicon-calibrated encoder cost model for a consumer-class GPU in a deployment
> planner**, contributed upstream.

Verified counter-evidence below defeats or pressures each **as worded**. None of the
underlying contributions is lost — each claim just needs its defensible qualifier made
explicit and the prior art credited.

---

## 1. ModServe — defeats claim #1 as worded (VERIFIED via RAG)

Query run:
`rag.py search "Token-Aware Pool Autoscaling image tokens per second modality-specific load" --collection rag --top-k 20 --rerank-top-n 3 --where title="ModServe: ..." --full`
Chunk `arxiv:2502.00937:0013`, rerank score 0.832. Paper is already cited by the thesis
as `\cite{Qiu2025ModServe}` (tese.tex:173, ACM SoCC 2025, arXiv:2502.00937).

**Exact scaling-signal sentences (verbatim from the chunk):**

> "The number of replicas per stage is computed as ⌈M_L / M_C⌉ where M_L is the
> **modality-specific load** (e.g., prompt tokens/sec for Text Instances, **image
> tokens/sec for Image Instances**) and M_C is the maximum capacity each stage can
> handle without violating SLOs, based on the offline LMM profiling data. **Unlike
> traditional web service autoscaling, which reacts to request rates, ModServe
> optimizes scaling based on token throughput (tokens/s), capturing variations in both
> request rates and request sizes** (Insight 6 and Figure 11a). For Image Instances,
> image token counts are precomputed based on the static mapping from image dimensions
> to the number of tokens per image."

Plus initial provisioning (same chunk):

> "Before their online operation, the initial number of Image Instances (N_i) is
> determined using the median image QPS multiplied by the median image encoding
> latency."

And the burstiness characterization (chunk `:0011`, **Insight 6**):

> "Production LMM image traffic exhibits **bursty behavior independent of the traffic
> patterns of text requests** due to the nature of different services. Serving systems
> must dynamically scale resources to handle modality-specific bursts efficiently."

**What this defeats:** ModServe already (a) drives per-pool (Image vs Text) autoscaling
on a *modality-specific* signal — image tokens/s — and (b) explicitly contrasts this
with request-rate autoscaling, and (c) characterizes production image traffic as bursty
and decoupled from text. So "first **per-pool demand-signal characterization** of a
production multimodal inference trace" is not defensible as a bare characterization.

**What survives (defensible):** ModServe's scaling is *reactive* (real-time token load,
no forecast) and its characterization is *qualitative* ("bursty, independent"). The
thesis's defensible edge is (i) the **forecast-driven** (predictive, not reactive)
framing, and (ii) the **quantified** decoupling: request rate explains only
`R^2 = 0.123` of the image-rate series vs `R^2 = 0.654` of decode demand
(`intro.tex:141--142`), turning ModServe's qualitative "independent" into a measured
inversion and tying it to forecastability. That quantified inversion — burstiest signal
is the least visible to request-rate scaling yet the most forecastable — is what no
prior work states or tests.

---

## 2. Diao et al. and Toner et al. — pressure claim #2 (VERIFIED via web + local PDF text)

Both are **absent** from the thesis bibliography (checked all 62 `\bibitem`s in
tese.tex). Both need new entries.

### 2a. Diao et al., SoCC 2024 (VERIFIED — full text extracted locally)

- **Exact title:** *Forecasting Algorithms for Intelligent Resource Scaling: An
  Experimental Analysis* (ACM DL / dl.acm.org title; the Amazon Science landing page
  renders the subtitle as "An Empirical Analysis" — use the ACM DL form "Experimental").
- **Authors (from the PDF front matter, in order):** Yanlei Diao, Dominik Horn, Andreas
  Kipf, Oleksandr Shchur, Ines Benito, Wenjian Dong, Davide Pagano, Pascal Pfeil, Vikram
  Nathan, Balakrishnan Narayanaswamy, Tim Kraska. (The Amazon Science page lists
  "Murali Narayanaswamy"; the PDF byline is "Balakrishnan Narayanaswamy", email
  muralibn@ — i.e. B. "Murali" Narayanaswamy. Use "B. Narayanaswamy".)
- **Venue/year/pages:** Proceedings of the 2024 ACM Symposium on Cloud Computing (SoCC
  '24), pp. 126--143. DOI 10.1145/3698038.3698564.
- **What it benchmarks (confirmed from extracted text):** an experimental comparison of
  forecasting algorithms for **cloud resource scaling / autoscaling** (Amazon Redshift
  Serverless query workloads). Methods span classical (ETS, ARIMA/AutoARIMA, Theta),
  deep learners (DeepAR, PatchTST, TFT), an AutoGluon weighted ensemble, **and the
  Chronos time-series foundation model** — explicitly discussed for its "ability to
  generate **zero-shot** forecasts on new [clusters]" and its known failure mode
  ("Chronos tokenization scheme is known to lose resolution on spiky data").
- **Bearing on claim #2:** this IS a provisioning-framed benchmark of forecasting
  algorithms — including a zero-shot foundation model (Chronos) — on cloud demand
  signals, for scaling decisions. It pressures "first provisioning-framed benchmark
  ... of foundation models on serving demand signals." Distinction that survives:
  its signals are cloud *query/VM* workloads, not modality-disaggregated *inference-
  serving* per-pool signals, and it studies forecast accuracy, not consumption of the
  forecast by a serving planner in a closed loop.

### 2b. Toner et al., PMLR 2025 (VERIFIED via arXiv abstract)

- **Exact title:** *Performance of Zero-Shot Time Series Foundation Models on Cloud
  Data*.
- **Authors (in order):** William Toner, Thomas L. Lee, Artjom Joosen, Rajkarn Singh,
  Martin Asenov.
- **Venue/year:** "I Can't Believe It's Not Better" (ICBINB) workshop at ICLR 2025;
  PMLR proceedings, 2025 (5-page paper). arXiv:2502.12944 [cs.LG] (v1 Feb 2025; final
  May 2025).
- **What it benchmarks:** the **zero-shot** forecasting quality of time-series
  **foundation models** on **cloud data**, motivated explicitly by pre-emptive resource
  scaling / avoiding over-provisioning. Headline finding: widespread failure — FMs are
  outperformed by simple linear baselines and can produce "erratic, random-looking
  forecasts" on spiky cloud series.
- **Bearing on claim #2:** this is the most direct prior art for "zero-shot benchmark
  of time-series foundation models" in a provisioning-motivated cloud setting. It
  pressures the claim head-on. Distinction that survives: again generic cloud data,
  not multimodal-serving per-pool signals, and accuracy-only (no rolling-origin
  provisioning frame, no forecast consumed by a planner in closed loop).

**Net for claim #2:** drop "first ... benchmark of time-series foundation models on
serving demand signals" in the broad form. Narrow to the multimodal-serving domain +
the closed-loop-consumption frame, and credit Diao and Toner for establishing the
zero-shot-FM-on-cloud-demand benchmark tradition.

---

## 3. HeteroServe — defeats broad claim #3 (already cited by the thesis)

Already in the bibliography as `\bibitem{Yu2026HeteroServe}` (tese.tex:418--422):

> D. Yu. *Cost-Efficient Multimodal LLM Inference via Cross-Tier GPU Heterogeneity*.
> 2026. arXiv:2603.12707.

Cited at `related.tex:71` for exactly the consumer-class-GPU encoder-placement split
this thesis adopts: "cross-tier deployments placing the compute-bound encode stage on
consumer-class GPUs ... have been costed~\cite{Yu2026HeteroServe}."

**What this defeats:** "first **silicon-calibrated encoder cost model for a
consumer-class GPU**" is too broad — HeteroServe already costs a consumer-class vision
encoder to make its cross-tier placement decision.

**What survives (defensible):** HeteroServe costs the encoder *standalone*, to inform a
placement choice. The thesis's defensible edge is integrating a silicon-calibrated
consumer-class-GPU (RTX 5090) encoder cost model **into a deployment planner**
(aiconfigurator's operator/perf database, which had *no* consumer-/workstation-class GPU
data for the encoder operator before this work — `related.tex:277--279`), and
**contributing that calibration upstream**. So: keep "in a deployment planner,
contributed upstream"; drop the bare "first ... cost model" framing.

---

## 4. Queueing/staffing lineage for the tail-aware conversion (P2-10)

### 4a. Where the anchor is missing

- The tail-aware conversion is defined at `closedloop.tex:152--184`: the planner sizes
  replicas `= ⌈d̂ / r̂⌉` on *mean* per-replica throughput `r̂` (10.07 req/s per TP2
  replica), but the SLA-relevant capacity is the **tail knee** `r_tail` (1.62 req/s on
  burst1; [1.26, 1.44] on burst4). Dividing forecast demand by `r_tail` instead of `r̂`
  builds a safety margin sized to hold the tail SLA. `baselines.tex:150--153` names the
  failure of the naive version: the "mean-based capacity conversion ... leaves no room
  for the tail the SLA prices."
- The only OR anchor currently present is the **newsvendor / critical-fractile** framing
  (`related.tex:252--257`, `\cite{Arrow1951Newsvendor}`, tese.tex:392). There is **no
  queueing/staffing citation anywhere** (grep of all `*.tex`: no Erlang / Halfin /
  Kleinrock / staffing / square-root). The tail-aware conversion — replace mean service
  rate by a tail-preserving effective rate = load + safety margin — is exactly the
  square-root safety-staffing idea from many-server queueing, and is currently
  un-anchored.

### 4b. What is available locally (RAG corpus + ./papers)

Queueing-theory textbooks confirmed present in the `rag` collection (raggae search
"Erlang staffing square-root ... Halfin-Whitt"):

- **Fundamentals of Queueing Theory, 5th ed.** — J. F. Shortle, J. M. Thompson, D.
  Gross, C. M. Harris. Wiley, 2018 (ISBN 9781118943526). [rag: chunks
  `54_Fundamentals_of_Queueing_Theory:*`] — Erlang-B/C, M/M/c, offered load.
- **Kleinrock, Queueing Systems, Vol. 2 (Computer Applications).** Wiley, 1976. [rag:
  `paper-image:...` "Kleinrock Queueing Systems, Vol. 2"]. (Vol. 1, *Theory*, 1975 is
  the more common foundational cite; only Vol. 2 is confirmed in-corpus.)
- **Probability, Stochastic Processes, and Queueing Theory** — R. Nelson, Springer,
  1995 (ISBN 978-1-4419-2846-7). [rag: `60_Probability__Stochastic_Processes__and_Q`].

Modern queueing-theoretic LLM-serving/provisioning papers present in `./papers` (useful
as the *bridge* from classical staffing to this thesis's setting, optional):

- `papers/2603.16054 - inference-fleet-sim A Queueing-Theory-Grounded Fleet Capacity
  Planner for LLM Inference.pdf`
- `papers/2407.00047 - Queue-Management-for-SLO-Oriented-Large-Language-Model-
  Serving.pdf`
- `papers/2605.01280 - Position LLM Serving Needs Mathematical Optimization and
  Algorithmic Foundations, Not Just Heuristics.pdf`

### 4c. Canonical square-root-staffing anchors (NOT in local corpus; web-verified)

The classical safety-staffing lineage — staffing = offered load + safety margin, margin
~ sqrt(load) — is not in `./papers` but is standard and its bibliographic details are
verified:

- **Halfin & Whitt (1981)**, *Heavy-Traffic Limits for Queues with Many Exponential
  Servers*, Operations Research **29(3):567--588**. Origin of the QED ("square-root")
  many-server heavy-traffic regime. [verified: ideas.repec.org/a/inm/oropre/
  v29y1981i3p567-588]
- **Borst, Mandelbaum & Reiman (2004)**, *Dimensioning Large Call Centers*, Operations
  Research **52(1):17--34**. Rigorous justification of the square-root safety-staffing
  rule `N* = R + y*·sqrt(R)`. [verified: ideas.repec.org/a/inm/oropre/
  v52y2004i1p17-34]
- *(optional, for the Palm/Erlang-A abandonment lineage the audit note mentions)*
  **Garnett, Mandelbaum & Reiman (2002)**, *Designing a Call Center with Impatient
  Customers*, Manufacturing & Service Operations Management 4(3):208--227.
  **VERIFY pages before use** — title/venue confident, exact pages not re-verified in
  this pass.

**Recommended minimal anchor set** for the 2--3-sentence addition: Halfin--Whitt (1981)
+ Borst--Mandelbaum--Reiman (2004) for the square-root safety-staffing rule, plus one
in-corpus textbook (Gross/Shortle et al. 2018 or Kleinrock) for the M/M/c / Erlang
foundation. Garnett et al. optional if the impatient-customer / Erlang-A analogy is
wanted (abandonment ~ dropped/timed-out requests under the tail SLA).

---

## 5. DRAFT (a): corrected three-precedence-claim paragraph

Proposed replacement for the sentence block at `tex/related.tex:303--309` (the
"The thesis makes three precedence claims ..." sentence). Keeps the same three-claim
structure and the "deliberately narrow" framing; each claim now carries its defensible
qualifier and credits the prior art. `\cite` keys used already exist except
`Diao2024Forecasting` and `Toner2025ZeroShot` (new bibitems in §6).

> The thesis makes three precedence claims, each deliberately narrow. ModServe already
> autoscales image and text pools on a modality-specific signal --- image tokens per
> second --- and contrasts this with request-rate
> autoscaling~\cite{Qiu2025ModServe}; what it does not do is forecast that signal or
> quantify how far it departs from request rate. The first claim is therefore not the
> per-pool characterization but its \emph{forecast-driven} sharpening: to our knowledge,
> the first work to measure that the vision pool's arrival signal is nearly decoupled
> from request rate ($R^2 = \num{0.123}$, versus $\num{0.654}$ for decode demand;
> Chapter~\ref{cap:trace-eda}) and to turn that measured inversion --- the burstiest,
> least rate-visible signal is also the most forecastable --- into a per-pool predictive
> provisioning signal. Second, zero-shot time-series foundation models have already been
> benchmarked on cloud demand for provisioning: Diao et al.\ compare Chronos against
> classical and deep forecasters for Redshift-Serverless resource
> scaling~\cite{Diao2024Forecasting}, and Toner et al.\ evaluate zero-shot foundation
> models on cloud data for the same purpose~\cite{Toner2025ZeroShot}. Narrowed against
> them, the claim is the first \emph{provisioning-framed, rolling-origin} zero-shot
> benchmark of such models on the \emph{per-pool demand signals of a production
> multimodal inference trace}, with the forecast consumed downstream by a serving
> planner in closed loop rather than scored on accuracy alone
> (Chapters~\ref{cap:predictors} and~\ref{cap:closedloop}). Third, a silicon-calibrated
> consumer-class vision encoder has already been costed for cross-tier
> placement~\cite{Yu2026HeteroServe}; the narrow claim is the first to integrate such a
> consumer-class-GPU encoder cost model into a \emph{deployment planner}
> (aiconfigurator's per-operator performance database, which held no consumer- or
> workstation-class GPU data for the encoder operator before this work), with the
> calibration contributed upstream (Chapter~\ref{cap:aiconfigurator}).

Notes for the editor:
- Chapter labels (`cap:trace-eda`, `cap:predictors`, `cap:closedloop`,
  `cap:aiconfigurator`) all already exist in the thesis and are referenced elsewhere.
- `\num{0.123}` / `\num{0.654}` match the siunitx usage at `intro.tex:141--142`.
  (`tese.tex:46` abbreviates to `R^2 = 0.12`; the related-work sentence can use the full
  0.123 for precision, or `0.12` to match the abstract --- editor's choice, keep one.)
- If the paragraph feels long, the middle (claim #2) sentence and the ModServe sentence
  can each be trimmed; the load-bearing pieces are the four credits
  (ModServe/Diao/Toner/HeteroServe) and the four qualifiers (forecast-driven +
  quantified inversion; multimodal per-pool + closed-loop-consumed; in-a-planner +
  upstreamed).

---

## 6. DRAFT (b): 2--3 sentence related-work addition anchoring the tail-aware conversion

Proposed insertion right after the newsvendor sentence at `related.tex:252--257` (which
already grounds the \emph{use} of the forecast). New `\cite` keys: `HalfinWhitt1981`,
`Borst2004Dimensioning`, `Gross2018QueueingFundamentals` (all new bibitems in §7).

> The conversion from that quantile forecast to a replica count has an equally classical
> anchor. Sizing servers so that a mean-rate estimate of load leaves a safety margin for
> the tail is the \emph{square-root safety-staffing} rule of many-server queueing: in
> the Halfin--Whitt heavy-traffic regime the economical staffing level is the offered
> load plus a margin that grows like its square
> root~\cite{HalfinWhitt1981,Borst2004Dimensioning}, exactly the quality-and-efficiency
> trade-off that dimensions call centers under a delay target. This thesis's tail-aware
> capacity conversion (Chapter~\ref{cap:closedloop}) is the serving analogue: it sizes
> the encoder and language pools not on mean per-replica throughput --- the M/M/c
> ``offered-load'' term~\cite{Gross2018QueueingFundamentals} --- but on the tail-knee
> rate a replica sustains under the SLA, so the extra replicas are precisely the
> safety staffing the percentile requires.

Optional one-clause extension linking to the modern LLM-queueing bridge (if the
`./papers` items are to be cited too): append
`, a connection recent queueing-grounded LLM capacity planners make explicit~\cite{...}`
using a new bibitem for `inference-fleet-sim` (2603.16054) or Queue Management
(2407.00047). Not required for the anchor; offered for completeness.

---

## 7. DRAFT (c): new \bibitem entries (matching tese.tex inline thebibliography style)

Style observed in tese.tex: `A.~B. Surname` initials with tie, `\emph{Title}.`,
then `Venue, Year. arXiv:XXXX.` for preprints/conferences or
`Journal, vol(issue):pp--pp, Year.` for journals; books `Publisher, City, Year.`

```latex
\bibitem{Diao2024Forecasting}
Y.~Diao, D.~Horn, A.~Kipf, O.~Shchur, I.~Benito, W.~Dong, D.~Pagano, P.~Pfeil,
V.~Nathan, B.~Narayanaswamy, T.~Kraska.
\emph{Forecasting Algorithms for Intelligent Resource Scaling: An Experimental
Analysis}.
ACM SoCC, 2024, pp.~126--143. \url{https://doi.org/10.1145/3698038.3698564}.

\bibitem{Toner2025ZeroShot}
W.~Toner, T.~L. Lee, A.~Joosen, R.~Singh, M.~Asenov.
\emph{Performance of Zero-Shot Time Series Foundation Models on Cloud Data}.
ICBINB Workshop, ICLR (PMLR), 2025. arXiv:2502.12944.

\bibitem{HalfinWhitt1981}
S.~Halfin, W.~Whitt.
\emph{Heavy-Traffic Limits for Queues with Many Exponential Servers}.
Operations Research, 29(3):567--588, 1981.

\bibitem{Borst2004Dimensioning}
S.~Borst, A.~Mandelbaum, M.~I. Reiman.
\emph{Dimensioning Large Call Centers}.
Operations Research, 52(1):17--34, 2004.

\bibitem{Gross2018QueueingFundamentals}
J.~F. Shortle, J.~M. Thompson, D.~Gross, C.~M. Harris.
\emph{Fundamentals of Queueing Theory}, 5th~ed.
Wiley, Hoboken, NJ, 2018.
```

Optional extras (only if the corresponding draft clause is kept):

```latex
% Erlang-A / Palm impatient-customer lineage -- VERIFY pages before use
\bibitem{Garnett2002ImpatientCustomers}
O.~Garnett, A.~Mandelbaum, M.~Reiman.
\emph{Designing a Call Center with Impatient Customers}.
Manufacturing \& Service Operations Management, 4(3):208--227, 2002.

% classical queueing foundation (in-corpus; Vol. 1 is the theory volume)
\bibitem{Kleinrock1975}
L.~Kleinrock.
\emph{Queueing Systems, Volume 1: Theory}.
Wiley, New York, 1975.

% modern queueing-grounded LLM capacity planner bridge (in ./papers)
\bibitem{InferenceFleetSim2026}
% first author/title verbatim from papers/2603.16054 before use
\emph{inference-fleet-sim: A Queueing-Theory-Grounded Fleet Capacity Planner for LLM
Inference}. 2026. arXiv:2603.16054.
```

---

## 8. Summary of what changed and confidence

| Item | Finding | Confidence |
| --- | --- | --- |
| Claim #1 defeated as worded | ModServe scales pools on image-tokens/s, contrasts with request-rate, calls image traffic bursty+independent (Insight 6) | HIGH (verbatim RAG quote) |
| Claim #1 defensible core | forecast-driven + quantified inversion (R^2=0.123 vs 0.654) | HIGH (intro.tex:141-142) |
| Claim #2 pressured | Diao (SoCC'24) benchmarks Chronos+forecasters for cloud scaling; Toner (PMLR'25) benchmarks zero-shot FMs on cloud data | HIGH (Diao full text extracted; Toner abstract) |
| Claim #2 defensible core | multimodal per-pool signals + closed-loop planner consumption | HIGH |
| Claim #3 defeated as worded | HeteroServe (Yu2026, already cited @related.tex:71) costs a consumer-GPU encoder | HIGH |
| Claim #3 defensible core | "in a deployment planner, contributed upstream" | HIGH |
| Tail-aware conversion anchor | square-root safety staffing: Halfin-Whitt 1981, Borst-Mandelbaum-Reiman 2004; textbook: Gross/Shortle 2018 (in-corpus), Kleinrock (in-corpus) | HIGH (bib details web-verified; textbooks confirmed in rag) |
| Diao author "Narayanaswamy" | PDF byline "Balakrishnan", email muralibn@ -> B. Narayanaswamy | HIGH (from PDF) |
| Diao subtitle | "Experimental" (ACM DL) vs "Empirical" (Amazon Science page) -> use "Experimental" | MEDIUM (two sources disagree; ACM DL authoritative) |
| Garnett 2002 pages | title/venue confident; exact pages not re-verified | MEDIUM -- verify before use |

All drafts are proposals in this file only; no `.tex` file was modified.
