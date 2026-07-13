import torch, json, statistics
from transformers.models.qwen3_vl.modeling_qwen3_vl import Qwen3VLVisionModel
GRID,PATCH=28,16; IN=3*2*PATCH*PATCH
m=torch.compile(Qwen3VLVisionModel.from_pretrained("models/Qwen3-VL-8B-ViT",dtype=torch.bfloat16,attn_implementation="sdpa").cuda().eval(),mode="max-autotune")
def bench(N,nruns=3,iters=30,warm=8):
    torch.cuda.empty_cache()
    grid=torch.tensor([[1,GRID,GRID]]*N,device="cuda"); px=torch.randn(GRID*GRID*N,IN,device="cuda",dtype=torch.bfloat16)
    rm=[]
    with torch.no_grad():
        for _ in range(warm): m(px,grid_thw=grid)
        torch.cuda.synchronize()
        for _ in range(nruns):
            ts=[]
            for _ in range(iters):
                s=torch.cuda.Event(True); e=torch.cuda.Event(True); s.record(); m(px,grid_thw=grid); e.record(); torch.cuda.synchronize(); ts.append(s.elapsed_time(e))
            rm.append(statistics.mean(ts))
    return round(statistics.mean(rm),3), round(1.96*statistics.pstdev(rm)/(nruns**0.5),3)
out={}
for N in [1,2,4,6,8,12,16,24,32,48,64,96,128]:
    try: mm,ci=bench(N); out[N]={'compiled_ms':mm,'ci95':ci}; print(f"N={N} compiled={mm} ci={ci}",flush=True)
    except Exception as ex: print(f"N={N} ERR {type(ex).__name__}",flush=True)
json.dump(out,open("collector_artifacts/phaseE_physical_anchor/vit_compile_dense.json","w"),indent=1); print("DONE",flush=True)
