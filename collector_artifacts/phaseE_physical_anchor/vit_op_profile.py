"""Per-op profile of the real Qwen3-VL ViT forward via torch.profiler — buckets
CUDA time into matmul / attention / elementwise / conv(patch_embed) to validate
AIC's op-composition against actual in-forward silicon time. Bare-metal, locked 2400."""
import torch, json
from collections import defaultdict
from transformers.models.qwen3_vl.modeling_qwen3_vl import Qwen3VLVisionModel
GRID, PATCH = 28, 16; IN=3*2*PATCH*PATCH
m=Qwen3VLVisionModel.from_pretrained("models/Qwen3-VL-8B-ViT",dtype=torch.bfloat16,attn_implementation="sdpa").cuda().eval()
def run(N):
    grid=torch.tensor([[1,GRID,GRID]]*N,device="cuda")
    px=torch.randn(GRID*GRID*N,IN,device="cuda",dtype=torch.bfloat16)
    with torch.no_grad():
        for _ in range(3): m(px,grid_thw=grid); torch.cuda.synchronize()
        with torch.profiler.profile(activities=[torch.profiler.ProfilerActivity.CUDA]) as p:
            for _ in range(10): m(px,grid_thw=grid)
        torch.cuda.synchronize()
    buckets=defaultdict(float)
    for e in p.key_averages():
        t=e.self_device_time_total/1e3/10  # ms per forward
        n=e.key.lower()
        if any(k in n for k in ('gemm','matmul','cutlass','ampere','sm90','sm120','linear','addmm')): buckets['matmul']+=t
        elif any(k in n for k in ('attention','flash','sdpa','fmha','softmax')): buckets['attention']+=t
        elif any(k in n for k in ('conv','patch')): buckets['conv/patch']+=t
        elif any(k in n for k in ('elementwise','norm','gelu','add','mul','layer','cast','copy')): buckets['elementwise']+=t
        else: buckets['other']+=t
    return dict(buckets)
out={}
for N in [8,32,64]:
    b=run(N); tot=sum(b.values()); out[N]={'total_ms':round(tot,2),**{k:round(v,2) for k,v in sorted(b.items(),key=lambda x:-x[1])}}
    print(f"N={N}: total={tot:.1f}ms  "+"  ".join(f"{k}={v:.1f}" for k,v in sorted(b.items(),key=lambda x:-x[1])),flush=True)
json.dump(out,open("collector_artifacts/phaseE_physical_anchor/vit_op_profile.json","w"),indent=1)
print("DONE",flush=True)
