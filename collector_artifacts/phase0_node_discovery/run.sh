#!/bin/bash
# Phase 0: node discovery for rtx_5090 AIC system onboarding
set -e
nvidia-smi
nvidia-smi --query-gpu=name,memory.total,power.limit,clocks.max.sm,clocks.max.memory,compute_cap,driver_version --format=csv
nvidia-smi -q -d CLOCK | grep -A4 "Max Clocks"
lspci -vv 2>/dev/null | grep -A2 -i "vga.*nvidia" | head -5 || true
