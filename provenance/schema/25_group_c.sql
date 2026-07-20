-- ============================================================================
-- 23_group_c.sql -- DDL for ADJUDICATION §2.4, §2.5, §2.11 (GROUP C).
--
-- Idempotent and re-runnable: every statement is CREATE ... IF NOT EXISTS or
-- ADD COLUMN IF NOT EXISTS. Data is loaded by provenance/loader/load_group_c.py
-- (kind K31), which is sha256-gated through ingest_log.
--
-- WHAT THIS ADDS AND WHY
--
-- §2.4  The riders knee/belief derivation is the provenance for the thesis's
--       detection-lead / capacity-conversion claims (closedloop.tex:328,331,337).
--       Before this file, only the OUTPUT runs were in the store; the derivation
--       -- the planner's per-tick throughput belief, the tail-knee ladder, and
--       the arithmetic that turns them into FORECAST_REQ_SCALE=8 -- lived only in
--       progress/results-ledger.md prose. Three tables make it RECOMPUTABLE:
--         capacity_belief_sample  raw per-tick planner observations (the input)
--         capacity_knee_probe     the offered-rate -> tail ladder (the input)
--         capacity_derivation     belief / r_tail -> scale + margin (the output)
--       capacity_derivation stores nothing that cannot be recomputed from the
--       other two, on purpose: check C401/C402 assert exactly that.
--
-- §2.5  The four riders ladder runs carried NULL lead_s / window_name / tp even
--       though run_44_riders.sh pins all three. Backfilling a NULL is not an
--       overwrite, but it is still a change to an archived row, so every one is
--       recorded in runs_config_backfill with its evidence (file:line).
--
-- §2.11 Three archived artifacts that answered "unverifiable" thesis claims:
--         (a) the AIC speed-of-light fallback bound  -> collector_scalar rows
--         (b) the ds4 fabric-sensitivity replay      -> handoff_gbps promoted
--             from encoder_run_summary.metrics to a first-class column
--         (c) the encoder factoring-invariance probe -> encoder_factoring_probe
-- ============================================================================

SET search_path = provenance, public;

-- ---------------------------------------------------------------------------
-- §2.4 (input 1) -- the planner's in-loop throughput belief, per tick
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS provenance.capacity_belief_sample (
    source_log      text     NOT NULL,
    tick_idx        integer  NOT NULL,
    run_id          text,
    agg_rps         double precision,
    engine_rps      double precision,
    is_degenerate   boolean  NOT NULL,
    PRIMARY KEY (source_log, tick_idx)
);

COMMENT ON TABLE provenance.capacity_belief_sample IS
 'ADJUDICATION §2.4 input 1. One row per planner tick emitted as "Agg: <agg_rps> rps / '
 '<engine_rps> engine_rps" in a riders44 replay log. engine_rps is the planner''s BELIEF '
 'about per-replica throughput -- what it divides demand by when sizing replicas. The '
 'published belief (10.07 req/s per TP2 replica, p10-p90 8.5-12.8, closedloop.tex:328) is '
 'the median over the non-degenerate ticks of fc_lead60.log ALONE, n=86. Other logs give '
 'different medians (7.3-10.5); the population matters and is why every tick is stored '
 'rather than the summary. Ticks are NOT interchangeable across runs.';
COMMENT ON COLUMN provenance.capacity_belief_sample.source_log IS
 'Absolute path of the replay log the tick was parsed from. Part of the key: the belief is '
 'only meaningful per-run.';
COMMENT ON COLUMN provenance.capacity_belief_sample.tick_idx IS
 '0-based ordinal of the tick within its log, in file order. Not a timestamp -- the log line '
 'carries none.';
COMMENT ON COLUMN provenance.capacity_belief_sample.agg_rps IS
 'First field: aggregate offered rate the planner saw this tick, req/s. Scaled by '
 'FORECAST_REQ_SCALE in the fc_* runs, so it is NOT the trace''s raw arrival rate.';
COMMENT ON COLUMN provenance.capacity_belief_sample.engine_rps IS
 'Second field: believed per-replica sustainable throughput, req/s per TP2 replica.';
