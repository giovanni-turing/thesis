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

# Password source order: env override > credentials file (post-rotation) > container env (stale after rotation)
if [ -z "${PGPASSWORD:-}" ]; then
  if [ -f "$(dirname "$0")/.goku_credentials" ]; then
    export PGPASSWORD=$(sed -n 's/.*password=//p' "$(dirname "$0")/.goku_credentials" | head -1)
  else
    export PGPASSWORD=$(docker inspect -f '{{range .Config.Env}}{{println .}}{{end}}' postgres 2>/dev/null \
                        | sed -n 's/^POSTGRES_PASSWORD=//p')
  fi
fi
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
# GUARD-PATH UPDATE 2026-07-26 (restructure gates adjudication, plan v3 §6). The old form read
# its verdict off latexmk's OWN stdout, which is wrong in both directions and was observed to be
# wrong in both directions on this tree:
#   - already-built tree: latexmk exits 0 printing "All targets are up-to-date" and writes NO
#     pages and NO warnings, so E=0/U=0/P="" and the gate printed PASS for a build it never
#     evaluated -- exactly the unevaluated-gate-printing-green failure line 11 forbids;
#   - built from a cleaned aux: the stdout accumulates EVERY pass, so pass-1's not-yet-resolved
#     \ref/\cite warnings (432 of them on the 2026-07-26 restructured tree) are counted even
#     though passes 2--3 resolve all of them -- a false FAIL on a converged document.
# tex/tese.log is the log of the FINAL pdflatex pass only, so it answers both correctly. latexmk
# still runs (its exit status is still the build verdict); only the parse target moves, and a
# missing page count is now a FAIL instead of a silent "? pages" pass. Thresholds unchanged:
# 0 errors, 0 undefined.
if (cd "$TESE/tex" && latexmk -pdf -interaction=nonstopmode tese.tex >"$TMP/build.log" 2>&1); then
  BLOG="$TESE/tex/tese.log"
  E=$(grep -cE '^! ' "$BLOG" 2>/dev/null); U=$(grep -c 'undefined' "$BLOG" 2>/dev/null)
  P=$(grep -oE '\([0-9]+ pages' "$BLOG" 2>/dev/null | tail -1 | tr -dc 0-9)
  if [ -z "${P:-}" ]; then bad "build gate NOT EVALUABLE: no page count in $BLOG"
  elif [ "${E:-1}" = "0" ] && [ "${U:-1}" = "0" ]; then ok "thesis builds: 0 errors, 0 undefined refs, ${P} pages (final pass, tex/tese.log)"
  else bad "build has $E errors / $U undefined refs (final pass)"
       grep -E "Reference \`|Citation \`" "$BLOG" | grep undefined | head -5 | sed 's/^/        /'; fi
else bad "latexmk exited non-zero"; grep -E '^! ' "$TMP/build.log" | head -3 | sed 's/^/        /'; fi

cd "$TESE"
# B0 built-chapter set -- GUARD-PATH UPDATE 2026-07-26 (restructure, plan v3 §2/§6).
# The chapter merge left tex/{aiconfigurator,twopool,validation,baselines,apendice_ecosystem}.tex
# ON DISK as frozen pre-merge sources that tese.tex no longer \include{}s. Every gate below that
# globbed tex/*.tex was therefore reading text that IS NOT IN THE THESIS, and wrong in both
# directions: must_exist could go green on a string surviving only in a dead file (false green --
# e.g. "were not priced" and "67.3 / 248" exist in BOTH metodologia.tex and the dead twopool.tex),
# and the rejected-fix / overclaim scans could go red on dead text (false red). TEXSET is derived
# from tese.tex's own \include list so it cannot go stale at the next restructure; the count
# assertion fails CLOSED if that parse ever breaks, since an empty set would make every grep
# below vacuous. No pattern and no threshold is changed -- only which files they are read from.
TEXSET=$( { echo tex/tese.tex
            grep -oE '^[[:space:]]*\\include\{[A-Za-z0-9_-]+\}' tex/tese.tex \
              | sed -E 's/.*\{([A-Za-z0-9_-]+)\}/tex\/\1.tex/'; } | sort -u )
NTEX=$(printf '%s\n' $TEXSET | grep -c .)
if [ "${NTEX:-0}" -ge 7 ]; then ok "built chapter set resolved from tese.tex: $NTEX files ($(printf '%s ' $TEXSET | sed 's|tex/||g'))"
else bad "built chapter set UNRESOLVABLE from tese.tex ($NTEX files) -- every tex gate below would be vacuous"; fi

