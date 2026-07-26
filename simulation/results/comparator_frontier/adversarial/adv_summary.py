import json,os,sys,glob
sys.path.insert(0,".")
from adv_recompute import recompute
A="/home/gio/tese/simulation/results/comparator_frontier/adversarial"
core=json.load(open("core_recompute.json"))
WIN=["aggregate","burst1","burst3","burst4","burst5","steady24h"]
rows={}
for v in ["oracleH3","oracleWS","oracleWSH3"]:
    for w in WIN:
        tag=f"{w}_{v}"
        r=recompute(os.path.join(A,tag+".jsonl"),os.path.join(A,tag+".sched.json"),w)
        st=json.load(open(os.path.join(A,tag+".jsonl.stats.json")))
        assert abs(r["p99"]-st["encoder_delay_ms"]["p99"])<1e-9, tag
        rows.setdefault(v,{})[w]=r
# reference arms
for a,key in [("oracle_H0","oracle"),("forecast_p90","fc"),("reactive","re"),("floorM4","floorM4"),("staticC8","staticC8")]:
    d={}
    for w in WIN:
        for t,rr in core.items():
            if t.startswith(w+"_") and (t.endswith("_"+key+"_L30") or t.endswith("_"+key+"_L30_H0")):
                d[w]=rr
    rows[a]=d
EPS=["burst1","burst3","burst4","burst5","steady24h"]
static=rows["staticC8"]["aggregate"]["worker_s"]
print(f"{'arm':14s}{'agg ws':>12s}{'vs_st':>7s}{'agg p99':>9s}" + "".join(f"{e:>11s}" for e in EPS) + "  fail")
for a,d in rows.items():
    ep=[d[w]["p99"] for w in EPS]
    fails=[w for w,p in zip(EPS,ep) if p>=1000]
    print(f"{a:14s}{d['aggregate']['worker_s']:>12.1f}{d['aggregate']['worker_s']/static:>7.3f}{d['aggregate']['p99']:>9.1f}"
          + "".join(f"{p:>11.1f}" for p in ep) + f"  {len(fails)} {','.join(fails) or '-'}")
json.dump({k:{w:v for w,v in d.items()} for k,d in rows.items()}, open("adv_summary.json","w"), indent=1)
