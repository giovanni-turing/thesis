#!/bin/bash
# dynamo 1.3.0 source build into its repo-local .venv + aiconfigurator co-residence.
set -euo pipefail
DYN=/home/gio/tese/ai-dynamo/dynamo
AIC=/home/gio/tese/ai-dynamo/aiconfigurator
export PROTOC=$HOME/.local/protoc/bin/protoc
# libclang-18 is installed without clang's own resource headers; bindgen
# (nixl-sys) needs freestanding headers (stdbool.h) — use GCC 13's builtins.
export BINDGEN_EXTRA_CLANG_ARGS="-isystem /usr/lib/gcc/x86_64-linux-gnu/13/include"
export VIRTUAL_ENV=$DYN/.venv
export PATH=$VIRTUAL_ENV/bin:$HOME/.local/bin:$PATH

step() { echo "=== STEP: $* ==="; }

step protoc; "$PROTOC" --version

step maturin-develop
cd "$DYN/lib/bindings/python"
# aic-forward-pass: the engine-timing AIC callback (dynamo._internal.aic) is
# feature-gated; the PyPI wheel ships it, default features do not.
maturin develop --uv --features aic-forward-pass || { echo "STEP_FAILED maturin"; exit 1; }

step gpu-memory-service
cd "$DYN"
uv pip install -e lib/gpu_memory_service || { echo "STEP_FAILED gms"; exit 1; }

step ai-dynamo-editable
uv pip install -e "$DYN" || { echo "STEP_FAILED ai-dynamo"; exit 1; }

step aiconfigurator-editable
uv pip install -e "$AIC" || { echo "STEP_FAILED aiconfigurator"; exit 1; }

step validate
"$VIRTUAL_ENV/bin/python" -c "import dynamo, aiconfigurator; print('imports ok')" || { echo "STEP_FAILED imports"; exit 1; }
"$VIRTUAL_ENV/bin/python" -m dynamo.replay --help > /tmp/claude-1000/-home-gio-tese/90971a3f-de36-42c1-8e55-f44080da5294/scratchpad/replay_help.txt 2>&1 || { echo "STEP_FAILED replay-help"; exit 1; }
grep -cE "planner-config|speedup|trace-format" /tmp/claude-1000/-home-gio-tese/90971a3f-de36-42c1-8e55-f44080da5294/scratchpad/replay_help.txt
echo "BUILD_CHAIN_OK"