# B2 rejected-fix audit -- these were overturned for cause and must never reappear
declare -A MUST_BE=( ["882"]=0 ["783"]=0 )
for pat in "${!MUST_BE[@]}"; do
  n=$(grep -rho "$pat" $TEXSET 2>/dev/null | wc -l)
  [ "$n" -eq "${MUST_BE[$pat]}" ] && ok "rejected fix absent: '$pat' ($n occurrences)" \
                                  || bad "REJECTED FIX PRESENT: '$pat' appears $n time(s)"
done
must_exist() { grep -rqF "$2" $TEXSET 2>/dev/null && ok "intact: $1" || bad "MISSING (was rejected-for-cause): $1"; }
must_exist "tab:sim-poly-aic poly cell 67.3 / 248"  "67.3 / 248"
must_exist "'were not priced' (R26; twopool.tex -> metodologia.tex 2026-07-26)" "were not priced"
must_exist "live-vs-sim band 1.1--6.8% (R1)"        "1.1--6.8"
must_exist "235B ITL p99 87.7 ms (s=1 head2k; artifact llm_head2k_aic235btp8_s1.json=87.72; 86.2 was a spurious revert, no artifact)" "\SI{87.7}{\milli\second}"
# ---- DERIVED-VALUE RECOMPUTATION (protocol R-A, added 2026-07-21) ----------
# Every printed headline ratio is recomputed from RAW operands (artifact files
# where they exist, provenance-commented operand pairs otherwise) and the
# printed value must be the correct rounding. Transcription-only checking is
# what let 0.96x survive four passes. See provenance/audit/REVIEW_PROTOCOL.md.
# R1 FIX 2026-07-26 (adversarial review): the encoder 0.62x check hard-coded
# rounded operands (2410800/3869300) and could not detect drift in the source
# artifacts; and neither new headline (0.76x hybrid, 0.82x language) was gated
# at all. Both encoder operands now come from the store (encoder_run_summary),
# and the hybrid/language ratios are recomputed from their artifacts below.
ENC_FC_WS=$(Q "select provisioned_worker_seconds from provenance.encoder_run_summary where run_id='aggregate44:fc_p90_L30_issuetime'")
ENC_STATIC_WS=$(Q "select provisioned_worker_seconds from provenance.encoder_run_summary where run_id='a6:static_C8'")
export ENC_FC_WS ENC_STATIC_WS
DERIVED=$(python3 - <<'PYEOF'
import json, sys
fails = []
def chk(name, val, printed, prec):
    r = round(val, prec)
    ok = abs(r - printed) < 10**(-prec) / 2
    print(("PASS " if ok else "FAIL ") + f"{name}: raw={val:.5f} -> {r} (printed {printed})")
    if not ok: fails.append(name)
# [1] language-week ratio: numerator READ FROM ARTIFACT, denom = 4 GPU x span
try:
    fc = json.load(open('simulation/results/llm_week/week_fc_p90.report.json'))['gpu_hours']
except Exception as e:
    fc = None; print(f"FAIL llm-week artifact unreadable: {e}"); fails.append('llm_week')
if fc is not None:
    span_s = 3869300.0 / 8            # static C=8 encoder ws / 8 workers
    static = 4 * span_s / 3600
    chk('0.965x language week', fc / static, 0.965, 3)
    chk('1.03x request-matched', fc / 503.7, 1.03, 2)
# [2] encoder week 0.62x -- operands READ FROM THE STORE (R1 fix 2026-07-26):
# encoder_run_summary aggregate44:fc_p90_L30_issuetime (issue-time fc) over
# a6:static_C8. Previously hard-coded 2410800/3869300; the store carries
# 2410754.7/3869278.8, so artifact drift is now detectable.
import os
enc_fc = os.environ.get('ENC_FC_WS', '')
enc_static = os.environ.get('ENC_STATIC_WS', '')
if enc_fc and enc_static:
    chk('0.62x encoder week', float(enc_fc) / float(enc_static), 0.62, 2)
else:
    print('FAIL 0.62x encoder operands unreadable from DB '
          f'(ENC_FC_WS={enc_fc!r}, ENC_STATIC_WS={enc_static!r})')
    fails.append('enc_db_operands')
# [3] full-trace reactive 0.687x (tab:cl-ledger-enc full-trace block)
chk('0.687x full trace', 3323200.0 / 4838400.0, 0.687, 3)
# [4] burst3 naive-sum error +21.9% (tab:cl-ledger-joint)
chk('21.9% naive-sum error', 100 * (26652.0 - 21868.0) / 21868.0, 21.9, 1)
# [5] live populations: counts + errors READ FROM ARTIFACTS (protocol R-B)
try:
    for run, n_exp, e_exp in [('live_fc', 3092, 1), ('live_re', 3089, 4)]:
        d = json.load(open(f'simulation/results/live51/live_runs/{run}/profile_export_aiperf.json'))
        n = d['time_to_first_token']['count']; e = d['error_summary'][0]['count']
        ok = (n == n_exp and e == e_exp and n + e == 3093)
        print(("PASS " if ok else "FAIL ") + f"{run} population: {n} tails + {e} errors = {n+e} of 3093")
        if not ok: fails.append(run)
except Exception as e:
    print(f"FAIL live artifacts unreadable: {e}"); fails.append('live')
# [6] hybrid 0.76x (R1/Finding-4 fix 2026-07-26): numerator READ FROM ARTIFACT
# (encoder_hybrid provisioned_worker_seconds), denominator the SAME store-read
# static C8 as [2] -- the encoder and hybrid headlines share one denominator.
try:
    hyb = json.load(open('simulation/results/encoder_hybrid/hybrid.jsonl.stats.json'))['provisioned_worker_seconds']
    if enc_static:
        chk('0.76x hybrid week', hyb / float(enc_static), 0.76, 2)
    else:
        print('FAIL 0.76x hybrid: static C8 denominator unreadable from DB')
        fails.append('hybrid_static')
except Exception as e:
    print(f"FAIL hybrid artifact unreadable: {e}"); fails.append('hybrid')
# [7] language 0.82x e13-robust (R1/Finding-4 fix 2026-07-26): BOTH sides read
# from the eval_p90_s6 week report -- gpu_hours over the static TP2x2 fleet
# time-scaled to the report's own span (4 GPUs x duration_ms/1000/3600 =
# 537.409 GPU-h; closedloop.tex prints 537.4). Also gates the printed 440.0.
try:
    wk = json.load(open('simulation/results/lang_qsweep/eval_p90_s6/week.report.json'))
    static_lang = 4.0 * (wk['duration_ms'] / 1000.0) / 3600.0
    chk('0.82x language e13-robust', wk['gpu_hours'] / static_lang, 0.82, 2)
    chk('440.0 GPU-h e13-robust', wk['gpu_hours'], 440.0, 1)
    chk('537.4 GPU-h static denom', static_lang, 537.4, 1)
except Exception as e:
    print(f"FAIL language week artifact unreadable: {e}"); fails.append('lang_week')
# [8] comparator frontier (plan §8.2, commit 4babe1c; gated 2026-07-26): the five
# printed arm ratios + the cheapest all-passing warm floor READ FROM the experiment
# summary, and its static reference must equal the same store-read static C8
# denominator used by [2]/[6] -- one denominator across every encoder headline.
try:
    fr = json.load(open('simulation/results/comparator_frontier/frontier_summary.json'))
    arms = fr['arms']
    chk('0.623x frontier forecast', arms['1_forecast_p90_issue_time']['vs_static'], 0.623, 3)
    chk('0.675x frontier reactive', arms['2_reactive_react_point']['vs_static'], 0.675, 3)
    chk('0.863x frontier floor M4', arms['3_reactive_plus_warm_floor_M4']['vs_static'], 0.863, 3)
    chk('0.292x frontier oracle', arms['5_perfect_future_oracle_H0']['vs_static'], 0.292, 3)
    env = fr['warm_floor_family_envelope']
    if env['cheapest_member_passing_all_episodes'] != 'warm_floor_M6':
        print('FAIL frontier cheapest all-passing floor is no longer M6'); fails.append('frontier_m6')
    m6 = env['members']['warm_floor_M6']
    chk('1.042x cheapest all-passing floor', m6['cost_worker_s_eval_span'] / fr['static_reference_worker_s'], 1.042, 3)
    if m6['episodes_failed'] != 0:
        print('FAIL frontier M6 no longer passes all episodes'); fails.append('frontier_m6_pass')
    if enc_static and abs(fr['static_reference_worker_s'] - float(enc_static)) > 0.5:
        print(f"FAIL frontier static reference {fr['static_reference_worker_s']} != store static C8 {enc_static}")
        fails.append('frontier_static')
    else:
        print('PASS frontier static reference == store-read static C8 denominator')
except Exception as e:
    print(f"FAIL frontier summary unreadable: {e}"); fails.append('frontier')
sys.exit(1 if fails else 0)
PYEOF
)
DERIVED_RC=$?
while IFS= read -r line; do
  case "$line" in PASS*) ok "derived: ${line#PASS }";; FAIL*) bad "derived: ${line#FAIL }";; esac
