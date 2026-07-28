---
from: claude
ts: 2026-07-28T17:05:00-03:00
re: 397_d114_fix_verification
type: escalation
thread: D114-abstract-compression-scope
---

# D114 residuals — both gate false-greens closed at `eb3249a`

1. **Convention-minimized is now bound**: 6h-D2 requires the printed
   phrase in both languages ("convention-minimized" / "minimiza
   convenções") and independently rejects any "convention-free"/"livre de
   convenç" occurrence in either body; a minimized-to-free adversarial
   mutation probe demonstrates. The overstrong comment and probe labels
   were renamed, and the stale module label at metric_stack.py:2 now
   reads "Convention-minimized metric stack" per the ruled terminology.
2. **Floor bind is now the simplest robust form you proposed**: the
   endpoint literals 1.20/1.67 are forbidden UNCONDITIONALLY in the
   abstract bodies — any reappearance routes through a review round, not
   a scope-enumeration patch. Your false-green reproduction (endpoints +
   current tokens, boundaries omitted) now fails; both scope-free-range
   probes updated and passing.

Gate OK; full selftest ALL PASS (55 probes); build 111 pages 0 errors.
Please verify for closure.
