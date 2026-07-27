#!/bin/bash
# §8.8-1 independent reproduction test (shortening plan v3): three headline
# results reproduced from a CLEAN CHECKOUT (detached git worktree at HEAD),
# following only the appendix quickstart's script->artifact rows.
#
#   Target 1  comparator frontier (§8.2): full 313-cell recomputation from the
#             tracked raw run outputs, self-verified against the tracked
#             frontier_summary.json (stats/calib-selection/calib-table/link).
#   Target 2  composed nine-cell join, Stage A -- TRACKED FILES ONLY: records
#             honestly which cells are reproducible without the supplementary
#             archive (3/9 cells read 1.8 GB of archive-listed replay outputs).
#   Target 3  composed nine-cell join, Stage B -- the four replay-input files
#             inflated from their TRACKED .zst archives inside the checkout
#             (zstd -d, no live-tree or external dependency): full regeneration
#             must be BYTE-IDENTICAL to the committed artifact.
#
# Read-only on the live tree (the worktree and scratch live under BASE).
# Emits verification/repro_clean_checkout_report.md.
set -u
TESE=/home/gio/tese
EDA_PY=$TESE/eda/.venv/bin/python
BASE=/home/gio/.cache/tese_repro
W=$BASE/checkout
REPORT=$TESE/verification/repro_clean_checkout_report.md
SUPP_INPUTS=(
  defense/anim/data/a2_runs/steady24h_forecast_L30.jsonl
  defense/anim/data/a2_runs/steady24h_reactive_L30.jsonl
  defense/anim/data/a13_runs/ft_static_C8.jsonl
  defense/anim/data/a13_runs/ft_llm_static.requests.jsonl
  defense/anim/data/a13_runs/ft_reactive_L30.jsonl
  defense/anim/data/a13_runs/ft_llm_reactive.requests.jsonl
)

mkdir -p "$BASE"
pass=0; fail=0
R=""
say() { echo "$1"; R+="$1"$'\n'; }
ok()  { pass=$((pass+1)); say "PASS  $1"; }
bad() { fail=$((fail+1)); say "FAIL  $1"; }

HEAD_SHA=$(git -C "$TESE" rev-parse HEAD)
say "# Clean-checkout reproduction test (§8.8-1)"
say ""
say "HEAD: $HEAD_SHA  ($(date -u +%Y-%m-%dT%H:%M:%SZ))"
say ""

# ---- fresh detached worktree ----
git -C "$TESE" worktree remove --force "$W" 2>/dev/null
rm -rf "$W"
if git -C "$TESE" worktree add --detach "$W" HEAD >/dev/null 2>&1 \
   && [ "$(git -C "$W" status --porcelain | wc -l)" -eq 0 ]; then
  ok "clean detached worktree at HEAD ($W)"
else
  bad "worktree creation not clean"; echo "$R" > "$REPORT"; exit 1
fi

# ---- Target 1: frontier 313-cell recomputation (tracked-only) ----
say ""
say "## Target 1 — comparator frontier (tracked files only)"
FR="$W/simulation/results/comparator_frontier"
(cd "$FR" && TESE_ROOT="$W" "$EDA_PY" build_frontier_summary.py --jobs 8 \
   >"$BASE/frontier_build.log" 2>&1)
rc=$?
VERDICT=$(grep -E "^cells=" "$BASE/frontier_build.log" | tail -1)
say "verdict: ${VERDICT:-<none>}  rc=$rc"
if [ $rc -eq 0 ] && echo "$VERDICT" | grep -q "stats-missing=0" \
   && echo "$VERDICT" | grep -q "stats-mismatches=0" \
   && echo "$VERDICT" | grep -q "calib-selection=OK" \
   && echo "$VERDICT" | grep -q "calib-table=OK" \
   && echo "$VERDICT" | grep -q "summary-link=OK"; then
  ok "frontier: 313 cells recomputed from raw tracked outputs; committed summary independently confirmed"
else
  bad "frontier recomputation/self-verification (see $BASE/frontier_build.log)"
fi
HL=$("$EDA_PY" - "$FR" <<'PYEOF'
import json, sys
fr = sys.argv[1]
s = json.load(open(f"{fr}/frontier_summary.json"))
fc = s["arms"]["1_forecast_p90_issue_time"]
cells = json.load(open(f"{fr}/frontier_summary_cells.json"))
core = [c for c in cells if c["group"] == "core" and c["arm"] == "forecast_p90"]
viol = sum(int(c["violations_1000ms"]) for c in core)
ws = fc["cost_worker_s_eval_span"]
print(f"forecast arm: vs_static={fc['vs_static']} (manuscript 0.623x)  "
      f"eval-span worker_s={ws:.0f}  "
      f"violations summed over ALL {len(core)} core windows={viol} (scope-labeled, no manuscript claim)")
PYEOF
)
say "headline: $HL"