COMMENT ON COLUMN provenance.capacity_belief_sample.is_degenerate IS
 'TRUE when engine_rps > 100 -- a start-up/idle tick where a handful of completions over a '
 'near-zero busy window produce an absurd rate. Dropped from the published median by the '
 'rule recorded at results-ledger.md:147. Stored, not deleted, so the rule is auditable.';

CREATE INDEX IF NOT EXISTS capacity_belief_sample_run_idx
    ON provenance.capacity_belief_sample (run_id);

-- ---------------------------------------------------------------------------
-- §2.4 (input 2) -- the tail knee ladder
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS provenance.capacity_knee_probe (
    probe_id            text NOT NULL PRIMARY KEY,
    run_id              text,
    window_name         text,
    probe_kind          text NOT NULL,
    arrival_speedup     double precision,
    forecast_req_scale  double precision,
    n_replicas          integer,
    tp                  integer,
    offered_rps         double precision,
    offered_rps_per_replica double precision,
    implied_r_tail      double precision,
    p99_ttft_ms         double precision,
    p99_itl_ms          double precision,
    gpu_hours           double precision,
    sla_ttft_p99_ms     double precision,
    sla_itl_p99_ms      double precision,
    passes              boolean,
    is_superseded       boolean NOT NULL DEFAULT false,
    superseded_reason   text,
    source_path         text,
    source_sha256       text
);

-- CREATE TABLE IF NOT EXISTS is a no-op on an existing table, so columns added to this
-- file after its first application need an explicit ALTER to reach a live store.
ALTER TABLE provenance.capacity_knee_probe
    ADD COLUMN IF NOT EXISTS source_sha256 text;

COMMENT ON TABLE provenance.capacity_knee_probe IS
 'ADJUDICATION §2.4 input 2. The measured tail-knee ladder behind closedloop.tex:331/337. '
 'Two probe kinds answer the same question from opposite directions. '
 'probe_kind=''arrival_speedup'': replay burst1 at N=2 TP2 replicas with the arrival clock '
 'sped up, and read the offered rate off the report -- this measures r_tail DIRECTLY as the '
 'largest per-replica rate that still meets the tail SLA (burst1: 1.6233 req/s, at s=1.5). '
 'probe_kind=''forecast_scale'': hold the arrival clock and vary FORECAST_REQ_SCALE, which '
 'is equivalent to asserting r_tail = belief/scale -- pass/fail therefore BRACKETS r_tail '
 'without measuring it (burst4: fails at 1.619, passes at 1.439 => r_tail in [1.259,1.439]). '
 'Pass/fail is the thesis evaluation SLA (TTFT p99 <= 1000 ms AND ITL p99 <= 100 ms), not a '
 'per-probe threshold.';
