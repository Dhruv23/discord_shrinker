# shrink_all.sh

Save this file as `shrink_all.sh` next to `shrink.py`.


#!/usr/bin/env bash
set -euo pipefail

# Where shrink.py lives (this script assumes it's in the same folder)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PY_SCRIPT="${SCRIPT_DIR}/shrink.py"

# Log folder
LOG_DIR="${SCRIPT_DIR}/shrink_logs"
mkdir -p "${LOG_DIR}"

# Video extensions (common FFmpeg inputs)
# Add more if you want.
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
echo

# Track PIDs so you can monitor/kill them easily
PID_FILE="${LOG_DIR}/pids.txt"
: > "${PID_FILE}"

# Find videos, skip ones already shrunk (ends with _shrunk.<ext>), run in background
# Note: Works in WSL and Git Bash. In Git Bash, Python is usually "python".
find "${SCRIPT_DIR}" -type f \( "${FIND_EXPR[@]}" \) -print0 | while IFS= read -r -d '' file; do
  base="$(basename "$file")"

  # Skip already-shrunk outputs like something_shrunk.mp4
  if [[ "$base" == *_shrunk.* ]]; then
    continue
  fi

  # Log filename safe-ish
  safe="${base//[^A-Za-z0-9._-]/_}"
  log="${LOG_DIR}/${safe}.log"

  echo "Starting: $file"
  # Run in background, write stdout+stderr to log
  # Use python (works in most Git Bash + Windows installs). In WSL, python3 may be required.
  ( python "${PY_SCRIPT}" "$file" ) >"$log" 2>&1 &

  pid=$!
  echo "$pid  $file" >> "${PID_FILE}"
done

echo
echo "All jobs launched in background."
echo "PID list: ${PID_FILE}"
echo "Logs: ${LOG_DIR}/*.log"
