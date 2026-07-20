#!/usr/bin/env bash
# RAM-aware staged runner for the 9 verified+fixed gap tracks.
# Launches a track only when free RAM covers its peak + margin; serializes GPU tracks.
# Longest pole (g2-conventions, 330 min) starts first so everything else overlaps it.
set -u
cd /home/gio/tese
S=/tmp/claude-1000/-home-gio-tese/9f01036b-6dca-44ec-b6d8-86c52f46aa1e/scratchpad
MARGIN_GB=25
say(){ echo "[$(date +%H:%M:%S)] $*"; }
freeg(){ free -g | awk 'NR==2{print $7}'; }
gpu_busy(){ nvidia-smi --query-compute-apps=pid --format=csv,noheader 2>/dev/null | grep -q . && echo 1 || echo 0; }

# name|peak_gb|needs_gpu|command
QUEUE=(
"g2_conventions|60|0|python3 defense/anim/build/gen_g2_conventions.py --conc 4 --week-conc 2 --no-jsonl"
"a16_decode|4|0|python3 defense/anim/build/gen_a16_decode_spread.py --records defense/anim/data/a15_runs/timesfm_e2e.requests.jsonl --out defense/anim/data/a16_decode"
"g3_32b|4|0|python3 defense/anim/build/gen_g3_32b.py --force"
"g6_sizesens|5|0|ai-dynamo/aiconfigurator/.venv/bin/python defense/anim/build/gen_g6_sizesens.py"
"a16_ctrlcost|18|1|python3 defense/anim/build/gen_a16_controller_cost.py --stage all"
"g1_burst26|12|0|ai-dynamo/dynamo/.venv/bin/python defense/anim/build/gen_g1_burst26.py"
"a16_endogenous|6|0|python3 defense/anim/build/gen_a16_endogenous.py"
"g4_folds|14|0|ai-dynamo/aiconfigurator/.venv/bin/python defense/anim/build/gen_g4_folds.py"
"a16_finetune|16|1|eda/.venv/bin/python defense/anim/build/gen_a16_finetune.py all"
)

declare -a PIDS=() NAMES=()
say "stage_all start; free=$(freeg)G"

for entry in "${QUEUE[@]}"; do
  IFS='|' read -r name peak gpu cmd <<< "$entry"
  # wait for RAM headroom
  while [ "$(freeg)" -lt $(( peak + MARGIN_GB )) ]; do
    say "waiting for RAM: need $(( peak + MARGIN_GB ))G for $name, free=$(freeg)G"
    sleep 60
  done
  # serialize GPU tracks
  if [ "$gpu" = "1" ]; then
    while [ "$(gpu_busy)" = "1" ]; do say "waiting for GPU: $name"; sleep 60; done
  fi
  say "LAUNCH $name (peak ${peak}G, gpu=$gpu); free=$(freeg)G"
  ( eval "$cmd" > "$S/stage_${name}.log" 2>&1; echo "rc=$? $name" >> "$S/stage_rc.txt" ) &
  PIDS+=($!); NAMES+=("$name")
  sleep 45   # let it allocate before sizing the next
done

say "all launched; waiting"
for i in "${!PIDS[@]}"; do
  wait "${PIDS[$i]}"; say "done ${NAMES[$i]} rc=$?"
done
say "STAGE_ALL COMPLETE; free=$(freeg)G"
cat "$S/stage_rc.txt" 2>/dev/null
