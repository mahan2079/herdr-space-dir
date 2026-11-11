#!/usr/bin/env python3
"""
Herdr Space Directory Picker Plugin
Interactive directory chooser for Herdr workspaces (spaces) and tabs.
"""

import sys
import os
import json
import shlex
import subprocess
import readline

def get_herdr_bin():
    herdr_bin = os.environ.get("HERDR_BIN_PATH")
    if herdr_bin and os.path.isfile(herdr_bin) and os.access(herdr_bin, os.X_OK):
        return herdr_bin
    local_bin = os.path.expanduser("~/.local/bin/herdr")
    if os.path.isfile(local_bin) and os.access(local_bin, os.X_OK):
        return local_bin
    return "herdr"

def get_context():
    raw = os.environ.get("HERDR_PLUGIN_CONTEXT_JSON")
    if raw:
        try:
            return json.loads(raw)
        except Exception:
            pass
    return {}

def load_config():
    config_dir = os.environ.get("HERDR_PLUGIN_CONFIG_DIR") or os.path.expanduser("~/.config/herdr/plugins/config/space-dir")
    config_file = os.path.join(config_dir, "config.json")
    default_config = {
        "search_dirs": ["~/Work", "~/Projects", "~", "~/Documents", "~/Downloads"],
        "search_depth": 3,
        "prompt_label": False,
        "preview": True
    }
    if os.path.isfile(config_file):
        try:
            with open(config_file, "r") as f:
                user_config = json.load(f)
                default_config.update(user_config)
        except Exception:
            pass
    return default_config

def get_history():
    state_dir = os.environ.get("HERDR_PLUGIN_STATE_DIR") or os.path.expanduser("~/.local/state/herdr/plugins/space-dir")
    history_file = os.path.join(state_dir, "history.txt")
    if os.path.isfile(history_file):
        try:
            with open(history_file, "r") as f:
                return [line.strip() for line in f if line.strip() and os.path.isdir(os.path.expanduser(line.strip()))]
        except Exception:
            pass
    return []

def save_history(path):
    state_dir = os.environ.get("HERDR_PLUGIN_STATE_DIR") or os.path.expanduser("~/.local/state/herdr/plugins/space-dir")
    os.makedirs(state_dir, exist_ok=True)
    history_file = os.path.join(state_dir, "history.txt")
    existing = get_history()
    # Bring to front
    new_hist = [path] + [p for p in existing if p != path]
    new_hist = new_hist[:20]
    try:
        with open(history_file, "w") as f:
            for p in new_hist:
                f.write(p + "\n")
    except Exception:
        pass

def collect_candidates(context, config):
    candidates = []
    seen = set()

    def add_path(p):
        if not p:
            return
        abs_p = os.path.abspath(os.path.expanduser(p))
        if abs_p not in seen and os.path.isdir(abs_p):
            seen.add(abs_p)
            candidates.append(abs_p)

    # 1. Current active directory from context
    curr_cwd = context.get("focused_pane_cwd") or context.get("workspace_cwd")
    if curr_cwd:
        add_path(curr_cwd)

    # 2. History
    for p in get_history():
        add_path(p)

    # 3. Discovered storage drives (500GB SSD, external drives)
    from tree_picker import discover_drives
    drives = discover_drives()
    for d in drives:
        add_path(d["path"])
        # Add immediate subdirectories of secondary storage
        if d["path"] != "/":
            try:
                for entry in sorted(os.listdir(d["path"])):
                    if not entry.startswith(".") and entry != "lost+found":
                        add_path(os.path.join(d["path"], entry))
            except Exception:
                pass

    # 4. Base directories in config
    home = os.path.expanduser("~")
    for base in config.get("search_dirs", []):
        add_path(base)

    # 5. Immediate subdirectories of ~/Work and ~/Projects
    for base in [os.path.join(home, "Work"), os.path.join(home, "Projects")]:
        if os.path.isdir(base):
            try:
                for entry in sorted(os.listdir(base)):
                    if not entry.startswith("."):
                        add_path(os.path.join(base, entry))
            except Exception:
                pass

    # 6. Git repositories in search bases (depth <= 4)
    drive_paths = [d["path"] for d in drives if d["path"] not in ("/", home)]
    search_roots = [os.path.expanduser(d) for d in config.get("search_dirs", []) if os.path.isdir(os.path.expanduser(d))] + drive_paths
    try:
        fd_cmd = ["fd", "-t", "d", "-H", r"^\.git$", "-E", ".Trash*", "-E", "lost+found"] + search_roots + ["-d", "4", "-x", "dirname", "{}"]
        res = subprocess.run(fd_cmd, capture_output=True, text=True, timeout=3)
        if res.returncode == 0:
            for line in res.stdout.strip().splitlines():
                add_path(line.strip())
    except Exception:
        pass

    # 6. Deep subdirectories up to search_depth
    depth = config.get("search_depth", 3)
    if depth > 1 and search_roots:
        try:
            fd_cmd = ["fd", "-t", "d", "--max-depth", str(depth), "-E", "node_modules", "-E", ".venv", "-E", "__pycache__", "-E", ".git", "-E", ".cache", "-E", "dist", "-E", "build", "-E", ".Trash*", "-E", "lost+found"] + search_roots
            res = subprocess.run(fd_cmd, capture_output=True, text=True, timeout=3)
            if res.returncode == 0:
                for line in res.stdout.strip().splitlines():
                    add_path(line.strip())
        except Exception:
            pass

    # Format for display: replace $HOME with ~
    display_candidates = []
    for p in candidates:
        if p == home:
            display_candidates.append("~")
        elif p.startswith(home + "/"):
            display_candidates.append("~" + p[len(home):])
        else:
            display_candidates.append(p)

    return display_candidates

