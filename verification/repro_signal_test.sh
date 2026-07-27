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
probe tools HUP 129
probe worktree INT 130
probe worktree TERM 143

# D57 negative probes: publication failure and directory destination must be
# fatal UP FRONT, leave zero residue, and never false-advertise a report.
scratch=$(mktemp -d) || exit 1
if out=$(REPRO_SCRATCH=$scratch REPRO_REPORT=$scratch/no/such/parent/r.md "$RUNNER" 2>&1); then
  bad "publication-failure probe: runner succeeded (rc=0)"
else
  if echo "$out" | grep -q "^FATAL: report parent" && ! echo "$out" | grep -q "^report:" \
     && [ "$(find "$scratch" -maxdepth 1 -name 'repro881*' | wc -l)" -eq 0 ]; then
    ok "publication-failure: fatal up front, no report advertised, zero residue"
  else
    bad "publication-failure: wrong failure shape"; echo "$out" | head -3
  fi
fi
rm -rf "$scratch"
scratch=$(mktemp -d) || exit 1
mkdir "$scratch/destdir"
if out=$(REPRO_SCRATCH=$scratch REPRO_REPORT=$scratch/destdir "$RUNNER" 2>&1); then
  bad "dir-destination probe: runner succeeded (rc=0)"
else
  if echo "$out" | grep -q "^FATAL: report destination is a directory" \
     && [ -d "$scratch/destdir" ] && [ -z "$(ls -A "$scratch/destdir")" ]; then
    ok "dir-destination: rejected, directory untouched and empty"
  else
    bad "dir-destination: wrong failure shape"; echo "$out" | head -3
  fi
fi
rm -rf "$scratch"

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

# D57 round 2: symlink destination (incl dangling) rejected with lstat
# semantics; planted temp-name symlinks cannot divert publication; a mid-run
# publication failure leaves existing explicit content byte-identical.
scratch=$(mktemp -d) || exit 1
echo "VICTIM" > "$scratch/victim"
ln -s "$scratch/victim" "$scratch/link.md"
if out=$(REPRO_SCRATCH=$scratch REPRO_REPORT=$scratch/link.md "$RUNNER" 2>&1); then
  bad "symlink-destination probe: runner succeeded"
else
  if echo "$out" | grep -q "^FATAL: report destination is a symlink" \
     && [ "$(cat "$scratch/victim")" = "VICTIM" ]; then
    ok "symlink-destination: rejected up front (lstat), victim untouched"
  else
    bad "symlink-destination: wrong failure shape"; echo "$out" | head -2
  fi
fi
ln -s "$scratch/nowhere" "$scratch/dangling.md"
if out=$(REPRO_SCRATCH=$scratch REPRO_REPORT=$scratch/dangling.md "$RUNNER" 2>&1); then
  bad "dangling-symlink probe: runner succeeded"
else
  if echo "$out" | grep -q "^FATAL: report destination is a symlink"; then
    ok "dangling-symlink destination: rejected up front (lstat)"
  else
    bad "dangling-symlink: wrong failure shape"; echo "$out" | head -2
  fi
fi
rm -rf "$scratch"

# temp-collision flood: pre-plant symlinks under the publication temp prefix;
# the exclusive random mktemp temp must dodge them all, publish successfully,
# and never write through any planted link.
scratch=$(mktemp -d) || exit 1
echo "VICTIM2" > "$scratch/victim2"
for i in 1 2 3 4 5 6 7 8; do ln -s "$scratch/victim2" "$scratch/.repro881_pub.plant$i"; done
if out=$(REPRO_SCRATCH=$scratch REPRO_REPORT=$scratch/r.md "$RUNNER" 2>&1); then
  if [ -f "$scratch/r.md" ] && [ ! -L "$scratch/r.md" ] \
     && [ "$(cat "$scratch/victim2")" = "VICTIM2" ]; then
    ok "temp-collision flood: exclusive temp dodged planted links, report regular, victim untouched"
  else
    bad "temp-collision flood: report/victim state wrong"
  fi
else
  bad "temp-collision flood: runner failed"; echo "$out" | tail -2
fi
rm -rf "$scratch"

# mid-run publication failure: destination parent made unwritable AFTER the
# upfront validation (readiness marker), existing explicit content must
# survive byte-identical and the failure must be fatal with no advertisement.
scratch=$(mktemp -d) || exit 1
mkdir "$scratch/ro"
echo "PRIOR CONTENT" > "$scratch/ro/r.md"
marker=$scratch/ready.marker
REPRO_SCRATCH=$scratch REPRO_PAUSE_AT=tools REPRO_PAUSE_MARKER=$marker \
  REPRO_REPORT=$scratch/ro/r.md "$RUNNER" >"$scratch/out.log" 2>&1 &
