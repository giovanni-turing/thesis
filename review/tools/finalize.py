#!/usr/bin/env python3
"""Combine Phase-2 verdicts + Phase-3 adjudications into a FINAL per-claim verdict.
Adjudicators (re-derived from scratch) outweigh Phase-2 verifiers. Emits:
  - review/final-verdicts.jsonl   (one record per data-verifiable claim)
  - the Phase-4 target list (confirmed failures needing cross-family validation)
Prints the final tally. Read-only w.r.t. the thesis."""
import json, glob, collections, os
REV="/home/gio/tese/review"
INV={json.loads(l)["claim_id"]:json.loads(l) for l in open(f"{REV}/claim-inventory.jsonl") if l.strip()}
PASS_V={"supported","holds"}; FAIL_V={"contradicted","overclaimed","inconsistent"}

def load(patt):
    d=collections.defaultdict(list)
    for f in glob.glob(patt):
        try: r=json.load(open(f)); d[r["claim_id"]].append(r)
        except: pass
    return d

p2=load(f"{REV}/reports/*/p2.*.jsonl")
p3=load(f"{REV}/reports/adjudication/*/p3.*.jsonl")

def final_verdict(cid):
    v2=[r for r in p2.get(cid,[]) if r.get("verdict")]
    v3=[r for r in p3.get(cid,[]) if r.get("verdict")]
    adj=[r.get("verdict") for r in v3]
    p2v=[r.get("verdict") for r in v2]
    # If adjudicated, adjudicators decide (they re-derived from scratch).
    if adj:
        aset=set(adj)
        if aset<=PASS_V: status,verdict="PASS", max(set(adj),key=adj.count)
        elif aset & FAIL_V:
            # at least one adjudicator confirms a defect
            fails=[v for v in adj if v in FAIL_V]
            status,verdict="FAIL", max(set(fails),key=fails.count)
        elif aset<={"unverifiable"}: status,verdict="UNVERIFIABLE","unverifiable"
        else: status,verdict="SPLIT", "/".join(sorted(aset))
        return status, verdict, "adjudicated", p2v, adj
    # not adjudicated -> Phase-2 consensus (these were the clean passes / unverifiables)
    s=set(p2v)
    if not s: return "NO-VERDICT", None, "none", p2v, adj
    if s<=PASS_V: return "PASS", max(set(p2v),key=p2v.count), "phase2", p2v, adj
    if s<={"unverifiable"}: return "UNVERIFIABLE","unverifiable","phase2", p2v, adj
    if s<=(PASS_V|{"unverifiable"}): return "PASS-UNVER", "supported","phase2", p2v, adj
    if s & FAIL_V: return "FAIL", max([v for v in p2v if v in FAIL_V],key=p2v.count),"phase2", p2v, adj
    return "SPLIT","/".join(sorted(s)),"phase2", p2v, adj

targets=[c for c in INV.values() if c.get("claim_type") in ("numeric","comparative")]
out=[]; tally=collections.Counter()
for c in targets:
    cid=c["claim_id"]
    status,verdict,basis,p2v,adj=final_verdict(cid)
    tally[status]+=1
    out.append({"claim_id":cid,"chapter":c["chapter"],"claim_type":c["claim_type"],
                "anchor":c["anchor"],"claim_text":c["claim_text"],"expected_backing":c.get("expected_backing"),
                "status":status,"verdict":verdict,"basis":basis,
                "phase2_verdicts":p2v,"adjudicator_verdicts":adj})
with open(f"{REV}/final-verdicts.jsonl","w") as f:
    for r in out: f.write(json.dumps(r)+"\n")
print("=== FINAL TALLY (227 data-verifiable claims) ===")
for s,n in tally.most_common(): print(f"  {s:12} {n}")
fails=[r for r in out if r["status"]=="FAIL"]
print(f"\nFAIL claims -> Phase-4 validation targets: {len(fails)}")
sev=collections.Counter()
for r in fails:
    for rr in p3.get(r["claim_id"],[])+p2.get(r["claim_id"],[]):
        raw=rr.get("raw") or {}
        if rr.get("verdict") in FAIL_V: sev[raw.get("severity")]+=1
print("fail severities (verdict-level):", dict(sev))
print("wrote final-verdicts.jsonl")
