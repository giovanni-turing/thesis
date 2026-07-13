"""Apply the MEASURED vLLM/AIC cost ratio (from the dense vLLM sweep) through the
encoder FIFO, so the rho-frontier / 0.62x can be validated on the serving-
implementation cost curve rather than inferred. Mirrors tier2_compiled.py but the
ratio comes from vllm_eager_dense.json vs the AIC composition."""
import json, sys, os
import numpy as np
A='/home/gio/tese/collector_artifacts/phaseE_physical_anchor/vllm_eager_dense.json'
d=json.load(open(A))['rows']
NS=np.array(sorted(int(k) for k in d),dtype=float)
VLLM=np.array([d[str(int(n))]['mean_ms'] for n in NS])
sys.path.insert(0,'/home/gio/tese/workload')
import trace_to_two_pool as T
_orig=T.EncoderCostModel.latency_ms
# AIC composition per N (the unscaled model) -> ratio = vLLM/AIC, interpolated
_enc_probe=None
def _aic(self,n):
    return _orig(self,int(n))[0]
def ratio_factory(self):
    aic=np.array([_orig(self,int(n))[0] for n in NS])
    r=VLLM/aic
    def ratio(n): return float(np.interp(max(1,int(n)),NS,r))
    return ratio
_RATIO={}
def wrapped(self,total_images):
    ms,tok=_orig(self,int(total_images))
    key=id(self)
    if key not in _RATIO: _RATIO[key]=ratio_factory(self)
    return ms*_RATIO[key](total_images), tok
if os.environ.get('VLLM_RATIO','1')=='1':
    T.EncoderCostModel.latency_ms=wrapped
    print(f"[vllm-ratio] applied from {len(NS)} dense points",file=sys.stderr)
sys.argv=['trace_to_two_pool']+sys.argv[1:]
T.main()
