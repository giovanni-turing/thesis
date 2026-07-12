#!/bin/bash
cd /home/gio/tese/collector_artifacts/phaseE_physical_anchor
PY=/home/gio/tese/eda/.venv/bin/python
TARGET="1 2 3 4 5 6 7 8 9 10 11 12 13 14 15 16 17 18 19 20 21 22 23 24 25 26 27 28 29 30 31 32 33 34 35 36 37 38 39 40 41 42 43 44 45 46 47 48 49 50 51 52 53 54 55 56 57 58 59 60 61 62 63 64 96 128 192 256 512"
# 1) wait for the running single-process sdpa sweep to exit (clean or OOM)
while pgrep -f "bench_encoder_anchor.py --attn sdpa --ns [0-9,]*,[0-9]" >/dev/null; do sleep 20; done
sleep 3
run_1by1() {  # $1=attn  $2=logfile(existing rows)  $3=merged.csv  $4=oom.txt
  local ATTN=$1 SRCLOG=$2 MERGED=$3 OOMF=$4
  # N already present in the source log
  done_n=$(grep -oE "^[0-9]+," "$SRCLOG" 2>/dev/null | tr -d , | sort -n | uniq)
  : > "$OOMF"
  for N in $TARGET; do
    if grep -q "^$N," "$MERGED" 2>/dev/null; then continue; fi
    if echo "$done_n" | grep -qx "$N"; then
      grep "^$N," "$SRCLOG" | head -1 >> "$MERGED"; continue
    fi
    # fresh process, single N -> clean allocator
    out=$($PY bench_encoder_anchor.py --attn $ATTN --ns $N --nruns 5 --iters 50 --warmup 10 --out /tmp/_anchor_${ATTN}_$N.json 2>/tmp/_err_${ATTN}_$N)
    row=$(echo "$out" | grep -E "^$N,[0-9]")
    if [ -n "$row" ]; then echo "$row" >> "$MERGED"; echo "OK N=$N ($ATTN)"
    else echo "$N" >> "$OOMF"; echo "OOM-ALONE N=$N ($ATTN) — genuine >32GB"; fi
  done
}
echo "=== sdpa mop-up (1-by-1) ==="
run_1by1 sdpa dense_anchor.log merged_sdpa.csv oom_sdpa.txt
echo "=== fa2 full (1-by-1, OOM-safe) ==="
run_1by1 flash_attention_2 dense_anchor_fa2.log merged_fa2.csv oom_fa2.txt
echo "DENSE_1BY1_DONE"