done <<< "$DERIVED"
# D12 FIX (reviewer 2026-07-26): an evaluator abort must never pass silently.
# If the embedded Python exited nonzero without emitting a formatted FAIL line
# (unexpected exception path), or emitted nothing at all, this gate is
# UNEVALUATED and per the design rule (line 11-13) that is a failure.
if [ "$DERIVED_RC" -ne 0 ] && ! printf '%s' "$DERIVED" | grep -q '^FAIL'; then
  bad "derived-value evaluator aborted (rc=$DERIVED_RC) without a formatted FAIL -- gate unevaluated"
fi
[ -z "$DERIVED" ] && bad "derived-value evaluator produced no output -- gate unevaluated"
# D12 FIX part 2: raw frontier recomputation, not summary-reading. The
# independent builder recomputes all 169 evaluation cells from the emitted
# schedules and replay stats (not from frontier_summary.json) and cross-checks
# each cell's stats agreement; any mismatch or nonzero exit fails the gate.
FR_LOG=$("$TESE/eda/.venv/bin/python"   "$TESE/simulation/results/comparator_frontier/build_frontier_summary.py"   --jobs 8 2>&1 >/dev/null); FR_RC=$?
# D20 (2026-07-26): the builder now fails on missing stats, recomputes the
# calibration selection against FROZEN.json, and cross-links the raw cells to
# frontier_summary.json. The gate pins the EXACT expected signature -- a
# shortened inventory, absent evidence, selection drift, or a summary/cells
# divergence all break the pinned line. Cell count 313 = 25 core + 90 family
# + 48 adversarial + 128 calib floor + 16 calib oracle + 5 eval-window
# variants + 1 path-identity check; adjudicate any legitimate inventory
# change here with a dated comment.
FR_WANT='cells=313  stats-missing=0  stats-mismatches=0  calib-selection=OK  summary-link=OK'
if [ $FR_RC -eq 0 ] && printf '%s' "$FR_LOG" | grep -qF "$FR_WANT"; then
  ok "frontier raw recompute: 313 cells (incl. calib grid), selection + summary-link verified"
