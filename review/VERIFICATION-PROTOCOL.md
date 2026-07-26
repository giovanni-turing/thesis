# Thesis Adversarial Verification Protocol

**Status:** operational spec — VERIFICATION-FIRST (design-complete, calibration-complete, review-db built+tested, not yet executed)
**Target:** `/home/gio/tese` thesis (11 chapters, `tex/`), grounded on the `provenance` Postgres DB + `progress/results-ledger.md`.
**Objective:** systematically **VERIFY every claim in the thesis against ground truth** — the `provenance` DB, `progress/results-ledger.md`, the source code, and the figures/tables — establishing, claim by claim, whether each is *supported at the stated strength*. Primary deliverable: a **verification ledger** (every claim → verdict → evidence) + the subset that is unsupported / contradicted / overclaimed / internally inconsistent, each with a fix. A diverse fleet cross-verifies each claim independently (grounded via `review-db`); adjudication + cross-family validation confirm every failure. The broad adversarial sweep (novelty, prose, threats-to-validity) is a **secondary, optional** pass — verification is the focus.

---

## 0. Governing principles

1. **Diversity is the yield.** Different labs (DeepSeek/Qwen/GLM/Kimi/ERNIE/Nemotron/Step/MiniMax/Hunyuan/MiMo/Cohere + frontier GPT/Gemini/Grok/Claude) have different training data → different blind spots → different attacks. We **maximize the union of unique valid findings** in generation; we converge only in adjudication.
2. **Spend where correctness matters.** High-volume/noisy *generation* → cheap/flat-rate/free models. High-stakes *adjudication + validation* → strongest reasoners (GPT-5.6-sol, Claude-Opus-4.8, Gemini-3.1-pro, Grok-4.5).
3. **Immutable thesis.** Reviewers are strictly read-only on `tex/` and code. Each writes **only** to its own report file. No model edits the manuscript.
4. **Verify against ground truth, per claim.** Every claim is checked against the `provenance` DB (start at `v_dim`; map `provenance/SCHEMA_GUIDE.md`) + `progress/results-ledger.md` + (for methodology) the source code, queried *per claim* via the `review-db` tool. A claim with no traceable backing is `unverifiable` — flagged, never assumed true. Never dump the whole DB.
5. **Compact structured output.** JSONL, one finding per line. Minimizes the expensive output-token side and makes clustering deterministic.
6. **Claude models never run through opencode.** `claude-opus-4-8` (adjudication/validation) and `claude-fable-5` (Phase 7) run as **Claude Code sub-agents via the Agent tool** (`model: opus` / `model: fable`). All non-Claude models run via their HTTP APIs / opencode providers.
7. **Runtime knobs (user-set).** Every model runs at its **full model-max output budget** (no per-model floors — the 8k/24k/32k values in calibration existed only to expose token-starvation), **reasoning effort = high**, and a **1000 s per-call timeout**. Model-max output makes the empty-content starvation mode effectively impossible.
8. **No silent truncation.** Any coverage bound (budget cap, dropped unit, disabled model) is logged explicitly.

---

## 1. Roster (calibration-locked)

Calibration method: a seeded canary (Appendix A) with **7 planted defects** + **3 clean "gold" passages**; each candidate scored on recall (planted defects caught), fabrication (errors asserted on gold passages), format compliance, latency. Approve gate: `recall ≥ 4/7 AND fabrication ≤ 1 AND ≥ 4 valid findings`.

### 1.1 Generators — APPROVED (13). Text review only; never touch figures here.

| Model | Route (provider / endpoint · slug) | Recall | Fab | Lat | Max-tok | Trust tier | Role |
|---|---|---|---|---|---|---|---|
| **minimax-m3** | minimax · `MiniMax-M3` | 7/7 | 0 | 26s | max | **T1 core** | **primary workhorse** (high cap, clean) |
| **hy3** | novita · `tencent/hy3` | 7/7 | 0 | 76s | 24k | **T1 core** | **free** volume; slower |
| **glm-5.2** | novita · `zai-org/glm-5.2` | 7/7 | 0 | 92s | 24k | **T1 core** | depth, core chapters |
| **kimi-k3** | novita · `moonshotai/kimi-k3` | 7/7 | 0 | 91s@24k | **32k** | **T1 core** | most thorough (12 findings); **slow/token-hungry → sparingly** |
| **gemini-3.5-flash** | gemini-openai · `gemini-3.5-flash` (×5 keys) | 6/7 | 0 | 17s | 8k | **T1 core** | high aggregate cap; also vision pool |
| **step-3.7-flash** | novita · `stepfun/step-3.7-flash` | 6/7 | 0 | 46s@24k | 24k | **T1 core** | reasoning-heavy |
| **gpt-5.6-sol** | opencode `openai` (codex, **flat-rate**) → overflow `openai-api-1/2` | 7/7 | 1 | 37s | max | T2 eager | **use extensively** (flat cost) |
| **qwen3.7-max\*** | novita · `qwen/qwen3.7-max` | 7/7 | 1 | 92s | max | T2 eager | slow |
| **ernie-4.5-424b\*** | openrouter · `baidu/ernie-4.5-vl-424b-a47b` | 7/7 | 1 | 15s | 8k | T2 eager | fast + thorough |
| **nemotron-3-ultra** | openrouter · `nvidia/nemotron-3-ultra-550b-a55b` | 7/7 | 1 | 20s | 8k | T2 eager | fast + thorough |
| **deepseek-v4-pro** | novita · `deepseek/deepseek-v4-pro` | 6/7 | 1 | 39s | 8k | T2 eager | solid all-rounder |
| **command-a** | openrouter · `cohere/command-a` | 5/7 | 1 | **7s** | 8k | T3 light | fastest; lighter recall |
| **mimo-v2.5** | novita · `xiaomimimo/mimo-v2.5` | 4/7 | 0 | 36s | 8k | T3 light | **low weight** (weakest approved) |

