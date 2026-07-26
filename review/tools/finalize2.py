#!/usr/bin/env python3
"""Final combiner. Layered authority per claim:
   opus arbitration (reports/arbitration/verdicts/*.json)  -- authoritative, decides contested
 > gemini+gpt-sol adjudication (Phase 3)                    -- for flagged claims not contested
 > phase-2 CONFIRM/REFUTE consensus                         -- for clean passes / unverifiables
minimax (Phase 4a) is recorded as a confirming third-family vote, not an override.
Emits review/final-verdicts.v2.jsonl and prints the definitive tally."""
import json, glob, collections
REV="/home/gio/tese/review"
FAIL_V={"contradicted","overclaimed","inconsistent"}; PASS_V={"supported","holds"}
INV={json.loads(l)["claim_id"]:json.loads(l) for l in open(f"{REV}/claim-inventory.jsonl") if l.strip()}
BASE={json.loads(l)["claim_id"]:json.loads(l) for l in open(f"{REV}/final-verdicts.jsonl") if l.strip()}

def load_dir(patt, key):
    d={}
    for f in glob.glob(patt):
        try:
            r=json.load(open(f)); d.setdefault(r["claim_id"],[]).append(r)
        except: pass
    return d
ARB=load_dir(f"{REV}/reports/arbitration/verdicts/*.json","claim_id")
MMX=load_dir(f"{REV}/reports/validation/minimax-m3/p4.*.jsonl","claim_id")

def status_of(v):
    if v in PASS_V: return "PASS"
    if v in FAIL_V: return "FAIL"
    if v=="unverifiable": return "UNVERIFIABLE"
    return "SPLIT"

out=[]; tally=collections.Counter(); src=collections.Counter()
for cid,base in BASE.items():
    arb=ARB.get(cid)
    if arb:
        v=arb[0].get("verdict"); status=status_of(v); basis="opus-arbitration"
    else:
        v=base["verdict"]; status=base["status"]; basis=base["basis"]
    mmx=[m.get("verdict") or ("contradicted" if m.get("decision")=="confirm" else "supported" if m.get("decision")=="overturn" else None) for m in MMX.get(cid,[])]
    mmx=[x for x in mmx if x]
    rec=dict(base); rec["status"]=status; rec["verdict"]=v; rec["basis"]=basis
    rec["minimax_vote"]=mmx
    # 3-family agreement flag for FAILs (adjudicators + minimax both defect)
    if status=="FAIL" and basis!="opus-arbitration":
        adj=[x for x in (base.get("adjudicator_verdicts") or []) if x]
        rec["three_family_defect"]= bool(adj) and all(x in FAIL_V for x in adj) and bool(mmx) and all(x in FAIL_V for x in mmx)
    out.append(rec); tally[status]+=1; src[basis]+=1
with open(f"{REV}/final-verdicts.v2.jsonl","w") as f:
    for r in out: f.write(json.dumps(r)+"\n")
print("=== DEFINITIVE TALLY (227 data-verifiable) ===")
for s,n in tally.most_common(): print(f"  {s:12} {n}")
print("\nbasis:", dict(src))
print("arbitration verdicts collected:", sum(len(v) for v in ARB.values()), "| claims arbitrated:", len(ARB))
print("minimax validations:", sum(len(v) for v in MMX.values()))
fails=[r for r in out if r["status"]=="FAIL"]
print(f"\nFINAL FAIL: {len(fails)} | 3-family-defect confirmed: {sum(1 for r in fails if r.get('three_family_defect'))}")
print("fail by chapter:", dict(collections.Counter(r['chapter'] for r in fails)))
