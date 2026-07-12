"""Compiled ViT f(N) across N -> compiled/AIC ratio curve. If ~flat ~1.13, the
residual under optimized execution is purely missing-ops (patch_embed+merger)."""
import torch, json
from transformers.models.qwen3_vl.modeling_qwen3_vl import Qwen3VLVisionModel
GRID,PATCH=28,16; IN=3*2*PATCH*PATCH
m=torch.compile(Qwen3VLVisionModel.from_pretrained("models/Qwen3-VL-8B-ViT",dtype=torch.bfloat16,attn_implementation="sdpa").cuda().eval(),mode="max-autotune")
def bench(N,iters=30,warm=8):
    grid=torch.tensor([[1,GRID,GRID]]*N,device="cuda"); px=torch.randn(GRID*GRID*N,IN,device="cuda",dtype=torch.bfloat16)
    with torch.no_grad():
        for _ in range(warm): m(px,grid_thw=grid)
        torch.cuda.synchronize(); t=[]
        for _ in range(iters):
            s=torch.cuda.Event(True); e=torch.cuda.Event(True); s.record(); m(px,grid_thw=grid); e.record(); torch.cuda.synchronize(); t.append(s.elapsed_time(e))
    return sum(t)/len(t)
out={}
for N in [4,8,16,24,32,48,64,96,128]:
    try: out[N]=round(bench(N),2); print(f"N={N} compiled={out[N]}ms",flush=True)
    except Exception as ex: print(f"N={N} ERR {type(ex).__name__}",flush=True)
json.dump(out,open("collector_artifacts/phaseE_physical_anchor/vit_compile_sweep.json","w"),indent=1); print("DONE",flush=True)
