#!/usr/bin/env bash
# Run the recorded needle sequence. Private evaluation flags are documentation.
set -euo pipefail
DRY=0
if [ "${1:-}" = --dry-run ]; then DRY=1; shift; fi
BASE=${1:-http://127.0.0.1:8888}
MODEL=${2:-deepseek-v4-flash-vision-exp}
OUT=${3:-results}
SCRIPT_DIR=$(cd "$(dirname "$0")" && pwd)
if [ "$DRY" = 0 ]; then mkdir -p "$OUT"; fi
for n in 128000 245000; do
  args=(python3 "$SCRIPT_DIR/v3_1m_needle.py" --base "$BASE" --model "$MODEL" --tokens "$n" --max-tokens 1500 --timeout 1700 --out "$OUT/needle-$n.jsonl")
  if [ "$DRY" = 1 ]; then printf '%q ' "${args[@]}"; printf '\n'; else "${args[@]}"; fi
done
printf '%s\n' 'Needle chain complete; evaluation sessions are documented in docs/acceptance.md.'
