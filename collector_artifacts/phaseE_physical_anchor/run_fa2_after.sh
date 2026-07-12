#!/bin/bash
cd /home/gio/tese/collector_artifacts/phaseE_physical_anchor
# wait for the running sdpa sweep to finish (uncontended GPU for clean timing)
while pgrep -f "bench_encoder_anchor.py --attn sdpa" >/dev/null; do sleep 20; done
sleep 5
/home/gio/tese/eda/.venv/bin/python bench_encoder_anchor.py --attn flash_attention_2 \
    --ns "1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17,18,19,20,21,22,23,24,25,26,27,28,29,30,31,32,33,34,35,36,37,38,39,40,41,42,43,44,45,46,47,48,49,50,51,52,53,54,55,56,57,58,59,60,61,62,63,64,96,128,192,256,512" --nruns 5 --iters 50 --warmup 10 --out anchor_dense_fa2_2400.json > dense_anchor_fa2.log 2>&1
echo "FA2_DENSE_DONE" >> dense_anchor_fa2.log
