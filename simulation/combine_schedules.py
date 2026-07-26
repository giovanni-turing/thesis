#!/usr/bin/env python3
"""Combine N [[t_s, workers],...] step schedules into their pointwise MAX.
Used to build the hybrid encoder controller: at each instant provision the larger
of the forecast-driven and the reactive (current-observed-load) worker counts, so
the forecast is an anticipatory floor and the reactive tops up on forecast error.

Fold fallback (--allow-missing): when a fold has no forecast coverage the
forecast generator refuses to emit a schedule (e.g. "no forecast rows cover
window F1"). With --allow-missing, input paths that do not exist are excluded
with a loud notice and the hybrid degenerates to the pointwise max of the
remaining arm(s) -- for the fc+re pair, to the reactive schedule alone. At
least one input must exist; without the flag any missing input is a hard error.

Usage: combine_schedules.py [--allow-missing] in1.json in2.json ... out.json
"""
import json, os, sys

def val_at(s, t):
    v = s[0][1]
    for tt, w in s:
        if tt <= t + 1e-9:
            v = w
        else:
            break
    return v

def main():
    argv = sys.argv[1:]
    allow_missing = "--allow-missing" in argv
    argv = [a for a in argv if a != "--allow-missing"]
    if len(argv) < 2:
        sys.exit("usage: combine_schedules.py [--allow-missing] in1.json [in2.json ...] out.json")
    ins, out = argv[:-1], argv[-1]
    missing = [p for p in ins if not os.path.exists(p)]
    if missing:
        if not allow_missing:
            sys.exit("combine: missing input schedule(s): " + ", ".join(missing)
                     + " (pass --allow-missing only for the documented no-forecast-coverage fallback)")
        for p in missing:
            print(f"combine: WARNING missing input {p} -> excluded; "
                  f"hybrid degenerates to the pointwise max of the remaining arm(s)")
        ins = [p for p in ins if os.path.exists(p)]
    if not ins:
        sys.exit("combine: no existing input schedules; refusing to write an empty hybrid")
    scheds = [json.load(open(p)) for p in ins]
    times = sorted({float(t) for s in scheds for t, _ in s})
    merged = [[t, max(val_at(s, t) for s in scheds)] for t in times]
    res = []
    for t, w in merged:
        if res and res[-1][1] == w:
            continue
        res.append([t, int(w)])
    json.dump(res, open(out, "w"))
    print(f"hybrid: {len(res)} steps from {len(ins)} arm(s), "
          f"workers {min(w for _,w in res)}..{max(w for _,w in res)}")

if __name__ == "__main__":
    main()
