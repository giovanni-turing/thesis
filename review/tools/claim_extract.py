#!/usr/bin/env python3
"""Phase 1 — claim extraction. Two extractors (ernie-4.5, nemotron) read each frozen
chapter and emit checkable-claim JSONL. Union + dedup + anchor-verify happens after.
Direct API (no tools needed for extraction)."""
import json, os, re, urllib.request, urllib.error, concurrent.futures
FROZEN = "/home/gio/tese-review-frozen"
OUT = "/home/gio/tese/review/claim-inventory"; os.makedirs(OUT, exist_ok=True)
ORK = json.load(open("/home/gio/snap/code/251/.local/share/opencode/auth.json"))["openrouter"]["key"]
EXTRACTORS = {"ernie": "baidu/ernie-4.5-vl-424b-a47b", "nemotron": "nvidia/nemotron-3-ultra-550b-a55b"}
CHAPTERS = ["intro","related","trace-eda","predictors","aiconfigurator","twopool",
            "baselines","closedloop","validation","conclusion","apendice"]
SYS = ("You extract checkable claims from a thesis chapter for later fact-checking against a results "
 "database. You do NOT judge them.")
def user(ch, text):
    return ('From the text, extract EVERY claim checkable against data: numbers, comparisons '
     '("X% cheaper","beats Y"), existence/behavioral results, methodology (configs/seeds/versions), '
     'citations. One JSON line each, ONLY JSON lines (no prose):\n'
     '{"anchor":"<exact quote <=240c>","claim_text":"<plain restatement>",'
     '"claim_type":"numeric|comparative|causal|existence|methodological|citation",'
     '"expected_backing":"<view/ledger/figure that would support it>"}\n'
     'Backing hints: latency->v_pool_latency; cost/ratios->v_cost_ratio; static optimum->v_grid_static_effective; '
     'SLA->v_infraction; forecast->forecast_metrics; silicon-vs-AIC->collector_encoder_fn; '
     'measured vLLM->measured_request/vllm_*; trace->eda_metric.\n=== CHAPTER '+ch+' ===\n'+text)

def run(unit):
    exn, ch = unit
    base = f"{OUT}/{exn}.{ch}.jsonl"
    if os.path.exists(base): return (unit, "skip", 0)
    text = open(f"{FROZEN}/tex/{ch}.tex").read()
    body = {"model": EXTRACTORS[exn],
            "messages": [{"role":"system","content":SYS},{"role":"user","content":user(ch,text)}],
            "max_tokens": 16000, "temperature": 0.2}
    req = urllib.request.Request("https://openrouter.ai/api/v1/chat/completions",
        json.dumps(body).encode(), {"Authorization":f"Bearer {ORK}","Content-Type":"application/json"})
    try:
        d = json.load(urllib.request.urlopen(req, timeout=1000))
        content = (d.get("choices") or [{}])[0].get("message",{}).get("content","") or ""
    except Exception as e:
        return (unit, f"err:{type(e).__name__}", 0)
    claims = []
    for m in re.finditer(r'\{[^{}]*"anchor"[^{}]*\}', content):
        try: claims.append(json.loads(m.group(0)))
        except Exception: pass
    with open(base, "w") as f:
        f.write("\n".join(json.dumps(c) for c in claims))
    return (unit, "ok", len(claims))

units = [(e, c) for e in EXTRACTORS for c in CHAPTERS]
print(f"claim extraction: {len(units)} runs (2 extractors x 11 chapters)")
with concurrent.futures.ThreadPoolExecutor(max_workers=6) as ex:
    for (e,c), st, n in ex.map(run, units):
        print(f"  {e:9} {c:16} {st:10} claims={n}")
print("done. per-file jsonl in review/claim-inventory/")
