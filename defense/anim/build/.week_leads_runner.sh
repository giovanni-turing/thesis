#!/bin/bash
set -uo pipefail
cd /home/gio/tese/defense/anim/build
export A11_CONC=8
echo "=== gen_a11_runs.py: chronos/toto/reactive x L120,L300 ==="
python3 gen_a11_runs.py week_fc_chronos_L120 week_fc_chronos_L300 \
  week_fc_toto_L120 week_fc_toto_L300 week_reactive_L120 week_reactive_L300
echo "RC_runs=$?"
echo "=== gen_a11_timesfm.py: timesfm x L120,L300 ==="
python3 gen_a11_timesfm.py week_fc_timesfm_L120 week_fc_timesfm_L300
echo "RC_timesfm=$?"
echo "=== reports produced ==="
ls -la --time-style=+%H:%M /home/gio/tese/defense/anim/data/a11_runs/week_*L120.report.json /home/gio/tese/defense/anim/data/a11_runs/week_*L300.report.json 2>/dev/null
echo "=== DONE ==="
