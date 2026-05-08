#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")"

if [ -x ".venv/bin/python" ]; then
  PYTHON=".venv/bin/python"
elif command -v python3 >/dev/null 2>&1; then
  PYTHON="python3"
elif command -v python >/dev/null 2>&1; then
  PYTHON="python"
else
  echo "No Python interpreter found. Expected .venv/bin/python, python3, or python." >&2
  exit 1
fi

echo "=== Harness Initialization ==="
echo "Python: $($PYTHON --version)"
echo ""

echo "=== Running tests ==="
"$PYTHON" -m pytest -q

echo ""
echo "=== Verification Complete ==="
echo "Next steps:"
echo "1. Read feature_list.json for current feature state"
echo "2. Pick one scoped task"
echo "3. Re-run ./init.sh before claiming done"

