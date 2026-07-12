"""Module-hook per-op profile: CUDA-event time each ViT submodule category
(patch_embed / attention / qkv+proj gemm / ffn gemm / norm+act / merger+deepstack)
to attribute the AIC residual term-by-term. Bare-metal, locked 2400."""
import torch, json, re
from collections import defaultdict
from transformers.models.qwen3_vl.modeling_qwen3_vl import Qwen3VLVisionModel
GRID,PATCH=28,16; IN=3*2*PATCH*PATCH
m=Qwen3VLVisionModel.from_pretrained("models/Qwen3-VL-8B-ViT",dtype=torch.bfloat16,attn_implementation="sdpa").cuda().eval()
def cat(name):
    n=name.lower()
    if 'patch_embed' in n: return 'patch_embed'
    if 'deepstack' in n or n.endswith('merger') or 'merger.' in n: return 'merger'
    if '.attn' in n and ('.qkv' in n or '.proj' in n): return 'attn_gemm'
    if '.attn' in n: return 'attention'
    if '.mlp' in n or 'linear_fc' in n or 'ffn' in n: return 'ffn_gemm'
    if 'norm' in n: return 'norm'
    return None
times=defaultdict(lambda:[0.0,0])
hooks=[]
for name,mod in m.named_modules():
    c=cat(name)
    if c is None or list(mod.children()): continue  # leaf modules only
    ev={}
    def pre(mod,inp,ev=ev):
        ev['s']=torch.cuda.Event(True); ev['e']=torch.cuda.Event(True); ev['s'].record()
    def post(mod,inp,out,ev=ev,c=c):
        ev['e'].record()
    hooks.append(mod.register_forward_pre_hook(pre)); hooks.append(mod.register_forward_hook(post))
# simpler: accumulate via a global list of (cat,event_pair)
evlist=[]
for h in hooks: h.remove()
hooks=[]
def mk(c):
    def pre(mod,inp):
        s=torch.cuda.Event(True); e=torch.cuda.Event(True); s.record(); mod.__ev=(s,e)
    def post(mod,inp,out):
        mod.__ev[1].record(); evlist.append((c,mod.__ev))
    return pre,post
for name,mod in m.named_modules():
    c=cat(name)
    if c is None or list(mod.children()): continue
    pre,post=mk(c); hooks.append(mod.register_forward_pre_hook(pre)); hooks.append(mod.register_forward_hook(post))
def run(N):
    global evlist
    grid=torch.tensor([[1,GRID,GRID]]*N,device="cuda"); px=torch.randn(GRID*GRID*N,IN,device="cuda",dtype=torch.bfloat16)
    with torch.no_grad():
        for _ in range(3): m(px,grid_thw=grid)
        torch.cuda.synchronize(); evlist=[]
        m(px,grid_thw=grid); torch.cuda.synchronize()
    agg=defaultdict(float)
    for c,(s,e) in evlist: agg[c]+=s.elapsed_time(e)
    return dict(agg)
out={}
for N in [8,32,64]:
    b=run(N); tot=sum(b.values()); out[N]={'sum_ops_ms':round(tot,2),**{k:round(v,2) for k,v in sorted(b.items(),key=lambda x:-x[1])}}
    print(f"N={N}: Σops={tot:.1f}ms  "+"  ".join(f"{k}={v:.1f}" for k,v in sorted(b.items(),key=lambda x:-x[1])),flush=True)
json.dump(out,open("collector_artifacts/phaseE_physical_anchor/vit_op_profile2.json","w"),indent=1)
print("DONE",flush=True)
