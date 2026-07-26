#!/usr/bin/env python3
"""Phase-1 adversarial generation harness (resumable, sandboxed, review-db-grounded).

Each unit = (model, chapter, lens). Runs the model as an opencode agent under
review/tools/opencode-reviewer.jsonc (read + review-db only; edit/bash/webfetch denied),
captures its JSONL findings from stdout, and atomically writes ONE notes file per unit:
  review/reports/<model>/p1.<chapter>.<lens>.jsonl   (+ .done marker)
Resumable: units with a .done marker are skipped. Nothing is written to the thesis.

Usage:
  run_phase1.py --dry-run                # print the unit plan, run nothing
  run_phase1.py --limit 1                # harness smoke: run one real unit
  run_phase1.py                          # full Phase-1 fan-out  (THE PAID PROCEDURE)
"""
import json, os, re, sys, argparse, subprocess, tempfile
from concurrent.futures import ThreadPoolExecutor

ROOT = "/home/gio/tese"
REV = f"{ROOT}/review"
R = json.load(open(f"{REV}/roster.active.json"))
CFG = R["reviewer_config"]
GEN, ASG = R["generators"], R["assignment"]
TIMEOUT = R["runtime"]["timeout_s"]

FROZEN = os.environ.get("REVIEW_FROZEN", ROOT)  # freeze sets this to the worktree path

def units():
    out = []
    for ch in R["chapters"]["core"]:
        for lens in ASG:                       # all 8 lenses, all assigned models
            for m in ASG[lens]:
                out.append((m, ch, lens))
    for ch in R["chapters"]["context"]:
        for lens in R["context_lenses"]:       # light: primary model only
            out.append((ASG[lens][0], ch, lens))
    # de-dupe (a model can appear in two lenses' lists but never same (m,ch,lens))
    seen, uniq = set(), []
    for u in out:
        if u not in seen: seen.add(u); uniq.append(u)
    return uniq

def prompt(model, ch, lens):
    ld = R["lenses"][lens]
    return f"""You are a hostile PhD thesis examiner. Adopt lens {lens}: {ld}.
Thesis = two-pool disaggregated multimodal LLM serving (vision-encoder pool + language prefill/decode pool; encoder autoscaling under static/reactive/forecast policies; 1M-request trace via simulator; validated vs static grid sweep, RTX-5090 silicon collector, and a measured vLLM deployment). Ramp up with {REV}/THESIS-MAP.md.

TASK:
1. Read the chapter file {FROZEN}/tex/{ch}.tex (read-only).
2. For every numeric/claim you attack, VERIFY it first with the `review-db` tool `db_query(sql)` (SELECT-only over schema provenance; start at v_dim, filter is_current) and/or {ROOT}/progress/results-ledger.md. Also honour {ROOT}/defense/anim/data/_final/CLAIM-STRUCTURE.md (do-not-claim list) for lens L5.
3. Output ONLY JSON Lines (one object per line, no prose, no fences), schema:
   {{"chapter":"{ch}","lens":"{lens}","quote":"<exact text>","type":"error|overclaim|causal|inconsistency|missing-baseline|stale-number|stat|repro|threat|logic","severity":"blocking|major|minor","claim":"..","attack":"..","evidence":"<db query/citation>","fix":"..","defense":"..","confidence":0.0}}
No praise. Never invent a number. If a passage is sound, do not flag it."""

FIND = re.compile(r'\{[^{}]*"quote"[^{}]*\}')

def run_unit(u):
    model, ch, lens = u
    outdir = f"{REV}/reports/{model}"
    base = f"{outdir}/p1.{ch}.{lens}"
    if os.path.exists(base + ".done"):
        return (u, "skip", 0)
    route = GEN[model]["route"]
    env = dict(os.environ, OPENCODE_CONFIG=CFG)
    try:
        r = subprocess.run(["opencode", "run", "--model", route, prompt(model, ch, lens)],
                           capture_output=True, text=True, timeout=TIMEOUT, env=env, cwd=ROOT)
        out = r.stdout + "\n" + r.stderr
    except subprocess.TimeoutExpired:
        return (u, "timeout", 0)
    findings = []
    for m in FIND.finditer(out):
        try: findings.append(json.loads(m.group(0)))
        except Exception: pass
    tmp = tempfile.NamedTemporaryFile("w", dir=outdir, delete=False)
    tmp.write("\n".join(json.dumps(f) for f in findings)); tmp.close()
    os.replace(tmp.name, base + ".jsonl")
    open(base + ".done", "w").write("")
    return (u, "ok", len(findings))

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--concurrency", type=int, default=R["runtime"]["concurrency"])
    a = ap.parse_args()
    U = units()
    if a.limit: U = U[:a.limit]
    from collections import Counter
    print(f"Phase-1 plan: {len(U)} units | {len(set(m for m,_,_ in U))} models | "
          f"{len(set(c for _,c,_ in U))} chapters | concurrency {a.concurrency} | timeout {TIMEOUT}s")
    per_ch = Counter(c for _, c, _ in U)
    print("  units/chapter:", dict(per_ch))
    done = sum(os.path.exists(f"{REV}/reports/{m}/p1.{c}.{l}.done") for m, c, l in U)
    print(f"  already done: {done} | remaining: {len(U)-done}")
    if a.dry_run:
        for u in U[:12]: print("   -", "/".join(u))
        print("   ... (dry-run, nothing executed)"); return
    print("EXECUTING (paid).")
    tot = 0
    with ThreadPoolExecutor(max_workers=a.concurrency) as ex:
        for u, st, n in ex.map(run_unit, U):
            tot += n
            print(f"[{st:7}] {'/'.join(u):48} findings={n}")
    print(f"done. total findings={tot}")

if __name__ == "__main__":
    main()
