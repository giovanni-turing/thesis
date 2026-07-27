"""Filename -> (run_id, dimensions). Best-effort: dims are for query filtering, NULL
where a token isn't present. The authoritative dims for factorial cells come from the
JSON `cell` object (see loaders.load_factorial), not the filename.

RUN_ID RULE
-----------
Historically  run_id = "<experiment>:<stem>"  where <stem> is the basename with its
artifact suffix (.report.json / .sched.json / .requests.jsonl / ...) stripped. Several
FILE KINDS of the SAME run legitimately share a run_id -- that is how a run's report,
schedule, series and request log are joined.

That rule is only injective when a family keeps all its runs in one flat directory. It
is NOT injective for the families whose runs live in per-run SUBDIRECTORIES (a16_runs,
a16_ft/runs, predictor_closedloop_v2, ...), where the same stem ("iter3", "run.report
.json", ...) recurs under many sibling directories. Two such files used to collapse onto
one run_id and the delete-then-insert loaders then destroyed the first file's rows.

So mappings in `_DIR_EXP` carry a third field, `scoped`:

    scoped=False  ->  run_id = "<exp>:<stem>"                       (legacy, unchanged)
    scoped=True   ->  run_id = "<exp>:<seg1>:<seg2>:...:<stem>"     where seg* are the
                      path segments between the matched family directory and the file.

`scoped=True` is used ONLY for directories that previously fell through to the 'misc'
experiment (plus the not-yet-ingested a16*/g* families). Every family already loaded
under a real experiment name keeps scoped=False, so no existing run_id changes and no
existing row is orphaned.

Note `_DIR_EXP` is scanned in order and matches anywhere in the path, so the specific,
slash-anchored family directories must come before the loose legacy substrings
("reactive", "live", "grid", ...) that would otherwise swallow them.
"""
import os, re

# Files sitting directly in an ingest root belong to no family directory; map the root
# itself so they never fall through to 'misc'. Keyed by exact dirname.
_DIR_EXACT = {
    "/home/gio/tese/simulation/results": "simroot",
    "/home/gio/tese/defense/anim/data": "dataroot",
}

# (directory substring, experiment, scoped) -- checked in order, first match wins.
# Section 1: specific, slash-anchored family directories. These are the directories the
# audit found falling into 'misc' (369 runs / 14 dirs), plus the a16*/g* families that
# are still being generated on disk. All are scoped=True: their runs live in per-run
# subdirectories, so the stem alone is not unique inside the family.
_DIR_EXP_SPECIFIC = [
    # --- a16 family (fine-tuning / decode / controller-cost sweeps; NOT yet ingested)
    ("/a16_controller_cost/", "a16_controller_cost", True),
    ("/a16_decode_spread/", "a16_decode_spread", True),
    ("/a16_decode/", "a16_decode", True),
    ("/a16_ft/", "a16_ft", True),
    ("/a16_runs/", "a16", True),
    ("/a16/", "a16", True),
    # --- g families (NOT yet ingested, or ingested as 'misc')
    ("/g2_runs/", "g2", True),
    ("/g3_32b_wheelcheck/", "g3_32b_wheelcheck", True),
    ("/g3_32b/", "g3_32b", True),
    ("/g4_folds/", "g4", True),
    ("/g6_runs/", "g6", True),
    ("/g7_coldstart/", "g7", True),
    # --- simulation/results families that were 'misc'
    ("/aggregate44_rho/", "aggregate44_rho", True),
    ("/aggregate44_strict/", "aggregate44_strict", True),
    ("/aggregate44/", "aggregate44", True),
    ("/cap_sensitivity/", "cap_sensitivity", True),
    ("/predictor_closedloop_v2/", "closedloop_v2", True),
    ("/rerun_verify/", "rerun_verify", True),
    ("/srcbuild/", "srcbuild", True),
    ("/235b/", "m235b", True),
    ("/logs_idle/", "logs_idle", True),
    ("/_final/", "final", True),
    # live51's three live_runs/ arms each ship a `manager.jsonl`; unscoped they all collapse
    # onto 'live:manager'. Experiment stays 'live' so the seven already-loaded live51
    # twin_*.report.json run_ids (which sit ABOVE live_runs/) are untouched.
    ("/live51/live_runs/", "live", True),
    # --- reframe-thread families (2026-07-26): previously fell through to 'misc'
    # (selftest B: 21 unmapped dirs; C: 9 stem collisions). Files already ingested by
    # the dedicated langcalib loader stay file-gated in ingest_log and are not re-read;
    # the 5 pre-mapping 'misc:*' rows are renamed by schema/32_scope_misc_runids.sql.
    ("/encoder_hybrid/", "encoder_hybrid", True),
    ("/lang_qsweep/", "lang_qsweep", True),
    # --- decisive comparator-frontier experiment (shortening plan v3 §8.2, commit
    # 4babe1c, 2026-07-26): 725 files fell through to 'misc' (selftest B) and 313 runs
    # landed as 'misc:<stem>' (DB check C306). scoped=True is required: stems repeat
    # across calib/, eval/, eval_family/ and adversarial/. The 313 pre-mapping rows are
    # renamed by schema/36_scope_comparator_frontier_runids.sql.
    ("/comparator_frontier/", "comparator_frontier", True),
    # composed-coverage fill campaign (2026-07-26, "no economy" directive): request-linked
    # composed cells for static/steady24h/full-trace arms; scoped, stems repeat per window.
    ("/composed_fill/", "composed_fill", True),
]

# Directory names that hold a run's artifacts BY KIND rather than identifying a run:
# sweeps/traces/x.jsonl and sweeps/series/x.series.json are the same run. These segments
# are dropped from scoped run_ids and from the collision-guard scope key.
_ARTIFACT_SUBDIRS = {"traces", "series", "reports", "logs", "points", "closeout",
                     "configs", "archives", "parts", "ckpt"}