def run_fzf(candidates, mode, plugin_dir):
    preview_script = os.path.join(plugin_dir, "preview.sh")
    
    if mode == "workspace":
        header = "[Enter] Open Space | [Ctrl-T] Tree View | [Ctrl-L] Custom Label | [Ctrl-N] New Subfolder | [?] Preview | [Esc] Cancel"
        prompt = "Create Space in Dir > "
    elif mode == "tab":
        header = "[Enter] Open Tab | [Ctrl-T] Tree View | [Ctrl-N] New Subfolder | [?] Preview | [Esc] Cancel"
        prompt = "Create Tab in Dir > "
    elif mode == "change":
        header = "[Enter] Switch Current Space Dir | [Ctrl-T] Tree View | [?] Preview | [Esc] Cancel"
        prompt = "Switch Space to Dir > "
    else:
        header = "[Enter] Select | [Ctrl-T] Tree View | [?] Preview | [Esc] Cancel"
        prompt = "Select Dir > "

    fzf_cmd = [
        "fzf",
        "--prompt=" + prompt,
        "--header=" + header,
        "--layout=reverse",
        "--border=rounded",
        "--info=inline",
        "--height=100%",
        "--print-query",
        "--expect=ctrl-l,ctrl-n,ctrl-y,alt-enter,ctrl-t",
        f"--preview=bash {shlex.quote(preview_script)} {{}}",
        "--preview-window=right:45%:hidden:wrap",
        "--bind=?:toggle-preview",
    ]

    input_data = "\n".join(candidates) + "\n"
    res = subprocess.run(fzf_cmd, input=input_data, text=True, capture_output=True)

    # Exit code 130 or 1 usually means Esc/Ctrl-C
    lines = res.stdout.split("\n")
    query = lines[0] if len(lines) > 0 else ""
    key = lines[1] if len(lines) > 1 else ""
    selected = lines[2] if len(lines) > 2 else ""

    if res.returncode != 0 and not key and not selected:
        return None, None

    return key, (selected or query)

