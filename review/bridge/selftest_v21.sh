#!/bin/bash
# D43 v2.1 negative tests: each probe is injected into a COPY of the bridge
# corpus; the real corpus is never touched.
set -u
SRC=/home/gio/tese/review/bridge
W=$(mktemp -d)
trap 'rm -rf "$W"' EXIT
cp -r "$SRC"/to_reviewer "$SRC"/from_reviewer "$SRC"/archive "$W"/
cp "$SRC"/validate.py "$W"/
cd "$W"

pass=0; fail=0
probe() { # name, expected-grep, probe-file-content(stdin)
  local name="$1" expect="$2" file="$3"
  cat > "$file"
  out=$(python3 validate.py 2>&1)
  rm -f "$file"
  if echo "$out" | grep -qE "$expect"; then
    echo "PASS: $name"; pass=$((pass+1))
  else
    echo "FAIL: $name -- wanted /$expect/, got:"; echo "$out" | grep ERROR | head -5; fail=$((fail+1))
  fi
}

# next CLAUDE sequence number (probe carries from: claude -- must extend claude's own sequence)
N=$(grep -l "^from: claude$" to_reviewer/*.md archive/*.md 2>/dev/null | xargs -n1 basename | grep -oE '^[0-9]{3}' | sort -n | tail -1)
NX=$(printf "%03d" $((10#$N + 1)))

# R1a: empty-component headers must violate the whole-value grammar
probe "R1-semicolon-only" "whole-value grammar" "to_reviewer/${NX}_probe.md" <<EOF
---
from: claude
ts: 2026-07-27T04:00:00-03:00
re: new
type: ack
authority: author-delegated:fable-5-2026-07-27-xhigh
rulings: ;
---
probe
EOF

# R1b: doubled semicolon between valid pairs
probe "R1-doubled-semicolon" "whole-value grammar" "to_reviewer/${NX}_probe.md" <<EOF
---
from: claude
ts: 2026-07-27T04:00:00-03:00
re: new
type: ack
authority: author-delegated:fable-5-2026-07-27-xhigh
rulings: D43-v183-unicode-raw-html=CLOSED-FIXED;;D44-k16-preflight-placement=CLOSED-FIXED
---
probe
EOF

# R1c: trailing semicolon
probe "R1-trailing-semicolon" "whole-value grammar" "to_reviewer/${NX}_probe.md" <<EOF
---
from: claude
ts: 2026-07-27T04:00:00-03:00
re: new
type: ack
authority: author-delegated:fable-5-2026-07-27-xhigh
rulings: D43-v183-unicode-raw-html=CLOSED-FIXED;
---
probe
EOF

# R2a: legacy RULING line in a message WITH a rulings header -> deprecated
probe "R2-legacy-body-with-header" "deprecated" "to_reviewer/${NX}_probe.md" <<EOF
---
from: claude
ts: 2026-07-27T04:00:00-03:00
re: new
type: ack
authority: author-delegated:fable-5-2026-07-27-xhigh
rulings: D43-v183-unicode-raw-html=CLOSED-FIXED
---
RULING D99-anything: CLOSED-FIXED
EOF

# R2b: legacy AUTHOR ADJUDICATION heading without header -> deprecated (no Markdown-model errors)
probe "R2-legacy-heading-no-header" "deprecated" "to_reviewer/${NX}_probe.md" <<EOF
---
from: claude
ts: 2026-07-27T04:00:00-03:00
re: new
type: ack
---
## AUTHOR ADJUDICATION
prose only
EOF

# R2c: prose lookalike must NOT error (narrow lint)
probe_ok() {
  local name="$1" file="$2"
  cat > "$file"
  out=$(python3 validate.py 2>&1)
  rm -f "$file"
  if echo "$out" | grep -q "errors=0"; then
    echo "PASS: $name"; pass=$((pass+1))
  else
    echo "FAIL: $name -- expected clean, got:"; echo "$out" | grep ERROR | head -5; fail=$((fail+1))
  fi
}
probe_ok "R2-prose-lookalike-clean" "to_reviewer/${NX}_probe.md" <<EOF
---
from: claude
ts: 2026-07-27T04:00:00-03:00
re: new
type: ack
---
The ruling D43-v183-unicode-raw-html discussion mentions RULING_RE and the
author adjudication process in prose, which is inert.
EOF

# R4: map probe -- add a never-escalated thread to pinned 059's rulings map
# (patches a validate.py copy instead of adding a message file)
python3 - <<'PYEOF'
import re
s = open("validate.py").read()
s = s.replace('{"D41-v182-commonmark-live-lines":"CLOSED-FIXED"}',
              '{"D41-v182-commonmark-live-lines":"CLOSED-FIXED","D43-v183-unicode-raw-html":"CLOSED-FIXED"}')
open("validate_probe.py","w").write(s)
PYEOF
out=$(python3 validate_probe.py 2>&1); rm -f validate_probe.py
# The injected map entry must be rejected. Before D43 was escalated+ruled the
# rejection read "never escalated"; once a legitimate structured ruling for D43
# exists, the injected grandfather entry instead collides with it ("duplicate"/
# "conflicting ruling"). Either way the probe corpus errors -- accept any of the
# three rejection signatures, but require errors!=0.
if echo "$out" | grep -qE "never escalated|duplicate ruling|conflicting ruling" && ! echo "$out" | grep -q "errors=0"; then
  echo "PASS: R4-map-probe-rejected"; pass=$((pass+1))
else
  echo "FAIL: R4-map-probe-rejected"; echo "$out" | grep ERROR | head -5; fail=$((fail+1))
fi

# R5: mixed valid;broken;valid -> transactional void, NO pair applied to STATE
cat > "to_reviewer/${NX}_probe.md" <<EOF
---
from: claude
ts: 2026-07-27T04:00:00-03:00
re: new
type: ack
authority: author-delegated:fable-5-2026-07-27-xhigh
rulings: D43-v183-unicode-raw-html=CLOSED-FIXED; BROKEN; D44-k16-preflight-placement=CLOSED-FIXED
---
probe
EOF
out=$(python3 validate.py 2>&1)
rm -f "to_reviewer/${NX}_probe.md"
if echo "$out" | grep -q "whole-value grammar" && ! grep -q "ADJUDICATED.*${NX}_probe" STATE.md; then
  echo "PASS: R5-transactional-void"; pass=$((pass+1))
else
  echo "FAIL: R5-transactional-void"; echo "$out" | grep ERROR | head -3; grep "${NX}_probe" STATE.md | head -3; fail=$((fail+1))
fi

# R5b: grammatically valid pairs where ONE fails eligibility (unknown thread) -> both voided
cat > "to_reviewer/${NX}_probe.md" <<EOF
---
from: claude
ts: 2026-07-27T04:00:00-03:00
re: new
type: ack
authority: author-delegated:fable-5-2026-07-27-xhigh
rulings: D43-v183-unicode-raw-html=CLOSED-FIXED; D97-nonexistent-thread=CLOSED-FIXED
---
probe
EOF
out=$(python3 validate.py 2>&1)
rm -f "to_reviewer/${NX}_probe.md"
if echo "$out" | grep -q "voided transactionally" && ! grep -q "ADJUDICATED.*${NX}_probe" STATE.md; then
  echo "PASS: R5b-eligibility-transactional"; pass=$((pass+1))
else
  echo "FAIL: R5b-eligibility-transactional"; echo "$out" | grep ERROR | head -3; fail=$((fail+1))
fi

# --- D45 (v2.1.1): the lint reserves ONLY exact retired canonical forms ---

# lookalikes must be inert prose
probe_ok "D45-unspaced-trailing-hashes" "to_reviewer/${NX}_probe.md" <<EOF
---
from: claude
ts: 2026-07-27T04:00:00-03:00
re: new
type: ack
---
# AUTHOR ADJUDICATION###
EOF

{ cat <<EOF
---
from: claude
ts: 2026-07-27T04:00:00-03:00
re: new
type: ack
---
EOF
printf '#\302\240AUTHOR ADJUDICATION\n'; } > "to_reviewer/${NX}_probe.md"
out=$(python3 validate.py 2>&1); rm -f "to_reviewer/${NX}_probe.md"
if echo "$out" | grep -q "errors=0"; then
  echo "PASS: D45-nbsp-separator"; pass=$((pass+1))
else
  echo "FAIL: D45-nbsp-separator"; echo "$out" | grep ERROR | head -3; fail=$((fail+1))
fi

probe_ok "D45-leading-space-heading" "to_reviewer/${NX}_probe.md" <<EOF
---
from: claude
ts: 2026-07-27T04:00:00-03:00
re: new
type: ack
---
 # AUTHOR ADJUDICATION
   ## AUTHOR ADJUDICATION
EOF

probe_ok "D45-ruling-prefix-in-sentence" "to_reviewer/${NX}_probe.md" <<EOF
---
from: claude
ts: 2026-07-27T04:00:00-03:00
re: new
type: ack
---
RULING D43-v183-unicode-raw-html is discussed here as ordinary prose.
EOF

# exact retired canonical forms must still be deprecated
probe "D45-canonical-ruling-line" "deprecated" "to_reviewer/${NX}_probe.md" <<EOF
---
from: claude
ts: 2026-07-27T04:00:00-03:00
re: new
type: ack
---
RULING D43-v183-unicode-raw-html: CLOSED-FIXED
EOF

probe "D45-canonical-heading-closing-hashes" "deprecated" "to_reviewer/${NX}_probe.md" <<EOF
---
from: claude
ts: 2026-07-27T04:00:00-03:00
re: new
type: ack
---
## AUTHOR ADJUDICATION ##
EOF

# Control: the untouched corpus is clean under v2.1
out=$(python3 validate.py 2>&1)
if echo "$out" | grep -q "errors=0"; then
  echo "PASS: control-corpus-clean"; pass=$((pass+1))
else
  echo "FAIL: control-corpus-clean"; echo "$out" | grep ERROR | head -5; fail=$((fail+1))
fi

echo "D43-NEGATIVE-TESTS: pass=$pass fail=$fail"
[ "$fail" -eq 0 ]
