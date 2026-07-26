import json, os, sys, glob, re
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from adv_recompute import recompute
C = "/home/gio/tese/simulation/results/comparator_frontier/calib"
res={}; bad=0
for j in sorted(glob.glob(os.path.join(C,"*.jsonl.zst"))):
    tag = os.path.basename(j)[:-len(".jsonl.zst")]
    w = tag.split("_")[0]
    r = recompute(j, os.path.join(C, tag+".sched.json"), w)
    st = json.load(open(os.path.join(C, tag+".jsonl.stats.json")))
    if abs(r["p99"]-st["encoder_delay_ms"]["p99"])>1e-9 or abs(r["worker_s"]-st["provisioned_worker_seconds"])>0.11:
        bad+=1; print("MISMATCH",tag,r["p99"],st["encoder_delay_ms"]["p99"],r["worker_s"],st["provisioned_worker_seconds"])
    res[tag]=r
print("calib cells:",len(res),"mismatches:",bad)
json.dump(res, open("calib_recompute.json","w"), indent=1)

# --- reconstruct R1 / R2 from MY numbers ---
MG=[1,2,3,4,5,6,7,8,9,10,12,14,16,20,24,32]; LG=[15,30,45,300]
def p(w,M,L): return res[f"{w}_floorM{M}_L{L}"]["p99"]
print("\nM   " + "".join(f"{'b2 L'+str(L):>12s}{'b6 L'+str(L):>12s}" for L in LG) + f"{'ws@L30':>12s}")
for M in MG:
    row=f"{M:<4d}"
    for L in LG:
        for w in ("burst2","burst6"):
            v=p(w,M,L); row+=f"{v:>10.1f}{'  ' if v<1000 else ' X'}"
    ws=res[f"burst2_floorM{M}_L30"]["worker_s"]+res[f"burst6_floorM{M}_L30"]["worker_s"]
    print(row+f"{ws:>12.1f}")
R1=[M for M in MG if p("burst2",M,30)<1000 and p("burst6",M,30)<1000]
R2=[M for M in MG if all(p(w,M,L)<1000 for L in LG for w in ("burst2","burst6"))]
print("\nR1 (L=30 only) passing M:",R1," -> cheapest",R1[0] if R1 else None)
print("R2 (all leads)  passing M:",R2," -> cheapest",R2[0] if R2 else None)
print("R2 binding cell for M=4:", min(((f'{w}_L{L}',p(w,4,L)) for L in LG for w in ('burst2','burst6')),key=lambda x:1000-x[1]))
for H in (0,3):
    print(f"oracle H={H}: b2 p99 {res[f'burst2_oracle_L30_H{H}']['p99']} ws {res[f'burst2_oracle_L30_H{H}']['worker_s']}; "
          f"b6 p99 {res[f'burst6_oracle_L30_H{H}']['p99']} ws {res[f'burst6_oracle_L30_H{H}']['worker_s']}")
