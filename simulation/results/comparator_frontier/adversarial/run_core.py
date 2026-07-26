import json, os, sys, glob
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from adv_recompute import recompute
E = "/home/gio/tese/simulation/results/comparator_frontier/eval"
WINDOWS = ["aggregate","burst1","burst3","burst4","burst5","steady24h"]
ARMS = {"fc":"{w}_fc_L30","re":"{w}_re_L30","floorM4":"{w}_floorM4_L30",
        "staticC8":"{w}_staticC8_L30","oracle":"{w}_oracle_L30_H0"}
out={}
for w in WINDOWS:
    for a,pat in ARMS.items():
        tag = pat.format(w=w)
        j = os.path.join(E, tag+".jsonl.zst")
        if not os.path.exists(j): j = os.path.join(E, tag+".jsonl")
        s = os.path.join(E, tag+".sched.json")
        r = recompute(j, s, w)
        st = json.load(open(os.path.join(E, tag+".jsonl.stats.json")))
        r["stats_p99"] = st["encoder_delay_ms"]["p99"]
        r["stats_worker_s"] = st["provisioned_worker_seconds"]
        r["stats_t_end"] = st["vision_sim_end_s"]
        r["stats_over1000"] = st["encoder_delay_violations"]["1000"]
        out[tag]=r
        print(f"{tag:32s} p99={r['p99']:>10.3f} (stats {r['stats_p99']:>10.3f}) "
              f"ws={r['worker_s']:>12.1f} (stats {r['stats_worker_s']:>12.1f}) "
              f"tend={r['t_end_s']:.3f}/{r['stats_t_end']:.3f} "
              f"v1000={r['over1000']}/{r['stats_over1000']} textresid={r['max_text_resid_ms']}", flush=True)
json.dump(out, open("core_recompute.json","w"), indent=1)
