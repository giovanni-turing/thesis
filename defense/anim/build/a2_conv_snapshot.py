#!/usr/bin/env python3
"""Run workload/trace_to_two_pool.py under the LOAD-BEARING SNAPSHOT encoder
graph: the aiconfigurator venv sits at the current data-branch HEAD, whose
guarded `encoder_patch_embed_gemm` operator POSTDATES the thesis's simulation
snapshot (Appendix 'Encoder-coverage contributions': +~0.3% of the forward at
N=64 -> f(64) 317.299 vs the ledgered 316.369 ms). This shim zeroes
`patch_embed_in_features` before ops are built, restoring the snapshot graph so
regenerated runs reproduce the ledgered endpoints exactly (588.37 ms etc.).

Usage: a2_conv_snapshot.py <trace_to_two_pool args...>
"""
import runpy
import sys
from pathlib import Path

import aiconfigurator.sdk.models.vit_ops as vit_ops

_orig = vit_ops._vit_transformer_ops


def _snapshot_ops(enc_cfg, tp_size):
    # enc_cfg is a frozen dataclass; drop the post-snapshot operator instead.
    return [op for op in _orig(enc_cfg, tp_size)
            if op._name != "encoder_patch_embed_gemm"]


vit_ops._vit_transformer_ops = _snapshot_ops

CONV = Path("/home/gio/tese/workload/trace_to_two_pool.py")
sys.argv = [str(CONV)] + sys.argv[1:]
runpy.run_path(str(CONV), run_name="__main__")