**Runtime (user-set, supersedes the Max-tok column):** every model runs at **model-max output tokens** + **reasoning effort high** + **1000 s call timeout**. The Max-tok figures below were calibration-only (to expose token-starvation).

`*` substitutions for unreachable flagships: `qwen3.7-max`←qwen3.8-max (proprietary, plan-only); `ernie-4.5-424b`←ernie-5.1 (proprietary, unreachable).
**DROPPED — `doubao-seed-2.0-pro`:** unreachable on any configured provider (OpenRouter carries only seed-mini/lite; flagship is Volcengine-China-gated).

**Trust-tier semantics (drives dedup weighting, §5):**
- **T1 core (0-fab):** never false-flagged a clean passage. A *lone* T1 finding gets normal scrutiny.
- **T2 eager (1-fab):** high recall but each over-flagged one gold line → their findings on clean-looking passages get **extra** adjudication scrutiny.
- **T3 light:** kept for cheap throughput but down-weighted; a lone T3 finding is low-priority until corroborated.

**Cost/latency classes (drives assignment §6):**
- **High-cap workhorses (fast/cheap/flat/free):** minimax-m3, gpt-sol (flat), gemini-flash (5 keys), ernie-4.5, nemotron, command-a, hy3 (free) → carry the bulk of (chapter×lens) units.
- **Slow reasoning (reserve for core-claim chapters, fewer units):** kimi-k3, glm-5.2, qwen3.7-max, step-3.7-flash.

### 1.2 Adjudicators / Validators — auto-approved (no calibration).
| Model | Route | Notes |
|---|---|---|
| **gpt-5.6-sol** | opencode `openai` (codex, flat-rate) → `openai-api` overflow | heavy use (flat cost) |
| **claude-opus-4-8** | **Claude Code Agent tool, `model: opus`** — never opencode | |
| **gemini-3.1-pro** | gemini-openai · `gemini-3.1-pro-preview` (×5 keys) | |
| **grok-4.5** | openrouter · `x-ai/grok-4.5` | adjudicator-only |

### 1.3 Vision (Phase 6) — auto-approved.
| Model | Route | Notes |
|---|---|---|
| **qwen3-vl-235b-a22b** | novita · `qwen/qwen3-vl-235b-a22b-instruct` | dedicated VL |
| **gemini-3.5-flash** | gemini-openai (×5 keys) | double-duty |
| **minimax-m3** | minimax · `MiniMax-M3` | double-duty |

### 1.4 Phase-7 trialogue — auto-approved.
- **claude-fable-5** = master analyzer → **Claude Code Agent tool, `model: fable`** (never opencode).
- **gpt-5.6-sol** = adversarial critic → codex flat-rate → `openai-api`/grok-4.5 fallback.
- **Claude-Opus-4.8 (orchestrator = this session)** = chair/grounder.

---

## 2. Shared infrastructure (build in Phase 0)

