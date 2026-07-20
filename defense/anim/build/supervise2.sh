#!/usr/bin/env bash
# Systematic supervisor v2 — PID-based liveness (v1's pgrep patterns misfired and
# spawned duplicates). Adopts already-running tracks by PID, owns all new launches,
# auto-retries genuine failures, detects stalls, writes one STATUS.md.
# Exits only when every track is terminal -> that re-invokes Claude.
set -u
cd /home/gio/tese
S=/tmp/claude-1000/-home-gio-tese/9f01036b-6dca-44ec-b6d8-86c52f46aa1e/scratchpad
STATUS="$S/STATUS.md"; SUPLOG="$S/supervise.log"
CYCLE_S=${CYCLE_S:-120}; MAX_RETRY=${MAX_RETRY:-2}; STALL_CYCLES=${STALL_CYCLES:-20}
PY_AIC=ai-dynamo/aiconfigurator/.venv/bin/python
PY_DYN=ai-dynamo/dynamo/.venv/bin/python
PY_EDA=eda/.venv/bin/python
B=defense/anim/build

declare -A CMD=(
 [g2_conventions]="python3 $B/gen_g2_conventions.py --conc 4 --week-conc 2 --no-jsonl"
 [a16_decode]="python3 $B/gen_a16_decode_spread.py --records defense/anim/data/a15_runs/timesfm_e2e.requests.jsonl --out defense/anim/data/a16_decode"
 [g3_32b]="python3 $B/gen_g3_32b.py --force"
 [g6_sizesens]="$PY_AIC $B/gen_g6_sizesens.py"
 [a16_ctrlcost]="python3 $B/gen_a16_controller_cost.py --stage all"
 [g1_burst26]="$PY_DYN $B/gen_g1_burst26.py"
 [a16_endogenous]="python3 $B/gen_a16_endogenous.py"
 [g4_folds]="$PY_AIC $B/gen_g4_folds.py"
 [a16_finetune]="$PY_EDA $B/gen_a16_finetune.py all"
)
declare -A DRV=(
 [g2_conventions]=gen_g2_conventions [a16_decode]=gen_a16_decode_spread [g3_32b]=gen_g3_32b
 [g6_sizesens]=gen_g6_sizesens [a16_ctrlcost]=gen_a16_controller_cost [g1_burst26]=gen_g1_burst26
 [a16_endogenous]=gen_a16_endogenous [g4_folds]=gen_g4_folds [a16_finetune]=gen_a16_finetune
)
# tracks whose peak RAM is large — do not launch concurrently past this floor
declare -A PEAK=( [g2_conventions]=60 [a16_ctrlcost]=18 [a16_finetune]=16 [g4_folds]=14
                  [g1_burst26]=12 [a16_endogenous]=6 [g6_sizesens]=5 [g3_32b]=4 [a16_decode]=4 )
declare -A GPU=( [a16_ctrlcost]=1 [a16_finetune]=1 )
ORDER=(g2_conventions a16_decode g3_32b g6_sizesens a16_ctrlcost g1_burst26 a16_endogenous g4_folds a16_finetune)

declare -A PID=() RETRY=() LASTSZ=() STALLN=() STATE=()
say(){ echo "[$(date +%H:%M:%S)] $*" >> "$SUPLOG"; }
logf(){ echo "$S/stage_${1}.log"; }
freeg(){ free -g | awk 'NR==2{print $7}'; }
DATADIR(){ case "$1" in
  g2_conventions) echo defense/anim/data/g2_runs;;
  g1_burst26) echo defense/anim/data/g1_runs;;
  g4_folds) echo defense/anim/data/g4_folds;;
  g6_sizesens) echo defense/anim/data/g6_runs;;
  g3_32b) echo defense/anim/data/g3_32b;;
  a16_ctrlcost) echo defense/anim/data/a16_controller_cost;;
  a16_finetune) echo defense/anim/data/a16_ft;;
  a16_endogenous) echo defense/anim/data/a16_runs;;
  a16_decode) echo defense/anim/data/a16_decode;;
  *) echo /nonexistent;; esac; }
# newest byte-size total under the data dir: advances even when driver stdout is silent
ACTIVITY(){ d=$(DATADIR "$1"); [ -d "$d" ] && du -sb "$d" 2>/dev/null | cut -f1 || echo 0; }
rc_of(){ grep -E " $1\$" "$S/stage_rc.txt" 2>/dev/null | tail -1 | sed 's/rc=\([0-9]*\).*/\1/'; }
gpu_busy(){ nvidia-smi --query-compute-apps=pid --format=csv,noheader 2>/dev/null | grep -q . && echo 1 || echo 0; }

