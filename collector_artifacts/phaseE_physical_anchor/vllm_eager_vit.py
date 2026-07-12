import os, json
os.environ.setdefault('MASTER_ADDR','127.0.0.1'); os.environ.setdefault('MASTER_PORT','12401')
os.environ.setdefault('RANK','0'); os.environ.setdefault('WORLD_SIZE','1'); os.environ.setdefault('LOCAL_RANK','0')
import torch
from vllm.config import VllmConfig, set_current_vllm_config
from vllm.distributed import init_distributed_environment, initialize_model_parallel
from transformers.models.qwen3_vl.configuration_qwen3_vl import Qwen3VLVisionConfig
from vllm.model_executor.models.qwen3_vl import Qwen3_VisionTransformer
GRID, IN = 28, 3*2*16*16
vcfg = Qwen3VLVisionConfig(depth=27, hidden_size=1152, num_heads=16, intermediate_size=4304,
    out_hidden_size=4096, patch_size=16, spatial_merge_size=2, temporal_patch_size=2,
    in_channels=3, num_position_embeddings=2304, deepstack_visual_indexes=[8,16,24], hidden_act='gelu_pytorch_tanh')
torch.set_default_dtype(torch.bfloat16)
vllm_cfg = VllmConfig()
with set_current_vllm_config(vllm_cfg):
    init_distributed_environment(world_size=1, rank=0, distributed_init_method='tcp://127.0.0.1:12401', local_rank=0, backend='nccl')
    initialize_model_parallel(1,1)
    model = Qwen3_VisionTransformer(vcfg, norm_eps=1e-6, quant_config=None, prefix='visual').to('cuda').to(torch.bfloat16).eval()
    backend = getattr(model,'attn_backend', 'unknown')
    def bench(N, iters=30, warm=8):
        grid = torch.tensor([[1,GRID,GRID]]*N, device='cuda')
        x = torch.randn(GRID*GRID*N, IN, device='cuda', dtype=torch.bfloat16)
        with torch.inference_mode():
            for _ in range(warm): model(x, grid)
            torch.cuda.synchronize(); ts=[]
            for _ in range(iters):
                s=torch.cuda.Event(True); e=torch.cuda.Event(True); s.record(); model(x, grid); e.record(); torch.cuda.synchronize(); ts.append(s.elapsed_time(e))
        ts.sort(); return sum(ts)/len(ts), ts[len(ts)//2]
    out={'attn_backend':str(backend), 'sm_clock':os.popen("nvidia-smi --query-gpu=clocks.sm --format=csv,noheader,nounits").read().strip(), 'results':{}}
    for N in [8,32,64]:
        m,p50=bench(N); out['results'][N]={'vllm_eager_ms':round(m,3),'p50':round(p50,3)}
        print(f"N={N} vllm_eager={m:.2f}ms p50={p50:.2f} backend={backend}", flush=True)
    json.dump(out, open('/ws/collector_artifacts/phaseE_physical_anchor/vllm_eager_vit.json','w'), indent=1)
    print("DONE", flush=True)
