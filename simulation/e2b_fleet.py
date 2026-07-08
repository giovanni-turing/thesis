#!/usr/bin/env python3
"""E2B fleet driver: one evaluation cell per sandbox on the tese-twopool
template, async fan-out, JSON-lines results.

Usage:
  .venv/bin/python simulation/e2b_fleet.py --cells-file cells.jsonl \
      --out results.jsonl [--concurrency 40] [--timeout 900]
Each input line is one CELL dict (see run_cell.py). Results stream to --out
as they finish (cell + result or error), so partial fleets are resumable by
diffing done cells. API key from .env / env.
"""
from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
from pathlib import Path

from dotenv import load_dotenv

load_dotenv("/home/gio/tese/.env")
from e2b_code_interpreter import AsyncSandbox  # noqa: E402

TEMPLATE = "tese-twopool"


async def run_cell(sem: asyncio.Semaphore, cell: dict, timeout: int) -> dict:
    async with sem:
        sbx = None
        try:
            sbx = await AsyncSandbox.create(TEMPLATE, timeout=timeout)
            # PYTHONPATH source tree has no dist-info; the SDK reads its own
            # version via importlib.metadata — fabricate it (template rev 2
            # will pip-install properly).
            await sbx.commands.run(
                "mkdir -p /opt/aic/src/aiconfigurator-0.10.0.dist-info && "
                "printf 'Metadata-Version: 2.1\nName: aiconfigurator\n"
                "Version: 0.10.0\n' > "
                "/opt/aic/src/aiconfigurator-0.10.0.dist-info/METADATA && "
                "python3 -m pip install --quiet pyarrow",
                timeout=240, user="root")
            # commands API: no Jupyter kernel needed (custom template does
            # not start the code-interpreter service on 49999).
            r = await sbx.commands.run(
                "python3 /opt/tese/scripts/run_cell.py",
                user="root",
                envs={"CELL": json.dumps(cell),
                      "TESE_TRACE": "/opt/tese/data/trace.csv.gz",
                      "TESE_WINDOWS": "/opt/tese/scripts/windows.json",
                      "FORECAST_PARQUET": "/opt/tese/forecasts/chronos_images.parquet",
                      "FORECAST_DIR": "/opt/tese/forecasts",
                      "PYTHONPATH": "/opt/aic/src"},
                timeout=timeout,
            )
            out = (r.stdout or "").strip().splitlines()
            if not out:
                return {"cell": cell, "error": "empty",
                        "detail": (r.stderr or "")[-400:]}
            return json.loads(out[-1])
        except Exception as e:  # noqa: BLE001
            return {"cell": cell, "error": type(e).__name__, "detail": str(e)[:300]}
        finally:
            if sbx is not None:
                try:
                    await sbx.kill()
                except Exception:  # noqa: BLE001
                    pass


async def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--cells-file", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--concurrency", type=int, default=40)
    ap.add_argument("--timeout", type=int, default=900)
    args = ap.parse_args()

    cells = [json.loads(l) for l in open(args.cells_file) if l.strip()]
    done = set()
    if os.path.exists(args.out):
        for l in open(args.out):
            try:
                done.add(json.dumps(json.loads(l)["cell"], sort_keys=True))
            except Exception:  # noqa: BLE001
                pass
    todo = [c for c in cells if json.dumps(c, sort_keys=True) not in done]
    print(f"{len(cells)} cells, {len(done)} done, running {len(todo)}", flush=True)

    sem = asyncio.Semaphore(args.concurrency)
    with open(args.out, "a") as f:
        tasks = [asyncio.create_task(run_cell(sem, c, args.timeout)) for c in todo]
        for fut in asyncio.as_completed(tasks):
            rec = await fut
            f.write(json.dumps(rec) + "\n")
            f.flush()
            tag = rec.get("cell", {})
            ok = "ERR" if "error" in rec else ("PASS" if rec.get("feasible") else "FAIL")
            print(f"  [{ok}] {tag.get('policy')}/{tag.get('window')}/"
                  f"{tag.get('quantile')}/rho{tag.get('rho')} "
                  f"p99={rec.get('p99_ms', '-')}", flush=True)
    errs = sum(1 for l in open(args.out) if "\"error\"" in l)
    print(f"fleet complete: results in {args.out} ({errs} errors)", flush=True)


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