# ---- Target 2: composed join, Stage A (tracked-only, honest gap record) ----
# NOTE the join catches per-cell exceptions and exits 0 with {"error": ...}
# cells, and it PRELOADS an existing --out -- so the verdict must come from a
# fresh output's per-cell CONTENT, never from the exit code.
say ""
say "## Target 2 — composed nine-cell join, Stage A (tracked files only)"
rm -f "$BASE/composed_A.json"
TESE_ROOT="$W" "$EDA_PY" "$W/simulation/composed_fill_join.py" \
  --out "$BASE/composed_A.json" >"$BASE/composed_A.log" 2>&1
MISSING=0
for f in "${SUPP_INPUTS[@]}"; do [ -e "$W/$f" ] || MISSING=$((MISSING+1)); done
AVERDICT=$("$EDA_PY" - "$BASE/composed_A.json" \
    "$W/simulation/results/composed_fill/composed_fill_joined.json" "$W" <<'PYEOF'
import json, sys
got = json.load(open(sys.argv[1]))
committed = json.load(open(sys.argv[2]))
wroot = sys.argv[3]
SUPP_CELLS = {"steady24h_fc_chronos", "steady24h_reactive",
              "fulltrace_static_C8", "fulltrace_reactive"}
ok_cells = {c for c, v in got.items() if "error" not in v}
err_cells = set(got) - ok_cells
proper_errors = all(
    got[c]["error"].startswith("FileNotFoundError") and wroot in got[c]["error"]
    for c in err_cells)
match = all(got[c] == committed[c] for c in ok_cells)
verdict = (set(got) == set(committed) and ok_cells == set(committed) - SUPP_CELLS
           and err_cells == SUPP_CELLS and proper_errors and match)
print(f"{'OK' if verdict else 'BAD'} tracked_ok={len(ok_cells)}/9 "
      f"supp_dependent={len(err_cells)}/9 errors_are_missing_checkout_files={proper_errors} "
      f"tracked_cells_equal_committed={match}")
PYEOF
)
say "supplementary inputs absent from checkout: $MISSING/6; $AVERDICT"
if [ "$MISSING" -eq 6 ] && echo "$AVERDICT" | grep -q "^OK"; then
  ok "stage A boundary exact: 5/9 cells reproduced from plain tracked files (values equal the committed artifact); 4/9 (steady24h fc/reactive + fulltrace pair) fail ONLY on inputs that ship as tracked .zst archives (Stage B inflates them)"
else
  bad "stage A boundary not as documented (see $BASE/composed_A.log)"
fi

# ---- Target 3: composed join, Stage B (inflate tracked .zst in-checkout) ----
say ""
say "## Target 3 — composed nine-cell join, Stage B (tracked .zst inflated)"
for f in "${SUPP_INPUTS[@]}"; do
  if [ -e "$W/$f.zst" ]; then
    zstd -d -q -f "$W/$f.zst" -o "$W/$f" || bad "inflating $f.zst"
  else
    bad "tracked archive missing in checkout: $f.zst"
  fi
done
rm -f "$BASE/composed_B.json"
TESE_ROOT="$W" "$EDA_PY" "$W/simulation/composed_fill_join.py" \
  --out "$BASE/composed_B.json" >"$BASE/composed_B.log" 2>&1
rcB=$?
if [ $rcB -eq 0 ] && cmp -s "$BASE/composed_B.json" \
     "$W/simulation/results/composed_fill/composed_fill_joined.json"; then
  ok "stage B: nine-cell artifact regenerated BYTE-IDENTICAL to the committed object"
else
  bad "stage B regeneration or byte-identity (rc=$rcB, see $BASE/composed_B.log)"
fi
if [ $rcB -eq 0 ]; then
  HL2=$("$EDA_PY" - "$BASE/composed_B.json" <<'PYEOF'
import json, sys
d = json.load(open(sys.argv[1]))
c = d["steady24h_fc_chronos"]
r = d["steady24h_reactive"]
print(f"steady24h forecast e2e_p99={c['e2e_p99']}  reactive e2e_p99={r['e2e_p99']}  "
      f"forecast gpu_h={c['gpu_h']:.2f}")
PYEOF
)
  say "headline: $HL2"
fi

# ---- wrap up ----
say ""
say "## Result"
say ""
say "$pass passed, $fail failed"
git -C "$TESE" worktree remove --force "$W" 2>/dev/null
printf '%s' "$R" > "$REPORT"
echo "report: $REPORT"
[ $fail -eq 0 ]
