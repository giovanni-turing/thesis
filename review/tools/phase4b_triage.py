#!/usr/bin/env python3
"""Phase 4b — fuse the three independent families on each FAIL and decide who needs opus.
  families:  adjudication = gemini(google) + gpt-sol(openai)   [Phase 3]
             validation   = minimax(minimax)                    [Phase 4a]
Classify each FAIL:
  CONFIRMED  = all present family-verdicts agree it's a defect (>=2 families, incl. minimax) -> failure stands
  CONTESTED  = adjudicators split, OR minimax disagrees with the adjudicators, OR any blocking severity,
               OR no adjudicator verdict -> escalate to opus (Agent tool) as authoritative arbiter
Writes review/reports/arbitration/queue/<claim_id>.json packets for the CONTESTED set and prints the split."""
import json, glob, collections, os
REV="/home/gio/tese/review"
FAIL_V={"contradicted","overclaimed","inconsistent"}; PASS_V={"supported","holds"}
F=[json.loads(l) for l in open(f"{REV}/final-verdicts.jsonl") if l.strip()]
fails=[r for r in F if r["status"]=="FAIL"]

def p3_for(cid):
    out=[]
    for f in glob.glob(f"{REV}/reports/adjudication/*/p3.{cid}.jsonl"):
        r=json.load(open(f)); raw=r.get("raw") or {}
        out.append({"model":r["model"],"verdict":r.get("verdict"),"observed":raw.get("observed"),
                    "evidence":raw.get("evidence"),"severity":raw.get("severity"),"fix":raw.get("fix"),"query":raw.get("query")})
    return out
def p4_for(cid):
    out=[]
    for f in glob.glob(f"{REV}/reports/validation/*/p4.{cid}.jsonl"):
        r=json.load(open(f)); raw=r.get("raw") or {}
        out.append({"model":r["model"],"decision":r.get("decision"),"verdict":r.get("verdict"),
                    "observed":raw.get("observed"),"evidence":raw.get("evidence")})
    return out

QDIR=f"{REV}/reports/arbitration/queue"; os.makedirs(QDIR, exist_ok=True)
cats=collections.Counter(); contested=[]
for r in fails:
    cid=r["claim_id"]; p3=p3_for(cid); p4=p4_for(cid)
    adj=[x["verdict"] for x in p3 if x["verdict"]]
    mmx=[x["verdict"] or ("contradicted" if x["decision"]=="confirm" else "supported" if x["decision"]=="overturn" else None) for x in p4]
    mmx=[v for v in mmx if v]
    sev=set(x["severity"] for x in p3 if x.get("severity"))
    adj_unanimous_fail = bool(adj) and all(v in FAIL_V for v in adj)
    adj_split = bool(adj) and any(v in PASS_V for v in adj) and any(v in FAIL_V for v in adj)
    mmx_defect = bool(mmx) and any(v in FAIL_V for v in mmx)
    mmx_pass   = bool(mmx) and all(v in PASS_V for v in mmx)
    reason=None
    if not adj: reason="no-adjudicator"
    elif adj_split: reason="adjudicators-split"
    elif adj_unanimous_fail and mmx_pass: reason="minimax-overturns"
    elif "blocking" in sev: reason="blocking-severity"
    if reason:
        cats["CONTESTED:"+reason]+=1; contested.append(cid)
        pkt={"claim_id":cid,"chapter":r["chapter"],"claim_type":r["claim_type"],"anchor":r["anchor"],
             "claim_text":r["claim_text"],"expected_backing":r.get("expected_backing"),
             "adjudication":p3,"minimax_validation":p4,"reason":reason}
        json.dump(pkt, open(f"{QDIR}/{cid}.json","w"), indent=1)
    else:
        cats["CONFIRMED"]+=1
print("=== Phase-4b triage of 85 FAILs ===")
for k,v in cats.most_common(): print(f"  {k:28} {v}")
print(f"\nCONTESTED -> opus arbitration queue: {len(contested)} packets in reports/arbitration/queue/")
json.dump(contested, open(f"{REV}/reports/arbitration/contested.json","w"))
