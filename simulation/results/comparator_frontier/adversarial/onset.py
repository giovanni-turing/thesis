import json,os,sys,numpy as np
sys.path.insert(0,os.path.dirname(os.path.abspath(__file__)))
from adv_recompute import window_arrivals, open_jsonl, pctl
E="/home/gio/tese/simulation/results/comparator_frontier/eval"
def load(tag,w):
    arr,ni=window_arrivals(w); N=len(arr); ts=np.full(N,np.nan)
    with open_jsonl(os.path.join(E,tag+".jsonl.zst")) as f:
        for line in f:
            r=json.loads(line); ts[r["hash_ids"][0]//100000]=r["timestamp"]
    d=np.where(ni>0, ts-arr, 0.0)
    return arr,ni,d
for w,tags in [("burst3",["burst3_fc_L30","burst3_re_L30","burst3_floorM4_L30","burst3_oracle_L30_H0","burst3_staticC8_L30"])]:
    for tag in tags:
        arr,ni,d=load(tag,w)
        print(f"\n== {tag} ==  p99_all={pctl(d,99)}")
        for cut in (30_000,60_000,120_000,300_000):
            m=arr>=cut
            print(f"   excl first {cut/1000:>5.0f}s: n={m.sum():5d} p99={pctl(d[m],99):>10.3f}  max={d[m].max():>10.1f}")
        # violations by arrival-time decile
        v=d>1000
        if v.any():
            print(f"   n>1s={v.sum()}  arrival-times of violators: min={arr[v].min()/1000:.1f}s med={np.median(arr[v])/1000:.1f}s max={arr[v].max()/1000:.1f}s")
        # worst-delay request
        k=int(np.argmax(d)); print(f"   argmax delay: t_arr={arr[k]/1000:.1f}s n_img={ni[k]} delay={d[k]:.1f}ms")
