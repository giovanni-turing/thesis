#!/usr/bin/env bash
# Finish the three-model (Chronos/Toto/TimesFM) animation update.
# Blocks until A15 (heavy expanding-context E2E) and the A12 burst-timesfm arms
# drain, then runs the two heavy WEEK timesfm replays 2-wide (RAM-safe only once
# A15 frees ~55GB), then extracts + rebuilds A11/A12 and refreshes the manifest.
set -u
cd /home/gio/tese
LOG=/tmp/claude-1000/-home-gio-tese/9f01036b-6dca-44ec-b6d8-86c52f46aa1e/scratchpad/finish_tf.log
say(){ echo "[$(date +%H:%M:%S)] $*"; }

# 1. wait for A15 + burst-timesfm to clear (block, don't hammer)
while pgrep -f gen_a15_expctx_e2e >/dev/null || pgrep -f 'gen_a12_timesfm.py burst' >/dev/null; do
  sleep 30
done
say "A15 + a12 bursts drained; RAM avail $(free -g|awk 'NR==2{print $7}')G"

# 2. heavy week arms, 2-wide (a12 week + a11 week)
python3 defense/anim/build/gen_a12_timesfm.py week_fc_timesfm \
  > "${LOG}.a12week" 2>&1 &
P12=$!
python3 defense/anim/build/gen_a11_timesfm.py week_fc_timesfm_L60 \
  > "${LOG}.a11week" 2>&1 &
P11=$!
wait $P12; R12=$?
wait $P11; R11=$?
say "a12 week rc=$R12 ; a11 week rc=$R11"
[ $R12 -eq 0 ] && [ $R11 -eq 0 ] || { say "WEEK ARM FAILED — aborting extract"; exit 1; }

# 3. extract (pandas via system py) + build the three-model HTMLs
say "extract_a11"; python3 defense/anim/build/extract_a11.py || { say "extract_a11 FAIL"; exit 2; }
say "extract_a12"; python3 defense/anim/build/extract_a12.py || { say "extract_a12 FAIL"; exit 2; }
say "build_a11";  python3 defense/anim/build/build_a11.py
say "build_a12";  python3 defense/anim/build/build_a12.py

# 4. refresh coverage manifest (A15 now populated too)
say "coverage manifest"; python3 defense/anim/build/build_coverage_manifest.py | tail -6

say "DONE — a11/a12 three-model rebuilt"
