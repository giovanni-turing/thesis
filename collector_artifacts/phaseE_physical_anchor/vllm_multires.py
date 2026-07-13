"""Matched-engine vLLM-vs-AIC across RESOLUTIONS: retire the '448^2 only' caveat.
Same Qwen3_VisionTransformer (FLASH_ATTN, eager), sweep (image_px, N). Random weights
(latency shape-determined). GRID=image_px/16, must be even (spatial_merge_size=2)."""
import os, json, statistics
os.environ.setdefault('MASTER_ADDR','127.0.0.1'); os.environ.setdefault('MASTER_PORT','12466')
os.environ.setdefault('RANK','0'); os.environ.setdefault('WORLD_SIZE','1'); os.environ.setdefault('LOCAL_RANK','0')
os.environ.setdefault('PYTORCH_CUDA_ALLOC_CONF','expandable_segments:True')
import torch
from vllm.config import VllmConfig, set_current_vllm_config
from vllm.distributed import init_distributed_environment, initialize_model_parallel
from transformers.models.qwen3_vl.configuration_qwen3_vl import Qwen3VLVisionConfig
from vllm.model_executor.models.qwen3_vl import Qwen3_VisionTransformer
IN = 3*2*16*16
vcfg = Qwen3VLVisionConfig(depth=27, hidden_size=1152, num_heads=16, intermediate_size=4304,
    out_hidden_size=4096, patch_size=16, spatial_merge_size=2, temporal_patch_size=2,
    in_channels=3, num_position_embeddings=2304, deepstack_visual_indexes=[8,16,24], hidden_act='gelu_pytorch_tanh')
torch.set_default_dtype(torch.bfloat16)
def smclk(): return os.popen("nvidia-smi --query-gpu=clocks.sm --format=csv,noheader,nounits").read().strip()
RES = [(14,224),(20,320),(28,448),(40,640),(56,896)]  # (GRID, image_px), GRID even
NS  = [1,2,4,8,16,32,48,64]
with set_current_vllm_config(VllmConfig()):
    init_distributed_environment(world_size=1, rank=0, distributed_init_method='tcp://127.0.0.1:12466', local_rank=0, backend='nccl')
    initialize_model_parallel(1,1)
    model = Qwen3_VisionTransformer(vcfg, norm_eps=1e-6, quant_config=None, prefix='visual').to('cuda').to(torch.bfloat16).eval()
    backend = str(getattr(model,'attn_backend','unknown'))
    def bench(GRID, N, nruns=5, iters=40, warm=8):
        torch.cuda.empty_cache()
        grid = torch.tensor([[1,GRID,GRID]]*N, device='cuda'); x = torch.randn(GRID*GRID*N, IN, device='cuda', dtype=torch.bfloat16)
        run_means=[]; clk=[]
        with torch.inference_mode():
            for _ in range(warm): model(x, grid)
            torch.cuda.synchronize()
            for r in range(nruns):
                ts=[]
                for _ in range(iters):
                    s=torch.cuda.Event(True); e=torch.cuda.Event(True); s.record(); model(x, grid); e.record(); torch.cuda.synchronize(); ts.append(s.elapsed_time(e))
                run_means.append(statistics.mean(ts)); clk.append(int(smclk()))
        m=statistics.mean(run_means); ci=2.776*statistics.stdev(run_means)/(nruns**0.5) if nruns>1 else 0.0  # Student-t t_4=2.776, sample SD, n=5
        return {'mean_ms':round(m,4),'ci95_ms':round(ci,4),'ms_per_img':round(m/N,4),'sm_clock_mhz':int(statistics.median(clk))}
    out={'attn_backend':backend,'protocol':{'nruns':5,'iters':40,'warmup':8},'rows':{}}
    for GRID,px in RES:
        for N in NS:
            try:
                r=bench(GRID,N); out['rows'][f"{px}x{N}"]=dict(r,image_px=px,grid=GRID,N=N)
                print(f"px={px:>3} N={N:>3} mean={r['mean_ms']:8.3f} ci95={r['ci95_ms']:.3f} sm={r['sm_clock_mhz']} ms/img={r['ms_per_img']:.3f}", flush=True)
            except Exception as ex:
                print(f"px={px} N={N} ERR {type(ex).__name__} {str(ex)[:60]}", flush=True)
        json.dump(out, open('/ws/collector_artifacts/phaseE_physical_anchor/vllm_multires.json','w'), indent=1)
    print("MULTIRES_DONE", flush=True)