pid=$!
waited=0
until [ -e "$marker" ]; do
  sleep 0.1; waited=$((waited + 1))
  [ "$waited" -gt 1200 ] && { bad "mid-run-pubfail: marker never appeared"; kill -9 "$pid"; break; }
done
chmod 500 "$scratch/ro"
wait "$pid"; rc=$?
chmod 700 "$scratch/ro"
if [ "$rc" -ne 0 ] && grep -q "^FATAL:" "$scratch/out.log" \
   && ! grep -q "^report:" "$scratch/out.log" \
   && [ "$(cat "$scratch/ro/r.md")" = "PRIOR CONTENT" ] \
   && [ "$(find "$scratch/ro" -name '.repro881_pub.*' | wc -l)" -eq 0 ]; then
  ok "mid-run publication failure: fatal, nothing advertised, prior content byte-identical, no temp residue"
else
  bad "mid-run-pubfail: rc=$rc"; tail -2 "$scratch/out.log"
fi
rm -rf "$scratch"

# D58 deterministic post-create replacement probe: swap the publication temp
# DURING the publisher's pause window (after exclusive creation + write,
# before the inode-bind check). The bind must fail, the prior explicit
# report must stay byte-identical, and the foreign object at the temp path
# must be left alone.
scratch=$(mktemp -d) || exit 1
echo "PRIOR58" > "$scratch/r.md"
echo "SAFE-VICTIM58" > "$scratch/victim58"
marker=$scratch/pub.marker
REPRO_SCRATCH=$scratch REPRO_PUB_PAUSE_MARKER=$marker \
  REPRO_REPORT=$scratch/r.md "$RUNNER" >"$scratch/out.log" 2>&1 &
pid=$!
waited=0
until [ -e "$marker" ]; do
  sleep 0.1; waited=$((waited + 1))
  [ "$waited" -gt 6000 ] && { bad "D58-swap: publisher pause marker never appeared"; kill -9 "$pid" 2>/dev/null; break; }
done
tmp=$(find "$scratch" -maxdepth 1 -name '.repro881_pub.*' ! -name '*.moved' | head -1)
if [ -n "$tmp" ]; then
  mv "$tmp" "$tmp.moved" && ln -s "$scratch/victim58" "$tmp"
fi
wait "$pid"; rc=$?
if [ "$rc" -ne 0 ] && grep -q "no longer names the exclusively" "$scratch/out.log" \
   && ! grep -q "^report:" "$scratch/out.log" \
   && [ "$(cat "$scratch/r.md")" = "PRIOR58" ] \
   && [ "$(cat "$scratch/victim58")" = "SAFE-VICTIM58" ] \
   && [ -L "$tmp" ]; then
  ok "D58 post-create swap: bind check failed publication, prior report byte-identical, victim and foreign object untouched"
else
  bad "D58 post-create swap: rc=$rc"; tail -3 "$scratch/out.log"
fi
rm -rf "$scratch"

# D58 round 2: helper unit selftest (short-write dribble, zero-progress) and
# a publication-phase PROCESS-GROUP TERM -- the helper's signal unwind must
# clean its own temp; nothing advertised, zero residue of any kind.
if python3 "$SELF/repro_publish.py" --selftest | grep -q "ALL PASS"; then
  ok "publisher selftest (write_all dribble + zero-progress + roundtrip)"
else
  bad "publisher selftest failed"
fi
scratch=$(mktemp -d) || exit 1
marker=$scratch/pub.marker
REPRO_SCRATCH=$scratch REPRO_PUB_PAUSE_MARKER=$marker "$RUNNER" >"$scratch/out.log" 2>&1 &
pid=$!
waited=0
until [ -e "$marker" ]; do
  sleep 0.1; waited=$((waited + 1))
  [ "$waited" -gt 6000 ] && { bad "pgroup-TERM: publisher pause marker never appeared"; kill -9 "$pid" 2>/dev/null; break; }
done
kill -TERM -- "-$pid" 2>/dev/null || kill -TERM "$pid"
wait "$pid"; rc=$?
temps=$(find "$scratch" -maxdepth 1 -name '.repro881_pub.*' | wc -l)
dirs=$(find "$scratch" -maxdepth 1 -type d -name 'repro881.*' | wc -l)
reports=$(find "$scratch" -maxdepth 1 -type f -name 'repro881_report.*' | wc -l)
if [ "$rc" -eq 143 ] && ! grep -q "^report:" "$scratch/out.log" \
   && [ "$temps" -eq 0 ] && [ "$dirs" -eq 0 ] && [ "$reports" -eq 0 ]; then
  ok "publication-phase pgroup TERM: exit 143, nothing advertised, zero temp/run/report residue"
else
  bad "pgroup-TERM: rc=$rc temps=$temps dirs=$dirs reports=$reports"
fi
rm -rf "$scratch"

echo "SIGNAL-TEST: $pass passed, $fail failed"
[ "$fail" -eq 0 ]
