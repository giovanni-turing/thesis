"""Data-immutability harness for the figure-regeneration pass.

Monkeypatches _theme.save so that building a figure serialises every plotted
value (trace x/y/z/text, plus every annotation string) to JSON instead of
writing PDFs. Run once before the regeneration (baseline) and once after; the
two dumps must be byte-identical, which proves the re-render touched only
layout/typography and never the data.

    python _datadump.py <outdir>
"""
from __future__ import annotations
import json
import os
import sys
import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)


def _norm(v):
    """Canonical JSON form for anything plotly may hold in a data attribute."""
    if v is None:
        return None
    if isinstance(v, (str, bool, int)):
        return v
    if isinstance(v, float):
        return round(v, 10)
    if isinstance(v, (np.floating,)):
        return round(float(v), 10)
    if isinstance(v, (np.integer,)):
        return int(v)
    if isinstance(v, (pd.Timestamp, np.datetime64)):
        return str(pd.Timestamp(v))
    if isinstance(v, pd.Series):
        return _norm(v.to_numpy())
    if isinstance(v, pd.Index):
        return _norm(v.to_numpy())
    if isinstance(v, np.ndarray):
        if v.dtype.kind == "M":
            return [str(pd.Timestamp(x)) for x in v]
        return [_norm(x) for x in v.tolist()]
    if isinstance(v, (list, tuple)):
        return [_norm(x) for x in v]
    if isinstance(v, dict):
        return {k: _norm(x) for k, x in v.items()}
    return str(v)


DATA_ATTRS = ("x", "y", "z", "text", "values", "labels", "base", "width",
              "customdata", "orientation", "type")


def dump(fig, name, outdir):
    rec = {"traces": [], "annotations": [], "shapes": []}
    for tr in fig.data:
        d = {"name": getattr(tr, "name", None), "cls": type(tr).__name__}
        for a in DATA_ATTRS:
            val = getattr(tr, a, None)
            if val is not None:
                d[a] = _norm(val)
        rec["traces"].append(d)
    for an in fig.layout.annotations:
        rec["annotations"].append({"text": _norm(an.text), "x": _norm(an.x),
                                   "y": _norm(an.y)})
    for sh in fig.layout.shapes:
        rec["shapes"].append({"type": _norm(sh.type), "x0": _norm(sh.x0),
                              "x1": _norm(sh.x1), "y0": _norm(sh.y0),
                              "y1": _norm(sh.y1)})
    with open(os.path.join(outdir, name + ".json"), "w") as f:
        json.dump(rec, f, indent=1, sort_keys=True, default=str)
    print("dump:", name, len(rec["traces"]), "traces",
          len(rec["annotations"]), "annotations")


def main(outdir):
    os.makedirs(outdir, exist_ok=True)
    import _theme as T
    T.save = lambda fig, name, *a, **k: (dump(fig, name, outdir), fig)[1]
    import eda, predictors, sim, aic
    eda.T.save = T.save
    predictors.T.save = T.save
    sim.T.save = T.save
    aic.T.save = T.save
    WANTED = [
        eda.fig_context_vs_numimages, eda.fig_seven_day, eda.fig_eval_windows,
        eda.fig_img_vs_req, eda.fig_burst_onsets, eda.fig_multires,
        aic.fig_aic, sim.fig_knees, sim.fig_burst_queue,
        predictors.fig_band, predictors.fig_horizon,
        predictors.fig_framework_diff, aic.fig_engines,
        predictors.fig_heatmap, predictors.fig_models_burst,
    ]
    bad = []
    for fn in WANTED:
        try:
            fn()
        except Exception as e:
            import traceback
            traceback.print_exc()
            bad.append(f"{fn.__name__}: {e!r}")
    if bad:
        print("FAILURES:", *bad, sep="\n  ")
        sys.exit(1)


if __name__ == "__main__":
    main(sys.argv[1])
