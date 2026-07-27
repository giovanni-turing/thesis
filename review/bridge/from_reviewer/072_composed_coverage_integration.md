---
from: reviewer
ts: 2026-07-26T23:37:31-03:00
re: new
type: finding
thread: D31-composed-coverage-integration
---

## HIGH — the 29-arm campaign is only partially integrated and its “forbidden gaps” claim is false

### 1. burst2/6 are not wholly forbidden

The contract says burst2/6 enter results grading through forecast-free
policies (`tex/closedloop.tex:51-57`, `:313-320`). Yet the new coverage prose
at `:798-806` and `:993-995`, plus
`provenance/schema/38_v_joint_e2e_29_arms.sql:39-44`, says **no composed arm**
may exist for either window and that no future ingest should fill them.

That restriction is valid for forecast arms, not for static/reactive arms.
Indeed, complete forecast-free static halves already exist:

```text
defense/anim/data/g1_runs/burst2_enc_static_C8.jsonl                 13,870
defense/anim/data/g1_runs/burst2_lang_static_C8.requests.jsonl      13,870
defense/anim/data/g1_runs/burst6_enc_static_C8.jsonl                  9,821
defense/anim/data/g1_runs/burst6_lang_static_C8.requests.jsonl        9,821
```

Running the committed join read-only on those pairs gives:

```text
burst2: drift 0.0 ms, enc 855.8 + TTFT 745.4 -> joined E2E p99 1603.2 ms
burst6: drift 0.0 ms, enc 720.1 + TTFT 700.3 -> joined E2E p99 1432.1 ms
```

Thus two permissible composed cells require no new replay at all. “No number
is withheld for want of a replay” and “protocol-forbidden” are materially
overbroad.

### 2. both per-pool ledgers and their synthesis still describe the old set

- The encoder table calls itself the request-linked arm set
  (`tex/closedloop.tex:816-825`) but `:836-851` omits the calm-day rows and the
  four newly joined burst-static rows.
- Its synthesis at `:863-876` still says forecast and reactive tie exactly on
  four of five windows and that all advantage lives in burst3. Under the
  declared five evaluation windows they tie on burst1/4/5; calm is
  `677.4` versus `682.1` ms and burst3 differs.
- The language table likewise says “same request-linked arm set” at
  `:1198-1200` but `:1220-1233` omits every calm-day and new burst-static row.
- `:1245-1255` says reactive violates TTFT on all five; the new calm reactive
  TTFT p99 is `494.3 ms`, a pass.
- The limitation at `:1273-1278` still says the calm day is priced only by the
  grid/knee rather than replayed end-to-end, contradicting the calm joined rows
  at `:945`, `:948`, and `:954`.

The composed table itself is numerically useful, but coverage completeness and
the chapter-wide conclusions must be re-synthesized from the declared
evaluation set rather than appending one table to the old aggregate+four-burst
narrative.
