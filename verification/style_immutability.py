#!/usr/bin/env python3
"""Phase 3.5 style-pass immutability harness (shortening plan v3).

Contract: a style/readiness pass may rewrite prose but must not change any
result-bearing content. Per tex chapter this extracts, as MULTISETS:

  numbers   every numeric literal in the file (incl. \\num{...} arguments,
            percentages, table entries, layout lengths -- deliberately
            over-strict: a legitimate layout tweak requires an explicit
            baseline regen recorded in the commit message);
  refs      every \\label/\\ref/\\autoref/\\eqref/\\cref key;
  cites     every \\cite/\\citet/\\citep key (split on commas);
  envs      counts of result-bearing environments (table/longtable/figure/
            equation/align) plus \\caption count.

Modes:
  baseline  write verification/style_immutability_baseline.json from HEAD's
            working tree state
  check     re-extract and diff against the baseline; nonzero exit on ANY
            difference, with a per-file report of added/removed elements
"""
import collections
import json
import re
import sys
from pathlib import Path

TESE = Path("/home/gio/tese")
BASELINE = TESE / "verification/style_immutability_baseline.json"
CHAPTERS = ["intro", "related", "trace-eda", "predictors", "metodologia",
            "closedloop", "conclusion", "apendice", "apendice_ecosystem", "tese"]

NUM_RE = re.compile(r"\d+(?:[.,]\d+)*")
REF_RE = re.compile(r"\\(?:label|ref|autoref|eqref|cref|Cref|pageref)\{([^}]*)\}")
CITE_RE = re.compile(r"\\cite[tp]?\*?(?:\[[^\]]*\])*\{([^}]*)\}")
ENV_RE = re.compile(r"\\begin\{(table\*?|longtable|figure\*?|equation\*?|align\*?)\}")
CAP_RE = re.compile(r"\\caption")
COMMENT_RE = re.compile(r"(?<!\\)%.*")


def extract(path: Path) -> dict:
    body = "\n".join(COMMENT_RE.sub("", ln) for ln in
                     path.read_text().splitlines())
    nums = collections.Counter(NUM_RE.findall(body))
    refs = collections.Counter(REF_RE.findall(body))
    cites = collections.Counter(
        k.strip() for m in CITE_RE.findall(body) for k in m.split(","))
    envs = collections.Counter(ENV_RE.findall(body))
    envs["caption"] = len(CAP_RE.findall(body))
    return {"numbers": dict(nums), "refs": dict(refs),
            "cites": dict(cites), "envs": dict(envs)}


def snapshot() -> dict:
    return {c: extract(TESE / f"tex/{c}.tex") for c in CHAPTERS}


def diff_counter(name, base, now, out):
    b, n = collections.Counter(base), collections.Counter(now)
    for k in sorted((b - n).keys()):
        out.append(f"    -{name} {k!r} x{(b - n)[k]}")
    for k in sorted((n - b).keys()):
        out.append(f"    +{name} {k!r} x{(n - b)[k]}")


def main():
    mode = sys.argv[1] if len(sys.argv) > 1 else "check"
    if mode == "baseline":
        BASELINE.write_text(json.dumps(snapshot(), indent=1, sort_keys=True))
        print(f"baseline written: {BASELINE}")
        return 0
    base = json.loads(BASELINE.read_text())
    now = snapshot()
    bad = []
    for c in CHAPTERS:
        out = []
        for key in ("numbers", "refs", "cites", "envs"):
            diff_counter(key[:-1] if key != "envs" else "env",
                         base[c][key], now[c][key], out)
        if out:
            bad.append(f"  tex/{c}.tex:")
            bad.extend(out)
    if bad:
        print("IMMUTABILITY VIOLATION -- result-bearing content changed:")
        print("\n".join(bad))
        return 1
    print(f"immutability OK: {len(CHAPTERS)} chapters, "
          "numeric/ref/cite/env multisets identical to baseline")
    return 0


if __name__ == "__main__":
    sys.exit(main())
