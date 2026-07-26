#!/bin/bash
# Full-frontier LANGUAGE rerun WITH per-request records (--report-jsonl) so week-wide SLO
# violation counts are EXACT at ANY threshold. Validated: per-request satisfying count ==
# native goodput_completed_requests (Rust-streamed JSONL, no estimate). Planner runs also pass
# --sla-ttft-ms/--sla-itl-ms for a native goodput cross-check.
#
# SEQUENTIAL by design: each full-week (749,601-req) replay is ~16 GB RSS + ~1 h. Do NOT
# parallelize (that is what swapped the box before). Idempotent: skips a point whose perreq exists.
set -u
OUT=/home/gio/tese/simulation/results/lang_qsweep/perreq
mkdir -p "$OUT"
PY=/home/gio/tese/ai-dynamo/dynamo/.venv/bin/python
RR=/home/gio/tese/simulation/run_replay.sh
RWF=/home/gio/tese/simulation/replay_with_forecast.py
TRACE=/home/gio/tese/simulation/results/aggregate44/fc_p90_L30.jsonl
FCFG=/home/gio/tese/simulation/planner_forecast_smoke.json
RCFG=/home/gio/tese/simulation/results/lang_qsweep/baseline_week/cfg_react.json
T0="2024-10-16 21:39:00"
SLA="--sla-ttft-ms 200 --sla-itl-ms 20"

run(){ # tag  cmd...
  local tag=$1; shift
  local pr="$OUT/$tag.perreq.jsonl" log="$OUT/$tag.log"
  [ -f "$pr" ] && { echo "skip $tag (perreq exists, $(wc -l <"$pr") recs)"; return; }
  echo "=== $tag  start $(date +%H:%M:%S) ==="
  ( "$@" > "$log" 2>&1 ) &
  local pid=$! peak=0 r
  while kill -0 $pid 2>/dev/null; do
    r=$(ps -o rss= -p "$(pgrep -f 'dynamo.replay|replay_with_forecast.py' | tr '\n' , | sed 's/,$//')" 2>/dev/null | awk '{s+=$1}END{print s+0}')
    [ "${r:-0}" -gt "$peak" ] && peak=$r; sleep 20
  done
  wait $pid; local rc=$?
  local n=0; [ -f "$pr" ] && n=$(wc -l <"$pr")
  echo "    $tag  rc=$rc  perreq=$n  peakRSS=$((peak/1024))MB  end $(date +%H:%M:%S)"
}
fc(){ # tag model quantile scale
  local tag=$1 M=$2 Q=$3 S=$4
  FORECAST_REQ_SCALE=$S AIC_TP=2 STARTUP_TIME=60 REPLAY_PY=$PY AIC_VER=0.19.0 \
    REPLAY_ENTRY=$RWF FORECAST_MODEL=$M FORECAST_RESOLUTION=15s FORECAST_QUANTILE=$Q \
    FORECAST_T0="$T0" RUST_LOG=warn \
    run "$tag" bash "$RR" "$TRACE" aic "$OUT/$tag.report.json" 2 \
       --planner-config "$FCFG" $SLA --report-jsonl "$OUT/$tag.perreq.jsonl"
}

# 1) reactive baseline (planner + SLA + perreq)
RUST_LOG=warn AIC_TP=2 STARTUP_TIME=60 REPLAY_PY=$PY AIC_VER=0.19.0 \
  run reactive_200_20 bash "$RR" "$TRACE" aic "$OUT/reactive_200_20.report.json" 2 \
    --planner-config "$RCFG" $SLA --report-jsonl "$OUT/reactive_200_20.perreq.jsonl"

# 2) robust forecast point (the deployable e13-safe operating point)
fc fc_chronos_p90_s6 chronos p90 6

# 3) static reference (non-planner; --report-jsonl ok, goodput SLA n/a so no --sla)
RUST_LOG=warn AIC_TP=2 STARTUP_TIME=0 REPLAY_PY=$PY AIC_VER=0.19.0 \
  run static_tp2x2 bash "$RR" "$TRACE" aic "$OUT/static_tp2x2.report.json" 2 \
    --report-jsonl "$OUT/static_tp2x2.perreq.jsonl"

# 4) fragile / aggressive frontier points
fc fc_chronos_p70_s6 chronos p70 6
fc fc_chronos_p50_s8 chronos p50 8
fc fc_chronos_p90_s4 chronos p90 4
fc fc_chronos_p90_s1 chronos p90 1     # mean-conversion (scale=1)

# 5) model-independence of the robust point
fc fc_toto_p90_s6    toto    p90 6
fc fc_timesfm_p90_s6 timesfm p90 6

echo "=== lang per-request rerun COMPLETE $(date +%H:%M:%S) ==="
