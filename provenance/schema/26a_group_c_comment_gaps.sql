-- 26a_group_c_comment_gaps.sql
-- ADJUDICATION §2.8/§2.11 verification pass, 2026-07-20.
-- The Group C ingest (25_group_c.sql / 26_group_c_checks.sql) satisfied every data
-- requirement of §2.8 and §2.11, but left five columns without a COMMENT, in
-- violation of the standing "COMMENT every new table/column" rule. One of them
-- (encoder_run_summary.image_px) is the column the §2.11 note explicitly warns
-- must NOT be trusted for g6 runs -- that warning lived only in the audit
-- markdown, where a future SQL-only reader would never meet it.
-- Idempotent: COMMENT ON is a pure upsert, re-runnable without effect.

COMMENT ON COLUMN provenance.encoder_factoring_probe.probe_id IS
  'ADJUDICATION §2.11. Synthetic key of the form aic<image_px>:n<total_images>:b<batch_size>x<images_per_request>, e.g. aic448:n64:b16x4. Encodes the full probe coordinate so a row is self-describing and the primary key is stable across re-ingest; it is NOT a run identifier and does not join to provenance.runs -- the probe is an AIC-model evaluation, not a measured run.';

COMMENT ON COLUMN provenance.collector_scalar.source_path IS
  'Absolute path of the collector artifact this scalar was read from. Part of the primary key, so the same metric name harvested from two artifacts never collides.';

COMMENT ON COLUMN provenance.collector_scalar.metric IS
  'Scalar name as it appears in (or is derived from) the source artifact. Free-form by design -- this table is the catch-all for scalars with no wide-table home, so the vocabulary is per-artifact rather than global.';

COMMENT ON COLUMN provenance.collector_scalar.value_num IS
  'Numeric value when the scalar is a number; NULL when the scalar is textual. Exactly one of value_num / value_text is populated per row.';

COMMENT ON COLUMN provenance.collector_scalar.value_text IS
  'Textual value when the scalar is not numeric (error class names, framework versions, free-text notes); NULL otherwise. Exactly one of value_num / value_text is populated per row.';

COMMENT ON COLUMN provenance.encoder_run_summary.image_px IS
  'Image edge in pixels. TRUSTWORTHY FOR THESIS RUNS ONLY (uniform 448 = 196 post-merge tokens/image). KNOWN DEFECT, recorded not fixed (ADJUDICATION §2.11): the 12 g6:u896* post-manuscript defence resolution-sweep rows read 448 here although their true payload is 896^2 = 784 post-merge tokens/image -- the simulator emits image_px as a default and the real mixture lives in the un-ingested <stem>.jsonl.g6mix.json sidecar. DO NOT use this column to reason about g6 payload or bytes-on-the-wire; that is why check C404 is scoped to thesis runs and C407 pins the excluded 12 explicitly. Ingesting the g6mix sidecars would retire this caveat.';
