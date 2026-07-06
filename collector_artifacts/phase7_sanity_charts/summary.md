## Sanity Check Chart Generation Report
download_link_placeholder

New perf data files were detected in this PR. Please use the link above to
download sanity check charts for the new perf data to compare the collected
perf data vs SOL (theoretical max performance).

Below is a report of whether the chart generation was successful for each op.
If doesn't validate whether the perf data itself is sane.
### Chart Generation Report for system: rtx_5090, backend: vllm, backend_version: 0.22.0
- `gemm` ✅
- CLI smoke test Skipped ⚠️: required default-model perf files are not present for this backend version: context_attention_perf.parquet, generation_attention_perf.parquet
