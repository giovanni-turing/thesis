#!/usr/bin/env bash
# Reconstruct the large result artifacts that were gzip-compressed (and, for the
# already-compressed parquets, split) so this repo stays under GitHub's 100 MB
# per-file limit WITHOUT Git LFS. Run from anywhere inside the repo.
#
#   text logs/jsonls : *.gz            -> gunzip
#   covariate parquets: *.parquet.gz.part00,01 -> cat parts, then gunzip
set -euo pipefail
cd "$(git rev-parse --show-toplevel)"

gunzip -kf \
  simulation/results/llm_week/week_re.log.gz \
  simulation/results/llm_week/week_fc_p90.log.gz \
  simulation/results/rerun_verify/week_static_C6.jsonl.gz \
  simulation/results/rerun_verify/week_static_C7.jsonl.gz \
  simulation/results/rerun_verify/week_static_C8.jsonl.gz

for p in predictors/results/chronos_covariates predictors/results/toto_covariates; do
  cat "$p.parquet.gz.part"* > "$p.parquet.gz"
  gunzip -f "$p.parquet.gz"
done

echo "Restored 2 logs + 3 jsonls + 2 parquets from their compressed/split forms."
