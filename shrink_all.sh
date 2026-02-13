#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PY_SCRIPT="${SCRIPT_DIR}/shrink.py"

LOG_DIR="${SCRIPT_DIR}/shrink_logs"
mkdir -p "${LOG_DIR}"

MAX_JOBS=3

EXTS=(
  mp4 mov avi mkv wmv flv webm m4v mpg mpeg 3gp 3g2
  ts mts m2ts vob ogv rm rmvb asf divx
)

FIND_EXPR=()
for ext in "${EXTS[@]}"; do
  FIND_EXPR+=(-iname "*.${ext}" -o)
done
unset 'FIND_EXPR[-1]'

echo "Searching recursively under: ${SCRIPT_DIR}"
echo "Logging to: ${LOG_DIR}"
echo "Max concurrent jobs: ${MAX_JOBS}"
echo

PID_FILE="${LOG_DIR}/pids.txt"
: > "${PID_FILE}"

pids=()

while IFS= read -r -d '' file; do
  base="$(basename "$file")"
  dir="$(dirname "$file")"
  name="${base%.*}"
  ext="${base##*.}"

  # Skip already shrunk outputs
  if [[ "$base" == *_shrunk.* ]]; then
    continue
  fi

  # Skip if corresponding _shrunk file already exists
  shrunk_candidate="${dir}/${name}_shrunk.${ext}"
  if [[ -f "$shrunk_candidate" ]]; then
    echo "Skipping (already shrunk exists): $file"
    continue
  fi

  # Concurrency control
  while [ "$(jobs -r | wc -l)" -ge "$MAX_JOBS" ]; do
    sleep 1
  done

  safe="${base//[^A-Za-z0-9._-]/_}"
  log="${LOG_DIR}/${safe}.log"

  echo "Starting: $file"
  ( python "${PY_SCRIPT}" "$file" ) >"$log" 2>&1 &

  pid=$!
  pids+=("$pid")
  echo "$pid  $file" >> "${PID_FILE}"

done < <(find "${SCRIPT_DIR}" -type f \( "${FIND_EXPR[@]}" \) -print0)

# Wait for all jobs
for pid in "${pids[@]}"; do
  wait "$pid" || true
done

echo
echo "All jobs completed."
echo "PID list: ${PID_FILE}"
echo "Logs: ${LOG_DIR}/*.log"
