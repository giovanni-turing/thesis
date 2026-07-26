#!/usr/bin/env python3
"""Phase 4 — cross-family validation of FAILURES. For every claim finalize.py marked FAIL,
a DIFFERENT strong family than the claim's adjudicators independently re-derives the verdict
from the provenance DB (2-of-N must confirm before a FAILURE stands). Guards against a single
wrong adjudication. review-db sandbox, E2 gate, resumable. Blocking-severity fails are ALSO
flagged for opus (Agent-tool) chair review, handled by the orchestrator, not here."""
import json, glob, collections, os, re, subprocess, tempfile
from concurrent.futures import ThreadPoolExecutor
REV="/home/gio/tese/review"; ROOT="/home/gio/tese"
R=json.load(open(f"{REV}/roster.active.json")); GEN=R["generators"]; CFG=R["reviewer_config"]
FAILS=[json.loads(l) for l in open(f"{REV}/final-verdicts.jsonl") if l.strip()]
FAILS=[r for r in FAILS if r["status"]=="FAIL"]

# lab family map (avoid same-family validator as adjudicator)
FAMILY={"kimi-k3":"moonshot","glm-5.2":"zhipu","qwen3.7-max":"alibaba","hy3":"tencent",
        "gemini-3.5-flash":"google","gpt-5.6-sol":"openai","deepseek-v4-pro":"deepseek",
        "mimo-v2.5":"xiaomi","minimax-m3":"minimax"}
# Phase-4 first pass: minimax (own family, funded official provider, fast, reliable DB-evidence
# 6/6 though verdict-label only 4/7 -> its OBSERVED rows are trusted, its label is advisory).
# Adjudicators were google+openai, so minimax is a genuine 3rd family. The contested set
# (splits / minimax-disagrees / blocking) then escalates to opus via the Agent tool.
VALIDATORS=["minimax-m3"]

SYS=("You independently VALIDATE an adjudicated thesis-claim FAILURE. Re-derive the verdict "
 "from the provenance DB via the review-db db_query tool (read-only) — do NOT defer to prior "
 "reasoning. Query the owning view; verify the denominator, is_current/is_superseded/_effective, "
 "and any per-fold/per-window breakdown that the failure rests on. Never invent a number.")

def usr(r):
    prior=[]
    for v in (r.get("adjudicator_verdicts") or []): prior.append(f"adjudicator={v}")
    for v in (r.get("phase2_verdicts") or []): prior.append(f"phase2={v}")
    return (f"CLAIM: {r['claim_text']}\nEXACT TEXT: \"{r['anchor']}\" (chapter {r['chapter']}, type {r['claim_type']})\n"
     f"EXPECTED BACKING: {r.get('expected_backing')}\nADJUDICATED VERDICT: {r['verdict']} (a FAILURE)\n"
     f"PRIOR (do NOT trust): {', '.join(prior)}\n\nRe-derive from the DB, then output ONE JSON:\n"
     '{"decision":"confirm|overturn|escalate","verdict":"supported|contradicted|overclaimed|inconsistent|unverifiable|holds",'
     '"query":"<exact SQL>","observed":"<DB value>","evidence":"<one line>","confidence":0.0}')

def pick_validators(r, i):
    return VALIDATORS[:]   # minimax first pass, one 3rd-family vote per FAIL; opus arbitrates contested

VJSON=re.compile(r'\{[^{}]*"decision"[^{}]*\}')
SQL=re.compile(r'db_query\s*\{"sql":"(.*?)"\}', re.S)

def run_unit(u):
    model, r = u
    outdir=f"{REV}/reports/validation/{model}"; os.makedirs(outdir, exist_ok=True)
    base=f"{outdir}/p4.{r['claim_id']}"
    if os.path.exists(base+".done"): return (model,r["claim_id"],"skip")
    env=dict(os.environ, OPENCODE_CONFIG=CFG, PATH="/home/gio/.opencode/bin:"+os.environ.get("PATH",""))
    try:
        pr=subprocess.run(["opencode","run","--model",GEN[model]["route"],f"SYSTEM: {SYS}\n\n{usr(r)}"],
                         capture_output=True,text=True,timeout=1000,env=env,cwd=ROOT)
        out=pr.stdout+"\n"+pr.stderr
    except subprocess.TimeoutExpired:
        return (model,r["claim_id"],"timeout")
    dec=None
    for m in VJSON.finditer(out):
        try: dec=json.loads(m.group(0)); break
        except: pass
    sqls=" ".join(SQL.findall(out)).lower()
    rec={"claim_id":r["claim_id"],"chapter":r["chapter"],"model":model,"role":"VALIDATE",
         "decision":(dec or {}).get("decision"),"verdict":(dec or {}).get("verdict"),
         "queried":bool(sqls),"raw":dec}
    tmp=tempfile.NamedTemporaryFile("w",dir=outdir,delete=False); tmp.write(json.dumps(rec)); tmp.close()
    os.replace(tmp.name, base+".jsonl"); open(base+".done","w").write("")
    return (model,r["claim_id"],"ok")

def main():
    import argparse
    ap=argparse.ArgumentParser(); ap.add_argument("--dry-run",action="store_true"); a=ap.parse_args()
    units=[]
    for i,r in enumerate(FAILS):
        for m in pick_validators(r,i): units.append((m,r))
    print(f"Phase 4: {len(FAILS)} FAIL claims -> {len(units)} validation units")
    print("per-model:", dict(collections.Counter(m for m,_ in units)))
    if a.dry_run: return
    workers=int(os.environ.get("WORKERS", R["runtime"]["concurrency"]))
    print(f"concurrency={workers}")
    with ThreadPoolExecutor(max_workers=workers) as ex:
        for m,cid,st in ex.map(run_unit, units):
            print(f"[{st:7}] {m:16} {cid}")
if __name__=="__main__": main()
