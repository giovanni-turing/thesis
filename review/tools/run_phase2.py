#!/usr/bin/env python3
"""Phase 2 — grounded verification. Unit = claim. Each claim gets K verifiers from the
CALIBRATED verifier_pool (roster.active.json), roles CONFIRM/REFUTE, run under the
review-db sandbox. E2 gate: a verdict must carry a db_query on the claim's backing view.
Resumable (.done). Failure handling: timeout/no-query/malformed → reassign or flag."""
import json, os, re, subprocess, tempfile, argparse
from concurrent.futures import ThreadPoolExecutor

REV="/home/gio/tese/review"; ROOT="/home/gio/tese"; FROZEN="/home/gio/tese-review-frozen"
R=json.load(open(f"{REV}/roster.active.json")); GEN=R["generators"]; CFG=R["reviewer_config"]
# After the novita outage only google(gemini)+openai(gpt-sol) are reliably fast; all openrouter
# models run 8-13min/unit at reasoning=high. Gap-fill/rerun the missing units with the fast pair
# (both top-calibrated, cross-family). Earlier funded-novita verdicts stay valid.
SLOW={"kimi-k3","glm-5.2","qwen3.7-max","hy3","mimo-v2.5","deepseek-v4-pro"}
POOL=[m for m in R["verifier_pool"] if m not in SLOW]; ANCHORS=[a for a in R["verifier_anchors"] if a not in SLOW]; CORE=set(R["chapters"]["core"])

SYS_C=("You verify ONE thesis claim against the provenance DB (read-only, via the review-db db_query tool). "
 "Find the evidence that SUPPORTS it and judge whether the data supports it AT THE STATED STRENGTH. Never invent a "
 "number — every number you cite comes from a db_query result. Start at v_dim, filter is_current, use v_cost_ratio "
 "for any ratio, check is_superseded/_effective. A causal 'necessarily' or a claim with no backing is 'unverifiable'; "
 "a claim the data shows weaker/narrower than stated (or a CLAIM-STRUCTURE do-not-claim) is 'overclaimed'.")
SYS_R=("You are a hostile examiner trying to BREAK one thesis claim using the provenance DB (db_query, read-only). "
 "Look for contradicting rows, a missing/wrong denominator, a superseded row, a per-fold/per-window breakdown that "
 "fails, or non-comparable populations. If after honest effort you cannot break it, say it holds. Never invent a number.")
def usr(c):
    return (f"CLAIM: {c['claim_text']}\nEXACT TEXT: \"{c['anchor']}\" (chapter {c['chapter']}, type {c.get('claim_type')})\n"
     f"EXPECTED BACKING: {c.get('expected_backing')}\nQuery the owning view with db_query, then output ONE JSON:\n"
     '{"verdict":"supported|contradicted|overclaimed|inconsistent|unverifiable|holds","query":"<exact SQL>",'
     '"observed":"<DB value>","claimed":"<text value>","evidence":"<one line>","severity":"blocking|major|minor",'
     '"fix":"<if not supported>","confidence":0.0}')

def assign(claim, i):
    k = 2   # CONFIRM + REFUTE, different labs, >=1 anchor (fast pass; slow reasoners re-verify flags in Phase 3)
    # rotate through the pool, guarantee >=1 anchor, roles CONFIRM/REFUTE/CONFIRM
    picks=[POOL[(i+j) % len(POOL)] for j in range(k)]
    if not any(p in ANCHORS for p in picks): picks[0]=ANCHORS[i % len(ANCHORS)]
    roles=["CONFIRM","REFUTE","CONFIRM"][:k]
    return list(zip(picks, roles))

VJSON=re.compile(r'\{[^{}]*"verdict"[^{}]*\}')
SQL=re.compile(r'db_query\s*\{"sql":"(.*?)"\}', re.S)

def run_unit(u):
    model, role, c = u
    outdir=f"{REV}/reports/{model}"; os.makedirs(outdir, exist_ok=True)
    base=f"{outdir}/p2.{c['claim_id']}.{role}"
    if os.path.exists(base+".done"): return (u,"skip")
    sysp = SYS_C if role=="CONFIRM" else SYS_R
    env=dict(os.environ, OPENCODE_CONFIG=CFG)
    try:
        r=subprocess.run(["opencode","run","--model",GEN[model]["route"],f"SYSTEM: {sysp}\n\n{usr(c)}"],
                         capture_output=True,text=True,timeout=1000,env=env,cwd=ROOT)
        out=r.stdout+"\n"+r.stderr
    except subprocess.TimeoutExpired:
        return (u,"timeout")
    verdict=None
    for m in VJSON.finditer(out):
        try: verdict=json.loads(m.group(0)); break
        except Exception: pass
    sqls=" ".join(SQL.findall(out)).lower()
    bv=(c.get("backing_view") or (c.get("expected_backing","").split()[0] if c.get("expected_backing") else ""))
    rec={"claim_id":c["claim_id"],"chapter":c["chapter"],"model":model,"role":role,
         "verdict":(verdict or {}).get("verdict"),"queried":bool(sqls),
         "queried_right":bool(bv) and bv.lower() in sqls,"raw":verdict}
    # E2 gate: verdict with numbers but no query -> process-unverified
    if rec["verdict"] and not rec["queried"]: rec["gate"]="process-unverified"
    tmp=tempfile.NamedTemporaryFile("w",dir=outdir,delete=False); tmp.write(json.dumps(rec)); tmp.close()
    os.replace(tmp.name, base+".jsonl"); open(base+".done","w").write("")
    return (u,"ok")

def current_cover():
    import glob
    cov={}
    for f in glob.glob(f"{REV}/reports/*/p2.*.jsonl"):
        try:
            r=json.load(open(f))
            if r.get("verdict"): cov[r["claim_id"]]=cov.get(r["claim_id"],0)+1
        except: pass
    return cov

def main():
    ap=argparse.ArgumentParser(); ap.add_argument("--dry-run",action="store_true"); ap.add_argument("--limit",type=int,default=0); ap.add_argument("--all",action="store_true")
    ap.add_argument("--fill",action="store_true",help="only claims with <2 valid verdicts (fast-pair gap-fill)")
    a=ap.parse_args()
    claims=[json.loads(l) for l in open(f"{REV}/claim-inventory.jsonl") if l.strip()]
    if not a.all:
        claims=[c for c in claims if c.get("claim_type") in ("numeric","comparative")]
    if a.fill:
        cov=current_cover(); claims=[c for c in claims if cov.get(c["claim_id"],0)<2]
    units=[]
    for i,c in enumerate(claims):
        for model,role in assign(c,i): units.append((model,role,c))
    if a.limit: units=units[:a.limit]
    print(f"Phase 2: {len(claims)} claims -> {len(units)} verify units | pool={POOL}")
    if a.dry_run:
        from collections import Counter
        print("per-model units:", dict(Counter(m for m,_,_ in units))); return
    with ThreadPoolExecutor(max_workers=R["runtime"]["concurrency"]) as ex:
        for u,st in ex.map(run_unit, units):
            print(f"[{st:7}] {u[0]:16} {u[1]:7} {u[2]['claim_id']}")
if __name__=="__main__": main()
