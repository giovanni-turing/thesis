#!/bin/bash
# Split bench.sql on "-- Qn:" markers and run each under EXPLAIN (ANALYZE, BUFFERS).
# Usage: runbench.sh <label>   -> writes results to results_<label>.txt
set -u
D=/tmp/claude-1000/-home-gio-tese/948dec29-8ae8-42e5-992c-9ce712056a71/scratchpad
LABEL=${1:-baseline}
export PGPASSWORD=$(docker inspect -f '{{range .Config.Env}}{{println .}}{{end}}' postgres | sed -n 's/^POSTGRES_PASSWORD=//p')
PSQL="psql -h localhost -p 5433 -U goku -d postgres -X -q"

ONERUN=$($PSQL -t -A -c "select run_id from provenance.llm_request where experiment='a11' limit 1")
echo "ONERUN=$ONERUN"

python3 - "$D" <<'PY'
import re,sys
d=sys.argv[1]
txt=open(d+'/bench.sql').read()
parts=re.split(r'\n(?=-- Q\d[ab]?:)', txt)
for p in parts:
    m=re.match(r'-- (Q\d[ab]?):', p.strip())
    if not m: continue
    open(f'{d}/q_{m.group(1)}.sql','w').write(p)
PY

OUT=$D/results_$LABEL.txt
: > $OUT
for f in $D/q_Q*.sql; do
  Q=$(basename $f .sql | sed 's/^q_//')
  SQL=$(cat $f | sed "s/:'ONERUN'/'$ONERUN'/")
  echo "===== $Q =====" | tee -a $OUT
  # warm the cache / plan once, discard
  $PSQL -c "$SQL" > /dev/null 2>&1
  # measure wall time (3 warm runs, report each)
  for i in 1 2 3; do
    S=$(date +%s.%N)
    $PSQL -c "$SQL" > /dev/null 2>&1
    E=$(date +%s.%N)
    echo "  wall_run$i: $(echo "$E - $S" | bc)" | tee -a $OUT
  done
  echo "--- EXPLAIN (ANALYZE, BUFFERS) ---" >> $OUT
  $PSQL -c "EXPLAIN (ANALYZE, BUFFERS) $SQL" >> $OUT 2>&1
  echo >> $OUT
done
echo "wrote $OUT"