else
  bad "frontier raw recompute FAILED (rc=$FR_RC): $(printf '%s' "$FR_LOG" | grep 'cells=' | tail -1)"
fi
# verb-convention regression (protocol R-C)
BILLMISUSE=$(grep -rcE "billed at (forecast-)?issue" $TEXSET | grep -v ':0' | wc -l)
[ "$BILLMISUSE" -eq 0 ] && ok "no billing-verb misuse (billed-at-issue: 0; R-C)" || bad "billing-verb misuse present (R-C)"

# R18 AMENDED 2026-07-21: raw operands 518.6063/537.4029 = 0.96502 -> printed
# ratio corrected 0.96x -> 0.965x at all sites (reviewer-caught mis-rounding;
# 2-dp rounding of 0.965 would be 0.97, so the 3-dp form with operands is used).
# FLOOR LOWERED 4->2 2026-07-26: the convergence de-hedge consolidated cost framing
# into canonical closedloop loci, intentionally removing 2 of the 4 mentions
# (certified by the R5 cost-framing consistency gate across all 10 loci).
N96=$(grep -rho '0[.,]965' $TEXSET 2>/dev/null | wc -l)
[ "$N96" -ge 2 ] && ok "0.965x intact at $N96 sites (R18-amended)" || bad "0.965x present at only $N96 sites (expected >=2)"
# PATTERN NARROWED 2026-07-26 (finalize pass): the review-F10 repair inserted the
# legitimate p90/s6 fold-ratio list "(0.96, 0.69, ...)" (91.9538/95.795 = 0.9599 -> 0.96),
# which the old bare '0[.,]96[^5]' pattern false-flagged. The forbidden stale form was the
# week ratio printed AS A x-RATIO (0.96$\times$ / 0.96x); match exactly that.
N96OLD=$(grep -rhoE '0[.,]96(\$?\\times|x)' $TEXSET 2>/dev/null | wc -l)
[ "$N96OLD" -eq 0 ] && ok "no stale 0.96x remains (all amended to 0.965x)" || bad "stale 0.96x still present at $N96OLD site(s)"

