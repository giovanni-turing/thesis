"""Multi-engine f(N) figure for the appendix: AIC composition + HF-SDPA + HF-FA2 +
vLLM-flash (dense) + torch.compile, log-log, with the vLLM/AIC and HF/AIC ratio
panel. Shows vLLM overlapping AIC while HF sits ~1.4x above."""
import json, csv, sys, io, contextlib
import numpy as np, matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt
A='/home/gio/tese/collector_artifacts/phaseE_physical_anchor/'
def csvcurve(f):
    d={}
    for line in open(A+f):
        p=line.strip().split(',')
        if p and p[0].isdigit(): d[int(p[0])]=float(p[2])
    return d
sdpa=csvcurve('merged_sdpa.csv'); fa2=csvcurve('merged_fa2.csv')
vll={int(k):v['mean_ms'] for k,v in json.load(open(A+'vllm_eager_dense.json'))['rows'].items()}
try: comp={int(k):v['compiled_ms'] for k,v in json.load(open(A+'vit_compile_dense.json')).items()}
except Exception: comp={}
sys.path.insert(0,'/home/gio/tese/workload')
# AIC curve: prefer the load-bearing postinfill snapshot (the headline +12.7% uses it) for every N
# it covers (N<=128); fall back to the current composed model only beyond that grid. Persist the
# exact curve used so the figure is reproducible from a frozen artifact, not a live model.
POST={}
for line in open('/home/gio/tese/collector_artifacts/phaseB_batch_validation/aic_f_n_postinfill.csv'):
    p=line.strip().split(',')
    if p and p[0].isdigit(): POST[int(p[0])]=float(p[1])
with contextlib.redirect_stderr(io.StringIO()),contextlib.redirect_stdout(io.StringIO()):
    from trace_to_two_pool import EncoderCostModel; enc=EncoderCostModel(image_px=448)
    allN=sorted(set(sdpa)|set(vll)); aic={N:(POST[N] if N in POST else enc.latency_ms(N)[0]) for N in allN}
with open('/home/gio/tese/figuras/aic/aic_fn_engines_aiccurve.csv','w') as fh:
    fh.write('N,aic_ms,source\n')
    for N in allN: fh.write(f"{N},{aic[N]:.4f},{'postinfill' if N in POST else 'model_b55dd0b7'}\n")
def arr(d): 
    ns=sorted(d); return np.array(ns), np.array([d[n] for n in ns])
plt.rcParams.update({'font.size':10,'font.family':'serif'})
fig,(a1,a2)=plt.subplots(1,2,figsize=(10,4))
for name,d,c,m in [('AIC composition',aic,'#000000','-'),('HF-SDPA',sdpa,'#c1121f','-'),
                   ('HF-FA2',fa2,'#e76f51','o'),('vLLM-flash',vll,'#2a9d8f','-'),('torch.compile',comp,'#457b9d',':')]:
    if not d: continue
    n,v=arr(d)
    a1.plot(n,v,m if len(m)>1 else '-',marker=('o' if name=='HF-FA2' else None),color=c,lw=1.7,ms=4,label=name)
a1.axvline(64,color='gray',ls=':',lw=1.2)
a1.set_xscale('log',base=2); a1.set_yscale('log',base=2); a1.set_xlabel('images per forward $N$'); a1.set_ylabel('ViT forward (ms)')
a1.set_title('Encoder $f(N)$ by execution engine'); a1.legend(fontsize=8); a1.grid(alpha=0.3,which='both')
# ratio panel: engine/AIC
for name,d,c in [('HF-SDPA',sdpa,'#c1121f'),('vLLM-flash',vll,'#2a9d8f'),('torch.compile',comp,'#457b9d')]:
    if not d: continue
    n=sorted(set(d)&set(aic)); a2.plot(n,[d[x]/aic[x] for x in n],'-o' if name=='vLLM-flash' else '-',color=c,lw=1.6,ms=3,label=f'{name}/AIC')
a2.axhline(1,color='gray',ls='--',lw=1); a2.axhspan(1-0.128,1+0.128,color='#2a9d8f',alpha=0.10)
a2.axvline(64,color='gray',ls=':',lw=1.2); a2.text(64,1.66,'FIFO cap',rotation=90,va='top',ha='right',fontsize=7,color='gray')
a2.text(2,1+0.128,'$\\pm12.8\\%$',va='bottom',ha='left',fontsize=7,color='#2a9d8f')
a2.set_xscale('log',base=2); a2.set_xlabel('images per forward $N$'); a2.set_ylabel('engine / AIC'); a2.set_ylim(0.9,1.75)
a2.set_title('vLLM tracks AIC to the FIFO cap; HF is the outlier'); a2.legend(fontsize=8,loc='upper left'); a2.grid(alpha=0.3,which='both')
fig.tight_layout(); out='/home/gio/tese/figuras/aic/aic_fn_engines.pdf'; fig.savefig(out,bbox_inches='tight')
print('saved',out,'| vLLM pts',len(vll),'HF-sdpa',len(sdpa),'HF-fa2',len(fa2),'compile',len(comp))
