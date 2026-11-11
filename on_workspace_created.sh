#!/usr/bin/env bash
set -u

herdr_bin="${HERDR_BIN_PATH:-herdr}"
if ! command -v "$herdr_bin" >/dev/null 2>&1; then
  if [[ -x "$HOME/.local/bin/herdr" ]]; then
    herdr_bin="$HOME/.local/bin/herdr"
  fi
fi

ignore_file="/tmp/herdr_space_dir_ignore_create.tmp"

# If this workspace was created directly by our picker, ignore this event
if [[ -f "$ignore_file" ]]; then
  # Check if timestamp is within last 3 seconds
  now=$(date +%s)
  created=$(stat -c %Y "$ignore_file" 2>/dev/null || echo 0)
  diff=$((now - created))
  rm -f "$ignore_file"
  if [[ $diff -le 3 ]]; then
    exit 0
  fi
fi

ws_id="${HERDR_WORKSPACE_ID:-}"
if [[ -z "$ws_id" ]]; then
  exit 0
fi

# User clicked "+ new workspace" in Herdr UI (or created a blank workspace)
# Launch the tree picker modal to configure the folder for this new space!
exec "$herdr_bin" plugin pane open \
  --plugin space-dir \
  --entrypoint picker \
  --placement popup \
  --width "85%" \
  --height "80%" \
  --env "HERDR_TARGET_WORKSPACE_ID=$ws_id"
