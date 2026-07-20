#!/usr/bin/env bash
# verify_all.sh -- the delivery gate.
#
# One command that re-verifies the whole chain: the store is internally consistent,
# the thesis agrees with it, and neither has drifted. Exits non-zero if any gate fails.
#
#   ./provenance/verify_all.sh            # everything
#   ./provenance/verify_all.sh --data     # gate A only (fast, no LaTeX build)
#   ./provenance/verify_all.sh --thesis   # gate B only
#
# Design rule: this script REPORTS failures, it never hides them. A gate that cannot be
# evaluated is a FAIL, not a skip -- an unevaluated check that prints green is worse than
# no check at all.

set -uo pipefail
TESE=/home/gio/tese
LOADER=$TESE/provenance/loader
TMP=$(mktemp -d)
trap 'rm -rf "$TMP"' EXIT

PASS=0; FAIL=0; WARN=0
ok()   { printf "  \033[32mPASS\033[0m  %s\n" "$1"; PASS=$((PASS+1)); }
bad()  { printf "  \033[31mFAIL\033[0m  %s\n" "$1"; FAIL=$((FAIL+1)); }
warn() { printf "  \033[33mWARN\033[0m  %s\n" "$1"; WARN=$((WARN+1)); }
hdr()  { printf "\n\033[1m%s\033[0m\n" "$1"; }

export PGPASSWORD=$(docker inspect -f '{{range .Config.Env}}{{println .}}{{end}}' postgres 2>/dev/null \
                    | sed -n 's/^POSTGRES_PASSWORD=//p')
Q() { psql -h localhost -p 5433 -U goku -d postgres -tAc "$1" 2>/dev/null; }

WANT_DATA=1; WANT_THESIS=1
[ "${1:-}" = "--data" ]   && WANT_THESIS=0
[ "${1:-}" = "--thesis" ] && WANT_DATA=0

# ─────────────────────────────────────────────────────────────── GATE A: data
if [ $WANT_DATA -eq 1 ]; then
hdr "GATE A — data verified"

