#!/bin/bash
# D54 integration test: INT/TERM against the REAL runner INSIDE the named
# active contexts, synchronized by a readiness marker (no fixed-delay guess):
#   tools    -- the runner touches the marker from INSIDE an active command
#               substitution, then pauses there;
#   worktree -- the marker is touched with the worktree REGISTERED
#               (git worktree list shows it), then pauses.
# Requires exit 130/143, no continued stages, no report advertised, ZERO
# report-file residue (the owned default placeholder must be removed on
# signal), complete owned run-dir cleanup, and no leftover registered
# worktree.
set -u
# Job control ON: without it, POSIX shells start async children with SIGINT
# IGNORED (untrappable by the child), which would test the caller's spawning
# semantics rather than the runner's handler. Interactive Ctrl-C corresponds
# to the job-control case exercised here.
set -m
SELF=$(cd "$(dirname "$0")" && pwd)
RUNNER=$SELF/repro_clean_checkout.sh
TESE=$(cd "$SELF/.." && pwd)
pass=0; fail=0
ok()  { pass=$((pass+1)); echo "PASS: $1"; }
bad() { fail=$((fail+1)); echo "FAIL: $1"; }

probe() { # phase, signal, expected-rc
  local phase=$1 sig=$2 want=$3
  local scratch out marker rc waited
  scratch=$(mktemp -d) || exit 1
  out=$scratch/stdout.log
  marker=$scratch/ready.marker
  REPRO_SCRATCH=$scratch REPRO_PAUSE_AT=$phase REPRO_PAUSE_MARKER=$marker \
    "$RUNNER" >"$out" 2>&1 &
  local pid=$!
  waited=0
  until [ -e "$marker" ]; do
    sleep 0.1
    waited=$((waited + 1))
    # the worktree phase first materializes a multi-GB checkout; allow 120 s
    if [ "$waited" -gt 1200 ]; then bad "$phase/$sig readiness marker never appeared"; kill -9 "$pid" 2>/dev/null; rm -rf "$scratch"; return; fi
  done
  if [ "$phase" = worktree ]; then
    if git -C "$TESE" worktree list | grep -q "$scratch"; then
      ok "$phase/$sig signal delivered with the worktree REGISTERED"
    else
      bad "$phase/$sig no registered worktree at signal time"
    fi
  fi
  kill "-$sig" "$pid"
  wait "$pid"; rc=$?
  if [ "$rc" -eq "$want" ]; then
    ok "$phase/$sig exit=$rc"
  else
    bad "$phase/$sig exit=$rc (wanted $want)"
  fi
  if grep -qE "^report:|HEADLINES|^PASS  frontier" "$out"; then
    bad "$phase/$sig continued/published after signal:"; sed 's/^/    /' "$out" | tail -3
  else
    ok "$phase/$sig no continued stages, no report advertised"
  fi
  local dirs reports
  dirs=$(find "$scratch" -maxdepth 1 -type d -name 'repro881.*' | wc -l)
  reports=$(find "$scratch" -maxdepth 1 -type f -name 'repro881_report.*' | wc -l)
  if [ "$dirs" -eq 0 ] && [ "$reports" -eq 0 ]; then
    ok "$phase/$sig zero residue (run dirs=0, report files=0)"
  else
    bad "$phase/$sig residue: run_dirs=$dirs report_files=$reports"
  fi
  if git -C "$TESE" worktree list | grep -q "$scratch"; then
    bad "$phase/$sig worktree still registered"
  else
    ok "$phase/$sig no leftover registered worktree"
  fi
  rm -rf "$scratch"
}

probe tools INT 130
probe tools TERM 143
probe worktree INT 130
probe worktree TERM 143

# Control: a successful default run's report SURVIVES (placeholder promoted
# by publication), while its run directory is still cleaned.
scratch=$(mktemp -d) || exit 1
if out=$(REPRO_SCRATCH=$scratch "$RUNNER" 2>&1); then
  rep=$(printf '%s' "$out" | sed -n 's/^report: //p')
  if [ -s "$rep" ] && [ "$(find "$scratch" -maxdepth 1 -type d -name 'repro881.*' | wc -l)" -eq 0 ]; then
    ok "control: successful default run's report survives cleanup ($(wc -c < "$rep") bytes)"
  else
    bad "control: report missing or run dir left after successful default run"
  fi
else
  bad "control: default run failed"
fi
rm -rf "$scratch"

echo "SIGNAL-TEST: $pass passed, $fail failed"
[ "$fail" -eq 0 ]