COMMENT ON COLUMN provenance.capacity_knee_probe.probe_kind IS
 '''arrival_speedup'' (measures r_tail) or ''forecast_scale'' (brackets it). Do not pool '
 'the two: only the first yields a measured rate.';
COMMENT ON COLUMN provenance.capacity_knee_probe.offered_rps IS
 'request_throughput_rps from the run report -- the rate actually offered across the whole '
 'pool. NULL for forecast_scale probes, where the arrival clock is unchanged and the knob '
 'moves the planner''s sizing, not the load.';
COMMENT ON COLUMN provenance.capacity_knee_probe.offered_rps_per_replica IS
 'offered_rps / n_replicas. For arrival_speedup probes this IS the candidate r_tail; the '
 'published burst1 knee 1.62 req/s is this column at the largest passing speedup.';
COMMENT ON COLUMN provenance.capacity_knee_probe.implied_r_tail IS
 'For forecast_scale probes: belief / forecast_req_scale -- the per-replica throughput the '
 'planner is implicitly assuming at this scale. A FAIL means the assumed value is too high, '
 'so it bounds r_tail from above; a PASS bounds it from below. NULL for arrival_speedup.';
COMMENT ON COLUMN provenance.capacity_knee_probe.source_sha256 IS
 'sha256 of source_path at the time this row was derived. These report files are owned by '
 'loader kind K1, and provenance.ingest_log is keyed on file_path, so K31 must not '
 're-register them -- that would erase the record of which loader read them first. The sha '
 'is carried here instead, which both preserves the byte-level provenance and gives K31 its '
 'idempotence gate: a re-run whose sha is unchanged writes nothing.';
COMMENT ON COLUMN provenance.capacity_knee_probe.is_superseded IS
 'TRUE for the two pre-bugfix burst4 probes (fc_scale6.22_burst4, fc_scale8_burst4). The '
 'sub-minute forecast feed had two compounding unit/tick bugs (results-ledger.md, 2026-07-09) '
 'that understated demand 4x at 15 s resolution; the _v2 reruns supersede them. Retained as '
 'the bug record, per the never-destroy rule -- exclude with is_superseded=false.';

-- ---------------------------------------------------------------------------
-- §2.4 (output) -- the derivation itself
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS provenance.capacity_derivation (
    derivation_id     text NOT NULL PRIMARY KEY,
    window_name       text,
    belief_rps        double precision,
    belief_p10_rps    double precision,
    belief_p90_rps    double precision,
    belief_n_ticks    integer,
    belief_source_log text,
    belief_p10_disc_rps double precision,
    belief_p90_disc_rps double precision,
    r_tail_rps        double precision,
    r_tail_lo_rps     double precision,
    r_tail_hi_rps     double precision,
    r_tail_method     text,
    implied_scale     double precision,
    adopted_scale     double precision,
    margin_over_knee  double precision,
    is_binding        boolean,
    thesis_location   text,
    published_text    text,
    rationale         text,
    source_paths      text[]
);

COMMENT ON TABLE provenance.capacity_derivation IS
 'ADJUDICATION §2.4 output. The tail-aware capacity conversion, one row per window plus one '
 'fleet-level row. FORMULA: scale = belief / r_tail, where belief is the planner''s median '
 'in-loop per-replica throughput (capacity_belief_sample) and r_tail is the measured tail '
 'knee (capacity_knee_probe). Every column here is recomputable from those two tables; '
 'checks C401-C403 assert it. This is what makes closedloop.tex:328-337 -- "the tail-aware '
 'conversion is derived, not tuned" -- checkable rather than arguable. The BINDING window is '
 'burst4 (lowest r_tail), and the adopted FORECAST_REQ_SCALE=8 is belief/1.26 = the binding '
 'window''s lower bracket, i.e. the knee plus ~14% capacity margin.';
ALTER TABLE provenance.capacity_derivation
    ADD COLUMN IF NOT EXISTS belief_p10_disc_rps double precision,
    ADD COLUMN IF NOT EXISTS belief_p90_disc_rps double precision,
    ADD COLUMN IF NOT EXISTS r_tail_basis text;

COMMENT ON COLUMN provenance.capacity_derivation.r_tail_basis IS
 'Which r_tail value implied_scale was computed from: ''measured'' (r_tail_rps), ''hi'' '
 '(r_tail_hi_rps -- the strictly-required scale) or ''lo'' (r_tail_lo_rps -- the conservative '
 'end, which is what the deployed setting uses). Stored explicitly because the three rows do '
 'NOT all use the same bound and a checker cannot infer which: the burst4 row divides by hi to '
 'show the minimum scale the SLA demands (7.0), while the fleet row divides by lo to reproduce '
 'the adopted 8.0. Without this column check C403 has to guess, and guessing wrong makes an '
 'honest row look like a defect.';

COMMENT ON COLUMN provenance.capacity_derivation.belief_p10_rps IS
 'p10 of the non-degenerate belief ticks under percentile_cont (linear interpolation): 8.46.';
COMMENT ON COLUMN provenance.capacity_derivation.belief_p90_rps IS
 'p90 under percentile_cont (linear interpolation): 12.66. NOTE this does NOT round to the '
 'published 12.8 -- it rounds to 12.7. See belief_p90_disc_rps; the disagreement is a '
 'percentile convention, not a data disagreement, and is recorded rather than reconciled '
 'away. The MEDIAN, which is the number the derivation actually uses, is 10.07 under every '
 'convention tested.';
COMMENT ON COLUMN provenance.capacity_derivation.belief_p10_disc_rps IS
 'p10 under percentile_disc (order statistic / inverted CDF): 8.45 -> 8.5.';
COMMENT ON COLUMN provenance.capacity_derivation.belief_p90_disc_rps IS
 'p90 under percentile_disc (order statistic / inverted CDF): 12.83 -> 12.8. THIS is the '
 'convention under which the published band "p10-p90 8.5-12.8" (closedloop.tex:328, '
 'results-ledger.md:147) reproduces exactly. The interpolating convention gives 8.46-12.66. '
 'Both are stored so a reader can see which one the thesis used instead of having to guess; '
 'nothing downstream depends on the choice, because the derivation consumes only the median.';
COMMENT ON COLUMN provenance.capacity_derivation.r_tail_method IS
 '''measured'' (arrival_speedup ladder gives a point value) or ''bracketed'' (forecast_scale '
 'ladder gives an interval only). burst1 is measured; burst4, the binding window, is only '
 'bracketed -- which is why the thesis prints an interval [1.26,1.44] for it.';
COMMENT ON COLUMN provenance.capacity_derivation.margin_over_knee IS
 'adopted_scale / implied_scale. >1 means the deployed setting provisions MORE capacity than '
 'the knee strictly requires. The ~14% margin is policy, not measurement: r_tail is '
 'mix-dependent and planner-in-loop replays show ~4% p99 run noise (fc_scale6.22 932.35 ms vs '
 'its rerun fc_scale6.22_regress 968.42 ms, same config).';
COMMENT ON COLUMN provenance.capacity_derivation.is_binding IS
 'TRUE on the window whose r_tail is lowest and therefore sets the fleet-wide scale.';

-- ---------------------------------------------------------------------------
-- §2.5 -- visible record of every backfilled configuration column on runs
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS provenance.runs_config_backfill (
    run_id        text NOT NULL,
    column_name   text NOT NULL,
    old_value     text,
    new_value     text,
    evidence_path text,
    evidence_line text,
    rationale     text,
    recorded_utc  timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (run_id, column_name)
);

COMMENT ON TABLE provenance.runs_config_backfill IS
 'ADJUDICATION §2.5 and §2.12. Every configuration column filled in on an already-archived '
 'provenance.runs row, with the file:line that settles it. A backfill only ever writes over '
 'NULL -- the loader refuses to change a non-NULL value -- so no measurement is destroyed, '
 'but the change is still recorded here so an auditor can tell an ingested dimension from a '
 'reconstructed one. Join this table before treating runs.lead_s / window_name / tp as '
 'having come from the artifact itself.';
COMMENT ON COLUMN provenance.runs_config_backfill.old_value IS
 'Always NULL in practice: the loader asserts the column was NULL before writing. A non-NULL '
 'value here would mean the never-overwrite rule was broken and should be investigated.';
COMMENT ON COLUMN provenance.runs_config_backfill.evidence_line IS
 'Line reference within evidence_path, as a text range (e.g. "3,32"), so the claim can be '
 'checked without re-deriving it.';

-- ---------------------------------------------------------------------------
-- §2.11 (b) -- promote the fabric dimension out of the metrics jsonb
-- ---------------------------------------------------------------------------
ALTER TABLE provenance.encoder_run_summary
    ADD COLUMN IF NOT EXISTS handoff_gbps   double precision,
    ADD COLUMN IF NOT EXISTS handoff_rtt_ms double precision;

COMMENT ON COLUMN provenance.encoder_run_summary.handoff_gbps IS
 'ADJUDICATION §2.11. Inter-pool handoff bandwidth in Gbps, promoted from metrics->>''handoff_gbps'' '
 '(present on all 1,117 rows) to a first-class column. Without it the fabric-conditional claim at '
 'intro.tex:514-516 -- that the 588 ms floor and the 0.62x result assume an embedding-only handoff '
 'or a >=100 Gbps fabric -- was unqueryable. The default fleet value is 25.0; the ds4 sensitivity '
 'replays run at 6.25 (a 4x downscale, hence the _ds4 suffix), where handoff transfer ALONE has '
 'p99 1087.406 ms and so violates the 1,000 ms bound before any policy is considered.';
COMMENT ON COLUMN provenance.encoder_run_summary.handoff_rtt_ms IS
 'ADJUDICATION §2.11. Handoff round-trip latency in ms, promoted from metrics->>''handoff_rtt_ms''. '
 '0.2 on every ingested run; stored as a column so a future run that changes it is visible.';

-- ---------------------------------------------------------------------------
-- §2.11 (c) -- the encoder factoring-invariance probe
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS provenance.encoder_factoring_probe (
    probe_id            text NOT NULL PRIMARY KEY,
    image_px            integer,
    batch_size          integer,
    images_per_request  integer,
    total_images        integer,
    predicted_ms        double precision,
    delta_vs_ref_ms     double precision,
    is_reference        boolean NOT NULL DEFAULT false,
    evidence_path       text,
    evidence_line       text,
    note                text
);

COMMENT ON TABLE provenance.encoder_factoring_probe IS
 'ADJUDICATION §2.11. The batching-law probe behind twopool.tex:110-123: AIC''s encoder graph '
 'prices a forward EXACTLY by its total image count, so every factoring of N images into '
 '(batch_size, images_per_request) returns the same latency. The key that was missing from the '
 'store is precisely (batch_size, images_per_request) -- provenance.collector_encoder_fn carries '
 'only n_images, which cannot express the invariance because it collapses the two axes the probe '
 'varies. delta_vs_ref_ms = 0.000000 for every factoring at a given total_images; that zero is the '
 'claim. The simulator''s per-batch costing rests on it (each dispatched batch is costed at its '
 'image total), so it is load-bearing, not incidental.';
COMMENT ON COLUMN provenance.encoder_factoring_probe.delta_vs_ref_ms IS
 'Predicted latency minus the reference factoring at the same total_images. Zero to six decimals '
 'across the probe -- the invariance itself.';
COMMENT ON COLUMN provenance.encoder_factoring_probe.predicted_ms IS
 'AIC-predicted forward latency. The two ends of the batching law, f(1)=8.162 and f(64)=316.369 ms '
 'at 448px, are the values PUBLISHED in twopool.tex and are corroborated independently by '
 'collector_encoder_fn.aic_pred_ms at the same shapes. The contemporaneous note '
 '(progress/phase2-simulation.md:109) records an EARLIER pair, 7.822 / 314.498 ms, from a '
 'superseded AIC data version; the invariance result is identical under both, which is why the '
 'thesis number and the probe''s provenance can differ without either being wrong. Rows carrying '
 'the earlier pair are labelled in note.';

-- ---------------------------------------------------------------------------
-- Views: the effective/queryable surface
-- ---------------------------------------------------------------------------
CREATE OR REPLACE VIEW provenance.v_capacity_knee AS
SELECT p.probe_id, p.window_name, p.probe_kind, p.arrival_speedup, p.forecast_req_scale,
       p.offered_rps_per_replica, p.implied_r_tail, p.p99_ttft_ms, p.p99_itl_ms,
       p.gpu_hours, p.passes, p.source_path
  FROM provenance.capacity_knee_probe p
 WHERE NOT p.is_superseded;

COMMENT ON VIEW provenance.v_capacity_knee IS
 'capacity_knee_probe with the two superseded pre-bugfix burst4 probes filtered out. Use this '
 'for any knee question; go to the base table only to inspect the bug record.';

CREATE OR REPLACE VIEW provenance.v_fabric_sensitivity AS
SELECT e.run_id, r.policy, r.quantile, r.lead_s,
       e.handoff_gbps, e.handoff_rtt_ms,
       e.handoff_p99_ms, e.encoder_delay_p99_ms,
       e.provisioned_worker_seconds,
       (e.handoff_p99_ms > 1000.0) AS handoff_alone_violates_sla
  FROM provenance.encoder_run_summary e
  JOIN provenance.runs r USING (run_id)
 WHERE e.handoff_gbps IS NOT NULL;

COMMENT ON VIEW provenance.v_fabric_sensitivity IS
 'ADJUDICATION §2.11. The fabric-conditional claim (intro.tex:514-516) in one query: group by '
 'handoff_gbps and read handoff_alone_violates_sla. At 25 Gbps no run violates on handoff alone; '
 'at 6.25 Gbps every run does, independent of policy -- which is exactly the thesis''s "a fabric '
 'requirement, not a policy weakness".';

-- ---------------------------------------------------------------------------
-- Remaining column documentation (standing rule: comment every non-obvious column).
-- Keys and plain source_path columns are self-describing and deliberately omitted.
-- ---------------------------------------------------------------------------
COMMENT ON COLUMN provenance.capacity_belief_sample.run_id IS
 'The riders run the log belongs to, joinable to provenance.runs. Derived from the log path by '
 'runid.run_id_of, so a log and its .report.json share it.';

COMMENT ON COLUMN provenance.capacity_knee_probe.run_id IS
 'Joins to provenance.runs / llm_run_summary for the full report behind this rung.';
COMMENT ON COLUMN provenance.capacity_knee_probe.window_name IS
 'Trace window the rung was replayed on. burst1 carries the measured ladder; burst4 -- the '
 'BINDING mix -- carries only the bracketing ladder.';
COMMENT ON COLUMN provenance.capacity_knee_probe.arrival_speedup IS
 'Arrival-clock multiplier (--arrival-speedup-ratio). Populated for arrival_speedup probes only; '
 'this is the knob that actually raises offered load.';
COMMENT ON COLUMN provenance.capacity_knee_probe.forecast_req_scale IS
 'FORECAST_REQ_SCALE for forecast_scale probes. Divides the belief to give implied_r_tail; it '
 'changes the planner''s SIZING, not the load.';
COMMENT ON COLUMN provenance.capacity_knee_probe.n_replicas IS
 'Language replicas (2 throughout). The divisor turning pool-wide offered_rps into a per-replica '
 'rate; the knee is only meaningful per replica.';
COMMENT ON COLUMN provenance.capacity_knee_probe.tp IS 'Tensor parallelism per replica (2 throughout).';
COMMENT ON COLUMN provenance.capacity_knee_probe.p99_ttft_ms IS
 'TTFT p99 from the run report -- the metric the tail SLA is graded on.';
COMMENT ON COLUMN provenance.capacity_knee_probe.p99_itl_ms IS
 'Inter-token latency p99. Graded jointly with TTFT: a rung passes only if BOTH bounds hold, '
 'which is what fails tp2knee_s2 (ITL 112.98 ms) as decisively as its TTFT does.';
COMMENT ON COLUMN provenance.capacity_knee_probe.gpu_hours IS
 'H100-equivalent GPU-hours for the rung -- the cost side of the knee.';
COMMENT ON COLUMN provenance.capacity_knee_probe.sla_ttft_p99_ms IS
 'The TTFT bound applied (1000 ms), stored per row so a future re-grading under a different SLA '
 'is visible rather than silently re-interpreting passes.';
COMMENT ON COLUMN provenance.capacity_knee_probe.sla_itl_p99_ms IS 'The ITL bound applied (100 ms).';
COMMENT ON COLUMN provenance.capacity_knee_probe.passes IS
 'p99_ttft_ms <= sla_ttft_p99_ms AND p99_itl_ms <= sla_itl_p99_ms. Computed at load, stored so '
 'the verdict cannot drift from the bounds recorded beside it.';
COMMENT ON COLUMN provenance.capacity_knee_probe.superseded_reason IS
 'Why a superseded row is retained: what was wrong and which run replaces it.';

COMMENT ON COLUMN provenance.capacity_derivation.window_name IS
 'Window the derivation applies to; NULL on the fleet-level row, which is not window-specific.';
COMMENT ON COLUMN provenance.capacity_derivation.belief_rps IS
 'The planner''s believed per-replica throughput, req/s per TP2 replica: the median of the '
 'non-degenerate ticks in belief_source_log. 10.07 on every row.';
COMMENT ON COLUMN provenance.capacity_derivation.belief_n_ticks IS
 'Number of non-degenerate ticks the median is over (86). Asserted against the live tick table by C401.';
COMMENT ON COLUMN provenance.capacity_derivation.belief_source_log IS
 'Basename of the log the belief was taken from. NOT interchangeable: other riders logs give '
 'medians from 7.31 to 10.51, so the published 10.07 is specific to fc_lead60.log.';
COMMENT ON COLUMN provenance.capacity_derivation.r_tail_rps IS
 'The measured tail knee, req/s per replica. Populated only when r_tail_method=''measured''.';
COMMENT ON COLUMN provenance.capacity_derivation.r_tail_lo_rps IS
 'Lower end of the bracket -- the most conservative r_tail still consistent with the ladder. '
 'The adopted scale divides by this.';
COMMENT ON COLUMN provenance.capacity_derivation.r_tail_hi_rps IS
 'Upper end of the bracket -- the largest r_tail that still PASSED, hence the smallest scale the '
 'SLA strictly demands (7.0).';
COMMENT ON COLUMN provenance.capacity_derivation.implied_scale IS
 'belief_rps / (the bound named by r_tail_basis). Asserted by C403.';
COMMENT ON COLUMN provenance.capacity_derivation.adopted_scale IS
 'FORECAST_REQ_SCALE actually deployed (8.0). The thesis''s claim is that this equals the '
 'derivation rather than being tuned -- which the fleet row shows exactly.';
COMMENT ON COLUMN provenance.capacity_derivation.thesis_location IS
 'file:line in tex/ that this row backs.';
COMMENT ON COLUMN provenance.capacity_derivation.published_text IS
 'The claim as printed, so a reader can compare wording against the stored arithmetic without '
 'opening the manuscript.';
COMMENT ON COLUMN provenance.capacity_derivation.rationale IS
 'Prose derivation with the concrete pass/fail evidence, including WHY the value is measured or '
 'only bracketed.';
COMMENT ON COLUMN provenance.capacity_derivation.source_paths IS
 'The specific report artifacts this row''s numbers come from -- the decisive rungs, not the whole family.';

COMMENT ON COLUMN provenance.runs_config_backfill.run_id IS 'The provenance.runs row that was backfilled.';
COMMENT ON COLUMN provenance.runs_config_backfill.column_name IS
 'Which runs column was filled. Checked against the live value by C405.';
COMMENT ON COLUMN provenance.runs_config_backfill.new_value IS
 'Value written, as text. C405 asserts it still matches provenance.runs, so an undocumented later '
 'edit surfaces as a failure instead of passing unnoticed.';
COMMENT ON COLUMN provenance.runs_config_backfill.evidence_path IS
 'The file that settles the value -- normally the generating script, never the run report, since '
 'the report is what lacked the dimension.';
COMMENT ON COLUMN provenance.runs_config_backfill.rationale IS
 'Why that file settles it, in one sentence.';
COMMENT ON COLUMN provenance.runs_config_backfill.recorded_utc IS 'When the backfill was applied.';

COMMENT ON COLUMN provenance.encoder_factoring_probe.image_px IS
 'Image edge in pixels (448 = the thesis''s uniform assumption).';
COMMENT ON COLUMN provenance.encoder_factoring_probe.batch_size IS
 'Requests per forward. Half of the key the invariance is stated over.';
COMMENT ON COLUMN provenance.encoder_factoring_probe.images_per_request IS
 'Images per request. The other half. batch_size * images_per_request = total_images by construction.';
COMMENT ON COLUMN provenance.encoder_factoring_probe.total_images IS
 'The product -- the ONLY thing the cost actually depends on, which is the finding.';
COMMENT ON COLUMN provenance.encoder_factoring_probe.is_reference IS
 'The factoring the deltas are measured against, one per total_images.';
COMMENT ON COLUMN provenance.encoder_factoring_probe.evidence_path IS
 'The contemporaneous note recording the probe. The probe harness itself was not archived, so this '
 'note plus the collector_encoder_fn corroboration is the whole provenance -- stated plainly rather '
 'than implied to be a rerunnable measurement.';
COMMENT ON COLUMN provenance.encoder_factoring_probe.evidence_line IS 'Line range within evidence_path.';
COMMENT ON COLUMN provenance.encoder_factoring_probe.note IS
 'Per-row provenance caveat, including which AIC data version the predicted_ms belongs to.';
