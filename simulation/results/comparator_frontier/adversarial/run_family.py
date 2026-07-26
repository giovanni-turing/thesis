import json, os, sys, glob, re
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from adv_recompute import recompute
E = "/home/gio/tese/simulation/results/comparator_frontier/eval_family"
out={}
bad=0
for j in sorted(glob.glob(os.path.join(E,"*.jsonl.zst"))):
    tag = os.path.basename(j)[:-len(".jsonl.zst")]
    m = re.match(r"^(.+)_floorM(\d+)_L30$", tag)
    w = m.group(1)
    r = recompute(j, os.path.join(E, tag+".sched.json"), w)
    st = json.load(open(os.path.join(E, tag+".jsonl.stats.json")))
    ok = (abs(r["p99"]-st["encoder_delay_ms"]["p99"])<1e-9 and
          abs(r["worker_s"]-st["provisioned_worker_seconds"])<0.11)
    if not ok:
        bad+=1
        print("MISMATCH", tag, r["p99"], st["encoder_delay_ms"]["p99"], r["worker_s"], st["provisioned_worker_seconds"])
    out[tag]=dict(window=w, M=int(m.group(2)), p99=r["p99"], worker_s=r["worker_s"],
                  over1000=r["over1000"], t_end=r["t_end_s"])
print("family cells:", len(out), "mismatches:", bad)
json.dump(out, open("family_recompute.json","w"), indent=1)