# Section 2: legacy loose substrings. DO NOT reorder or re-scope -- run_ids already in
# provenance.runs are derived from these.
_DIR_EXP_LEGACY = [
    ("/a11_runs/", "a11", False), ("/a12_runs/", "a12", False), ("/a13_runs/", "a13", False),
    ("/a14_runs/", "a14", False), ("/a15_runs/", "a15", False), ("/g1_runs/", "g1", False),
    ("/a2tf_runs/", "a2tf", False), ("/a2t_runs/", "a2t", False),
    ("/a2x_runs/", "a2x", False), ("/a2_runs/", "a2", False), ("/a6_runs/", "a6", False),
    ("factorial", "factorial", False), ("/grid/", "grid", False), ("/sweeps/", "sweeps", False),
    ("reactive", "reactive", False), ("ct_matrix", "ctmatrix", False), ("riders", "riders", False),
    ("live", "live", False), ("/predictors/", "predictors", False), ("trace_eda", "eda", False),
    ("phaseE", "phasee", False), ("phasee", "phasee", False), ("ewma", "ewma", False),
    ("episode_twins", "episode", False), ("planner", "planner", False),
    ("llm_week", "planner", False),
    ("week_matrix", "factorial", False), ("week_surface", "factorial", False),
]

_DIR_EXP = _DIR_EXP_SPECIFIC + _DIR_EXP_LEGACY

MODELS = ["chronos", "toto", "timesfm", "holt_winters", "ewma", "naive",
          "arima", "kalman", "prophet", "constant", "moirai"]

_SUFFIXES = [".requests.jsonl", ".jsonl.stats.json", ".report.json", ".sched.json",
             ".series.json", ".stats.json", ".jsonl", ".json", ".parquet", ".csv"]


def _match(path):
    """-> (matched_substring, experiment, scoped). ('', 'misc', False) if nothing matches."""
    p = path.replace("\\", "/")
    exact = _DIR_EXACT.get(os.path.dirname(p))
    if exact:
        return "", exact, False
    for sub, exp, scoped in _DIR_EXP:
        if sub in p:
            return sub, exp, scoped
    return "", "misc", False


def experiment_of(path):
    return _match(path)[1]


def stem_of(name):
    for suf in _SUFFIXES:
        if name.endswith(suf):
            return name[: -len(suf)]
    return os.path.splitext(name)[0]


def run_id_of(path):
    """Canonical run_id for a source file. See the RUN_ID RULE in the module docstring."""
    p = path.replace("\\", "/")
    sub, exp, scoped = _match(p)
    stem = stem_of(os.path.basename(p))
    if not scoped:
        return f"{exp}:{stem}"
    segs = [s for s in p.split(sub, 1)[1].split("/")[:-1]
            if s and s not in _ARTIFACT_SUBDIRS]
    return ":".join([exp] + segs + [stem])


def run_scope_key(path):
    """Files that may legitimately share a run_id: same run directory, same stem, different
    file KIND. Artifact-by-kind subdirectories are folded away first, so
    sweeps/traces/x.jsonl and sweeps/series/x.series.json share a scope. Used by the
    ingest collision guard."""
    p = path.replace("\\", "/")
    segs = [s for s in os.path.dirname(p).split("/") if s not in _ARTIFACT_SUBDIRS]
    return "/".join(segs), stem_of(os.path.basename(p))


def parse(path, kind=None, pool=None):
    exp = experiment_of(path)
    stem = stem_of(os.path.basename(path))
    s = stem.lower()
    d = {"run_id": run_id_of(path), "experiment": exp, "kind": kind,
         "source_path": path, "pool": pool}

    # window / episode
    for w in ("fulltrace", "steady24h", "aggregate", "week"):
        if w in s:
            d["window_name"] = w
            break
    m = re.search(r"burst[1-6]", s)
    if m:
        d["window_name"] = m.group(0)
    m = re.search(r"span[_-](chronos|toto|timesfm)", s)
    if m:
        d["window_name"] = "span_" + m.group(1)
    if "window_name" not in d:
        m = re.search(r"(?:^|[_-])e(\d{1,2})(?:[_-]|$)", s)
        if m:
            d["window_name"] = "e" + m.group(1)

    # policy
    if "forecast" in s or re.search(r"(?:^|[_-])fc(?:[_-]|$)", s):
        d["policy"] = "forecast"
    elif "reactive" in s or "react" in s:
        d["policy"] = "reactive"
    elif "static" in s:
        d["policy"] = "static"

    # forecaster model
    for mdl in MODELS:
        if mdl in s:
            d["model"] = mdl
            break

    # numeric tokens
    def num(pat, cast=int):
        m = re.search(pat, s)
        return cast(m.group(1)) if m else None

    d["lead_s"] = num(r"[_-]l(\d+)")
    d["cold_start_s"] = num(r"cs(\d+)")
    d["config_c"] = num(r"[_-]c(\d+)")
    d["n_replicas"] = num(r"[_-]n(\d+)")
    d["tp"] = num(r"tp(\d+)")
    d["rho"] = num(r"rho(\d+)")
    m = re.search(r"[_-](p\d{2})(?:[_-]|$)", s)
    if m:
        d["quantile"] = m.group(1)
    m = re.search(r"[_-](\d+)(s|min)(?:[_-]|$)", s)
    if m:
        d["resolution"] = m.group(1) + m.group(2)
    if "aic" in s:
        d["converter"] = "aic"
    elif "poly" in s:
        d["converter"] = "poly"

    return {k: v for k, v in d.items() if v is not None}
