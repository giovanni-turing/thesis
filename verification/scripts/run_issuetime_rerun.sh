#!/bin/bash
# B2 rerun: encoder schedule actuated on honest ISSUE time vs the shipped
# target-time path, for the fast onset (burst3) and the slow onset (burst1),
# p90 / rho=15, at leads L in {30,165}. 165 s is the H=12 15-s archive's max
# honest issued lead ((12-1)*15). 300 s is NOT run for issue-time (refused).
set -u
VP=/home/gio/tese/ai-dynamo/aiconfigurator/.venv/bin/python
SHIP=/home/gio/tese/simulation/forecast_schedule.py
ISSUE=/home/gio/tese/verification/scripts/forecast_schedule_issuetime.py
CONV=/home/gio/tese/workload/trace_to_two_pool.py
PARQ=/home/gio/tese/predictors/results/chronos_images.parquet
O=/home/gio/tese/simulation/results/rerun_verify
mkdir -p "$O"
declare -A OFF=( [burst1]=843072 [burst3]=531966 )
declare -A NRQ=( [burst1]=64804 [burst3]=3093 )

run_conv () { # tag sched
  local tag=$1 sched=$2 w=$3
  $VP "$CONV" --out "$O/$tag.jsonl" --offset "${OFF[$w]}" \
      --max-requests "${NRQ[$w]}" --encoder-workers 2 \
      --worker-schedule "$sched" > "$O/$tag.sim.log" 2>&1 \
      && echo "  converter done: $tag" || { echo "  CONVERTER FAIL: $tag"; cat "$O/$tag.sim.log"; }
}

for w in burst3 burst1; do
  for L in 30 165; do
    # (a) shipped target-time forecast
    tag="${w}_ship_L${L}"
    $VP "$SHIP" --window "$w" --policy forecast --resolution 15s --quantile p90 --rho 15 \
        --cold-start-s "$L" --hysteresis-min 3 --parquet "$PARQ" \
        --out "$O/$tag.sched.json" > "$O/$tag.ctl.log" 2>&1
    run_conv "$tag" "$O/$tag.sched.json" "$w"
    # (b) honest issue-time forecast
    tag="${w}_issue_L${L}"
    $VP "$ISSUE" --window "$w" --quantile p90 --rho 15 \
        --cold-start-s "$L" --hysteresis-min 3 --parquet "$PARQ" \
        --out "$O/$tag.sched.json" --ledger-out "$O/$tag.ledger.json" > "$O/$tag.ctl.log" 2>&1
    run_conv "$tag" "$O/$tag.sched.json" "$w"
    # (c) reactive (already honest; trailing observation) for context
    tag="${w}_react_L${L}"
    $VP "$SHIP" --window "$w" --policy reactive --resolution 15s --quantile p90 --rho 15 \
        --cold-start-s "$L" --hysteresis-min 3 --parquet "$PARQ" \
        --out "$O/$tag.sched.json" > "$O/$tag.ctl.log" 2>&1
    run_conv "$tag" "$O/$tag.sched.json" "$w"
  done
  # (d) shipped target-time at the impossible L=300 (to show it fabricates lead)
  tag="${w}_ship_L300"
  $VP "$SHIP" --window "$w" --policy forecast --resolution 15s --quantile p90 --rho 15 \
      --cold-start-s 300 --hysteresis-min 3 --parquet "$PARQ" \
      --out "$O/$tag.sched.json" > "$O/$tag.ctl.log" 2>&1
  run_conv "$tag" "$O/$tag.sched.json" "$w"
done
echo "ALL DONE"