# B3 containment -- post-manuscript defence material must not be ADDED as a thesis result.
# Semantics matter: pre-existing limitation language legitimately mentions these concepts
# (closedloop.tex has always said real-client abandonment is unmodelled). What must never
# happen is this working tree ADDING the post-manuscript RESULT to a results chapter. So the
# test is on newly-added lines only, not on presence.
CONTAIN=0
# R1 FIX 2026-07-26 (adversarial review): the old pipeline's second stage was BASIC-regex
# grep -v '^\+\+\+', where \+ is a repetition operator -- it matched EVERY added line and
# silently emptied $ADDED, making this gate false-green. Structural awk parse instead:
# drop the '+++' file header by prefix, keep '+' hunk lines (incl. '++x'), strip the '+'.
_added_lines() { awk '/^\+\+\+ /{next} /^\+/{print substr($0,2)}'; }
# parser regression fixture -- header excluded, added lines kept, leading '+' preserved
_FIXWANT='kept line
+kept plusline'
_FIXGOT=$(printf '+++ b/tex/x.tex\n+kept line\n++kept plusline\n-removed\n context\n' | _added_lines)
[ "$_FIXGOT" = "$_FIXWANT" ] || bad "containment-gate parser self-test FAILED (regression)"
# GUARD-PATH UPDATE 2026-07-26 (restructure, plan v3 §2/§6): the watched file list is re-pointed
# at the CURRENT results/methodology chapters. twopool.tex and baselines.tex were merged away
# (-> metodologia.tex and closedloop.tex) and are now frozen, un-\include{}d pre-merge sources:
# diffing them watches nothing, while the chapters that actually carry results (trace-eda.tex,
# predictors.tex, and the new metodologia.tex) were unwatched. metodologia.tex is untracked at
# HEAD, so `git diff HEAD --` emits nothing for it; it is diffed against /dev/null instead, i.e.
# EVERY line counts as added -- the strictest possible reading, and it currently yields zero hits
# on all ten patterns. No forbidden pattern is dropped and no value assertion is touched.
CONTAIN_FILES="tex/closedloop.tex tex/trace-eda.tex tex/predictors.tex tex/metodologia.tex"
_chapter_diff() {
  for f in $CONTAIN_FILES; do
    [ -f "$f" ] || continue
    if git ls-files --error-unmatch "$f" >/dev/null 2>&1; then git diff HEAD -- "$f"
    else git diff --no-index -- /dev/null "$f"; fi
  done
}
ADDED=$(_chapter_diff 2>/dev/null | _added_lines)
# ADJUDICATED 2026-07-26: 'fold-robust' removed from the forbidden list -- the hybrid /
# fold-robust result was deliberately promoted into closedloop.tex by the author-approved
# reframe (ledger "Iterative fix+review convergence" entry); its addition is intended.
for pat in 'limit cycle' 'mean-field' 'period-2' 'retry fraction' \
           '2\.3 (offered )?req/s' '7\.2.?x at equal GPU' '17 of 18' '0 of 6' \
           'C\^?\*?=5' '0\.980'; do
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
# Scope moved tex/*.tex -> $TEXSET 2026-07-26 (see B0): the frozen pre-merge sources are not in
# the thesis, so an overclaim surviving there is not a thesis overclaim (and would be a false red).
for pat in \
    'real H100 silicon' 'real H100 GPU' 'real H100s' 'on real H100' 'H100 silicon' \
    'mocker[^.]*on[^.]*silicon' 'mock(ed|er)[^.]*on real[^.]*GPU' \
    'live[- ]valid[a-z]*[^.]*on real[^.]*GPU' 'live[- ]valid[a-z]*[^.]*on silicon'; do
  hits=$(grep -rniE "$pat" $TEXSET 2>/dev/null)
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
  for f in $TEXSET; do
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
