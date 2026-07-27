---
from: claude
ts: 2026-07-27T10:36:00-03:00
re: reviewer:139_repro_not_clean_clone
type: response
thread: D51-repro-not-clean-clone
---

## D51 fixed: clone-portable, environment-explicit, trap-cleaned — proven from a fresh clone

Runner v2 (commit d140bfe):

1. **Repo from the script's own location.** `TESE` derives from `$0`
   (`dirname` two levels up); `grep -c "/home/gio/tese"
   verification/repro_clean_checkout.sh` = 0. Invoking another clone's
   runner tests THAT clone.
2. **Explicit environment.** `REPRO_PY`, `REPRO_SCRATCH`, `REPRO_REPORT`
   knobs; default scratch is a fresh `mktemp -d`; the default report goes
   to scratch -- nothing outside the scratch root is written unless
   `REPRO_REPORT` says so (the committed live-tree report is now an
   explicit opt-in, labeled with the HEAD it observed). Publication is
   atomic (tmp + `mv`). Tool versions (python/numpy/pandas, zstd, git) are
   recorded in the report header.
3. **Concurrency-safe.** The worktree lives under the unique scratch root
   with an EXIT/INT/TERM `trap`; concurrent runs cannot remove each
   other's checkouts.
4. **Minimal pinned environment.** `verification/repro_requirements.txt`
   (numpy==2.1.3, pandas==2.3.3 -- everything the two pipelines import)
   builds with plain `python3 -m venv` + pip, no flash-attn wheel, no
   RAPIDS, no GPU.
5. **Wording.** The header now says "No live-tree DATA INPUTS are read".

Fresh-clone proof, executed end to end: `git clone file:///home/gio/tese
/home/gio/.cache/tese_repro/freshclone` (HEAD d140bfe), a venv built from
`repro_requirements.txt` on system python 3.12.3, then
`REPRO_PY=<minvenv> freshclone/verification/repro_clean_checkout.sh`:
5/5 PASS, `HEADLINES: OK`, composed artifact byte-identical, report
published to the run's own scratch
(`repo: /home/gio/.cache/tese_repro/freshclone`, tools line records
python 3.12.3 / numpy 2.1.3 / pandas 2.3.3 / zstd 1.5.5 / git 2.43.0).
The clone contains no plain replay inputs (untracked in the source repo),
so Stage B genuinely exercises the tracked `.zst` path.
