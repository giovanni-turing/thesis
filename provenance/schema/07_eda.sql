-- =========================================================================
-- FAMILY "eda" (K22): trace exploratory characterization of the corpus trace
-- Source: /home/gio/tese/analysis/trace_eda/*_stats.json  (14 files, scripts a..q)
-- Corpus: AzureLMMInferenceDataset2025 multimodal trace, 1,000,000 requests,
--         168 h (2024-10-15 12:00 -> 2024-10-22 12:00), 4 fields per request
--         (TIMESTAMP, NumImages, ContextTokens, GeneratedTokens).
-- Backs tex/trace-eda.tex (Ch.3).
--
-- Design: the 14 JSONs are structurally heterogeneous (scalars, nested percentile
-- maps, correlation matrices, ragged arrays). One TALL table `eda_metric` holds an
-- EXHAUSTIVE recursive flattening of every leaf scalar of every file, so nothing is
-- lost and any number in Ch.3 is reachable by its dotted JSON path. Four small typed
-- entity tables sit alongside it for the repeating entities a reviewer actually joins
-- on (burst episodes, request classes, request archetypes, silhouette scans). The
-- typed tables are a convenience projection: every value in them also exists in
-- eda_metric under its original path.
--
-- Apply: psql -h localhost -p 5433 -U goku -d postgres -v ON_ERROR_STOP=1 -f 07_eda.sql
-- =========================================================================
CREATE SCHEMA IF NOT EXISTS provenance;
SET search_path = provenance, public;

-- ---------------------------------------------------------------- tall store
CREATE TABLE IF NOT EXISTS provenance.eda_metric (
    script       text NOT NULL,
    metric_path  text NOT NULL,
    run_id       text REFERENCES provenance.runs(run_id) ON DELETE CASCADE,
    signal       text,
    window_bin   text,
    stat         text,
    value_num    double precision,
    value_bool   boolean,
    value_text   text,
    PRIMARY KEY (script, metric_path)
);
CREATE INDEX IF NOT EXISTS eda_metric_signal_idx ON provenance.eda_metric (signal);
CREATE INDEX IF NOT EXISTS eda_metric_window_idx ON provenance.eda_metric (window_bin);
CREATE INDEX IF NOT EXISTS eda_metric_stat_idx   ON provenance.eda_metric (stat);
CREATE INDEX IF NOT EXISTS eda_metric_path_idx   ON provenance.eda_metric (metric_path);

COMMENT ON TABLE provenance.eda_metric IS
  'Exhaustive flattening of the 14 analysis/trace_eda/*_stats.json files: one row per leaf scalar. Every number in tex/trace-eda.tex (Ch.3, trace characterization of the 1M-request 168h trace) is here. Lookup by (script, metric_path); signal/window_bin/stat are best-effort parsed facets for filtering, and are NULL when the path has no such facet. Values are never rounded - full float64 precision as emitted by the analysis scripts.';
COMMENT ON COLUMN provenance.eda_metric.script IS
  'Analysis script stem that produced the file, = basename minus "_stats.json": a_quality, b_marginals, c_temporal, d_signals, e_comprehensive, f_fourier, f2_fourier_ctx, g_ctx, i_burst_anatomy, j_classes, k_episode_clusters, l_request_clusters, m_gen_and_global, q_multires_tails.';
COMMENT ON COLUMN provenance.eda_metric.metric_path IS
  'Dotted path of the leaf inside the source JSON; list elements are indexed as name[0], name[1]... e.g. "window_1min.img_per_s.p99", "requests.top_peaks_period_gt_10min[0].period_hours", "multi_resolution.60s.images.cv2". Note: percentile keys that themselves contain a dot (p99.9) appear verbatim, so "global_request_level.ContextTokens.p99.9" is one path with a literal p99.9 leaf.';
COMMENT ON COLUMN provenance.eda_metric.run_id IS
  'FK to runs: "eda:<script>". One run per stats file, experiment=eda, pool=both.';
COMMENT ON COLUMN provenance.eda_metric.signal IS
  'Parsed time-series / per-request signal the leaf describes, when identifiable: requests|images|ctx|gen (rate signals), req_per_s|img_per_s|tokens_per_s, NumImages|ContextTokens|GeneratedTokens (per-request fields), requests_per_s|images_per_s|ctx_tokens_per_s|gen_tokens_per_s. NULL when the path is not signal-scoped.';
COMMENT ON COLUMN provenance.eda_metric.window_bin IS
  'Parsed aggregation bin of the leaf, when identifiable: 1s,2s,3s,5s,8s,12s,15s,20s,30s,45s,60s,90s,120s,180s,300s,600s,900s,1800s,3600s (q_multires_tails grid); also s,10s,min,10min,h (Fano-factor bins) and 1min/1s (c_temporal window_* keys, normalised to 1min/1s). NULL for request-level or window-free metrics.';
COMMENT ON COLUMN provenance.eda_metric.stat IS
  'Parsed statistic of the leaf when the last path component is one: mean, median, min, max, count, cv2, p1, p10, p50, p90, p95, p99, p99.9, quantile keys 0.5/0.9/0.99/0.999, r2, share, sum. NULL otherwise (e.g. structural or identity leaves).';
COMMENT ON COLUMN provenance.eda_metric.value_num IS 'Numeric leaf value (int or float), full precision. NULL if the leaf was a bool or string.';
COMMENT ON COLUMN provenance.eda_metric.value_bool IS 'Boolean leaf value (e.g. numimages.all_perfect_squares=false). NULL otherwise.';
COMMENT ON COLUMN provenance.eda_metric.value_text IS 'String leaf value (timestamps as "YYYY-MM-DD HH:MM:SS", class names, semantic archetype names, provenance notes). NULL otherwise.';

-- ------------------------------------------------------- typed: burst episodes
CREATE TABLE IF NOT EXISTS provenance.eda_burst_episode (
    source_script      text NOT NULL,
    start_ts           timestamp NOT NULL,
    peak_ts            timestamp,
    episode_kind       text NOT NULL,
    rank_by_peak       int,
    end_ts             timestamp,
    minutes            int,
    onset_min          int,
    decay_min          int,
    duration_min       int,
    peak_img_per_s     double precision,
    peak_req_per_s     double precision,
    ramp_img_per_s_per_min      double precision,
    steepest_1min_jump_img_per_s double precision,
    ctx_p50            double precision,
    cluster_id         int,
    share_single       double precision,
    share_tiled_small  double precision,
    share_tiled_large  double precision,
    share_frames       double precision,
    dominant_class     text,
    dominant_share     double precision,
    run_id             text REFERENCES provenance.runs(run_id) ON DELETE CASCADE,
    PRIMARY KEY (source_script, start_ts)
);
CREATE INDEX IF NOT EXISTS eda_burst_episode_peak_idx ON provenance.eda_burst_episode (peak_ts);
COMMENT ON TABLE provenance.eda_burst_episode IS
  'Image-rate burst episodes of the 168h trace, as emitted by three different scripts with three different episode definitions - hence source_script is part of the key and rows across scripts are NOT duplicates, they are different segmentations of the same peaks. c_temporal: 87 RAW episodes (contiguous 1-min bins with img/s > p99=223.985), top6 by peak recorded. i_burst_anatomy: the 87 raw merged into 18 MERGED episodes with baseline-to-baseline extents, top6 by peak recorded - this is the SOURCE of the burst1..burst6 evaluation windows used throughout the thesis (join provenance.windows). k_episode_clusters: all 18 merged episodes with class-mix features and their KMeans cluster label. j_classes burst attribution (dominant_class/dominant_share) is merged onto the i_burst_anatomy top6 rows, which share the same peak timestamps.';
COMMENT ON COLUMN provenance.eda_burst_episode.source_script IS 'Which EDA script defined this episode row: c_temporal | i_burst_anatomy | k_episode_clusters. Part of the PK.';
COMMENT ON COLUMN provenance.eda_burst_episode.start_ts IS 'Episode start minute (naive local trace clock, no tz). Part of the PK: unique within each source_script. For merged episodes this is the start_baseline (last pre-burst baseline minute), not the threshold crossing.';
COMMENT ON COLUMN provenance.eda_burst_episode.peak_ts IS 'Minute bin of the episode peak image rate; the natural join key to burst attribution and to the burst1..6 evaluation windows. NULL for c_temporal raw episodes, which report only the start/end of the above-threshold run and no peak timestamp.';
COMMENT ON COLUMN provenance.eda_burst_episode.episode_kind IS 'raw = contiguous run of 1-min bins above the img/s p99 threshold (c_temporal, 87 of them). merged = raw episodes merged and extended to surrounding baseline (i_burst_anatomy/k_episode_clusters, 18 of them).';
COMMENT ON COLUMN provenance.eda_burst_episode.rank_by_peak IS '1-based rank within that script''s top-6-by-peak list; NULL for the k_episode_clusters rows, which are the full set of 18 rather than a top-6.';
COMMENT ON COLUMN provenance.eda_burst_episode.end_ts IS 'Episode end (end_baseline for merged episodes). NULL where the script did not emit one.';
COMMENT ON COLUMN provenance.eda_burst_episode.minutes IS 'Length in minutes of a RAW episode (number of above-threshold 1-min bins).';
COMMENT ON COLUMN provenance.eda_burst_episode.onset_min IS 'Minutes from start_baseline to peak - the ramp-up time an autoscaler must beat.';
COMMENT ON COLUMN provenance.eda_burst_episode.decay_min IS 'Minutes from peak back to baseline. NULL where the episode did not return to baseline before the analysis cut (common: only 1 of the top 6 decays).';
COMMENT ON COLUMN provenance.eda_burst_episode.duration_min IS 'Total merged-episode duration in minutes (k_episode_clusters feature).';
COMMENT ON COLUMN provenance.eda_burst_episode.peak_img_per_s IS 'Peak images/s in the 1-min bin at peak_ts. Trace-wide max is 370.183 (2024-10-21 19:53).';
COMMENT ON COLUMN provenance.eda_burst_episode.ramp_img_per_s_per_min IS 'Mean ramp slope over the onset: (peak_img_per_s - baseline) / onset_min.';
COMMENT ON COLUMN provenance.eda_burst_episode.steepest_1min_jump_img_per_s IS 'Largest single-minute increase in images/s within the episode - the worst-case step an autoscaler sees.';
COMMENT ON COLUMN provenance.eda_burst_episode.ctx_p50 IS 'Median ContextTokens of the requests inside the episode.';
COMMENT ON COLUMN provenance.eda_burst_episode.cluster_id IS 'KMeans cluster label from k_episode_clusters (chosen_k=2: cluster 0 has 17 episodes, cluster 1 has 1).';
COMMENT ON COLUMN provenance.eda_burst_episode.share_frames IS 'Fraction of the episode''s images contributed by the "frames" request class (large k-by-k frame grids). Typically >0.94 - bursts are a frames phenomenon.';
COMMENT ON COLUMN provenance.eda_burst_episode.dominant_class IS 'Request class contributing the largest image share during the peak (j_classes burst attribution); always "frames" for the top 6.';

-- -------------------------------------------------------- typed: request classes
CREATE TABLE IF NOT EXISTS provenance.eda_request_class (
    class_name     text PRIMARY KEY,
    requests       bigint,
    request_share  double precision,
    image_share    double precision,
    ctx_p50        double precision,
    gen_p50        double precision,
    img_rate_cv2   double precision,
    img_rate_mean  double precision,
    run_id         text REFERENCES provenance.runs(run_id) ON DELETE CASCADE
);
COMMENT ON TABLE provenance.eda_request_class IS
  'The 5 RULE-BASED request classes of j_classes_stats.json, cut on NumImages: text (0 images), single (1), tiled_small (2..~16), tiled_large, frames (large k-by-k grids). Deterministic taxonomy - distinct from the unsupervised 4 archetypes in eda_request_archetype. Headline: frames is 2.7% of requests but 81.2% of all images.';
COMMENT ON COLUMN provenance.eda_request_class.requests IS 'Absolute request count in the 1,000,000-request trace; the 5 classes partition it exactly.';
COMMENT ON COLUMN provenance.eda_request_class.request_share IS 'Fraction of the 1M requests in this class (sums to 1.0).';
COMMENT ON COLUMN provenance.eda_request_class.image_share IS 'Fraction of ALL images in the trace contributed by this class (sums to 1.0). The load-relevant share for the encoder pool.';
COMMENT ON COLUMN provenance.eda_request_class.ctx_p50 IS 'Median ContextTokens of requests in this class.';
COMMENT ON COLUMN provenance.eda_request_class.gen_p50 IS 'Median GeneratedTokens of requests in this class.';
COMMENT ON COLUMN provenance.eda_request_class.img_rate_cv2 IS 'Squared coefficient of variation of this class''s 1-min images/s series - its burstiness. NULL for the text class (no images).';
COMMENT ON COLUMN provenance.eda_request_class.img_rate_mean IS 'Mean images/s contributed by this class over the whole trace. NULL for the text class.';

-- ----------------------------------------------------- typed: request archetypes
CREATE TABLE IF NOT EXISTS provenance.eda_request_archetype (
    cluster_id     int PRIMARY KEY,
    semantic_name  text,
    n_requests     bigint,
    img_p50        double precision,
    ctx_p50        double precision,
    gen_p50        double precision,
    img_sum        bigint,
    ctx_sum        bigint,
    req_share      double precision,
    img_share      double precision,
    ctx_share      double precision,
    run_id         text REFERENCES provenance.runs(run_id) ON DELETE CASCADE
);
COMMENT ON TABLE provenance.eda_request_archetype IS
  'The 4 UNSUPERVISED request archetypes of l_request_clusters_stats.json: cuML KMeans (chosen_k=4) on StandardScaler(log1p(NumImages, ContextTokens, GeneratedTokens)) over all 1M requests, n_init=10, random_state=0. Distinct from the rule-based eda_request_class. Headline: cluster 1 ("vision: video/frame analysis") is 3.4% of requests but 85.7% of images.';
COMMENT ON COLUMN provenance.eda_request_archetype.cluster_id IS 'KMeans label 0..3. Labels are arbitrary but reproducible at random_state=0; use semantic_name in prose.';
COMMENT ON COLUMN provenance.eda_request_archetype.semantic_name IS 'Human-assigned interpretation of the cluster centroid, as quoted in Ch.3: "text: short-answer / extraction", "vision: video/frame analysis", "text: conversational generation", "vision: doc/tiled understanding".';
COMMENT ON COLUMN provenance.eda_request_archetype.n_requests IS 'Requests assigned to this cluster; the 4 clusters sum to 1,000,000.';
COMMENT ON COLUMN provenance.eda_request_archetype.img_sum IS 'Total images contributed by the cluster (absolute, over the whole trace).';
COMMENT ON COLUMN provenance.eda_request_archetype.ctx_sum IS 'Total ContextTokens contributed by the cluster - the prefill-volume weight.';
COMMENT ON COLUMN provenance.eda_request_archetype.req_share IS 'Cluster share of requests (rounded to 3dp in the source; use n_requests/1e6 for full precision).';
COMMENT ON COLUMN provenance.eda_request_archetype.img_share IS 'Cluster share of all images (rounded to 3dp in the source).';
COMMENT ON COLUMN provenance.eda_request_archetype.ctx_share IS 'Cluster share of all context tokens (rounded to 3dp in the source).';

-- --------------------------------------------------------- typed: silhouette scan
CREATE TABLE IF NOT EXISTS provenance.eda_silhouette (
    source_script  text NOT NULL,
    k              int  NOT NULL,
    silhouette     double precision,
    is_chosen      boolean NOT NULL DEFAULT false,
    is_argmax      boolean NOT NULL DEFAULT false,
    entity         text,
    is_valid       boolean NOT NULL DEFAULT true,
    provenance_note text,
    run_id         text REFERENCES provenance.runs(run_id) ON DELETE CASCADE,
    PRIMARY KEY (source_script, k)
);
COMMENT ON TABLE provenance.eda_silhouette IS
  'KMeans model-selection scans behind the two clusterings in Ch.3, at full source precision. k_episode_clusters: k=2..5 over the 18 merged burst episodes, chosen_k=2 (silhouette 0.6578 at k=2 is also the argmax). l_request_clusters: k=3..9 over all 1M requests, chosen_k=4 (silhouette 0.3880, the argmax by a hair over k=8''s 0.3871 - hence the standalone recomputation whose note is carried in provenance_note). NOTE: the 4-decimal values in l_silhouette_scan.json are a rounded RECOMPUTATION of the l_request_clusters values and are deliberately NOT stored as separate rows - only its provenance string is attached here.';
COMMENT ON COLUMN provenance.eda_silhouette.source_script IS 'k_episode_clusters (episode-level clustering) | l_request_clusters (request-level clustering). Part of the PK.';
COMMENT ON COLUMN provenance.eda_silhouette.k IS 'Number of KMeans clusters evaluated.';
COMMENT ON COLUMN provenance.eda_silhouette.silhouette IS 'Mean silhouette score at this k, full precision from the source JSON (higher = better separated).';
COMMENT ON COLUMN provenance.eda_silhouette.is_chosen IS 'True for the k the analysis actually adopted downstream (chosen_k): 2 for episodes, 4 for requests.';
COMMENT ON COLUMN provenance.eda_silhouette.is_argmax IS 'True for the k with the maximum silhouette in that scan. Equals is_chosen for both scans here; kept separate so a reviewer can check the choice was not overridden.';
COMMENT ON COLUMN provenance.eda_silhouette.entity IS 'What was clustered: burst_episode (n=18) | request (n=1,000,000).';
COMMENT ON COLUMN provenance.eda_silhouette.is_valid IS 'False would mark a superseded/retracted scan point; all rows currently true.';
COMMENT ON COLUMN provenance.eda_silhouette.provenance_note IS 'Free-text reproduction note. For l_request_clusters this is the "provenance" string of l_silhouette_scan.json, the independent 2026-07-08 recomputation that confirms k=4 is the argmax.';
