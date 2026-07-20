#!/usr/bin/env python3
"""Run workload/trace_to_two_pool.py with the encoder repriced under an image
SIZE MIXTURE instead of the uniform 448^2 assumption.

Same shim pattern as `a2_conv_snapshot.py` (which this supersedes for G6 runs:
`g6_sizemix` applies the identical load-bearing snapshot patch on import, so
`u448` runs here reproduce the ledgered a2 endpoints bit-for-bit). The extra
step is swapping the converter's `EncoderCostModel` for
`g6_sizemix.MixtureEncoderCostModel` *before* `main()` runs — the converter
holds the model only through the local `encoder` object, so a drop-in class
with the same surface is enough and the pool/batching/schedule logic is
untouched.

The mixture is passed in `G6_MIX` as JSON, either a catalogue name or an
explicit {px: weight} map:

    G6_MIX=mix_heavytail        g6_conv_sizemix.py --out ... --offset ...
    G6_MIX='{"448":0.8,"896":0.2}'  g6_conv_sizemix.py ...

Writes the mixture's provenance (per-op DB source tags, batch-size histogram,
mean post-merge tokens) next to the converter's own stats as
`<out>.g6mix.json`, so every repriced number carries its extrapolation status.
"""
from __future__ import annotations

import importlib.util
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

# NB: importing g6_sizemix installs the snapshot vit_ops patch. Must precede
# any import that builds encoder ops.
from g6_sizemix import (  # noqa: E402
    DISTRIBUTION_RATIONALE, DISTRIBUTIONS, SIZE_PROVENANCE,
    MixtureEncoderCostModel)

CONV = Path("/home/gio/tese/workload/trace_to_two_pool.py")


def resolve_mix(spec: str) -> tuple[str, dict[int, float]]:
    spec = (spec or "u448").strip()
    if spec in DISTRIBUTIONS:
        return spec, DISTRIBUTIONS[spec]
    raw = json.loads(spec)
    return "custom", {int(k): float(v) for k, v in raw.items()}


def main() -> None:
    name, mix = resolve_mix(os.environ.get("G6_MIX", "u448"))

    spec = importlib.util.spec_from_file_location("g6_ttp", CONV)
    mod = importlib.util.module_from_spec(spec)
    sys.modules["g6_ttp"] = mod
    spec.loader.exec_module(mod)  # defines main(), EncoderCostModel, ... (no run)

    holder: dict[str, MixtureEncoderCostModel] = {}

    def factory(_image_px, **kw):  # converter calls EncoderCostModel(args.image_px)
        m = MixtureEncoderCostModel(mix)
        holder["m"] = m
        return m

    mod.EncoderCostModel = factory

    argv = sys.argv[1:]
    sys.argv = [str(CONV)] + argv
    mod.main()

    # provenance sidecar
    m = holder.get("m")
    if m is not None:
        out = None
        for i, a in enumerate(argv):
            if a == "--out":
                out = argv[i + 1]
        if out:
            counts_by_size = {n: c for n, c in sorted(m.batch_hist.items())}
            frac = m.small_batch_fractions(8)
            Path(out + ".g6mix.json").write_text(json.dumps({
                "mixture_name": name,
                "size_distribution_provenance": SIZE_PROVENANCE,
                "size_distribution_rationale": DISTRIBUTION_RATIONALE.get(
                    name, "custom mixture supplied via G6_MIX; ASSUMED."),
                "mixture": {str(k): v for k, v in m.mix.items()},
                "pre_merge_per_image": {str(k): v for k, v in m.pre_per.items()},
                "post_merge_per_image": {str(k): v for k, v in m.post_per.items()},
                "mean_post_merge_tokens_per_image": m.tokens_per_image,
                "op_db_sources": m.op_sources,
                "extrapolated_ops": [k for k, v in m.op_sources.items()
                                     if v not in ("silicon", "empirical")],
                "distinct_batch_sizes": len(counts_by_size),
                **frac,
            }, indent=1))
            print(f"  g6 mixture: {name} {m.mix} -> {out}.g6mix.json")


if __name__ == "__main__":
    main()