launch(){ local t=$1
  # RAM gate
  local need=$(( ${PEAK[$t]} + 20 ))
  local waited=0
  while [ "$(freeg)" -lt "$need" ] && [ $waited -lt 40 ]; do sleep 30; waited=$((waited+1)); done
  # GPU gate
  if [ "${GPU[$t]:-0}" = "1" ]; then
    waited=0
    while [ "$(gpu_busy)" = "1" ] && [ $waited -lt 120 ]; do sleep 30; waited=$((waited+1)); done
  fi
  say "LAUNCH $t (retry ${RETRY[$t]:-0}) free=$(freeg)G"
  sed -i "/ $t\$/d" "$S/stage_rc.txt" 2>/dev/null
  ( eval "${CMD[$t]}" > "$(logf "$t")" 2>&1; echo "rc=$? $t" >> "$S/stage_rc.txt" ) &
  PID[$t]=$!
}

: > "$SUPLOG"; say "supervisor v2 start (PID-based liveness)"
# adopt anything already running, by PID
for t in "${ORDER[@]}"; do
  RETRY[$t]=0; LASTSZ[$t]=-1; STALLN[$t]=0; STATE[$t]=unknown
  p=$(pgrep -f "[${DRV[$t]:0:1}]${DRV[$t]:1}\.py" 2>/dev/null | head -1)
  if [ -n "$p" ]; then PID[$t]=$p; say "ADOPT $t pid=$p"; else PID[$t]=""; fi
done

while :; do
  allterm=1
  for t in "${ORDER[@]}"; do
    rc=$(rc_of "$t"); lf=$(logf "$t"); sz=$( [ -f "$lf" ] && stat -c%s "$lf" || echo 0 )
    sz=$(( sz + $(ACTIVITY "$t") ))   # child artifact growth counts as progress
    if [ -n "$rc" ] && [ "$rc" = "0" ]; then STATE[$t]=done; continue; fi

    live=0
    if [ -n "${PID[$t]}" ] && kill -0 "${PID[$t]}" 2>/dev/null; then live=1; fi
    # adopt late-appearing process (e.g. relaunched outside supervisor)
    if [ $live -eq 0 ]; then
      p=$(pgrep -f "[${DRV[$t]:0:1}]${DRV[$t]:1}\.py" 2>/dev/null | head -1)
      if [ -n "$p" ]; then PID[$t]=$p; live=1; fi
    fi

    if [ $live -eq 1 ]; then
      if [ "$sz" -eq "${LASTSZ[$t]}" ]; then
        STALLN[$t]=$(( STALLN[$t] + 1 ))
        if [ "${STALLN[$t]}" -ge "$STALL_CYCLES" ]; then STATE[$t]="STALLED(${STALLN[$t]}c ${sz}B)"
        else STATE[$t]="running(quiet ${STALLN[$t]})"; fi
      else STALLN[$t]=0; STATE[$t]="running(${sz}B)"; fi
      LASTSZ[$t]=$sz; allterm=0; continue
    fi

    # not live
    if [ -n "$rc" ] && [ "$rc" != "0" ]; then
      if [ "${RETRY[$t]}" -lt "$MAX_RETRY" ]; then
        RETRY[$t]=$(( RETRY[$t] + 1 )); say "FAIL $t rc=$rc -> retry ${RETRY[$t]}/$MAX_RETRY"
        STALLN[$t]=0; LASTSZ[$t]=-1; launch "$t"; STATE[$t]=retrying; allterm=0
      else STATE[$t]="FAILED(rc=$rc, exhausted)"; fi
    elif [ ! -f "$lf" ] || [ "$sz" -eq 0 ]; then
      if [ "${RETRY[$t]}" -lt "$MAX_RETRY" ]; then
        RETRY[$t]=$(( RETRY[$t] + 1 )); say "NOT-STARTED $t -> launch ${RETRY[$t]}/$MAX_RETRY"
        launch "$t"; STATE[$t]=starting; allterm=0
      else STATE[$t]="FAILED(never started)"; fi
    else
      # log exists, process gone, no rc: died without recording
      if [ "${RETRY[$t]}" -lt "$MAX_RETRY" ]; then
        RETRY[$t]=$(( RETRY[$t] + 1 )); say "DIED-NO-RC $t (${sz}B) -> retry ${RETRY[$t]}/$MAX_RETRY"
        launch "$t"; STATE[$t]=retrying; allterm=0
      else STATE[$t]="FAILED(died, exhausted)"; fi
    fi
  done

  { echo "# Gap-track supervisor"; echo
    echo "updated $(date +%H:%M:%S) · load $(uptime | grep -oE 'load average: [0-9.]+' | cut -d' ' -f3) · free $(freeg)G · gpu $(nvidia-smi --query-gpu=utilization.gpu --format=csv,noheader 2>/dev/null | head -1)"
    echo; echo "| track | state | try | pid | last line |"; echo "|---|---|---:|---:|---|"
    for t in "${ORDER[@]}"; do
      printf "| %s | %s | %s | %s | %s |\n" "$t" "${STATE[$t]}" "${RETRY[$t]}" "${PID[$t]:--}" \
        "$(tail -1 "$(logf "$t")" 2>/dev/null | cut -c1-64 | tr '|' '/')"
    done
    echo; echo '```'; tail -20 "$SUPLOG"; echo '```'
  } > "$STATUS"

  [ "$allterm" = "1" ] && { say "ALL TERMINAL"; break; }
  sleep "$CYCLE_S"
done
say "supervisor exit"; cat "$STATUS"
