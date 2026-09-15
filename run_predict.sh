#!/usr/bin/env bash
# run_predict.sh — 一键跑完整预测流水线
# 用法：在 DataWars 终端直接 ./run_predict.sh

set -euo pipefail
cd "$(dirname "$0")"
source .venv/bin/activate
python orchestrate.py --top-k 5