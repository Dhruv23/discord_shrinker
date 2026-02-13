#!/usr/bin/env bash
set -euo pipefail

# Where shrink.py lives (this script assumes it's in the same folder)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PY_SCRIPT="${SCRIPT_DIR}/shrink.py"

# Log folder
LOG_DIR="${SCRIPT_DIR}/shrink_logs"
mkdir -p "${LOG_DIR}"

# Limit concurrency
MAX_JOBS=3

# Video extensions (common FFmpeg inputs)
EXTS=(
  mp4 mov avi mkv wmv flv webm m4v mpg mpeg 3gp 3g2
  ts mts m2ts vob ogv rm rmvb asf divx
)

# Build a find expression: \( -iname '*.mp4' -o -iname '*.mov' ... \)
FIND_EXPR=()
for ext in "${EXTS[@]}"; do
  FIND_EXPR+=(-iname "*.${ext}" -o)
done
unset 'FIND_EXPR[-1]' # remove trailing -o

echo "Searching recursively under: ${SCRIPT_DIR}"
echo "Logging to: ${LOG_DIR}"
echo "Max concurrent jobs: ${MAX_JOBS}"
echo

# Track PIDs so you can monitor/kill them easily
PID_FILE="${LOG_DIR}/pids.txt"
: > "${PID_FILE}"

# Store PIDs of launched python processes so we can wait reliably
pids=()

# Use process substitution instead of a pipe so we DON'T run the while-loop in a subshell.
while IFS= read -r -d '' file; do
  base="$(basename "$file")"

  # Skip already-processed outputs and intermediates created by shrink.py
  # - final outputs:   *_shrunk.<ext>
  # - temp outputs:    *_shrunk__*.mp4  (and similar)
  if [[ "$base" == *_shrunk.* || "$base" == *_shrunk__*.mp4 ]]; then
    continue
  fi

  # Wait until fewer than MAX_JOBS are running
  while [ "$(jobs -r | wc -l)" -ge "$MAX_JOBS" ]; do
    sleep 1
  done

  # Log filename safe-ish
  safe="${base//[^A-Za-z0-9._-]/_}"
  log="${LOG_DIR}/${safe}.log"

  echo "Starting: $file"
  # Run in background, write stdout+stderr to log
  # Use python (works in most Git Bash + Windows installs). In WSL, python3 may be required.
  ( python "${PY_SCRIPT}" "$file" ) >"$log" 2>&1 &

  pid=$!
  pids+=("$pid")
  echo "$pid  $file" >> "${PID_FILE}"
done < <(find "${SCRIPT_DIR}" -type f \( "${FIND_EXPR[@]}" \) -print0)

# Wait for all launched Python processes (reliable because pids[] exists in this shell)
for pid in "${pids[@]}"; do
  wait "$pid" || true
done

echo
echo "All jobs completed."
echo "PID list: ${PID_FILE}"
echo "Logs: ${LOG_DIR}/*.log"
