#!/usr/bin/env bash
set -euo pipefail

# --- config ---
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PY_SCRIPT="${SCRIPT_DIR}/shrink.py"

LOG_DIR="${SCRIPT_DIR}/shrink_logs"
mkdir -p "${LOG_DIR}"

# One job at a time (sequential)
MAX_JOBS=1

EXTS=(
  mp4 mov avi mkv wmv flv webm m4v mpg mpeg 3gp 3g2
  ts mts m2ts vob ogv rm rmvb asf divx
)

# Build find expression WITHOUT needing to trim trailing -o (macOS bash 3.2 safe)
FIND_EXPR=()
for ext in "${EXTS[@]}"; do
  if ((${#FIND_EXPR[@]})); then
    FIND_EXPR+=(-o)
  fi
  FIND_EXPR+=(-iname "*.${ext}")
done

echo "Searching recursively under: ${SCRIPT_DIR}"
echo "Logging to: ${LOG_DIR}"
echo "Max concurrent jobs: ${MAX_JOBS}"
echo

PID_FILE="${LOG_DIR}/pids.txt"
: > "${PID_FILE}"

# Optional: prefer python3 if available, else python
PYTHON_BIN="python"
if command -v python3 >/dev/null 2>&1; then
  PYTHON_BIN="python3"
fi

# Helper to create a safe log filename (portable)
safe_name() {
  # Replace anything not in this set with underscore
  # Works in bash 3.2+ (no extglob needed)
  local s="$1"
  s="${s//[^A-Za-z0-9._-]/_}"
  printf '%s' "$s"
}

while IFS= read -r -d '' file; do
  base="$(basename "$file")"
  dir="$(dirname "$file")"
  name="${base%.*}"

  # Skip files that are themselves shrunk outputs or temp outputs
  if [[ "$base" == *_shrunk.* || "$base" == *_shrunk__*.mp4 ]]; then
    continue
  fi

  # Skip if shrunk output already exists (shrink.py default output is mp4)
  if [[ -f "${dir}/${name}_shrunk.mp4" ]] || compgen -G "${dir}/${name}_shrunk__*.mp4" > /dev/null; then
    echo "Skipping (already shrunk exists): $file"
    continue
  fi

  safe="$(safe_name "$base")"
  log="${LOG_DIR}/${safe}.log"

  echo "Starting: $file"
  echo "---- $(date) ----" >>"$log"

  # Sequential run (no &). If it fails, continue to next file but log the failure.
  if "${PYTHON_BIN}" "${PY_SCRIPT}" "$file" >>"$log" 2>&1; then
    echo "Done: $file"
  else
    rc=$?
    echo "FAILED (exit ${rc}): $file"
    echo "FAILED (exit ${rc})" >>"$log"
    # keep going
  fi

done < <(find "${SCRIPT_DIR}" -type f \( "${FIND_EXPR[@]}" \) -print0)

echo
echo "All jobs completed (sequential)."
echo "Logs: ${LOG_DIR}/*.log"
