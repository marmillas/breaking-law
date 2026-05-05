#!/usr/bin/env bash
# -----------------------------------------------------------------------------
# Minimal linting gate for the legal platform.
#
# This script runs Python's built-in py_compile on every *.py file under
# src/ and tests/ to catch syntax errors and basic import issues.
#
# NOTE: This is a placeholder. A future iteration should integrate:
#   - ruff (linting + formatting)
#   - mypy (static type checking)
#   - bandit (security checks)
# -----------------------------------------------------------------------------

set -euo pipefail

EXIT_CODE=0

while IFS= read -r -d '' file; do
    if ! python -m py_compile "$file"; then
        echo "FAILED: $file"
        EXIT_CODE=1
    fi
done < <(find src tests -name "*.py" -print0)

if [ "$EXIT_CODE" -eq 0 ]; then
    echo "All Python files compiled successfully."
fi

exit $EXIT_CODE
