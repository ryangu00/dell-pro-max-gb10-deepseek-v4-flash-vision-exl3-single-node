#!/usr/bin/env bash
# Move a completed download into the cache layout and write the reference env.
set -euo pipefail
SOURCE_DIR=${1:?Usage: ve-finalize-layout.sh SOURCE_DIR HF_CACHE RECIPE_DIR DOWNLOAD_LOG}
HF_CACHE_DIR=${2:?HF cache directory required}
RECIPE_DIR=${3:?Recipe directory required}
DOWNLOAD_LOG=${4:?Download log required; success marker is DL_EXIT=0}
R=wrldsuksgo2mars/DeepSeek-V4-Flash-Vision-Exp-EXL3-K2.2-D2-v1
REV=8347bfb8776287ef2dcab2b46e9f15c655825c3a
grep -qx 'DL_EXIT=0' "$DOWNLOAD_LOG" || { echo 'download not finished/ok'; exit 1; }
mkdir -p "$HF_CACHE_DIR" "$RECIPE_DIR"
HF_CACHE_DIR=$(cd "$HF_CACHE_DIR" && pwd)
D=$HF_CACHE_DIR/hub/models--${R//\//--}
mkdir -p "$D/snapshots" "$D/refs"
if [ ! -e "$D/snapshots/$REV" ]; then
  mv "$SOURCE_DIR" "$D/snapshots/$REV"
  rm -rf "$D/snapshots/$REV/.cache"
fi
printf '%s\n' "$REV" > "$D/refs/main"
SCRIPT_DIR=$(cd "$(dirname "$0")" && pwd)
python3 - "$SCRIPT_DIR/../configs/reference.env" "$RECIPE_DIR/.env" "$HF_CACHE_DIR" <<'PY'
import pathlib, shlex, sys
source, target, cache = sys.argv[1:]
s = pathlib.Path(source).read_text().replace('HF_CACHE=./hf', 'HF_CACHE=' + shlex.quote(cache))
pathlib.Path(target).write_text(s)
PY
printf '%s\n' 'LAYOUT_DONE' '.env written'
