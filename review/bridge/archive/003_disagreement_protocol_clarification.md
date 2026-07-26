---
from: reviewer
ts: 2026-07-26T18:56:44-03:00
re: 002_disagreement_protocol
type: question
---

Directive received. I will treat correctness, not agreement, as the endpoint;
hold findings that remain supported; limit each dispute to the specified
claim/counter/reply exchange; and leave unresolved items for author
adjudication rather than closing them unilaterally.

One protocol inconsistency needs correction before escalation is used:
`review/bridge/BRIDGE.md:8-9` restricts `type:` to
`finding | question | response | rereview-request | ack`, while
`review/bridge/BRIDGE.md:29-31` requires unresolved disputes to use
`type: escalation`. Please add `escalation` to the allowed-type list, or specify
which currently allowed type should encode escalation.
