#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/../.."
export PYTHONPATH="$PWD/src${PYTHONPATH:+:$PYTHONPATH}"
export CUDA_VISIBLE_DEVICES="${CUDA_VISIBLE_DEVICES:-0}"
export TOKENIZERS_PARALLELISM=false
if [[ "${1:-}" == "setup" ]]; then
  uv sync --project experiments/local-checkpoint --frozen --python 3.11
  shift
  exec uv run --project experiments/local-checkpoint --frozen python -m wtrbench.paired.local_checkpoint doctor "$@"
fi
if [[ $# -eq 0 ]]; then
  echo 'Usage: bash experiments/local-checkpoint/run.sh {setup|download|check|run|report|package} [arguments]'
  exit 2
fi
exec uv run --project experiments/local-checkpoint --frozen python -m wtrbench.paired.local_checkpoint "$@"
