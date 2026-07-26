#!/usr/bin/env python3
"""Verification calibration (plan §5.1): run each generator as a VERIFIER on planted
claims with known verdicts, score verdict-accuracy + evidence-correctness (did it query
the right backing view via review-db). Gate: keep models that verify accurately.
"""
import json, os, re, subprocess, tempfile
from concurrent.futures import ThreadPoolExecutor

REV = "/home/gio/tese/review"; ROOT = "/home/gio/tese"
R = json.load(open(f"{REV}/roster.active.json"))
GEN = R["generators"]; CFG = R["reviewer_config"]
CLAIMS = json.load(open(f"{REV}/tools/verify_canary/claims.json"))
OUT = f"{REV}/tools/verify_canary/results"; os.makedirs(OUT, exist_ok=True)

SYS = ("You verify ONE thesis claim against the provenance DB (read-only, via the review-db db_query tool). "
 "Find the evidence and judge whether the data supports the claim AT THE STATED STRENGTH. Never invent a number — "
 "every number you cite must come from a db_query result. Start at v_dim, filter is_current, use v_cost_ratio for any "
 "ratio, check is_superseded/_effective. A causal 'necessarily' or a claim with no data backing is 'unverifiable'. "
 "A claim the data shows weaker/narrower than stated (or a CLAIM-STRUCTURE.md do-not-claim) is 'overclaimed'.")

def user(c):
    return (f"CLAIM: {c['claim_text']}\nEXACT TEXT: \"{c['anchor']}\" (type {c['claim_type']})\n"
            f"EXPECTED BACKING: {c['expected_backing']}\n"
            "Query the owning view with db_query, compare, then output ONE JSON object only:\n"
            '{"verdict":"supported|contradicted|overclaimed|inconsistent|unverifiable","query":"<exact SQL>",'
            '"observed":"<DB value>","claimed":"<text value>","evidence":"<one line>","confidence":0.0}')

VJSON = re.compile(r'\{[^{}]*"verdict"[^{}]*\}')
SQLCALL = re.compile(r'db_query\s*\{"sql":"(.*?)"\}', re.S)

def run(unit):
    model, c = unit
    base = f"{OUT}/{model}__{c['id']}"
    if os.path.exists(base + ".json"): return json.load(open(base + ".json"))
    env = dict(os.environ, OPENCODE_CONFIG=CFG)
    try:
        r = subprocess.run(["opencode","run","--model",GEN[model]["route"],
                            f"SYSTEM: {SYS}\n\n{user(c)}"],
                           capture_output=True, text=True, timeout=1000, env=env, cwd=ROOT)
        out = r.stdout + "\n" + r.stderr
    except subprocess.TimeoutExpired:
        out = ""
    verdict = None
    for m in VJSON.finditer(out):
        try: verdict = json.loads(m.group(0)).get("verdict"); break
        except Exception: pass
    sqls = " ".join(SQLCALL.findall(out)).lower()
    bv = c.get("backing_view")
    queried_right = (bv is not None and bv.lower() in sqls)
    res = {"model": model, "claim": c["id"], "known": c["known_verdict"],
           "got": verdict, "queried_right_view": queried_right, "any_query": bool(sqls)}
    json.dump(res, open(base + ".json", "w"))
    return res

units = [(m, c) for m in GEN for c in CLAIMS]
print(f"verification calibration: {len(GEN)} models x {len(CLAIMS)} claims = {len(units)} runs")
results = []
with ThreadPoolExecutor(max_workers=8) as ex:
    for res in ex.map(run, units):
        results.append(res)
        print(f"  {res['model']:18} {res['claim']:22} known={res['known']:12} got={str(res['got']):12} view={'Y' if res['queried_right_view'] else '-'}")

# score
def polarity(v): return "pass" if v == "supported" else ("fail" if v in ("contradicted","overclaimed","inconsistent","unverifiable") else "?")
print("\n=== SCORECARD (gate: verdict-acc>=0.7 AND evidence>=0.6) ===")
scores = {}
for m in GEN:
    rs = [r for r in results if r["model"] == m]
    exact = sum(r["got"] == r["known"] for r in rs)
    pol = sum(polarity(r["got"]) == polarity(r["known"]) for r in rs if r["got"])
    ev_claims = [r for r in rs if r["known"] != "unverifiable"]   # ones with a real backing view
    ev = sum(r["queried_right_view"] for r in ev_claims)
    va, ec = exact/len(rs), (ev/len(ev_claims) if ev_claims else 0)
    keep = va >= 0.7 and ec >= 0.6
    scores[m] = {"verdict_acc": round(va,2), "polarity": round(pol/len(rs),2), "evidence": round(ec,2), "keep": keep}
    print(f"  {'KEEP ' if keep else 'DROP '} {m:18} verdict={exact}/{len(rs)} polarity={pol}/{len(rs)} evidence={ev}/{len(ev_claims)}")
json.dump(scores, open(f"{REV}/tools/verify_canary/scores.json","w"), indent=1)
print("\nwrote scores.json")
