#!/usr/bin/env python3
"""Phase 3 — reconcile & adjudicate. Reads all Phase-2 verdicts, reconciles per claim
into pass / flagged / split / unverifiable, and re-verifies the FLAGGED+SPLIT set from
scratch with strong cross-family adjudicators (the reserved slow reasoners + high-verify
anchors). Adjudicator sees the claim + the CONFIRM/REFUTE verdicts but is told to re-derive
from the DB, not trust them. Same review-db sandbox, E2 gate, resumable (.done)."""
import json, os, re, subprocess, tempfile, collections, argparse
from concurrent.futures import ThreadPoolExecutor

REV="/home/gio/tese/review"; ROOT="/home/gio/tese"
R=json.load(open(f"{REV}/roster.active.json")); GEN=R["generators"]; CFG=R["reviewer_config"]
INV={json.loads(l)["claim_id"]:json.loads(l) for l in open(f"{REV}/claim-inventory.jsonl") if l.strip()}

# Adjudicator pool: after the novita outage, only google (gemini) + openai (gpt-sol) are
# reliably fast AND are the two best-calibrated verifiers (7/7, 6/7). Everything via openrouter
# is 8-13min/unit at reasoning=high. Two cross-family adjudicators per claim; genuinely split /
# blocking claims escalate to opus via the Agent tool (handled by the orchestrator).
ADJ=["gemini-3.5-flash","gpt-5.6-sol"]
ANCHORS=["gemini-3.5-flash","gpt-5.6-sol"]
FLAG_V={"contradicted","overclaimed","inconsistent"}
PASS_V={"supported","holds"}

def reconcile():
    import glob
    byclaim=collections.defaultdict(list)
    for f in glob.glob(f"{REV}/reports/*/p2.*.jsonl"):
        try: r=json.load(open(f)); byclaim[r["claim_id"]].append(r)
        except: pass
    out={}
    for cid,rs in byclaim.items():
        vset=set(v for v in (r.get("verdict") for r in rs) if v)
        if not vset or vset<={None}: cat="no-verdict"
        elif vset & FLAG_V: cat="flagged"
        elif vset<=PASS_V: cat="pass"
        elif vset<={"unverifiable"}: cat="unverifiable"
        elif vset<=(PASS_V|{"unverifiable"}): cat="pass-unver"
        else: cat="split"
        out[cid]={"cat":cat,"verdicts":rs}
    return out

SYS=("You are the ADJUDICATOR. Two verifiers disagreed on (or flagged) a thesis claim. "
 "Re-verify it FROM SCRATCH against the provenance DB via the review-db db_query tool (read-only) — "
 "do NOT trust their reasoning or numbers. Query the owning view yourself; check the denominator, "
 "is_current/is_superseded/_effective columns, and per-fold/per-window breakdowns. Weigh any overclaim "
 "against CLAIM-STRUCTURE.md tiers. A causal 'necessarily' or a claim with no backing is 'unverifiable'. "
 "Never invent a number — every number you cite comes from a db_query result.")

def usr(c, verdicts):
    lines=[]
    for r in verdicts:
        raw=r.get("raw") or {}
        lines.append(f"  [{r['role']}/{r['model']}] verdict={r.get('verdict')} "
                     f"observed={str(raw.get('observed'))[:120]} evidence={str(raw.get('evidence'))[:120]}")
    prior="\n".join(lines)
    return (f"CLAIM: {c['claim_text']}\nEXACT TEXT: \"{c['anchor']}\" (chapter {c['chapter']}, type {c.get('claim_type')})\n"
     f"EXPECTED BACKING: {c.get('expected_backing')}\n\nPRIOR VERIFIER VERDICTS (do NOT trust — re-derive):\n{prior}\n\n"
     "Query the DB yourself, then output ONE authoritative JSON:\n"
     '{"verdict":"supported|contradicted|overclaimed|inconsistent|unverifiable|holds","query":"<exact SQL>",'
     '"observed":"<DB value>","claimed":"<text value>","evidence":"<one line>","severity":"blocking|major|minor",'
     '"fix":"<if not supported>","confidence":0.0}')

VJSON=re.compile(r'\{[^{}]*"verdict"[^{}]*\}')
SQL=re.compile(r'db_query\s*\{"sql":"(.*?)"\}', re.S)

def assign_adj(cid, verdicts, i):
    flaggers={r["model"] for r in verdicts}
    rot=ADJ[i % len(ADJ):] + ADJ[:i % len(ADJ)]        # rotate pool by claim -> lab diversity across claims
    picks=[m for m in rot if m not in flaggers] + [m for m in rot if m in flaggers]
    seen=[]
    for m in picks:
        if m not in seen: seen.append(m)
    chosen=seen[:2]
    if not any(m in ANCHORS for m in chosen):          # guarantee >=1 high-calibration anchor
        for a in (ANCHORS[i%len(ANCHORS):]+ANCHORS[:i%len(ANCHORS)]):
            if a not in flaggers and a not in chosen: chosen[-1]=a; break
        else: chosen[-1]=ANCHORS[i%len(ANCHORS)]
    return chosen

def run_unit(u):
    model, cid = u
    c=INV[cid]; verdicts=STATE[cid]["verdicts"]
    outdir=f"{REV}/reports/adjudication/{model}"; os.makedirs(outdir, exist_ok=True)
    base=f"{outdir}/p3.{cid}"
    if os.path.exists(base+".done"): return (u,"skip")
    env=dict(os.environ, OPENCODE_CONFIG=CFG, PATH="/home/gio/.opencode/bin:"+os.environ.get("PATH",""))
    try:
        r=subprocess.run(["opencode","run","--model",GEN[model]["route"],f"SYSTEM: {SYS}\n\n{usr(c,verdicts)}"],
                         capture_output=True,text=True,timeout=1000,env=env,cwd=ROOT)
        out=r.stdout+"\n"+r.stderr
    except subprocess.TimeoutExpired:
        return (u,"timeout")
    verdict=None
    for m in VJSON.finditer(out):
        try: verdict=json.loads(m.group(0)); break
        except: pass
    sqls=" ".join(SQL.findall(out)).lower()
    rec={"claim_id":cid,"chapter":c["chapter"],"model":model,"role":"ADJUDICATE",
         "verdict":(verdict or {}).get("verdict"),"queried":bool(sqls),"raw":verdict}
    tmp=tempfile.NamedTemporaryFile("w",dir=outdir,delete=False); tmp.write(json.dumps(rec)); tmp.close()
    os.replace(tmp.name, base+".jsonl"); open(base+".done","w").write("")
    return (u,"ok")

STATE=None
def main():
    global STATE
    ap=argparse.ArgumentParser(); ap.add_argument("--dry-run",action="store_true")
    a=ap.parse_args()
    STATE=reconcile()
    cats=collections.Counter(v["cat"] for v in STATE.values())
    print("reconciliation:", dict(cats))
    targets=[cid for cid,v in STATE.items() if v["cat"] in ("flagged","split","no-verdict")]
    units=[]
    for i,cid in enumerate(sorted(targets)):
        for m in assign_adj(cid, STATE[cid]["verdicts"], i):
            units.append((m,cid))
    print(f"Phase 3: {len(targets)} claims -> {len(units)} adjudication units")
    print("per-model:", dict(collections.Counter(m for m,_ in units)))
    if a.dry_run: return
    with ThreadPoolExecutor(max_workers=R["runtime"]["concurrency"]) as ex:
        for u,st in ex.map(run_unit, units):
            print(f"[{st:7}] {u[0]:16} {u[1]}")
if __name__=="__main__": main()
