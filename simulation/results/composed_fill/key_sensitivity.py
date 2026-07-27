#!/usr/bin/env python3
"""How much does the FIFO-key ambiguity move the reported statistics?

On the planner arms both keys exist. Compute the full endpoint set under the
authoritative session_id assignment and under the FIFO key, and diff. This
bounds the error the 6 static cells inherit, where only the FIFO key exists.
"""
import json
import re
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, "/home/gio/tese/simulation")
import composed_fill_join as J  # noqa: E402

ROOT = Path("/home/gio/tese")
A12 = ROOT / "defense/anim/data/a12_runs"
VER = json.load(open(A12 / "verification.json"))
CHECK = [("burst4", "reactive"), ("burst1", "reactive"), ("burst1", "fc_chronos"),
         ("burst1", "fc_timesfm"), ("burst4", "fc_chronos"), ("burst5", "fc_chronos")]

for win, arm in CHECK:
    tag = f"{win}_{arm}"
    w = J.WINS[win]
    N = int(w["max_requests"])
    fr = J.raw_frame().iloc[w["offset"]:w["offset"] + N].reset_index(drop=True)
    rel_ms = ((fr.ts - fr.ts.iloc[0]).dt.total_seconds() * 1000.0).to_numpy()
    t_ts, t_il, t_ol, t_cl = J.read_trace(ROOT / VER[tag]["composed_trace"])
    import collections
    k2i = collections.defaultdict(collections.deque)
    for i, (ci, gi) in enumerate(zip(fr["ContextTokens"], fr["GeneratedTokens"])):
        k2i[(max(1, int(ci)), max(1, int(gi)))].append(i)
    enc = np.full(N, np.nan); line2raw = np.empty(N, dtype=np.int64)
    for li in range(N):
        i = k2i[(int(t_il[li]), int(t_ol[li]))].popleft()
        enc[i] = t_ts[li] - rel_ms[i]; line2raw[li] = i
    enc_line = enc[line2raw]

    sid, r_arr, r_ttft, r_il, r_ol = J.read_records(A12 / f"{tag}.requests.jsonl")
    auth = np.array([int(re.match(r"request_(\d+)", s).group(1)) - 1 for s in sid])
    fifo, amb = J.key_assign(t_ts, t_cl, t_ol, r_arr, r_il, r_ol)

    out = {}
    for name, a in (("session_id", auth), ("fifo_key", fifo)):
        ttft = np.full(N, np.nan); ttft[a] = r_ttft
        e2e = enc_line + ttft
        out[name] = (round(J.p99(e2e), 1), round(float(e2e.max()), 1),
                     round(J.p99(ttft), 1))
    d = out["session_id"]; f = out["fifo_key"]
    print(f"{tag:20s} disagree={int((auth!=fifo).sum()):3d}/{N} ambiguous={amb:3d} | "
          f"e2e_p99 {d[0]} vs {f[0]} (d={f[0]-d[0]:+.1f})  "
          f"e2e_max {d[1]} vs {f[1]} (d={f[1]-d[1]:+.1f})  "
          f"ttft_p99 {d[2]} vs {f[2]} (d={f[2]-d[2]:+.1f})")
