#!/usr/bin/env bash
# One arm with a separate env file and failure-log capture. Cache drop is opt-in.
set -euo pipefail
label=${1:?Usage: arm.sh LABEL [VAR=value ...]}; shift
case "$label" in *[!a-zA-Z0-9_-]*|'') echo 'invalid label'; exit 1;; esac
SCRIPT_DIR=$(cd "$(dirname "$0")" && pwd)
RECIPE_DIR=${RECIPE_DIR:-./recipe}
ARM_DIR=${ARM_DIR:-./results/arms}
BASE_URL=${BASE_URL:-http://127.0.0.1:8888}
CONTAINER=${CONTAINER:-ds4-mia-vision-k22-tp1}
mkdir -p "$ARM_DIR"
ARM_DIR=$(cd "$ARM_DIR" && pwd)
envf=$ARM_DIR/$label.env
python3 - "$RECIPE_DIR/.env" "$envf" "$@" <<'PY'
import pathlib,re,sys
src,dst,*overrides=sys.argv[1:]
lines=pathlib.Path(src).read_text().splitlines()
for item in overrides:
    key,sep,value=item.partition('=')
    if not sep or not re.fullmatch('[A-Z][A-Z0-9_]*',key) or '\n' in value:
        raise SystemExit('invalid override')
    lines=[line for line in lines if not line.startswith(key+'=')]+[item]
pathlib.Path(dst).write_text('\n'.join(lines)+'\n')
PY
docker stop --time 30 "$CONTAINER" >/dev/null 2>&1 || true
docker rm -f "$CONTAINER" >/dev/null 2>&1 || true
if [ "${DROP_CACHES:-0}" = 1 ]; then
  sync
  echo 3 | sudo -n tee /proc/sys/vm/drop_caches >/dev/null
fi
capture_failure() {
  docker logs "$CONTAINER" > "$ARM_DIR/$label.docker.log" 2>&1 || true
  grep -aE 'Error|Exception|raise |assert|must be|not supported|mismatch' "$ARM_DIR/$label.docker.log" | head -8 || true
}
echo "ARM $label overrides: $*"
if ! (cd "$RECIPE_DIR" && ENV_FILE="$envf" ./launch.sh --nodes 1) > "$ARM_DIR/$label.launch.log" 2>&1; then
  echo "LAUNCH_FAIL $label"; tail -5 "$ARM_DIR/$label.launch.log"; capture_failure; exit 1
fi
t=0
until curl -fsS -m 5 "$BASE_URL/health" >/dev/null 2>&1; do
  if ! docker ps --format '{{.Names}}' | grep -qx "$CONTAINER"; then
    echo "CONTAINER_EXITED $label"; capture_failure; exit 1
  fi
  sleep "${POLL_SECONDS:-15}"; t=$((t+${POLL_SECONDS:-15}))
  if [ "$t" -gt 1800 ]; then echo "TIMEOUT $label"; capture_failure; exit 1; fi
done
echo "READY $label ${t}s"
docker inspect "$CONTAINER" --format '{{.Config.Image}}'
docker logs "$CONTAINER" > "$ARM_DIR/$label.docker.log" 2>&1
grep -aE 'revision|max_model_len|max_num_seqs|kv_cache_dtype|speculative_config|GPU KV cache size|DSpark draft model loaded' "$ARM_DIR/$label.docker.log" || true
python3 "$SCRIPT_DIR/suite.py" --base "$BASE_URL" --trials 3 --label "$label" --out "$ARM_DIR/arms.jsonl"
docker logs "$CONTAINER" > "$ARM_DIR/$label.docker.log" 2>&1
grep -aoE 'Mean acceptance length: [0-9.]+' "$ARM_DIR/$label.docker.log" | awk '{s+=$4;n++} END {if(n) printf "ACCEPT_LEN_MEAN %.2f over %d samples\n",s/n,n}' || true
