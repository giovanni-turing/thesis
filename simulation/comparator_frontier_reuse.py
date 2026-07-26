#!/usr/bin/env python3
"""§8.2 -- INDEPENDENT recomputation of the *pre-existing* eval-span artifacts.

The orchestration asks arms 1 (forecast p90 issue-time), 2 (same-image-signal
reactive) and 4 (deployable static fleet) to be READ OFF EXISTING artifacts
rather than rerun.  This script does exactly that: it points the same
independent recomputation used for the calibration split
(comparator_frontier_summarize.recompute -- per-request delay from the emitted
mooncake JSONL, provisioned worker-seconds by integrating the schedule) at the
archived artifacts, and cross-checks against each run's own stats.json.

Nothing here is rerun; every artifact is opened read-only.
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import comparator_frontier_summarize as S  # noqa: E402

ROOT = Path("/home/gio/tese")
R = ROOT / "simulation/results"

# (label, window, jsonl, sched, provenance note)
# sched=None => constant-capacity run (converter --encoder-workers C); the
# equivalent schedule is [[0, C]], which the design agent proved bit-identical.
ARTIFACTS = [
    ("arm1 forecast_p90 issue-time  L30 rho15 hyst3", "aggregate",
     R / "encoder_hybrid/fc.jsonl.zst", R / "encoder_hybrid/fc.sched.json",
     "simulation/run_encoder_hybrid.sh:22-24 (dynamo .venv, forecast_schedule_issuetime.py p90 rho15 L30)"),
    ("arm2 reactive react_point     L30 rho15 hyst3", "aggregate",
     R / "encoder_hybrid/re.jsonl.zst", R / "encoder_hybrid/re.sched.json",
     "simulation/run_encoder_hybrid.sh:25-27 (dynamo .venv, reactive_quantile_schedule.py --mode react_point rho15 L30)"),
    ("arm4 static C=8 (deployable)", "aggregate",
     R / "rerun_verify/week_static_C8.jsonl.gz", None,
     "scripts/decompress_large_results.sh:16 / provenance run_id rerun_verify:week_static_C8"),
]


def main() -> None:
    out = []
    for label, window, jsonl, sched, note in ARTIFACTS:
        if not jsonl.exists():
            print(f"ABSENT  {label}: {jsonl}")
            continue
        tmp_jsonl = None
        if str(jsonl).endswith(".gz"):
            # recompute() understands plain/.zst only; stream-decompress read-only
            import gzip
            import shutil
            tmp_jsonl = Path(os.environ.get("TMPDIR", "/tmp")) / (jsonl.name[:-3])
            if not tmp_jsonl.exists():
                with gzip.open(jsonl, "rb") as fi, open(tmp_jsonl, "wb") as fo:
                    shutil.copyfileobj(fi, fo)
            read_from = tmp_jsonl
        else:
            read_from = jsonl
        tmp_sched = None
        if sched is None:
            tmp_sched = Path("/tmp/claude-1000/-home-gio-tese/const_c8.sched.json")
            tmp_sched.parent.mkdir(parents=True, exist_ok=True)
            tmp_sched.write_text("[[0, 8]]")
            sched = tmp_sched
        r = S.recompute(str(read_from), str(sched), window)
        stats_p = Path(str(jsonl).split(".jsonl")[0] + ".jsonl.stats.json")
        st = json.load(open(stats_p)) if stats_p.exists() else None
        agree = None
        if st is not None:
            agree = bool(abs(st["encoder_delay_ms"]["p99"] - r["p99"]) <= 1e-3
                         and abs(st["provisioned_worker_seconds"] - r["prov_worker_s"]) <= 0.2)
        print(f"{label}\n   window={window}  file={jsonl}\n   provenance: {note}")
        print(f"   recomputed p99={r['p99']} ms  prov={r['prov_worker_s']} worker-s  "
              f"n={r['n_requests']}  t_end={r['t_end_s']} s")
        if st is not None:
            print(f"   stats.json  p99={st['encoder_delay_ms']['p99']} ms  "
                  f"prov={st['provisioned_worker_seconds']} worker-s   agrees={agree}")
        out.append({"label": label, "window": window, "file": str(jsonl),
                    "provenance": note, "stats_agrees": agree, **r})
        if tmp_sched is not None:
            tmp_sched.unlink(missing_ok=True)
        if tmp_jsonl is not None:
            tmp_jsonl.unlink(missing_ok=True)
    Path(R / "comparator_frontier/reuse_existing.json").write_text(json.dumps(out, indent=1))
    print(f"\n-> {R / 'comparator_frontier/reuse_existing.json'}")


if __name__ == "__main__":
    main()
