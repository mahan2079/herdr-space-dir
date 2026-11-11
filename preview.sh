#!/usr/bin/env bash
set -u

raw_path="${1:-}"
if [[ -z "$raw_path" ]]; then
  exit 0
fi

target_path="${raw_path/#\~/$HOME}"

if [[ ! -e "$target_path" ]]; then
  echo -e "\033[1;33mDirectory does not exist yet.\033[0m"
  echo -e "\033[90mPath: $target_path\033[0m"
  echo ""
  echo -e "\033[1;32mPress Enter to create and open workspace here.\033[0m"
  exit 0
fi

if [[ ! -d "$target_path" ]]; then
  echo -e "\033[1;31mNot a directory:\033[0m $target_path"
  exit 0
fi

echo -e "\033[1;34m📁 $target_path\033[0m"
echo ""

# Git details if available
if command -v git >/dev/null 2>&1 && git -C "$target_path" rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  branch=$(git -C "$target_path" branch --show-current 2>/dev/null || echo "detached")
  commit=$(git -C "$target_path" log -1 --format="%h %s (%cr)" 2>/dev/null || echo "no commits")
  status_summary=$(git -C "$target_path" status --short 2>/dev/null | head -n 6 || true)

  echo -e "\033[1;35mGit Branch:\033[0m \033[1m$branch\033[0m"
  echo -e "\033[1;90mCommit:\033[0m     $commit"
  if [[ -n "$status_summary" ]]; then
    echo -e "\033[1;33mChanges:\033[0m"
    echo "$status_summary"
  fi
  echo -e "\033[90m──────────────────────────────────────────\033[0m"
fi

# Directory tree view
if command -v eza >/dev/null 2>&1; then
  eza --tree --level=2 --color=always \
    --ignore-glob ".git|.venv|node_modules|__pycache__|.cache|dist|build" \
    "$target_path" 2>/dev/null | head -n 40
else
  ls -lh --color=always "$target_path" 2>/dev/null | head -n 30
fi
