#!/bin/bash
# 4.4 weekly aggregate -- ISSUE-TIME headline (the honest 0.62x figure).
#
# Supersedes the forecast rows of run_44_aggregate.sh, which used the
# TARGET-time generator (forecast_schedule.py --cold-start-s L). This driver
# uses verification/scripts/forecast_schedule_issuetime.py, which honours the
# H=12 / 15-s archive's tiled issue times (issue <= decision, refuses L>165 s)
# and emits the schedule the converter's --worker-schedule hook consumes.
#
# Two readiness models (see the generator's docstring):
#   warm-pool (default) : lifetime warm envelope; cost ~lead-invariant 0.62x.
#   strict  (--strict-rewarm) : a matured level retires after --warm-hold-s;
#                               cost mildly lead-dependent, 0.59-0.62x.
#
# Denominator: static C=8 over the covered span = 8 * 483660 = 3,869,278 ws.
# Regenerates the committed .sched/.stats/.ledger artifacts; the 124 MB
# per-request .jsonl intermediates are gitignored and reproduced here.
set -u
EDA_PY=/home/gio/tese/eda/.venv/bin/python
AIC_PY=/home/gio/tese/ai-dynamo/aiconfigurator/.venv/bin/python
CONV=/home/gio/tese/workload/trace_to_two_pool.py
GEN=/home/gio/tese/verification/scripts/forecast_schedule_issuetime.py
PARQUET=/home/gio/tese/predictors/results/chronos_images.parquet
export TESE_WINDOWS=/home/gio/tese/simulation/windows.json
OFFSET=250399; MAXREQ=749601

run() {  # $1 out-dir  $2 tag  $3 lead  $4 rho  $5 extra-gen-flags
  local D=$1 TAG=$2 L=$3 RHO=$4 EXTRA=$5
  mkdir -p "$D"
  $EDA_PY $GEN --window aggregate --quantile p90 --rho "$RHO" --cold-start-s "$L" \
      --parquet "$PARQUET" $EXTRA \
      --out "$D/$TAG.sched.json" --ledger-out "$D/$TAG.ledger.json" \
      > "$D/$TAG.sched.log" 2>&1 || { echo "SCHED FAIL $TAG"; return; }
  $AIC_PY $CONV --out "$D/$TAG.jsonl" --offset "$OFFSET" --max-requests "$MAXREQ" \
      --encoder-workers 2 --worker-schedule "$D/$TAG.sched.json" \
      > "$D/$TAG.log" 2>&1 && echo "done $TAG" || echo "FAIL $TAG"
}

A=/home/gio/tese/simulation/results/aggregate44
R=/home/gio/tese/simulation/results/aggregate44_rho
S=/home/gio/tese/simulation/results/aggregate44_strict

# headline: warm-pool p90/rho15 at every realizable lead (0.62x, flat)
for L in 15 30 45 165; do run "$A" "fc_p90_L${L}_issuetime" "$L" 15 "" ; done
# rho frontier (warm-pool, L=30): rho10 0.89x, rho15 0.62x, rho20 0.48x, rho25 0.40x
for RHO in 10 20 25; do run "$R" "fc_p90_rho${RHO}_L30_issuetime" 30 "$RHO" "" ; done
# strict re-warm sensitivity: p90/rho15 at every lead (0.59-0.62x, lead-dependent)
for L in 15 30 45 165; do run "$S" "fc_p90_L${L}_strict" "$L" 15 "--strict-rewarm" ; done

echo "=== issue-time aggregate complete; summary (ws / 3,869,278 = ratio) ==="
for f in "$A"/fc_p90_L*_issuetime.jsonl.stats.json \
         "$R"/fc_p90_rho*_issuetime.jsonl.stats.json \
         "$S"/fc_p90_L*_strict.jsonl.stats.json; do
  python3 -c "
import json,sys; st=json.load(open('$f')); ws=st['provisioned_worker_seconds']
print('$f'.split('/')[-1].replace('.jsonl.stats.json',''),
      '| p99', st['encoder_delay_ms']['p99'], '| ws', round(ws),
      '| %.4fx'%(ws/3869278.4), '| div', st.get('queue_divergent'))"
done