### 2.1 `call_model()` wrapper — every model call routes through this
- **Runtime config injection:** `max_tokens` = **model-max** for every model (§0.7; harness resolves each provider's ceiling), `reasoning_effort=high` where supported, `temperature=0.6` for generators that accept it (diversity) / omitted for OpenAI-reasoning + novita-reasoning models (they reject non-default temp), `max_completion_tokens` (not `max_tokens`) for `api.openai.com` reasoning models.
- **Retry/backoff:** 3 attempts, exponential + jitter on 5xx / connection / timeout.
- **429 handling:** rotate to a sibling key first (`gemini`→`google`,`google-2..5`; `gpt-sol`→`openai-api-1/2`), or an overflow provider for the *same open model* (`novita`↔`openrouter`↔`fireworks`); only then back off.
- **Timeout:** per-call wall-clock deadline = **1000 s** (user-set), plus a **120 s idle timeout** (no new stream chunk) to catch true hangs early. On deadline: `SIGKILL` the process tree (`timeout -k 30`), one respawn, then reroute; a chunk arrival resets the idle timer. At model-max budget a single chapter/lens review completes well inside 1000 s.
- **Empty-content guard:** at model-max budget this should not occur; if `finish_reason=length` AND `content==""` still happens, the model is unusable for that unit → mark `starved` and reallocate (no resubmit — already maxed).
- **Malformed output:** salvage JSON objects via regex; if unsalvageable, one repair re-ask ("your last reply was invalid JSONL; re-emit only valid JSON lines"); else drop the *unit* (never let prose pollute the pool).
- **Idempotent + resumable:** unit = `(model, chapter, lens)` → own file `review/reports/<model>/<chapter>.<lens>.jsonl` + `.done` marker. Re-run resumes only missing units.
- **Panel-tolerant:** one unit/model failure never aborts the run.
- **Budget guard:** hard `$`/token ceiling per phase; near cap, stop assigning new units (prefer chapter breadth over depth) and log dropped units.
- **Audit log:** append `{unit, model, params, prompt_hash, response_hash, latency, tokens, cost, status}` to `review/audit.jsonl` → the review is itself reproducible (matches the thesis provenance ethos).

### 2.2 Health ledger — `review/health/<model>.json`
Running per-model counters, updated after every unit: `valid_json_rate`, `grounding_rate` (finding cites a real tex quote/line that matches + a real DB number), `fabrication_rate` (spot-checked claims contradicted by DB/tex), `unique_survivor_yield` (findings that survive dedup + adjudication), `refusal_error_rate`, `cost_per_useful_finding`, `mean_latency`. Seeded from §1.1 calibration numbers. Drives rolling auto-disable (§4/Phase-1).

### 2.3 Provenance DB access (the numeric oracle)
- **Tool:** `mcp__technonous__postgres_query(sql)` (+ `postgres_table_columns(schema,table)`, `postgres_list_tables(schema='provenance')`) → schema `provenance` (PostgreSQL 16 @ `localhost:5433`), **read-only `provenance_ro` role — SELECT only**, hard-enforced at the DB layer (`default_transaction_read_only` + SELECT-only grants).
- Agents query it **themselves** (see the briefing §2A.3); the canonical schema map is `provenance/SCHEMA_GUIDE.md` (written expressly for LLM agents — 56 views over a `runs`/`windows` star schema). If the DB is unreachable, Phase 1 **fails fast** (never run a grounded review ungrounded).
- **Fallback for weak tool-callers:** for any model that does not reliably emit MCP calls, the harness pre-runs that chapter's `claim-inventory` queries and injects the resulting `v_*` rows into the grounding block (the 2-turn scheme). No model is trusted to invent numbers.

### 2.4 Claim inventory — `review/claim-inventory.jsonl`
Built in Phase 0 by a cheap model (ernie-4.5 / nemotron): every numeric claim + strong assertion per chapter → `{chapter, anchor(quote+line), claimed_value, ledger_entry?, provenance_view+row?, unmatched:bool}`. **Any number with no ledger entry is pre-flagged as a defect** (your own rule). Attached to each reviewer's grounding block.

### 2.5 File layout
```
review/
  VERIFICATION-PROTOCOL.md        (this file)
  claim-inventory.jsonl
  roster.active.json              (13 approved generators + configs)
  canary/ {canary.txt, planted.json, scores.json}
  reports/<model>/<step>.jsonl   (+ .done)     # the ONLY writable path for any agent (one file / model / step)
  health/<model>.json
  clusters.json
  adjudicated.jsonl
  validated.jsonl
  audit.jsonl
  VERIFICATION-LEDGER.md             (Phase 5 deliverable)
  figure-verification.md          (Phase 6 deliverable)
  EVIDENTIAL-INTEGRITY.md         (Phase 7 deliverable)
  FAILURES.md                     (actionable failed-claim subset)
```

---

## 2A. Agent briefing & sandbox contract (prepended to EVERY reviewer agent)

Every reviewer runs as a **sandboxed, tool-using agent** — an opencode agent (non-Claude models) or a Claude Code sub-agent (opus/fable). Each receives, verbatim, the four blocks below. Companion ramp-up reading: **`review/THESIS-MAP.md`**.

### 2A.1 Execution substrate & sandbox (filesystem-enforced, not prompt-enforced)
- **Non-Claude models →** `opencode run --model <provider>/<model>`, launched with `cwd` = a per-agent bounded sandbox and opencode `permission`: `edit: deny`, `bash: deny`, `webfetch: deny`; tools = read/grep/glob + the `technonous` MCP only.
- **Claude models (opus/fable) →** Claude Code Agent tool (`model: opus` / `model: fable`); tools = Read/Grep/Glob + `mcp__technonous__postgres_query` + a single Write path.
- **Read scope (read-only):** the whole thesis tree under `/home/gio/tese` — `tex/`, `provenance/SCHEMA_GUIDE.md`, `progress/results-ledger.md`, `defense/anim/data/_final/CLAIM-STRUCTURE.md`, `review/THESIS-MAP.md`, figures. May `read/grep/glob/ls`. **Never** edit, move, execute, or write anywhere in the repo.
- **Write scope — the agent has NO write tool.** It emits its findings as JSONL on stdout; the **trusted harness** captures that stdout and writes it atomically (`tmp`+`rename`) to the one notes file `review/reports/<model>/<step>.jsonl`. This resolves the `edit:deny` paradox (a denied-edit agent cannot write its own file) and removes any agent-side write path entirely. `step` ids are defined in §2.5. One file per (model, step); the harness `mkdir -p`s the dir first (agents cannot).
- **Tool whitelist (security-critical, see §9):** a reviewer agent exposes ONLY `read`/`grep`/`glob` + exactly three read-only MCP tools — `postgres_query`, `postgres_table_columns`, `postgres_list_tables`. The full `technonous` MCP surface (vault, e2b exec, `postgres_execute`, destructive redis/mongo/qdrant/rustfs, tavily) is **denied**.

### 2A.2 Thesis context (block given to every agent)
> You are adversarially reviewing a PhD thesis on **two-pool disaggregated multimodal LLM serving**. Inference is split into a **vision-encoder pool** (ViT) and a **language prefill–decode pool**; the study examines **encoder autoscaling** under **static, reactive, and forecast-driven** policies. A **1,000,000-request production trace** is replayed through a simulator; results are compared against (a) a **static grid sweep** (feasibility/optimum), (b) **silicon measurements** from a physical GPU collector (which reveal that **aiconfigurator under-models the ViT encoder**), and (c) a **measured real vLLM deployment** (ground truth). Manuscript = 11 chapters in `tex/` (intro, related, trace-eda, predictors, aiconfigurator, twopool, baselines, closedloop, validation, conclusion, apendice). **Core-claim chapters:** predictors, aiconfigurator, twopool, baselines, closedloop, validation. Read **`review/THESIS-MAP.md`** to ramp up on chapter-by-chapter claims, figures, and data sources. Before attacking claim strength, read `defense/anim/data/_final/CLAIM-STRUCTURE.md` (tiered claims + explicit **do-not-claim** list) and flag any text that overclaims beyond its tier. Every number must trace to `progress/results-ledger.md` **and** to the `provenance` database; a number with neither is already a defect.

### 2A.3 The provenance database — MCP tool + schema (block given to every agent)
> **DB access = the `review-db` tool `db_query(sql)` only** (§9.1; `technonous` is disabled for reviewers). **Ground every numeric claim against the `provenance` database** (PostgreSQL 16, read-only, generation complete: 211 tables, 56 views, ~99M rows, 21 GB). Query with **`mcp__technonous__postgres_query(sql)`** (returns rows as dicts; read-only `provenance_ro` role — SELECT only). Helpers: `postgres_table_columns(schema,table)`, `postgres_list_tables(schema='provenance')`. Fully-qualify as `provenance.<name>`, or begin with `SET search_path=provenance,public;`.
> **READ `provenance/SCHEMA_GUIDE.md` FIRST — it is written for you and prevents confidently-wrong answers.**
> **Star schema:** spine `runs` (3,147 rows; **always filter `is_current`**), dimension `windows`. **Do not start at `runs` — start at `v_dim`** (one row per run, vocabulary normalized: e.g. `'both (E2E)'→'both'`, `'vLLM'→'vllm'`, `'week'→'aggregate'`).
> **Pick the semantic view that owns your quantity:**
> - `v_dim` — run dimensions (entry point)
> - `v_pool_latency` — latency by pool, **ms** (`encoder_delay`, `ttft`, `itl`)
> - `v_pool_cost` — cost · `v_cost_ratio` — **any "X% cheaper" claim (mandatory; carries the denominator — never divide by hand)**
> - `v_grid_static_effective` / `grid_window_effective` — static optimum / feasibility (**watch `is_superseded` / the `_effective` columns**)
> - `v_infraction` — SLA infraction intensity
> - `forecast_metrics` / `v_forecast_best` — forecast accuracy (WAPE etc.)
> - `collector_encoder_fn` — silicon vs aiconfigurator model (the ViT under-modelling result)
> - `measured_request` / `vllm_*` — measured real-vLLM ground truth
> - `v_joint_e2e` — end-to-end composition · `v_coverage` / `coverage` — experiment coverage · `eda_metric` — trace characterization
> - `v_verification_resolved` / `v_corroboration` — trust/verification layer
> **Three traps before quoting any number:** (1) is there a **denominator**, and is it stated? (2) are you **adding percentiles**? (never) (3) has the row been **superseded**? Only **178 of 610** language summaries are recomputable from raw — check `v_llm_summary_backing` and say "summary-only" when it is not. Re-derive a percentile from raw with `provenance.check_run(run_id)` / `provenance.recompute_p99(run_id, metric)`.

### 2A.4 The task (block given to every agent)
> You are **verifying a specific claim** from the thesis against ground truth. You are given the claim, its exact anchor, its `claim_type`, and its `expected_backing`. Read the anchor in context (read-only), then **query `review-db` `db_query(sql)`** for the owning `provenance` view (and/or read `progress/results-ledger.md`, and/or the code for methodology) to establish whether the claim is true **at the stated strength**. Return ONE JSON verdict (schema §3.1) to your own notes file only: `supported` / `unsupported` / `contradicted` / `overclaimed` (evidence weaker than the claim or a CLAIM-STRUCTURE do-not-claim violation) / `inconsistent` / `unverifiable` — with the **exact query + result** as evidence. Never guess or invent a number. If it fails, give the minimal fix (or the scope that must travel with the claim).

---

## 3. Taxonomies

### 3.1 Verdict schema (one JSON object per JSONL line)
```json
{
  "claim_id": "<chapter>-<n>",
  "chapter": "predictors",
  "anchor": "<exact quote from tex, ≤240 chars>",
  "claim_text": "<the assertion in plain terms>",
  "claim_type": "numeric|comparative|causal|existence|methodological|citation",
  "expected_backing": "<owning provenance view/table, ledger entry, code path, or figure/table>",
  "method": "db|ledger|code|figure|cross-doc",
  "verdict": "supported|unsupported|contradicted|overclaimed|inconsistent|unverifiable",
  "evidence": "<the exact query+result / ledger line / code ref that settles it>",
  "severity": "blocking|major|minor",
  "fix": "<the correction, or the scope that must travel with the claim>",
  "confidence": 0.0
}
```
**Verdicts:** `supported` (backing found, value matches, within tier) · `unsupported` (no backing exists) · `contradicted` (backing says otherwise) · `overclaimed` (evidence weaker than the claim / violates a CLAIM-STRUCTURE tier) · `inconsistent` (text↔table↔figure↔ledger↔DB mismatch) · `unverifiable` (not checkable against available ground truth → flag the author). `severity`/`fix` only when verdict ≠ supported.

### 3.2 Severity
- **blocking** — invalidates a core claim / a wrong number that propagates / an unsupported headline result.
- **major** — weakens a claim, missing baseline, unprovenanced number feeding a table/figure, threat-to-validity not addressed.
- **minor** — wording, undefined term, presentation, non-load-bearing imprecision.

### 3.3 Verification dimensions
**Primary (the verification core):**
- **V1 numeric** — every number traces to a `provenance` row / ledger entry at the stated value (stale-number drift, rounding, wrong denominator).
- **V2 comparative** — every "X% cheaper/faster / beats Y" verified via the owning view (`v_cost_ratio` etc.), denominator + scope stated.
- **V3 consistency** — text ↔ tables ↔ figures ↔ `progress/results-ledger.md` ↔ DB all agree.
- **V4 claim-strength** — claim strength ≤ what the evidence supports; **no TIER-3 (do-not-claim) violations**; required scope attached (`CLAIM-STRUCTURE.md`).
- **V5 methodology/repro** — the stated method/config/seed/version is what actually produced the number (code + ledger).

**Secondary (optional adversarial sweep, only on request):** novelty/related-work, prose/logic gaps, threats-to-validity, missing-baseline framing.

### 3.4 Chapters & stakes
- **Core-claim (heavy coverage):** `predictors`, `aiconfigurator`, `twopool`, `baselines`, `closedloop`, `validation`.
- **Context/support (lighter):** `intro`, `related`, `trace-eda`, `conclusion`, `apendice` (+`apendice_ecosystem`).

---

## 4. Rolling bad-performer control (active in every generation/adjudication phase)
1. **Calibration gate (done, Phase 0.5):** only §1.1's 13 survivors get paid volume.
2. **Rolling disable:** after each unit, update `health/<model>.json`. If a model's `valid_json_rate < 0.7` **or** `grounding_rate < 0.5` over a sliding window of `K=4` units → **auto-disable** (stop new assignments); reallocate its remaining units to healthy high-cap workhorses (minimax-m3 / gpt-sol / gemini-flash / hy3 / ernie / nemotron). Log the disable + reason.
3. **Fabrication brake:** if `fabrication_rate` on spot-checks exceeds cap → down-weight that model's findings to require corroboration before adjudication.
4. **Adjudicator demotion:** track each adjudicator's **override rate** (verdicts overturned in Phase 4). High override → route it fewer clusters and always validate its verdicts.
5. **Rubber-stamp flag:** a validator that *never* disagrees is audited for non-engagement.

---

## 5. Schedule (verification-first)

### Phase 0 — Freeze & prep (unchanged infra)
Freeze the latest text to a read-only worktree (captures your in-flight edits), **regenerate `THESIS-MAP.md` from the freeze**, tool-probe every generator → `tool_mode`, smoke-ping all routes, `mkdir` report dirs + seed health, build the vision canary, verify the DB + start the 5-min canary, **start the supervisor** (§10.3). Fail-fast if the DB is unreachable.

### Phase 1 — Claim inventory = the verification target set (CORE, no longer just prep)
Exhaustively extract **every verifiable claim** from the frozen thesis → `claim-inventory.jsonl`: `{claim_id, chapter, anchor+line, claim_text, claim_type, expected_backing}`. Shard ≤1500 lines; **dual-extractor** (ernie-4.5 + nemotron) + union; deterministically verify each anchor substring-matches the frozen tex; classify `claim_type`; map `expected_backing` to the owning `provenance` view / ledger entry / code path / figure-table (using THESIS-MAP + SCHEMA_GUIDE). Coverage gate ≥0.95 of numeric tokens. **This inventory is the checklist the whole review executes against.**

### Phase 2 — Grounded verification (THE CORE — replaces lens×chapter generation)
The unit of work is now the **claim**. Each claim is verified **independently by K diverse models** (K=3 for core-claim chapters + TIER-1 claims, K=2 otherwise), from different labs (≥1 T1). Each verifier reads the anchor + `expected_backing`, **queries `review-db` / reads the ledger / (for V5) checks the code**, and returns a §3.1 verdict with the exact evidence. Dimensions §3.3 (V1–V5). Prompt: *"VERIFY this claim against ground truth. Query the owning view; report the query + result. Return supported/unsupported/contradicted/overclaimed/inconsistent/unverifiable — never guess a number."* Grounding mandatory (smoke-test-proven). Output: one verdict file per (claim, model).

### Phase 3 — Reconcile & adjudicate
Per claim: **fast path** — all K verifiers `supported` with matching evidence → **PASS**, no further spend. **Adjudicate** only claims that are flagged (any non-`supported`) or where verifiers disagree: a strong cross-family model (opus via Agent tool / gpt-sol / gemini-3.1-pro / grok-4.5) re-queries the DB and issues the authoritative verdict + evidence + (if failed) the fix. Spend concentrates on disputed claims.

### Phase 4 — Cross-family validation (fail-safe)
Every FAILED verdict is independently re-verified by a **different-family** strong model (**2-of-N** to confirm). A claim is marked FAILED only when two families agree — never cry wolf on a claim that is actually sound. Spot-check a random sample of PASS claims to bound the false-pass rate.

### Phase 5 — Verification ledger (primary deliverable)
`VERIFICATION-LEDGER.md`: every claim → type → verdict → evidence (query+result / ledger line / code ref). **Scorecard:** N claims, % supported, counts by failure type. `FAILURES.md`: the actionable subset, ranked by severity × whether it feeds a TIER-1 claim, each with the exact fix or the scope that must travel with the claim. Dedup across chapters.

### Phase 6 — Figure & table verification (data integrity, not appearance)
For each of the **18 figures** + every table: verify the **plotted/tabulated numbers match their DB/ledger source**. Vision models read the figure; a `review-db` cross-check confirms the values; tables checked text-vs-DB. Appearance (legibility/labels) demoted to a secondary note. Output: `figure-verification.md`.

### Phase 7 — Evidential-integrity master analysis (trialogue)
Fable ⇄ gpt-sol ⇄ Opus over the ledger + failures: is **every TIER-1 claim robustly verified**? Which failures threaten a core claim vs are cosmetic? The **verification defense narrative** — *"every headline number traces to a verified `provenance` row."* Prioritized remediation. ≤12 rounds, early-stop on 2 dry rounds. Output: `EVIDENTIAL-INTEGRITY.md`.

### Secondary (optional, post-verification)
The broad adversarial sweep (novelty/related-work, prose/logic, threats-to-validity, missing-baseline framing) — run only on request.

## 6. Claim→verifier assignment (Phase 2)

The unit is the **claim**, not (chapter×lens). Each claim gets **K diverse verifiers** drawn round-robin from the fleet, constrained so:
- **K = 3** for claims in core-claim chapters (`predictors`,`aiconfigurator`,`twopool`,`baselines`,`closedloop`,`validation`) and any TIER-1 claim; **K = 2** otherwise.
- Verifiers span **≥2 labs** and include **≥1 T1** (0-fab) model.
- Slow reasoners (kimi-k3, glm-5.2, qwen3.7-max, step-3.7-flash) are steered to the **hardest** claims (multi-step numeric/derivation); fast models (command-a, ernie, nemotron, gemini-flash, minimax) take the high-volume numeric/consistency claims.
- `tool_mode: injected` models get the claim's `expected_backing` rows pre-fetched into the prompt (they still return a verdict).

Load balances by claim count, not a fixed matrix, so a disabled model's claims re-assign automatically (§4/§10). Notes file per (model, claim): `review/reports/<model>/p2.<claim_id>.jsonl`.

## 7. Cost model & guards
- **Near-zero generation core:** gpt-sol (flat-rate subscription), hy3 (free), minimax-m3 ($0.30/$1.20 + high cap), gemini-flash (×5 keys) carry the bulk. Paid spend concentrates on the diversity tier and the deduped adjudication set.
- **Adjudication touches only ~deduped clusters,** not raw chapters. Compact JSONL + 2-turn DB grounding keep tokens small. Dedup-before-adjudicate avoids N× redundant strong-model calls.
- **Per-phase hard ceilings** in `call_model()` budget guard; over-budget → prefer chapter breadth, log drops.
- **Vision spend** confined to ~30 figures × 3 models.

---

## 8. Runbook (execution order)
1. `Phase 0` — snapshot, claim-inventory, DB helper check, `roster.active.json`.
2. `Phase 0.5` — (done) confirm/refresh calibration.
3. `Phase 1` — generation fan-out (`llm_panel`-style harness + `call_model()` wrapper), resume-safe.
4. `Phase 2` — cluster + dedup → `clusters.json`.
5. `Phase 3` — Workflow adjudication (Opus via Agent + gpt/gemini/grok via API) → `adjudicated.jsonl`.
6. `Phase 4` — cross-family validation → `validated.jsonl`.
7. `Phase 5` — merge → `VERIFICATION-LEDGER.md`.
8. `Phase 6` — vision pass (parallel any time after Phase 0) → `figure-review.md`.
9. `Phase 7` — Fable⇄gpt-sol⇄Opus trialogue → `MASTER-ANALYSIS.md`.

Between every phase: read the output, check `health/*` + `audit.jsonl`, apply rolling disables, then proceed.

---

## Appendix A — Calibration canary (seeded)
Excerpt in `review/canary/canary.txt` (a synthetic Section 5.3 in-domain: two-pool ViT disaggregation). **7 planted defects:** D1 arithmetic (4.1× vs true 2.38× from 1240/520); D2 overclaim ("optimal for all workloads"); D3 unsupported causal ("necessarily reduces p99"); D4 internal inconsistency (TTFT 82 ms text vs 128 ms table); D5 missing baseline ("sole baseline is static colocation"); D6 stale/unprovenanced (91% "earlier run"); D7 statistical weakness ("averaged over 3 runs", no CI). **3 gold (clean) passages** (1:3 GPU ratio; WAPE-vs-MAPE justification; vLLM 0.6.3 + provenance-DB repro line) — flagging an *error* on these = fabrication.

## Appendix B — Calibration results (final)
Gate: recall ≥4/7, fabrication ≤1, ≥4 findings, valid JSONL. **13/14 reachable APPROVED** (§1.1 table). Key lessons folded into the protocol: (1) reasoning models return empty content when token-starved → §2.1 empty-content resubmit + §0.7 max-budget rule; (2) 0-fabrication models = trust tier T1; (3) doubao-seed-2.0-pro unreachable → dropped; (4) kimi-k3 most thorough (12 findings) but needs 24k+ budget & ~90s → "use sparingly, core chapters".

## Appendix C — Routing/keys quick reference
- **novita** (`https://api.novita.ai/v3/openai`, key in opencode auth `novita`; UA `curl/8.5.0` required): hy3, glm-5.2, kimi-k3, deepseek-v4-pro, mimo-v2.5, step-3.7-flash, qwen3.7-max, qwen3-vl.
- **minimax** (`https://api.minimax.io/v1`, token): MiniMax-M3.
- **gemini-openai** (`https://generativelanguage.googleapis.com/v1beta/openai`, keys `google`+`google-2..5`, round-robin): gemini-3.5-flash, gemini-3.1-pro-preview.
- **openrouter** (`https://openrouter.ai/api/v1`, key in opencode auth `openrouter`): ernie-4.5-424b, nemotron-3-ultra, command-a, grok-4.5.
- **openai** (codex flat-rate via opencode `openai`; pay overflow `openai-api-1/2`, `max_completion_tokens`, no temp): gpt-5.6-sol.
- **Claude Code Agent tool** (never opencode): opus-4.8 (adjudicate/validate), fable-5 (Phase 7).


---

## 9. Security & secrets (MUST-FIX — from the Fable-5 hardening pass)

**Threat.** Phase 1 runs **13 third-party open models that we explicitly prompt to be hostile**, inside opencode — whose *default* config enables the **entire `technonous` MCP** (`vault_read_secret`, `e2b_*` code-exec, `postgres_execute`, `redis_flushdb`, destructive `qdrant/mongo/rustfs`, Cloudflare-bypassing `tavily`) and whose permission model fences only `edit/bash/webfetch`, **not reads** (`auth.json` is one `Read` away). The `technonous` MCP **runs locally on this host**, so containment is a local config choice we control — closed before any generator runs.

- **9.1 Expose ONLY a read-only DB query. Two equivalent builds (pick one in Phase 0):**
  - **(A, CHOSEN — BUILT & TESTED) Dedicated single-tool RO query.** `review/tools/review_db_mcp.py` — a local stdlib MCP exposing exactly `db_query(sql)`, **four independent RO layers**: (1) SELECT/WITH-only validation (writes/DDL/multi-statement/CTE-DELETE rejected), (2) connects as the DB-level read-only role `picolo`, (3) forced read-only transaction (`default_transaction_read_only=on`), (4) 1000-row cap + 15 s `statement_timeout`. Reviewers load `review/tools/opencode-reviewer.jsonc` (`technonous` **disabled**, only `review-db`, `edit/bash/webfetch: deny`). **Verified end-to-end:** an agent queried `v_dim`→2461 and reported *"no vault/secret or code-execution tool present."* Password in `review/tools/.pw` (`0600`, git-ignored); prod runs reviewers as a low-priv user.
  - **(B) Strip the local `technonous` MCP.** Run a reviewer-scoped MCP config that registers only `postgres_query` / `postgres_table_columns` / `postgres_list_tables` and omits every other tool.
  Because the MCP is **local**, there is **no remote gateway or shared `x-api-key` SPOF** and DB latency is low; the only residual shared limit is the Postgres 100-connection ceiling (§10.1).
- **9.2 Credential isolation.** Reviewer opencode processes run as a **dedicated low-privilege user**; the author's `auth.json`/`.codex/auth.json` are `0600` and unreadable by that user. The frozen review worktree contains **no secrets**.
- **9.3 Read fence.** Reviewer `cwd` = the frozen worktree; reads are confined to it (no `~`, no `..`, no `/etc`). The harness passes chapter/figure paths as worktree-relative.
- **9.4 DB least-privilege.** All queries go through the `provenance_ro` role (SELECT-only, `statement_timeout='15s'`). No agent ever sees a writable DB handle.
- **9.5 No write/exec tools.** Reviewers have **no** Write/Edit/Bash tool at all — the harness captures stdout and owns every file write (§2A.1).
- **9.6 Secrets scan.** The supervisor greps every notes file + `audit.jsonl` for key-shaped strings (`sk-`, `AIza`, `fw_`, `sk_`, JWT); any hit → abort + `PushNotification`.

---

## 10. Resilience: contention, failures, runtime supervisor

### 10.1 Concurrency & contention caps (hard limits, enforced by the supervisor)
| Shared resource | Cap | Policy on breach |
|---|---|---|
| Postgres `provenance` (`max_connections=100`, ~7 author sessions live) | **≤20** concurrent DB-calling agents | `statement_timeout=15s`; conns>70 → halve dispatch, >85 → pause until drain |
| local `review-db` MCP (RO, single tool; runs on this host — **not** a remote SPOF) | same 20-conn cap | still serializes DB access → the 20-agent cap protects the Postgres 100-conn ceiling; 5-min DB canary |
| opencode processes (local server/run; 2-min cold starts; 24-core shared box) | **≤12** concurrent | each under `timeout -k 30 <budget-aware deadline>`; pre-warm 1/provider; kill-tree + 1 respawn on hang |
| Claude Agent/Workflow lane (16-cap) | **≤8** concurrent Claude sub-agents | adjudication batched to fit; **Phase 7 runs solo** |
| Gemini 5-key pool (gen + vision + 3.1-pro adjudication) | token-bucket **≤4** | round-robin; per-key daily counters persisted across phases |
| gpt-5.6-sol codex flat-rate (5h/weekly windows) | allowance split **gen 30 / adj 40 / P7 20 / 10 headroom** | cap error → overflow to `openai-api-1/2` |
| novita (single key, 7/13 gens + qwen-vl; UA `curl/8.5.0`) | **≤6** concurrent | circuit breaker: 5 err / ≥2 models / 5 min → open 10 min, overflow to openrouter |
| openrouter (single key: ernie, nemotron, command-a, grok) | **≤6** | Phase-0 credit check; treat 402 (credit) ≠ 429 (rate) |
| minimax (single key, primary workhorse + vision) | **≤4** | vision units yield to generation backlog |
| `review/reports/` + `audit.jsonl` + `health/*` | 1 file/(model,step) | **harness-only** writes (stdout→tmp+rename); audit `O_APPEND` <4KB atomic lines; health written only by the supervisor |

### 10.2 Failure matrix — top modes → automatic on-the-fly action (35 catalogued; highest-value shown)
| Mode | Detect | Auto-action |
|---|---|---|
| Dirty tree ⇒ stale review | git status non-empty; per-chapter sha256 drift | reads pinned to frozen worktree (cannot drift); canary value drift also flags it |
| Reasoning empty content (token-starved) | `finish_reason=length ∧ content==''` | resubmit ×1 @1.5× budget; 2nd empty → reallocate to minimax/gpt-sol |
| Timeout kills legit full-budget call | deadline vs active token flow | budget-aware deadline `max(400s,max_tok/20)` cap 1800s + 120s idle timer |
| opencode cold-start hang | no first stream event ≤150s | kill-tree + 1 respawn → reroute to alt provider |
| Weak tool-caller can't drive MCP | Phase-0 tool-probe; 0 MCP calls but DB-style evidence | flip model to `tool_mode: injected` (harness feeds `v_*` rows); its agentic findings → mandatory Phase-3 re-verify |
| Fabricated anchor/number | ingest-time substring match vs frozen tex, line ±30 | exclude from clustering; count into `fabrication_rate`; brake + retro-quarantine that model's uncorroborated singletons |
| Provider outage disables good models | fault tagged `provider_fault` | excluded from §4 K=4 window (only `model_fault` counts) → protects diversity; circuit-break provider |
| Gemini 429 storm (shared 5-key) | per-key daily counter | token-bucket throttle; adjudication reserves pro-model quota |
| DB busy/unreachable mid-run (local Postgres shared with author sessions) | 5-min canary red / conns>85 | pause dispatch (backoff ×6); in-flight tagged `db_unverified` → Phase-3 re-verify; resume on green |
| Latin-square hole after disables | supervisor re-checks coverage per lens | reassign the (chapter×lens) cell to a healthy other-lab model |
| Trialogue non-convergence | dry-round score (0 novel grounded points) | early-stop after 2 dry; a point re-raised 3× is frozen to the disagreement appendix |
| Crash at 3am | heartbeat stale >3 min | watchdog cron relaunches supervisor; resume from `state.json` + `.done` markers (all phases) |

### 10.3 Runtime supervisor (the mechanism that makes "no failures on the fly" real)
One long-lived process, started at Phase 0 (§5 item 8), heartbeat every 60s, watchdog-cron relaunched if stale >3 min. **Single writer** of `health/*.json` + `state.json`, event-sourced from `audit.jsonl` + each `opencode run --format json` stream + direct probes. **Monitors:** per-event status/latency/tokens/cost/`finish_reason`/tool-calls/fault-attribution; every 60s → `pg_stat_activity` conn count, in-flight unit ages vs deadlines, per-lane concurrency; every 5 min → DB canary (expect **2461**), gateway p95, per-gemini-key counters, codex allowance, per-phase burn, fleet-diversity index, `pending-human` fraction, disk. **Fault attribution** (`model_fault` vs `provider_fault`) — only `model_fault` feeds §4 disable, so a novita outage never disables 7 healthy models.

### 10.4 Escalation (unattended run)
Supervisor sends `PushNotification` on: any phase abort · `pending-human` >20% · budget ≥95% · secrets-scan hit · a provider circuit open >30 min · DB canary red >30 min. Otherwise it runs silently to completion.

### 10.5 Cost ceilings (concrete)
Phase 1 $40 · Phase 3 $60 · Phase 4 $30 · Phase 6 $10 · Phase 7 $20 → **$160 hard total** (generation is mostly flat-rate/free, so most spend is adjudication). Supervisor halts a phase at 95% of its ceiling (prefer breadth over depth, log drops). Codex flat-rate is *not* dollar-metered but allowance-split (§10.1).

### 10.6 step-id scheme (resolves the `<step>` ambiguity)
`p1.<chapter>.<lens>` · `p3.<cluster_id>` · `p4.<cluster_id>` · `p6.<figure>` · `p7.round<k>.<role>` — one notes file per id under `review/reports/<model>/`.

### 10.7 Resolved contradictions (all 10 from the Fable pass)
ledger path → `progress/results-ledger.md` (§0.4, §2A.2) · fixed-400s timeout → budget-aware deadline (§2.1) · agent-write vs `edit:deny` → harness-owned stdout capture, no agent write tool (§2A.1) · figure scope → the 18 `\includegraphics` under `figuras/{aic,eda,pred,sim}` (§5 P6) · `<step>` defined (§10.6) · step-3.7-flash now assigned (L7-deep) + hy3 removed from the slow-reasoner column (§6) · gemini provider ids = `google`/`google-2..5` in `roster.active.json` (Appendix C label is descriptive) · gpt-sol multi-role guarded by the different-family validation gate (§4/Phase 4) + allowance split (§10.1) · sandbox "filesystem-enforced" now true via tool-whitelist + read-fence + no-write (§9) · claim-inventory built by T2 models now deterministically verified before distribution (§5 P0).

### 10.8 Remaining gap-fixes folded in
tool-probe→`tool_mode` (§5 P0.3) · hallucination retro-quarantine (§10.2) · Phase-7 convergence definition (§10.2) · determinism = audit-trail-level for generation (params+hashes logged, temp 0.6 not bitwise), low-temp for adjudication · resumability extended to Phases 2–6 via `.done` + `state.json` cursor + watchdog · figure→ledger mapping: harness extracts each figure's ledger-source numbers and passes them in-prompt (VL models have no MCP) · Phase-3 spawn = lane A `Agent(model:opus)` ≤8 + lane B API adjudicators `call_model()` ≤6, cluster-batched.

---

*Hardened with a Fable-5 (max-reasoning) adversarial pass + a live substrate smoke test (gpt-5.6-sol read a chapter, queried `provenance` via MCP → 2461, emitted a grounded finding) + a live DB/MCP reachability test. Verdict: architecture sound; the three must-fixes (MCP/secrets containment §9, frozen-worktree §5 P0.1, budget-aware timeout §2.1) are applied.*
