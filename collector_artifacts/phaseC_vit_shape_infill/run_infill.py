# Phase C: targeted shape infill for the ViT query path (rtx_5090, vllm 0.22.0).
# Collects EXACTLY the cases the two-pool encoder cost model queries but the
# original campaign's sweep grid did not include (see cases.json, generated
# host-side against the existing parquet):
#   - encoder_attention: the s=784 line (448 px) across b=1..64, plus the
#     s=3136 (896 px) and s=12544 (1344 px) lines at feasible batches —
#     16 heads x 72 head_dim (Qwen3-VL tower geometry).
#   - bf16 GEMM: m = 784*N (block GEMMs) and m = 196*N (merger GEMMs) for
#     N=1..64 at the encoder graph's exact (n, k) pairs.
# Runs the UNMODIFIED registered runners (same invocation identity as
# collect.py), with the phase6b line-based resume checkpoint + error ledger.
# Run inside the pinned container at locked clocks:
#   docker run --rm --gpus all --ipc=host -v $AIC:/workspace \
#     -v $ARTDIR:/artifacts -w /workspace vllm/vllm-openai:v0.22.0 \
#     python /artifacts/run_infill.py
import json
import os

from collector.vllm.collect_attn_encoder import run_encoder_attention_torch
from collector.vllm.collect_gemm import run_gemm

ART = os.path.dirname(os.path.abspath(__file__))
CKPT = os.path.join(ART, "infill.done")
ERRS = os.path.join(ART, "infill_errors.jsonl")
EA_CSV = os.path.join(ART, "encoder_attention_perf.txt")
GM_CSV = os.path.join(ART, "gemm_perf.txt")

cases = json.load(open(os.path.join(ART, "cases.json")))
limit = int(os.environ.get("INFILL_LIMIT", "0"))  # smoke gate: N cases per op
if limit:
    cases = {op: lst[:limit] for op, lst in cases.items()}
done = set()
if os.path.exists(CKPT):
    done = {line.strip() for line in open(CKPT)}

errors = 0
with open(CKPT, "a") as ck, open(ERRS, "a") as ef:
    for b, s, n, h in cases["encoder_attention"]:
        key = f"ea:{b}:{s}:{n}:{h}"
        if key in done:
            continue
        try:
            run_encoder_attention_torch(b, s, n, h, perf_filename=EA_CSV,
                                        device="cuda:0")
        except Exception as e:  # noqa: BLE001 — ledgered, not hidden
            errors += 1
            ef.write(json.dumps({"case": key, "type": type(e).__name__,
                                 "msg": str(e)[:400]}) + "\n")
            ef.flush()
        ck.write(key + "\n")
        ck.flush()

    for dtype, m, n, k in cases["gemm"]:
        key = f"gemm:{dtype}:{m}:{n}:{k}"
        if key in done:
            continue
        try:
            # @with_exit_stack injects the stack; callers pass shape only.
            run_gemm(dtype, m, n, k, perf_filename=GM_CSV, device="cuda:0")
        except Exception as e:  # noqa: BLE001
            errors += 1
            ef.write(json.dumps({"case": key, "type": type(e).__name__,
                                 "msg": str(e)[:400]}) + "\n")
            ef.flush()
        ck.write(key + "\n")
        ck.flush()

print(f"infill complete: {len(done)} previously done, {errors} errors "
      f"(see {ERRS})", flush=True)
