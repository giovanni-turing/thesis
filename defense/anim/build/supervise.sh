#!/usr/bin/env bash
# Systematic supervisor for the 9 gap tracks.
# Runs unattended: every CYCLE_S it classifies every track, auto-remediates failures
# (retry with the correct interpreter, bounded retries), detects STALLED tracks (log
# not growing while process alive), and writes a single STATUS.md.
# Exits only when every track is terminal (done or exhausted) -> that re-invokes Claude.
set -u
cd /home/gio/tese
S=/tmp/claude-1000/-home-gio-tese/9f01036b-6dca-44ec-b6d8-86c52f46aa1e/scratchpad
STATUS="$S/STATUS.md"
SUPLOG="$S/supervise.log"
CYCLE_S=${CYCLE_S:-120}
MAX_RETRY=${MAX_RETRY:-2}
STALL_CYCLES=${STALL_CYCLES:-15}     # log unchanged this many cycles => stalled

PY_AIC=ai-dynamo/aiconfigurator/.venv/bin/python
PY_DYN=ai-dynamo/dynamo/.venv/bin/python
PY_EDA=eda/.venv/bin/python
B=defense/anim/build

# name|command  (correct interpreter per track — the g6 venv bug is fixed here)
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
ORDER=(g2_conventions a16_decode g3_32b g6_sizesens a16_ctrlcost g1_burst26 a16_endogenous g4_folds a16_finetune)

declare -A RETRY=() LASTSZ=() STALLN=() STATE=()
for t in "${ORDER[@]}"; do RETRY[$t]=0; LASTSZ[$t]=-1; STALLN[$t]=0; STATE[$t]=unknown; done

say(){ echo "[$(date +%H:%M:%S)] $*" >> "$SUPLOG"; }
logf(){ echo "$S/stage_${1}.log"; }
alive(){ pgrep -f "[g]en_${1#*_}" >/dev/null 2>&1 || pgrep -f "$(basename "${CMD[$1]#* }" | sed 's/^\(.\)/[\1]/')" >/dev/null 2>&1; }

rc_of(){ grep -E " $1\$" "$S/stage_rc.txt" 2>/dev/null | tail -1 | sed 's/rc=\([0-9]*\).*/\1/'; }

launch(){ local t=$1
  say "LAUNCH $t (retry ${RETRY[$t]}): ${CMD[$t]}"
  ( eval "${CMD[$t]}" > "$(logf "$t")" 2>&1; echo "rc=$? $t" >> "$S/stage_rc.txt" ) &
}

: > "$SUPLOG"
say "supervisor start; cycle=${CYCLE_S}s max_retry=$MAX_RETRY"

while :; do
  allterm=1
  for t in "${ORDER[@]}"; do
    rc=$(rc_of "$t"); lf=$(logf "$t")
    sz=$( [ -f "$lf" ] && stat -c%s "$lf" || echo 0 )

    if [ -n "$rc" ] && [ "$rc" = "0" ]; then
      STATE[$t]=done; continue
    fi

    if [ -n "$rc" ] && [ "$rc" != "0" ]; then
      # terminal failure -> retry if budget remains
      if [ "${RETRY[$t]}" -lt "$MAX_RETRY" ]; then
        RETRY[$t]=$(( RETRY[$t] + 1 ))
        say "FAIL $t rc=$rc -> auto-retry ${RETRY[$t]}/$MAX_RETRY"
        sed -i "/ $t\$/d" "$S/stage_rc.txt" 2>/dev/null
        STALLN[$t]=0; LASTSZ[$t]=-1
        launch "$t"; STATE[$t]=retrying; allterm=0
      else
        STATE[$t]="FAILED(rc=$rc, retries exhausted)"
      fi
      continue
    fi

    # no rc yet: running, stalled, or never started
    if pgrep -f "[/]$(basename "${CMD[$t]##* }")" >/dev/null 2>&1 || \
       pgrep -f "[g]en_$(echo "$t" | sed 's/^[ag][0-9]*_//')" >/dev/null 2>&1; then
      if [ "$sz" -eq "${LASTSZ[$t]}" ]; then
        STALLN[$t]=$(( STALLN[$t] + 1 ))
        if [ "${STALLN[$t]}" -ge "$STALL_CYCLES" ]; then
          STATE[$t]="STALLED(${STALLN[$t]} cycles, log ${sz}B)"
          say "STALL $t: log flat ${STALLN[$t]} cycles at ${sz}B"
        else
          STATE[$t]="running(quiet ${STALLN[$t]})"
        fi
      else
        STALLN[$t]=0; STATE[$t]="running(${sz}B)"
      fi
      LASTSZ[$t]=$sz; allterm=0
    else
      if [ -f "$lf" ]; then
        STATE[$t]="exited-no-rc(${sz}B)"
        if [ "${RETRY[$t]}" -lt "$MAX_RETRY" ]; then
          RETRY[$t]=$(( RETRY[$t] + 1 )); say "NO-RC $t -> relaunch ${RETRY[$t]}/$MAX_RETRY"
          launch "$t"; allterm=0
        fi
      else
        STATE[$t]=not-started; allterm=0
      fi
    fi
  done

  { echo "# Gap-track supervisor status"; echo
    echo "updated $(date +%H:%M:%S) · load $(uptime | grep -oE 'load average: [0-9.]+' | cut -d' ' -f3) · free $(free -g | awk 'NR==2{print $7}')G · gpu $(nvidia-smi --query-gpu=utilization.gpu --format=csv,noheader 2>/dev/null | head -1)"
    echo; echo "| track | state | retries | log |"; echo "|---|---|---:|---|"
    for t in "${ORDER[@]}"; do
      printf "| %s | %s | %s | %s |\n" "$t" "${STATE[$t]}" "${RETRY[$t]}" "$(tail -1 "$(logf "$t")" 2>/dev/null | cut -c1-70 | tr '|' '/')"
    done
    echo; echo "## supervisor events"; echo '```'; tail -25 "$SUPLOG"; echo '```'
  } > "$STATUS"

  [ "$allterm" = "1" ] && { say "ALL TERMINAL"; break; }
  sleep "$CYCLE_S"
done

say "supervisor exit"
cat "$STATUS"
