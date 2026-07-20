#!/usr/bin/env bash
# Wave 1 — cheap gap tracks (pure analysis + AIC pricing). No heavy language replays,
# so these are RAM-safe and cannot collide with staged week-scale work.
# Supervisor-staged: sequential-ish with bounded concurrency (2), each logged separately.
set -u
cd /home/gio/tese
S=/tmp/claude-1000/-home-gio-tese/9f01036b-6dca-44ec-b6d8-86c52f46aa1e/scratchpad
say(){ echo "[$(date +%H:%M:%S)] $*"; }

say "wave1 start; load=$(uptime|grep -oE 'load average: [0-9.]+'|cut -d' ' -f3) ram=$(free -g|awk 'NR==2{print $7}')G"

# --- 1. decode upper-bound (pure analysis on existing 999,599 per-request records) ---
( say "decode_spread start"
  timeout 2400 python3 defense/anim/build/gen_a16_decode_spread.py \
    --records defense/anim/data/a15_runs/timesfm_e2e.requests.jsonl \
    --out defense/anim/data/a16_decode > "$S/w1_decode.log" 2>&1
  say "decode_spread rc=$?" ) &
P1=$!

# --- 2. 32B intermediate pricing (AIC, minutes) ---
( say "g3_32b start"
  timeout 2400 python3 defense/anim/build/gen_g3_32b.py > "$S/w1_32b.log" 2>&1
  say "g3_32b rc=$?" ) &
P2=$!

wait $P1; wait $P2

# --- 3. controller cost (brief GPU timing + ARIMA + accounting) — GPU exclusive, run alone ---
say "controller_cost start (GPU)"
timeout 3000 python3 defense/anim/build/gen_a16_controller_cost.py --stage all \
  > "$S/w1_ctrl.log" 2>&1
say "controller_cost rc=$?"

say "wave1 done; load=$(uptime|grep -oE 'load average: [0-9.]+'|cut -d' ' -f3) ram=$(free -g|awk 'NR==2{print $7}')G"
for f in w1_decode w1_32b w1_ctrl; do
  echo "--- $f (tail) ---"; tail -12 "$S/$f.log" 2>/dev/null
done
