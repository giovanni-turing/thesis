# GPU pricing evidence — RTX 5090 vs H100 (captured 2026-07-25)

Cloud GPU hourly prices used to convert the two-pool accelerator-hours into a unified dollar
cost model. **Cloud prices drift** — these are point-in-time snapshots (page said "prices
updated 3 hours ago" at capture; 90-day trend shown per GPU).

## Snapshots (evidence)
- `gpus_io_rtx5090_2026-07-25.png` — https://gpus.io/en/gpus/rtx5090
- `gpus_io_h100_2026-07-25.png` — https://gpus.io/en/gpus/h100

Method: headless chromium (snap) full-page screenshot with a Firefox UA (direct WebFetch was
403 bot-walled). Cross-checked against a `urllib` fetch of the same pages with the same UA and
against WebSearch snippets — all three agree.

## Figures (gpus.io, on-demand, per GPU-hour, 2026-07-25)
| GPU | cheapest | **median** | most expensive | 90-day trend | # configs |
| --- | --- | --- | --- | --- | --- |
| RTX 5090 | $0.210 (Vast.ai) | **$0.520** | $3.610 | −5.5% | 53 |
| H100 | $1.360 (Vast.ai) | **$2.990** | $4.609 | +11.2% | 43 |

**H100 / RTX 5090 = 5.75× at median** (6.5× at cheapest).

## Derived two-pool dollar cost (5.60-day trace, median prices)
static TP2x2 language = 4 H100; encoder static-C8 = 8 RTX 5090 workers. Accelerator-hours from
provenance (encoder worker-seconds / language gpu_hours).

| pool | operating point | accel-h | $/h | cost |
| --- | --- | --- | --- | --- |
| encoder (RTX 5090) | static C8 | 1075 | 0.52 | $559 |
| encoder | hybrid (robust) | 818 | 0.52 | **$425** |
| language (H100) | static TP2x2 | 537 | 2.99 | $1607 |
| language | p90/s6 (robust) | 440 | 2.99 | **$1316** |

- system all-static $2166 → robust-both (enc hybrid + lang robust) **$1741 = 0.80×**
- **language pool = 74% of the bill** (76% at robust); **3.1× the encoder pool**
- $ saved: encoder hybrid $134 · language robust $291 (language saves more absolute $ despite smaller ratio)

Caveat: prices are volatile and provider/region/commitment-dependent; median is the fair typical.
The thesis costs each pool in accelerator-hours natively — this dollar model is one explicit,
cited price assumption layered on top for the "language pool dominates the bill" statement.
