"""Dense vLLM-eager ViT f(N): full N grid matched to the HF anchor, CIs, per-N clock.
vLLM's own Qwen3_VisionTransformer (FLASH_ATTN, eager). Random weights (latency is
shape-determined). empty_cache between N to avoid allocator accumulation."""
import os, json, statistics
os.environ.setdefault('MASTER_ADDR','127.0.0.1'); os.environ.setdefault('MASTER_PORT','12455')
os.environ.setdefault('RANK','0'); os.environ.setdefault('WORLD_SIZE','1'); os.environ.setdefault('LOCAL_RANK','0')
os.environ.setdefault('PYTORCH_CUDA_ALLOC_CONF','expandable_segments:True')
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
def smclk():
    return os.popen("nvidia-smi --query-gpu=clocks.sm --format=csv,noheader,nounits").read().strip()
NS = list(range(1,65)) + [96,128,192,256,512]
with set_current_vllm_config(VllmConfig()):
    init_distributed_environment(world_size=1, rank=0, distributed_init_method='tcp://127.0.0.1:12455', local_rank=0, backend='nccl')
    initialize_model_parallel(1,1)
    model = Qwen3_VisionTransformer(vcfg, norm_eps=1e-6, quant_config=None, prefix='visual').to('cuda').to(torch.bfloat16).eval()
    backend = str(getattr(model,'attn_backend','unknown'))
    def bench(N, nruns=5, iters=50, warm=10):
        torch.cuda.empty_cache()
        grid = torch.tensor([[1,GRID,GRID]]*N, device='cuda'); x = torch.randn(GRID*GRID*N, IN, device='cuda', dtype=torch.bfloat16)
        run_means=[]; allt=[]; clk=[]
        with torch.inference_mode():
            for _ in range(warm): model(x, grid)
            torch.cuda.synchronize()
            for r in range(nruns):
                ts=[]
                for _ in range(iters):
                    s=torch.cuda.Event(True); e=torch.cuda.Event(True); s.record(); model(x, grid); e.record(); torch.cuda.synchronize(); ts.append(s.elapsed_time(e))
                run_means.append(statistics.mean(ts)); allt+=ts; clk.append(int(smclk()))
        m=statistics.mean(run_means)
        ci=2.776*statistics.stdev(run_means)/(nruns**0.5) if nruns>1 else 0.0  # Student-t t_4=2.776, sample SD, n=5 -> 95% CI
        allt.sort()
        return {'mean_ms':round(m,4),'ci95_ms':round(ci,4),'p50_ms':round(allt[len(allt)//2],4),
                'min_ms':round(allt[0],4),'ms_per_img':round(m/N,4),'sm_clock_mhz':int(statistics.median(clk))}
    out={'attn_backend':backend,'protocol':{'nruns':5,'iters':50,'warmup':10,'image_px':448,'grid':GRID},'rows':{}}
    for N in NS:
        try:
            r=bench(N); out['rows'][N]=r
            print(f"N={N:>3} mean={r['mean_ms']:8.3f} ci95={r['ci95_ms']:.3f} sm={r['sm_clock_mhz']} ms/img={r['ms_per_img']:.3f}", flush=True)
        except Exception as ex:
            print(f"N={N} ERR {type(ex).__name__} {str(ex)[:60]}", flush=True)
    json.dump(out, open('/ws/simulation/results/silicon_anchor/reps/engine__vllm_serving/vllm_eager_dense_rerun.json','w'), indent=1)
    print("DONE", flush=True)
