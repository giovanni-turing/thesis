#!/bin/bash
# Block until the 4 in-flight week replays exit, then idempotently ingest the whole langcalib
# batch (picks up the 5 new week-scale reports) and print the new headline metrics. One job ->
# one completion notification (no polling from the caller).
set -u
PIDS="1908435 1914385 1914386 1914387"   # react / chronos-mean / toto / timesfm week replays
PY=/home/gio/tese/ai-dynamo/dynamo/.venv/bin/python
cd /home/gio/tese
echo "waiting on week replays: $PIDS"
for i in $(seq 1 100); do   # 100*30s = 50min safety cap
  alive=""
  for p in $PIDS; do kill -0 "$p" 2>/dev/null && alive="$alive $p"; done
  [ -z "$alive" ] && { echo "all week replays exited (~$((i*30))s waited)"; break; }
  sleep 30
done
sleep 5   # let final report flush
echo "=== reports present ==="
ls -la simulation/results/lang_qsweep/baseline_week/*.report.json \
       simulation/results/lang_qsweep/extra_week/*.report.json 2>/dev/null

echo "=== ingest (idempotent) ==="
POSTGRES_PASSWORD=$(grep -oE "password=[^ ]+" provenance/.goku_credentials | head -1 | cut -d= -f2) \
  $PY provenance/loader/load_langcalib.py

echo "=== new week-scale headline metrics (p99 e2e, throughput, gpu_hours) ==="
$PY - <<'PY'
import json, glob, os
for p in sorted(glob.glob("simulation/results/lang_qsweep/baseline_week/*.report.json")
              + glob.glob("simulation/results/lang_qsweep/extra_week/*.report.json")):
    try: d=json.load(open(p))
    except Exception as e: print(f"  {os.path.basename(p)}: UNREADABLE {e}"); continue
    print(f"  {os.path.basename(p):<40} p99_e2e={d.get('p99_e2e_latency_ms')!s:>9}  "
          f"gpu_h={d.get('gpu_hours')!s:>7}  rps={d.get('request_throughput_rps')!s:>7}  "
          f"n={d.get('completed_requests') or d.get('num_requests')}")
PY
echo "=== wait_and_ingest_week complete ==="
