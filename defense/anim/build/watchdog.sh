#!/usr/bin/env bash
# Watchdog for the read-only verification phase.
# Agents already proved they will launch compute despite instructions. This kills any
# gap-driver execution while WATCH_MODE=enforce, logs the violation, and reports load/RAM/GPU.
# Supervisor-staged runs are exempt via the marker file (STAGED).
set -u
cd /home/gio/tese
LOG=/tmp/claude-1000/-home-gio-tese/9f01036b-6dca-44ec-b6d8-86c52f46aa1e/scratchpad/watchdog.log
STAGED=/tmp/claude-1000/-home-gio-tese/9f01036b-6dca-44ec-b6d8-86c52f46aa1e/scratchpad/STAGED
DRIVERS='build/gen_g[0-9]_|build/gen_a16_'
: > "$LOG"
viol=0
for i in $(seq 1 "${WATCH_TICKS:-80}"); do
  if [ ! -f "$STAGED" ]; then
    # enforce: no driver may run unless the supervisor staged it
    pids=$(pgrep -f "$DRIVERS" 2>/dev/null | grep -v $$ || true)
    if [ -n "$pids" ]; then
      for p in $pids; do
        cmd=$(ps -o args= -p "$p" 2>/dev/null | cut -c1-120)
        [ -z "$cmd" ] && continue
        echo "[$(date +%H:%M:%S)] VIOLATION killed pid=$p :: $cmd" >> "$LOG"
        kill -TERM "$p" 2>/dev/null
        viol=$((viol+1))
      done
      sleep 2
      pgrep -f "$DRIVERS" 2>/dev/null | xargs -r kill -KILL 2>/dev/null || true
    fi
  fi
  la=$(uptime | grep -oE 'load average: [0-9.]+' | cut -d' ' -f3)
  ram=$(free -g | awk 'NR==2{print $7}')
  gpu=$(nvidia-smi --query-gpu=utilization.gpu --format=csv,noheader 2>/dev/null | tr -d ' ')
  echo "[$(date +%H:%M:%S)] load=$la ram=${ram}G gpu=$gpu violations=$viol" >> "$LOG"
  sleep 15
done
echo "[$(date +%H:%M:%S)] watchdog done, total violations=$viol" >> "$LOG"