def main():
    mode = "workspace"
    args = sys.argv[1:]
    if "--mode" in args:
        idx = args.index("--mode")
        if idx + 1 < len(args):
            mode = args[idx + 1]

    plugin_dir = os.path.dirname(os.path.abspath(__file__))
    herdr_bin = get_herdr_bin()
    context = get_context()
    config = load_config()

    candidates = collect_candidates(context, config)

    key, chosen_path = run_fzf(candidates, mode, plugin_dir)
    if key == "ctrl-t":
        # Switch to tree view
        tree_script = os.path.join(plugin_dir, "tree_picker.py")
        os.execlp("python3", "python3", tree_script, "--mode", mode)

    if not chosen_path or not chosen_path.strip():
        # User cancelled
        sys.exit(0)

    chosen_path = chosen_path.strip()
    # Expand ~
    home = os.path.expanduser("~")
    if chosen_path == "~":
        target_dir = home
    elif chosen_path.startswith("~/"):
        target_dir = os.path.join(home, chosen_path[2:])
    else:
        target_dir = os.path.abspath(os.path.expanduser(chosen_path))

    # If key is ctrl-n, user wants to create a subfolder under target_dir
    if key == "ctrl-n":
        print(f"\033[1;34mTarget parent directory:\033[0m {target_dir}")
        try:
            sub = input("\033[1;32mNew subfolder name: \033[0m").strip()
            if sub:
                target_dir = os.path.join(target_dir, sub)
            else:
                print("Cancelled.")
                sys.exit(0)
        except (KeyboardInterrupt, EOFError):
            sys.exit(0)

    # Check if target directory exists
    if not os.path.isdir(target_dir):
        print(f"\033[1;33mDirectory does not exist:\033[0m {target_dir}")
        try:
            ans = input("\033[1;32mCreate directory? [Y/n]: \033[0m").strip().lower()
            if ans and ans not in ("y", "yes"):
                print("Aborted.")
                sys.exit(0)
            os.makedirs(target_dir, exist_ok=True)
            print(f"\033[32mCreated {target_dir}\033[0m")
        except (KeyboardInterrupt, EOFError):
            sys.exit(0)

    # Save to history
    save_history(target_dir)

    # Default workspace / tab label
    if target_dir == home:
        default_label = "~"
    else:
        default_label = os.path.basename(target_dir)

    label = default_label
    # If user pressed Ctrl-L or prompt_label is true, ask for custom label
    if (key == "ctrl-l" or config.get("prompt_label")) and mode in ("workspace", "tab"):
        readline.set_startup_hook(lambda: readline.insert_text(default_label))
        try:
            custom_label = input(f"\033[1;34mSpace label\033[0m [\033[90m{default_label}\033[0m]: ").strip()
            if custom_label:
                label = custom_label
        except (KeyboardInterrupt, EOFError):
            pass
        finally:
            readline.set_startup_hook(None)

    # Perform creation / change
    target_workspace_id = os.environ.get("HERDR_TARGET_WORKSPACE_ID")
    if target_workspace_id:
        pane_id = None
        try:
            res = subprocess.run([herdr_bin, "pane", "list", "--workspace", target_workspace_id], capture_output=True, text=True)
            if res.returncode == 0:
                data = json.loads(res.stdout)
                panes = data.get("result", {}).get("panes", [])
                if panes:
                    pane_id = panes[0].get("pane_id")
        except Exception:
            pass

        if pane_id:
            subprocess.run([herdr_bin, "pane", "run", pane_id, f"cd {shlex.quote(target_dir)} && clear"], check=True)
        if label != "~":
            subprocess.run([herdr_bin, "workspace", "rename", target_workspace_id, label], check=False)
        subprocess.run([herdr_bin, "workspace", "focus", target_workspace_id], check=False)
        sys.exit(0)

    if mode == "workspace":
        try:
            import time
            with open("/tmp/herdr_space_dir_ignore_create.tmp", "w") as f:
                f.write(str(time.time()))
        except Exception:
            pass

        cmd = [herdr_bin, "workspace", "create", "--cwd", target_dir, "--label", label, "--focus"]
        try:
            subprocess.run(cmd, check=True)
        except subprocess.CalledProcessError as e:
            print(f"\033[1;31mFailed to create workspace:\033[0m {e}", file=sys.stderr)
            sys.exit(1)

    elif mode == "tab":
        cmd = [herdr_bin, "tab", "create", "--cwd", target_dir, "--label", label, "--focus"]
        try:
            subprocess.run(cmd, check=True)
        except subprocess.CalledProcessError as e:
            print(f"\033[1;31mFailed to create tab:\033[0m {e}", file=sys.stderr)
            sys.exit(1)

    elif mode == "change":
        # Change current pane directory and optionally rename workspace
        focused_pane_id = context.get("focused_pane_id")
        workspace_id = context.get("workspace_id")
        if focused_pane_id:
            subprocess.run([herdr_bin, "pane", "run", focused_pane_id, f"cd {shlex.quote(target_dir)} && clear"], check=True)
        if workspace_id and label != "~":
            subprocess.run([herdr_bin, "workspace", "rename", workspace_id, label], check=False)

    sys.exit(0)

if __name__ == "__main__":
    main()
