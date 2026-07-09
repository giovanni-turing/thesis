#!/usr/bin/env python
"""Phase 5.1: LIVE planner entry for both anchor policies.

Always installs the FPM parity patch (see planner_live_patch.py); when
REGISTER_FORECAST=1, also registers the thesis's forecast_file predictor
(replay_with_forecast.py side effect) so the live planner constructs it
through the same registry/order as the offline replay.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

if os.environ.get("SKIP_PARITY_PATCH") != "1":
    import planner_live_patch  # noqa: F401

if os.environ.get("REGISTER_FORECAST") == "1":
    import replay_with_forecast  # noqa: F401

from dynamo.planner.__main__ import main  # noqa: E402

if __name__ == "__main__":
    sys.exit(main())
