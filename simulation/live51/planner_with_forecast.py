#!/usr/bin/env python
"""Phase 5.1: the LIVE planner with the thesis's forecast_file predictor.

Importing simulation/replay_with_forecast.py registers the archived-forecast
predictor into dynamo.planner's LOAD_PREDICTORS registry (module-level side
effect); the live planner component then constructs it through the exact
same BuiltinLoadPredict path as the offline replay (same registry, same
req/isl/osl order — plugins/builtins/local_planner.py:112-115). The only
difference between offline and live is the clock and the metric source.

Env (same as offline): FORECAST_DIR/MODEL/QUANTILE/RESOLUTION/T0,
FORECAST_REQ_SCALE. Run:
  .../dynamo/.venv/bin/python planner_with_forecast.py --config <json>
"""
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import replay_with_forecast  # noqa: F401  (registers "forecast_file")

from dynamo.planner.__main__ import main  # noqa: E402

if __name__ == "__main__":
    sys.exit(main())
