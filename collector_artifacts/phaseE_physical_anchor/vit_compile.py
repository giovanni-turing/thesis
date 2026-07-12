"""torch.compile ViT f(N) vs eager — tests whether a compiled/fused kernel beats
eager (elementwise fusion + launch removal). Bare-metal, locked 2400."""
import torch, json, time
from transformers.models.qwen3_vl.modeling_qwen3_vl import Qwen3VLVisionModel
GRID,PATCH=28,16; IN=3*2*PATCH*PATCH
def load(): return Qwen3VLVisionModel.from_pretrained("models/Qwen3-VL-8B-ViT",dtype=torch.bfloat16,attn_implementation="sdpa").cuda().eval()
def bench(model,N,iters=30,warm=8):
    grid=torch.tensor([[1,GRID,GRID]]*N,device="cuda"); px=torch.randn(GRID*GRID*N,IN,device="cuda",dtype=torch.bfloat16)
    with torch.no_grad():
        for _ in range(warm): model(px,grid_thw=grid)
        torch.cuda.synchronize(); t=[]
        for _ in range(iters):
            s=torch.cuda.Event(True); e=torch.cuda.Event(True); s.record(); model(px,grid_thw=grid); e.record(); torch.cuda.synchronize(); t.append(s.elapsed_time(e))
    return sum(t)/len(t)
m=load(); out={}
print("N   eager_ms  compiled_ms  speedup",flush=True)
mc=None
for N in [8,32,64]:
    eag=bench(m,N)
    try:
        if mc is None: mc=torch.compile(load(),mode="max-autotune")
        comp=bench(mc,N)
    except Exception as ex:
        comp=float('nan'); print("compile err:",type(ex).__name__,str(ex)[:80],flush=True)
    out[N]={'eager_ms':round(eag,2),'compiled_ms':round(comp,2),'speedup':round(eag/comp,3) if comp==comp else None}
    print(f"{N:>3} {eag:9.2f} {comp:11.2f}  {eag/comp if comp==comp else float('nan'):.3f}",flush=True)
json.dump(out,open("collector_artifacts/phaseE_physical_anchor/vit_compile.json","w"),indent=1); print("DONE",flush=True)
