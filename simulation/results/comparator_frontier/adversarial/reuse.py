import json,os,sys
sys.path.insert(0,os.path.dirname(os.path.abspath(__file__)))
from adv_recompute import recompute
R="/home/gio/tese/simulation/results"
cases=[("encoder_hybrid/fc.jsonl.zst","encoder_hybrid/fc.sched.json","encoder_hybrid/fc.jsonl.stats.json","aggregate"),
       ("encoder_hybrid/re.jsonl.zst","encoder_hybrid/re.sched.json","encoder_hybrid/re.jsonl.stats.json","aggregate"),
       ("encoder_hybrid/hybrid.jsonl.zst","encoder_hybrid/hybrid.sched.json","encoder_hybrid/hybrid.jsonl.stats.json","aggregate")]
import glob
for j,s,st,w in cases:
    r=recompute(os.path.join(R,j),os.path.join(R,s),w)
    S=json.load(open(os.path.join(R,st)))
    print(f"{j:35s} p99={r['p99']:>10.3f} (stats {S['encoder_delay_ms']['p99']:>10.3f}) ws={r['worker_s']:>12.1f} (stats {S['provisioned_worker_seconds']:>12.1f}) p90={r['p90']} (stats {S['encoder_delay_ms']['p90']}) tend={r['t_end_s']}/{S['vision_sim_end_s']}")
# static C8 week
p=os.path.join(R,"rerun_verify/week_static_C8.jsonl.gz")
print("\nstatic C8 archived:", os.path.exists(p))
if os.path.exists(p):
    stf=os.path.join(R,"rerun_verify/week_static_C8.jsonl.stats.json")
    S=json.load(open(stf)) if os.path.exists(stf) else None
    # no schedule file: static run used --encoder-workers 8
    import numpy as np
    from adv_recompute import window_arrivals, open_jsonl, pctl, RTT_MS, PER_IMG_MS
    arr,ni=window_arrivals("aggregate"); N=len(arr); ts=np.full(N,np.nan)
    with open_jsonl(p) as f:
        for line in f:
            rr=json.loads(line); ts[rr["hash_ids"][0]//100000]=rr["timestamp"]
    d=np.where(ni>0, ts-arr, 0.0)
    h=RTT_MS+PER_IMG_MS*ni; fin=ts-h
    t_end=max(float(arr[-1]), float(fin[ni>0].max()))
    print(f"  recomputed p99={pctl(d,99)} p90={pctl(d,90)} n_over1s={(d>1000).sum()} t_end_s={t_end/1000:.3f} ws(8*t_end)={8*t_end/1000:.1f}")
    if S: print(f"  stats  p99={S['encoder_delay_ms']['p99']} ws={S['provisioned_worker_seconds']} tend={S['vision_sim_end_s']}")
