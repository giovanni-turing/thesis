#!/bin/bash
# D54 integration test: INT/TERM against the REAL runner at the
# command-substitution ("tools") and worktree phases, via the runner's
# deterministic REPRO_PAUSE_AT hook. Requires exit 130/143, no continued
# stages, no report advertised, complete owned cleanup (no repro881.* run
# directories, no leftover registered worktree).
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
  local scratch out rc
  scratch=$(mktemp -d) || exit 1
  out=$scratch/stdout.log
  REPRO_SCRATCH=$scratch REPRO_PAUSE_AT=$phase "$RUNNER" >"$out" 2>&1 &
  local pid=$!
  sleep 1.5
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
  local leftover
  leftover=$(find "$scratch" -maxdepth 1 -type d -name 'repro881.*' | wc -l)
  if [ "$leftover" -eq 0 ]; then
    ok "$phase/$sig owned run directory cleaned"
  else
    bad "$phase/$sig $leftover run director(ies) left"
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

echo "SIGNAL-TEST: $pass passed, $fail failed"
[ "$fail" -eq 0 ]
