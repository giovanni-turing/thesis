-- 33_fulltrace_window_backfill.sql -- adversarial-review Finding 20 (2026-07-26):
-- "The full-trace result is numerically correct but has no canonical database window
-- identity." The three A13 full-trace encoder runs behind tex/baselines.tex:239-243
-- (reactive 3,323,189.5 worker-s p99 588.370 ms; static C8 4,838,397.6 worker-s p99
-- 677.461 ms; ratio 3323189.5/4838397.6 = 0.686838x -- all three re-read from
-- provenance.encoder_run_summary before this migration was written) carried
-- window_name IS NULL, although windows() has registered 'fulltrace' (604,799.7 s /
-- 1,000,000 req, GENUINELY DISTINCT from the 5.60-day 'aggregate' span -- see
-- v_window_alias "DO NOT FOLD") since schema/22_corrections.sql. They therefore could
-- not join the canonical window identity their published ratio depends on.
--
-- CORRECTION (recorded in provenance.ingest_correction as IC004): backfill
-- window_name='fulltrace' on exactly the three runs Finding 20 names. This is a
-- backfill of a NULL, not a rename, so window_name_as_ingested stays NULL (the
-- as-ingested state WAS the absence of a window label). Coverage evidence:
-- v_coverage fleet='A13' shows 1,000,000/1,000,000 requests (is_full) for all three.
--
-- Deliberately untouched: the two language siblings a13:ft_llm_static /
-- a13:ft_llm_reactive also replay the full trace (v_coverage 1,000,000 each) but are
-- outside Finding 20's scope (it names only the encoder-cost rows behind the 0.687x
-- claim); a follow-up may extend the backfill to them under its own correction id.
--
-- Idempotent: the UPDATE matches only rows still lacking the label; the INSERT is
-- ON CONFLICT DO NOTHING.
BEGIN;

UPDATE provenance.runs
   SET window_name = 'fulltrace'
 WHERE run_id IN ('a13:ft_reactive_L30', 'a13:ft_static_C8', 'a13:ft_static_C2')
   AND window_name IS DISTINCT FROM 'fulltrace';

INSERT INTO provenance.ingest_correction
  (correction_id, table_name, field, original_value, corrected_value, n_rows,
   source_path, evidence, rationale)
VALUES
  ('IC004', 'runs', 'window_name', 'NULL', 'fulltrace', 3,
   '/home/gio/tese/defense/anim/data/a13_runs/',
   'windows(fulltrace)=604799.7 s/1,000,000 req; v_coverage A13: ft_reactive_L30, '
   'ft_static_C2, ft_static_C8 each 1,000,000/1,000,000 (is_full); '
   'encoder_run_summary: reactive 3323189.5 ws / 588.370 ms p99, static C8 '
   '4838397.6 ws / 677.461 ms p99, static C2 1209599.4 ws / 2904.556 ms p99; '
   'ratio 0.686838x = tex/baselines.tex:239-243. Adversarial review Finding 20.',
   'The A13 family replays the ENTIRE 7-day trace, a genuinely distinct window from '
   'the 5.60-day aggregate (forecast-covered) span. The runs were ingested before the '
   'fulltrace window was registered in windows(), so they carried no window identity '
   'and could not join the canonical alias layer that distinguishes fulltrace from '
   'aggregate. The label is a backfill of missing dimension data, not a change to any '
   'measured value; every measurement column is untouched.')
ON CONFLICT (correction_id) DO NOTHING;

COMMIT;
