# Thin driver: run the registered vllm gemm collector over the bf16 subset only.
# Rationale: ViT ops are bf16-only (vit_ops.py); collect.py has no dtype filter.
# Uses the unmodified registered getter+runner (same invocation identity and
# logging path as collect.py) with a simple line-based resume checkpoint.
import json
import os
import sys

import torch

from collector.vllm.collect_gemm import get_gemm_test_cases, run_gemm

CKPT = "/workspace/collector_checkpoints/vllm/0.22.0/gemm_bf16.done"
ERRS = "/workspace/collector_logs/vllm/0.22.0/gemm_bf16_errors.jsonl"
os.makedirs(os.path.dirname(CKPT), exist_ok=True)
os.makedirs(os.path.dirname(ERRS), exist_ok=True)

done = set()
if os.path.exists(CKPT):
    with open(CKPT) as f:
        done = {line.strip() for line in f}

cases = [c for c in get_gemm_test_cases() if c[0] == "bfloat16"]
limit = int(sys.argv[1]) if len(sys.argv) > 1 else None
todo = [c for c in cases if repr(c) not in done]
if limit:
    todo = todo[:limit]
print(f"bf16 cases: {len(cases)} total, {len(done)} done, running {len(todo)}", flush=True)

# Pre-skip shapes that cannot fit on a 32GB card: repeated OOM churn corrupts
# CUDA-graph state in the collector and eventually segfaults the process.
# 2*(M*K + K*N + M*N) bytes is the bf16 tensor footprint alone; the collector's
# graph pools and dual buffers multiply that, so use a conservative 4GB cutoff.
OOM_CUTOFF_BYTES = 4 * 1024**3

errors = skipped = 0
with open(CKPT, "a") as ck, open(ERRS, "a") as ef:
    for i, case in enumerate(todo):
        _, m, n, k = case
        if 2 * (m * k + k * n + m * n) > OOM_CUTOFF_BYTES:
            skipped += 1
            ef.write(json.dumps({"case": case, "type": "SkippedResource",
                                 "msg": "pre-skipped: exceeds 32GB-card footprint cutoff"}) + "\n")
            ef.flush()
            ck.write(repr(case) + "\n")
            ck.flush()
            continue
        try:
            run_gemm(*case, perf_filename="gemm_perf.txt", device="cuda:0")
        except Exception as e:
            errors += 1
            ef.write(json.dumps({"case": case, "type": type(e).__name__,
                                 "msg": str(e)[:300]}) + "\n")
            ef.flush()
            torch.cuda.empty_cache()
        ck.write(repr(case) + "\n")
        ck.flush()
        if (i + 1) % 500 == 0:
            print(f"{i+1}/{len(todo)} done, {errors} errors, {skipped} skipped", flush=True)

print(f"finished: {len(todo)} cases, {errors} errors", flush=True)