if [ -z "$PGPASSWORD" ]; then bad "cannot reach postgres (no password from docker inspect)"; else

  # A1 error-level checks. Failures are acceptable ONLY if documented as accepted.
  ERR=$(Q "select count(*) from provenance.check_all() where not passed and severity='error'")
  ACC=$(Q "select count(*) from provenance.check_all() c
           join provenance.check_definition d using (check_id)
           where not c.passed and c.severity='error' and d.note ilike '%ACCEPTED%'")
  if [ "${ERR:-x}" = "0" ]; then ok "check_all: 0 error-level failures"
  elif [ "${ERR:-0}" = "${ACC:-0}" ]; then
    ok "check_all: $ERR error-level failure(s), all documented ACCEPTED"
    Q "select '        - '||check_id||': '||left(title,60) from provenance.check_all() where not passed and severity='error'"
  else bad "check_all: $ERR error-level failures, only $ACC documented as accepted"
    Q "select '        - '||check_id||': '||left(title,60) from provenance.check_all() where not passed and severity='error'"
  fi
  WRN=$(Q "select count(*) from provenance.check_all() where not passed and severity='warn'")
  [ "${WRN:-0}" -gt 0 ] && warn "check_all: $WRN warn-level failure(s) (see check_definition.note)"

  # A2 orphans: every run_id must resolve to the spine.
  ORPH=$(Q "select coalesce(sum(n),0) from (
              select (xpath('/row/c/text()', query_to_xml(
                format('select count(*) c from provenance.%I x where x.run_id is not null
                        and not exists (select 1 from provenance.runs r where r.run_id=x.run_id)', c.table_name),
                false,true,'')))[1]::text::bigint n
              from information_schema.columns c
              join information_schema.tables t using (table_schema, table_name)
              where c.table_schema='provenance' and c.column_name='run_id'
                and t.table_type='BASE TABLE' and c.table_name<>'runs'
                and c.table_name not in ('ingest_log','verification')) s")
  [ "${ORPH:-x}" = "0" ] && ok "orphan run_ids across analytic tables: 0" \
                         || bad "orphan run_ids: ${ORPH:-unknown}"

  # A3 lineage freshness + drift
  MV=$(Q "select count(*) from provenance.mv_llm_p99_check")
  LIVE=$(Q "select count(distinct run_id) from provenance.llm_request
            where run_id in (select run_id from provenance.llm_run_summary)")
  [ "${MV:-0}" = "${LIVE:-1}" ] && ok "lineage matview fresh ($MV runs)" \
                                || bad "lineage matview STALE ($MV materialized vs $LIVE live) -- REFRESH MATERIALIZED VIEW provenance.mv_llm_p99_check"
  DRIFT=$(Q "select coalesce(max(ttft_pct_diff),0)::numeric(10,4) from provenance.v_llm_drift")
  awk -v d="${DRIFT:-99}" 'BEGIN{exit !(d<2.0)}' && ok "worst raw-vs-summary drift ${DRIFT}% (<2%)" \
                                                 || bad "worst drift ${DRIFT}% exceeds 2%"
  RC=$(Q "select bool_and(rowcount_matches) from provenance.v_llm_drift")
  [ "${RC:-f}" = "t" ] && ok "every summary rowcount matches its raw rows" || bad "rowcount mismatch in v_llm_drift"

  # A4 totals (informational, printed so drift over time is visible)
  printf "        store: %s runs / %s rows / %s / %s files\n" \
    "$(Q 'select count(*) from provenance.runs')" \
    "$(Q "select to_char(sum(n_live_tup),'FM999,999,999') from pg_stat_user_tables where schemaname='provenance'")" \
    "$(Q "select pg_size_pretty(sum(pg_total_relation_size(c.oid))) from pg_class c join pg_namespace n on n.oid=c.relnamespace where n.nspname='provenance'")" \
    "$(Q 'select count(*) from provenance.ingest_log')"
fi

# A5 loader selftest
if (cd "$LOADER" && python3 selftest.py >"$TMP/self.log" 2>&1); then
  ok "loader selftest (collision guard, dir coverage, run_id injectivity)"
else bad "loader selftest FAILED"; sed 's/^/        /' "$TMP/self.log" | tail -6; fi

# A6 idempotency -- a re-run must CHANGE NOTHING.
#
# Judge by content hashes, not by main.py's stdout counters. SCHEMA_GUIDE §6.14: three
# POST-passes (K34 config_backfill, K40 srcbuild, K41 runtime_build) are deliberately NOT
# ingest_log-gated -- their ingest_log key is owned by another kind -- so they always PRINT
# files>0 while COALESCE-ing deterministically-read values that change nothing; K13 reloads
# the ledger once whenever results-ledger.md's sha moves, then settles. A stdout "files=0"
# proxy therefore reports a false FAIL on a store that is in fact byte-stable, and -- worse --
# it would MISS a POST-pass that overwrote an existing value without changing its file count.
# The digest below is strictly stronger: it fails on ANY change to the data the loaders can
# touch (raw counts, the annotated runs columns, and ingest_log content excluding loaded_at),
# and it fails if any file-gated loader added an ingest_log row.
DIGEST() { Q "select md5(string_agg(x,'|' order by x)) from (
    select 'il_ct='||count(*)::text x from provenance.ingest_log
    union all select 'il='||md5(string_agg(file_path||'#'||sha256||'#'||n_rows::text||'#'||coalesce(run_id,''), '\n' order by file_path)) from provenance.ingest_log
    union all select 'runs='||md5(string_agg(run_id||'#'||coalesce(runtime_build,'')||'#'||coalesce(runtime_version,'')||'#'||coalesce(window_name,'')||'#'||coalesce(tp::text,'')||'#'||coalesce(artifact_commit_sha,'')||'#'||coalesce(model_checkpoint,'')||'#'||coalesce(arrival_speedup::text,'')||'#'||coalesce(config_provenance::text,''), '\n' order by run_id)) from provenance.runs
    union all select t||'='||(xpath('/r/c/text()',query_to_xml('select count(*) c from provenance.'||t,false,true,''))::text[])[1] from unnest(array['llm_request','composed_request','encoder_series','forecast','worker_schedule','factorial_cell']) t
  ) s"; }
# Two-run form: the FIRST run may legitimately absorb a genuinely-changed file on disk (e.g.
# K13 re-loads results-ledger.md whenever its sha moves -- §6.14). Idempotency is the property
# that, ONCE SETTLED, a further run changes nothing. So settle first, then assert the SECOND run
# leaves the digest byte-identical.
if (cd "$LOADER" && timeout 3600 python3 main.py >"$TMP/ingest1.log" 2>&1); then :
else bad "main.py (settle pass) exited non-zero"; tail -5 "$TMP/ingest1.log" | sed 's/^/        /'; fi
D_BEFORE=$(DIGEST)
if (cd "$LOADER" && timeout 3600 python3 main.py >"$TMP/ingest.log" 2>&1); then
  D_AFTER=$(DIGEST)
  if [ -n "$D_BEFORE" ] && [ "$D_BEFORE" = "$D_AFTER" ]; then
    ok "ingest idempotent (settled re-run changes nothing -- content digest byte-stable; §6.14)"
    grep -E 'files=[1-9]' "$TMP/ingest.log" | sed 's/^/        (post-pass counter, no data change) /' | head -5
  else bad "ingest NOT idempotent -- content digest changed on a settled re-run ($D_BEFORE -> $D_AFTER)"
    grep -E 'files=[1-9]' "$TMP/ingest.log" | sed 's/^/        /' | head -8; fi
else bad "main.py exited non-zero"; tail -5 "$TMP/ingest.log" | sed 's/^/        /'; fi
fi

# ─────────────────────────────────────────────────────────── GATE B: thesis
if [ $WANT_THESIS -eq 1 ]; then
hdr "GATE B — thesis verified against the data"

# B1 build
if (cd "$TESE/tex" && latexmk -pdf -interaction=nonstopmode tese.tex >"$TMP/build.log" 2>&1); then
  E=$(grep -cE '^! ' "$TMP/build.log"); U=$(grep -c 'undefined' "$TMP/build.log")
  P=$(grep -oE '\([0-9]+ pages' "$TMP/build.log" | tail -1 | tr -dc 0-9)
  if [ "${E:-1}" = "0" ] && [ "${U:-1}" = "0" ]; then ok "thesis builds: 0 errors, 0 undefined refs, ${P:-?} pages"
  else bad "build has $E errors / $U undefined refs"; fi
else bad "latexmk exited non-zero"; grep -E '^! ' "$TMP/build.log" | head -3 | sed 's/^/        /'; fi

# B2 rejected-fix audit -- these were overturned for cause and must never reappear
cd "$TESE"
declare -A MUST_BE=( ["882"]=0 ["783"]=0 )
for pat in "${!MUST_BE[@]}"; do
  n=$(grep -rho "$pat" tex/*.tex 2>/dev/null | wc -l)
  [ "$n" -eq "${MUST_BE[$pat]}" ] && ok "rejected fix absent: '$pat' ($n occurrences)" \
                                  || bad "REJECTED FIX PRESENT: '$pat' appears $n time(s)"
done
must_exist() { grep -rqF "$2" tex/*.tex 2>/dev/null && ok "intact: $1" || bad "MISSING (was rejected-for-cause): $1"; }
must_exist "tab:sim-poly-aic poly cell 67.3 / 248"  "67.3 / 248"
must_exist "twopool 'were not priced' (R26)"        "were not priced"
must_exist "live-vs-sim band 1.1--6.8% (R1)"        "1.1--6.8"
must_exist "235B ITL p99 87.7 ms (wheel-consistent)" "87.7"
N96=$(grep -rho '0[.,]96' tex/*.tex 2>/dev/null | wc -l)
[ "$N96" -ge 4 ] && ok "0.96x intact at $N96 sites (R18)" || bad "0.96x present at only $N96 sites (expected >=4)"

# B3 containment -- post-manuscript defence material must not be ADDED as a thesis result.
# Semantics matter: pre-existing limitation language legitimately mentions these concepts
# (closedloop.tex has always said real-client abandonment is unmodelled). What must never
# happen is this working tree ADDING the post-manuscript RESULT to a results chapter. So the
# test is on newly-added lines only, not on presence.
CONTAIN=0
ADDED=$(git diff HEAD -- tex/closedloop.tex tex/twopool.tex tex/baselines.tex 2>/dev/null \
        | grep -E '^\+' | grep -v '^\+\+\+')
for pat in 'limit cycle' 'mean-field' 'period-2' 'retry fraction' \
           '2\.3 (offered )?req/s' '7\.2.?x at equal GPU' '17 of 18' '0 of 6' \
           'fold-robust' 'C\^?\*?=5' '0\.980'; do
  if printf '%s' "$ADDED" | grep -Eqi "$pat"; then
    bad "post-manuscript material ADDED to a results chapter: '$pat'"; CONTAIN=1
  fi
done
[ $CONTAIN -eq 0 ] && ok "post-manuscript defence material contained (none added to results chapters)"

# B4 methodological-overclaim gate -- REPORT, don't hide (false positives OK, misses are not).
# Simulation / mocker / live-validation must never be written as real-H100-silicon execution.
# The only physically-measured pool is the RTX-5090 encoder (its "on silicon" is legitimate);
# the language pool is the discrete-event mocker on AIC timing and the live anchor runs mocked
# engines. This audit already hand-fixed one defect (closedloop "real H100 silicon" -> mocker
# control plane); B4a asserts that class can never reappear, B4b surfaces new near-misses.
cd "$TESE"
# B4a HARD -- the caught defect and its per-line siblings. Each must be 0 or the gate FAILS.
for pat in \
    'real H100 silicon' 'real H100 GPU' 'real H100s' 'on real H100' 'H100 silicon' \
    'mocker[^.]*on[^.]*silicon' 'mock(ed|er)[^.]*on real[^.]*GPU' \
    'live[- ]valid[a-z]*[^.]*on real[^.]*GPU' 'live[- ]valid[a-z]*[^.]*on silicon'; do
  hits=$(grep -rniE "$pat" tex/*.tex 2>/dev/null)
  n=$(printf '%s' "$hits" | grep -c .)
  if [ "$n" -eq 0 ]; then ok "no methodological overclaim matching /$pat/"
  else bad "METHODOLOGICAL OVERCLAIM (hard): /$pat/ -- $n line(s)"
       printf '%s\n' "$hits" | sed 's/^/        /'; fi
done
# B4b MANUAL-REVIEW WARN -- any silicon/real-GPU phrasing sitting within 3 lines of a
# language-pool / mocker / live-validation cue. Deliberately over-broad: a WARN here is an
# instruction to a human to re-read the passage, not a failure. Legitimate encoder-silicon and
# other-systems-on-real-GPU passages are expected to trip it; that is the point of a REPORT gate.
SIL='on silicon|on real [A-Za-z0-9]* ?GPU|real GPU|silicon-(validated|measured|collected|calibrated)'
CUE='mocker|mocked|language[ -]pool|live[- ]valid|live-runtime|control[- ]plane replay|discrete-event'
NEAR=0
while IFS= read -r line; do
  [ -n "$line" ] && { warn "manual-review (silicon/GPU phrase <=3 lines from a sim/mocker/live cue): $line"; NEAR=$((NEAR+1)); }
done < <(
  for f in tex/*.tex; do
    awk -v S="$SIL" -v C="$CUE" -v F="$f" '
      { L[NR]=$0 }
      END { for (i=1;i<=NR;i++) if (L[i] ~ S)
              for (j=i-3;j<=i+3;j++)
                if (j>=1 && j<=NR && L[j] ~ C) { printf "%s:%d: %s\n", F, i, substr(L[i],1,88); break } }' "$f"
  done)
[ $NEAR -eq 0 ] && ok "no silicon/real-GPU phrase within 3 lines of a sim/mocker/live cue" \
                || printf "        (%d near-miss(es) above are for human re-read, not gate failures)\n" "$NEAR"
fi

# ─────────────────────────────────────────────────────── GATE C: delivery-ready
hdr "GATE C — delivery-ready"
for f in provenance/SCHEMA_GUIDE.md provenance/audit/FINAL_STATE.md provenance/audit/ADJUDICATION.md \
         provenance/audit/DELIVERY_RULING.md progress/results-ledger.md; do
  [ -s "$TESE/$f" ] && ok "present: $f ($(wc -l < "$TESE/$f") lines)" || bad "missing or empty: $f"
done

hdr "RESULT"
printf "  %d passed, %d failed, %d warnings\n\n" "$PASS" "$FAIL" "$WARN"
[ "$FAIL" -eq 0 ] && { printf "  \033[32mDELIVERY-READY\033[0m\n\n"; exit 0; } \
                  || { printf "  \033[31mNOT DELIVERY-READY — %d gate(s) failed\033[0m\n\n" "$FAIL"; exit 1; }
