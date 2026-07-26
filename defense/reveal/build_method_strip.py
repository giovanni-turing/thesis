#!/usr/bin/env python3
"""Method-slide data: burst3 offered demand (1-s bins) + the L=30 capacity
schedules of both policies from the verified a2_data.json — the static
'capacity before vs after the burst' preview. Output: assets/method_data.js."""
import json
from pathlib import Path

ROOT = Path("/home/gio/tese")
d = json.load(open(ROOT / "defense/anim/data/a2_data.json"))
w = d["windows"]["burst3"]
out = {
    "span_s": w["meta"]["span_s"],
    "rho": 15, "lead": 30,
    "offered15": [round(sum(w["offered"][i:i + 15]) / 15.0, 1)
                  for i in range(0, len(w["offered"]) - 14, 15)],
    "offered5": [round(sum(w["offered"][i:i + 5]) / 5.0, 1)
                 for i in range(0, len(w["offered"]) - 4, 5)],
    "fc": w["runs"]["forecast_L30"]["sched"],
    "re": w["runs"]["reactive_L30"]["sched"],
    "provenance": "burst3 window of a2_data.json (ledger-verified); "
                  "offered15/offered5 = 15-s/5-s means of the 1-s offered series "
                  "(scheduler consumes the 15-s means; 5-s is the display series); "
                  "sched = [t_s, workers], capacity = workers x rho",
}
p = ROOT / "defense/reveal/assets/method_data.js"
p.write_text("const METHOD = " + json.dumps(out) + ";\n")
print(f"wrote {p}: {len(out['offered15'])} offered 15-s bins, "
      f"fc steps {len(out['fc'])}, re steps {len(out['re'])}, "
      f"offered15 max {max(out['offered15'])}")
