#!/usr/bin/env bash
set -euo pipefail

mode="workspace"
while [[ $# -gt 0 ]]; do
  case "$1" in
    --mode)
      mode="$2"
      shift 2
      ;;
    *)
      shift
      ;;
  esac
done

herdr_bin="${HERDR_BIN_PATH:-herdr}"
if ! command -v "$herdr_bin" >/dev/null 2>&1; then
  if [[ -x "$HOME/.local/bin/herdr" ]]; then
    herdr_bin="$HOME/.local/bin/herdr"
  fi
fi

entrypoint="picker"
case "$mode" in
  tab)
    entrypoint="tab-picker"
    ;;
  change)
    entrypoint="change-picker"
    ;;
  *)
    entrypoint="picker"
    ;;
esac

exec "$herdr_bin" plugin pane open \
  --plugin space-dir \
  --entrypoint "$entrypoint" \
  --placement popup \
  --width "85%" \
  --height "80%"
