#!/usr/bin/env bash
set -euo pipefail

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

python_bin="python3"
if command -v /usr/bin/python3 >/dev/null 2>&1; then
  python_bin="/usr/bin/python3"
fi

# If user explicitly requests --fzf, use fzf picker, otherwise use interactive tree GUI
use_fzf=false
args=()
for arg in "$@"; do
  if [[ "$arg" == "--fzf" ]]; then
    use_fzf=true
  else
    args+=("$arg")
  fi
done

if [[ "$use_fzf" == true ]]; then
  exec "$python_bin" "$script_dir/picker.py" "${args[@]}"
else
  exec "$python_bin" "$script_dir/tree_picker.py" "${args[@]}"
fi
