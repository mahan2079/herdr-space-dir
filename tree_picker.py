#!/usr/bin/env python3
"""
Herdr Space Directory Tree Navigator
Interactive directory tree explorer & workspace creator for Herdr.
Supports internal/external drives, project bookmarks, search, and full mouse support.
"""

import sys
import os
import shlex
import subprocess
import curses
import time
import json
import traceback

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

def discover_drives():
    """Discover Home, secondary internal storage (e.g. 500GB SSD), and external drives."""
    drives = []
    seen = set()
    user = os.environ.get("USER", "mahan")
    home = os.path.expanduser("~")

    # 1. Primary Home drive
    drives.append({
        "path": home,
        "name": "Home (~)",
        "label": "~",
        "icon": "🏠",
        "type": "home"
    })
    seen.add(home)

    # 2. Query lsblk for mounted storage partitions
    try:
        res = subprocess.run(
            ["lsblk", "-J", "-o", "NAME,SIZE,TYPE,MOUNTPOINTS,LABEL,MODEL,RM"],
            capture_output=True, text=True, timeout=2
        )
        if res.returncode == 0:
            data = json.loads(res.stdout)
            def walk(dev, model=None):
                cur_model = dev.get("model") or model
                is_removable = dev.get("rm") in (True, 1, "1")
                mps = dev.get("mountpoints") or []
                if "mountpoint" in dev and dev["mountpoint"]:
                    mps.append(dev["mountpoint"])
                for mp in mps:
                    if mp and mp not in ("/", "/boot", "[SWAP]", "/var/log", "/var/cache/pacman/pkg") and not mp.startswith("/home"):
                        if os.path.isdir(mp) and mp not in seen:
                            seen.add(mp)
                            size = dev.get("size") or ""
                            label = dev.get("label")

                            if "512G" in (cur_model or "") or "476" in size or "477" in size:
                                friendly_name = f"500GB Storage ({size})"
                                default_lbl = "500GB-Storage"
                            elif label:
                                friendly_name = f"{label} ({size})" if size else label
                                default_lbl = label
                            elif cur_model:
                                friendly_name = f"{cur_model} ({size})" if size else cur_model
                                default_lbl = os.path.basename(mp)
                            else:
                                friendly_name = f"Storage ({size})" if size else os.path.basename(mp)
                                default_lbl = os.path.basename(mp)

                            icon = "🔌" if is_removable else "💾"
                            drives.append({
                                "path": mp,
                                "name": friendly_name,
                                "label": default_lbl,
                                "icon": icon,
                                "type": "external" if is_removable else "internal_secondary"
                            })
                for c in dev.get("children", []):
                    walk(c, cur_model)

            for d in data.get("blockdevices", []):
                walk(d)
    except Exception:
        pass

    # 3. Scan /run/media/$USER, /media/$USER, /media, /mnt for any additional mounted drives
    for base in [f"/run/media/{user}", "/run/media", f"/media/{user}", "/media", "/mnt"]:
        if os.path.isdir(base):
            try:
                for entry in os.scandir(base):
                    if entry.is_dir(follow_symlinks=True) and entry.name != user:
                        p = os.path.abspath(entry.path)
                        if p not in seen:
                            seen.add(p)
                            drives.append({
                                "path": p,
                                "name": f"External Drive: {entry.name}",
                                "label": entry.name,
                                "icon": "🔌",
                                "type": "external"
                            })
            except Exception:
                pass

    # 4. Root filesystem
    drives.append({
        "path": "/",
        "name": "Root (/)",
        "label": "root",
        "icon": "📁",
        "type": "root"
    })

    return drives

class TreeNode:
    def __init__(self, path, name=None, icon="📁", default_label=None, parent=None, depth=0):
        self.path = os.path.abspath(path)
        home = os.path.expanduser("~")
        if name:
            self.name = name
        elif self.path == home:
            self.name = "~"
        elif self.path == "/":
            self.name = "/"
        else:
            self.name = os.path.basename(self.path) or self.path

        self.default_label = default_label or (os.path.basename(self.path) if self.path != home else "~")
        self.icon = icon
        self.parent = parent
        self.depth = depth
        self.expanded = False
        self.children = None
        self.has_children = True
        self.git_info = None
        self.contents_preview = None

    def load_children(self, show_hidden=False):
        self.children = []
        try:
            entries = []
            with os.scandir(self.path) as it:
                for entry in it:
                    if entry.is_dir(follow_symlinks=False):
                        if not show_hidden and entry.name.startswith("."):
                            continue
                        if entry.name in ("node_modules", ".venv", "__pycache__", ".git", "lost+found", ".Trash-1000"):
                            continue
                        entries.append(entry.name)
            entries.sort(key=lambda s: s.lower())
            for name in entries:
                child_path = os.path.join(self.path, name)
                self.children.append(TreeNode(child_path, name=name, parent=self, depth=self.depth + 1))
            self.has_children = len(self.children) > 0
        except (PermissionError, FileNotFoundError):
            self.children = []
            self.has_children = False

    def get_visible_nodes(self, filter_query=None):
        if self.children is None and self.expanded:
            self.load_children()

        res = [self]
        if self.expanded and self.children:
            for child in self.children:
                res.extend(child.get_visible_nodes(filter_query))
        return res

    def get_git_info(self):
        if self.git_info is not None:
            return self.git_info

        git_dir = os.path.join(self.path, ".git")
        if not os.path.exists(git_dir):
            self.git_info = False
            return False

        try:
            branch = subprocess.check_output(
                ["git", "-C", self.path, "branch", "--show-current"],
                text=True, stderr=subprocess.DEVNULL, timeout=1
            ).strip() or "detached"
            commit = subprocess.check_output(
                ["git", "-C", self.path, "log", "-1", "--format=%h %s (%cr)"],
                text=True, stderr=subprocess.DEVNULL, timeout=1
            ).strip()
            status_lines = subprocess.check_output(
                ["git", "-C", self.path, "status", "--short"],
                text=True, stderr=subprocess.DEVNULL, timeout=1
            ).strip().splitlines()
            self.git_info = {
                "branch": branch,
                "commit": commit,
                "changes_count": len(status_lines)
            }
        except Exception:
            self.git_info = False
        return self.git_info

    def get_contents_preview(self, show_hidden=False):
        if self.contents_preview is not None:
            return self.contents_preview

        try:
            items = []
            with os.scandir(self.path) as it:
                for entry in it:
                    if not show_hidden and entry.name.startswith("."):
                        continue
                    if entry.name in ("node_modules", ".venv", "__pycache__", "lost+found", ".Trash-1000"):
                        continue
                    items.append((entry.is_dir(), entry.name))
            items.sort(key=lambda x: (not x[0], x[1].lower()))
            self.contents_preview = items[:50]
        except Exception:
            self.contents_preview = []
        return self.contents_preview

class TreeApp:
    def __init__(self, mode="workspace", start_dir=None):
        self.mode = mode
        self.herdr_bin = get_herdr_bin()
        self.context = get_context()
        self.show_hidden = False
        self.filter_query = ""
        self.filter_mode = False
        self.message = ""
        self.message_time = 0

        # Click tracking for double click detection
        self.last_click_idx = -1
        self.last_click_time = 0

        home = os.path.expanduser("~")
        curr = start_dir or self.context.get("focused_pane_cwd") or self.context.get("workspace_cwd") or home

        # Discover all available drives (Home, 500GB internal storage, USB drives, etc.)
        self.drives = discover_drives()
        self.roots = []
        for d in self.drives:
            node = TreeNode(d["path"], name=d["name"], icon=d["icon"], default_label=d["label"], depth=0)
            self.roots.append(node)

        # Expand Home root by default
        self.roots[0].expanded = True
        self.roots[0].load_children(self.show_hidden)

        self.selected_index = 0
        self.scroll_offset = 0
        self.visible_nodes = []
        self.preview_items_coords = []  # List of (y, name, is_dir) for click navigation in preview

        self.navigate_to_path(curr)

    def navigate_to_path(self, target_path):
        target = os.path.abspath(os.path.expanduser(target_path))

        # Find which root contains this target
        matched_root = None
        for r in self.roots:
            if r.path == "/" and target != "/":
                continue
            if target == r.path or target.startswith(r.path.rstrip("/") + "/"):
                matched_root = r
                break

        if not matched_root:
            # Fall back to root /
            matched_root = self.roots[-1]

        matched_root.expanded = True
        matched_root.load_children(self.show_hidden)
        self._expand_path_down(matched_root, target)

        self.update_visible_nodes()
        for i, node in enumerate(self.visible_nodes):
            if node.path == target:
                self.selected_index = i
                break

    def _expand_path_down(self, node, target):
        if node.path == target:
            return
        if not target.startswith(node.path.rstrip("/") + "/"):
            return
        node.expanded = True
        node.load_children(self.show_hidden)
        if node.children:
            for c in node.children:
                if target == c.path or target.startswith(c.path.rstrip("/") + "/"):
                    self._expand_path_down(c, target)
                    break

    def update_visible_nodes(self):
        nodes = []
        for r in self.roots:
            nodes.extend(r.get_visible_nodes())

        if self.filter_query:
            q = self.filter_query.lower()
            filtered = [n for n in nodes if q in n.name.lower() or q in n.path.lower()]
            self.visible_nodes = filtered if filtered else nodes
        else:
            self.visible_nodes = nodes

        if not self.visible_nodes:
            self.selected_index = 0
        elif self.selected_index >= len(self.visible_nodes):
            self.selected_index = len(self.visible_nodes) - 1
        elif self.selected_index < 0:
            self.selected_index = 0

    def current_node(self):
        if 0 <= self.selected_index < len(self.visible_nodes):
            return self.visible_nodes[self.selected_index]
        return None

    def draw_header(self, stdscr, max_x):
        title = " 🌲 HERDR SPACE DIRECTORY NAVIGATOR "
        mode_str = f" [{self.mode.upper()} MODE] "

        try:
            stdscr.attron(curses.color_pair(1) | curses.A_BOLD)
            stdscr.addnstr(0, 0, title, max_x - 1)
            stdscr.attroff(curses.color_pair(1) | curses.A_BOLD)

            if max_x > len(title) + len(mode_str) + 2:
                stdscr.attron(curses.color_pair(3) | curses.A_BOLD)
                stdscr.addnstr(0, max_x - len(mode_str) - 1, mode_str, len(mode_str))
                stdscr.attroff(curses.color_pair(3) | curses.A_BOLD)

            curr = self.current_node()
            if curr and max_x > 10:
                crumb = f" {curr.icon} {curr.path}"
                stdscr.attron(curses.color_pair(4))
                stdscr.addnstr(1, 0, crumb.ljust(max_x - 1), max_x - 1)
                stdscr.attroff(curses.color_pair(4))
        except curses.error:
            pass

    def draw_tree(self, stdscr, max_y, tree_width):
        view_height = max_y - 4
        if view_height <= 0:
            return

        if self.selected_index < self.scroll_offset:
            self.scroll_offset = self.selected_index
        elif self.selected_index >= self.scroll_offset + view_height:
            self.scroll_offset = self.selected_index - view_height + 1

        for row in range(view_height):
            idx = self.scroll_offset + row
            y = 2 + row
            if y >= max_y - 2:
                break

            if idx >= len(self.visible_nodes):
                try:
                    stdscr.addnstr(y, 0, " " * (tree_width - 1), tree_width - 1)
                except curses.error:
                    pass
                continue

            node = self.visible_nodes[idx]
            is_selected = (idx == self.selected_index)

            if node.children is None and not node.expanded:
                arrow = "▸"
            elif node.expanded:
                arrow = "▾" if node.children else " "
            else:
                arrow = "▸" if node.has_children else " "

            indent = "  " * node.depth
            line_content = f"{indent}{arrow} {node.icon} {node.name}"
            line_str = f" {line_content}".ljust(tree_width - 1)[:tree_width - 1]

            try:
                if is_selected:
                    stdscr.attron(curses.color_pair(2) | curses.A_BOLD)
                    stdscr.addnstr(y, 0, line_str, tree_width - 1)
                    stdscr.attroff(curses.color_pair(2) | curses.A_BOLD)
                else:
                    stdscr.attron(curses.color_pair(1))
                    stdscr.addnstr(y, 0, line_str, tree_width - 1)
                    stdscr.attroff(curses.color_pair(1))
            except curses.error:
                pass

    def draw_preview(self, stdscr, max_y, max_x, start_x):
        preview_width = max_x - start_x - 1
        if preview_width < 10:
            return

        self.preview_items_coords = []
        curr = self.current_node()

        # Vertical separator
        for y in range(2, max_y - 2):
            try:
                stdscr.attron(curses.color_pair(5))
                stdscr.addstr(y, start_x - 1, "│")
                stdscr.attroff(curses.color_pair(5))
            except curses.error:
                pass

        if not curr:
            return

        p_y = 2
        try:
            stdscr.attron(curses.A_BOLD | curses.color_pair(4))
            stdscr.addnstr(p_y, start_x + 1, "DETAILS & PREVIEW", preview_width)
            stdscr.attroff(curses.A_BOLD | curses.color_pair(4))
            p_y += 1

            if p_y < max_y - 2:
                stdscr.addnstr(p_y, start_x + 1, f"Path: {curr.path}", preview_width)
                p_y += 1

            if p_y < max_y - 2:
                stdscr.addnstr(p_y, start_x + 1, f"Space Label: {curr.default_label}", preview_width)
                p_y += 2

            # Git Status
            git = curr.get_git_info()
            if git:
                if p_y < max_y - 2:
                    stdscr.attron(curses.color_pair(6) | curses.A_BOLD)
                    stdscr.addnstr(p_y, start_x + 1, f"Git Branch: {git['branch']}", preview_width)
                    stdscr.attroff(curses.color_pair(6) | curses.A_BOLD)
                    p_y += 1
                if p_y < max_y - 2:
                    stdscr.addnstr(p_y, start_x + 1, f"Last Commit: {git['commit'][:preview_width - 13]}", preview_width)
                    p_y += 1
                if p_y < max_y - 2:
                    if git['changes_count'] > 0:
                        stdscr.attron(curses.color_pair(7))
                        stdscr.addnstr(p_y, start_x + 1, f"Changes: {git['changes_count']} modified files", preview_width)
                        stdscr.attroff(curses.color_pair(7))
                    else:
                        stdscr.attron(curses.color_pair(6))
                        stdscr.addnstr(p_y, start_x + 1, "Working tree clean", preview_width)
                        stdscr.attroff(curses.color_pair(6))
                    p_y += 1
                p_y += 1

            if p_y < max_y - 2:
                stdscr.attron(curses.color_pair(5))
                stdscr.addnstr(p_y, start_x, "─" * preview_width, preview_width)
                stdscr.attroff(curses.color_pair(5))
                p_y += 1

            if p_y < max_y - 2:
                stdscr.attron(curses.A_BOLD)
                stdscr.addnstr(p_y, start_x + 1, "Contents (click to step in):", preview_width)
                stdscr.attroff(curses.A_BOLD)
                p_y += 1

            items = curr.get_contents_preview(self.show_hidden)
            for is_dir, name in items:
                if p_y >= max_y - 3:
                    stdscr.addnstr(p_y, start_x + 1, "... and more", preview_width)
                    break
                icon = "📁 " if is_dir else "📄 "
                color = curses.color_pair(1) if is_dir else curses.color_pair(0)
                stdscr.attron(color)
                stdscr.addnstr(p_y, start_x + 1, f"{icon}{name}", preview_width)
                stdscr.attroff(color)
                self.preview_items_coords.append((p_y, name, is_dir))
                p_y += 1
        except curses.error:
            pass

    def draw_footer(self, stdscr, max_y, max_x):
        y = max_y - 2
        y_bottom = max_y - 1

        help_text = " [Enter/Click] Choose  [→/Tab] Expand  [←] Collapse  [n] New Dir  [l] Label  [/] Filter  [q] Quit "
        try:
            stdscr.attron(curses.color_pair(3))
            stdscr.addnstr(y, 0, help_text.ljust(max_x - 1), max_x - 1)
            stdscr.attroff(curses.color_pair(3))

            if self.filter_mode:
                prompt = f" Search Filter: {self.filter_query}█"
                stdscr.attron(curses.color_pair(2) | curses.A_BOLD)
                stdscr.addnstr(y_bottom, 0, prompt.ljust(max_x - 1), max_x - 1)
                stdscr.attroff(curses.color_pair(2) | curses.A_BOLD)
            elif self.filter_query:
                prompt = f" Active Filter: '{self.filter_query}' (Press '/' to edit, 'Esc' to clear) "
                stdscr.attron(curses.color_pair(7))
                stdscr.addnstr(y_bottom, 0, prompt.ljust(max_x - 1), max_x - 1)
                stdscr.attroff(curses.color_pair(7))
            elif self.message and time.time() - self.message_time < 4:
                stdscr.attron(curses.color_pair(7) | curses.A_BOLD)
                stdscr.addnstr(y_bottom, 0, f" {self.message}".ljust(max_x - 1), max_x - 1)
                stdscr.attroff(curses.color_pair(7) | curses.A_BOLD)
            else:
                bookmarks = " Bookmarks: [1] ~  [2] Work  [3] Projects  [4] 💾 Storage  [5] /  [.] Hidden "
                stdscr.attron(curses.color_pair(5))
                stdscr.addnstr(y_bottom, 0, bookmarks.ljust(max_x - 1), max_x - 1)
                stdscr.attroff(curses.color_pair(5))
        except curses.error:
            pass

    def prompt_input(self, stdscr, prompt_text, default_val=""):
        curses.curs_set(1)
        curses.echo()
        h, w = stdscr.getmaxyx()
        try:
            stdscr.attron(curses.color_pair(2) | curses.A_BOLD)
            stdscr.addnstr(h - 1, 0, f" {prompt_text}: {default_val}".ljust(w - 1), w - 1)
            stdscr.attroff(curses.color_pair(2) | curses.A_BOLD)
            stdscr.refresh()
            stdscr.move(h - 1, min(len(f" {prompt_text}: "), w - 2))
            stdscr.clrtoeol()
            stdscr.addnstr(h - 1, 0, f" {prompt_text}: ", w - 1)
            val = stdscr.getstr().decode("utf-8", errors="ignore").strip()
        except curses.error:
            val = ""
        finally:
            curses.noecho()
            curses.curs_set(0)
        return val if val else default_val

    def execute_choice(self, stdscr, custom_label=None):
        curr = self.current_node()
        if not curr:
            return None

        target_dir = curr.path
        label = custom_label or curr.default_label
        return (target_dir, label)

    def handle_mouse(self, stdscr, max_y, max_x, tree_width):
        try:
            _, mx, my, _, bstate = curses.getmouse()
        except curses.error:
            return None

        # 1. Mouse wheel UP
        if bstate & (curses.BUTTON4_PRESSED | 65536):
            if self.selected_index > 0:
                self.selected_index = max(0, self.selected_index - 1)
            return None

        # 2. Mouse wheel DOWN
        if bstate & (curses.BUTTON5_PRESSED | 2097152):
            if self.selected_index < len(self.visible_nodes) - 1:
                self.selected_index = min(len(self.visible_nodes) - 1, self.selected_index + 1)
            return None

        # 3. Left Click on Tree Area
        if my in range(2, max_y - 2) and mx < tree_width:
            row_offset = my - 2
            clicked_idx = self.scroll_offset + row_offset
            if 0 <= clicked_idx < len(self.visible_nodes):
                now = time.time()
                is_double_click = bool(
                    (bstate & curses.BUTTON1_DOUBLE_CLICKED) or
                    (clicked_idx == self.last_click_idx and (now - self.last_click_time) < 0.4)
                )
                self.last_click_idx = clicked_idx
                self.last_click_time = now

                if is_double_click:
                    # Double click = Select & Open Workspace!
                    self.selected_index = clicked_idx
                    return self.execute_choice(stdscr)

                # Single click
                if clicked_idx == self.selected_index:
                    # Toggle expand/collapse on clicked item
                    node = self.visible_nodes[clicked_idx]
                    node.expanded = not node.expanded
                    if node.expanded:
                        node.load_children(self.show_hidden)
                    self.update_visible_nodes()
                else:
                    self.selected_index = clicked_idx
            return None

        # 4. Left Click on Preview Area (click on folder to step in)
        if my in range(2, max_y - 2) and mx >= tree_width:
            curr = self.current_node()
            if curr:
                for p_y, name, is_dir in self.preview_items_coords:
                    if my == p_y and is_dir:
                        sub_path = os.path.join(curr.path, name)
                        self.navigate_to_path(sub_path)
                        break
            return None

        # 5. Left Click on Footer Action Buttons (row max_y - 2)
        if my == max_y - 2:
            if 1 <= mx <= 21: # Choose
                return self.execute_choice(stdscr)
            elif 22 <= mx <= 36: # Expand
                curr = self.current_node()
                if curr and not curr.expanded:
                    curr.expanded = True
                    curr.load_children(self.show_hidden)
                    self.update_visible_nodes()
            elif 37 <= mx <= 51: # Collapse
                curr = self.current_node()
                if curr and curr.expanded:
                    curr.expanded = False
                    self.update_visible_nodes()
            elif 52 <= mx <= 64: # New Dir
                curr = self.current_node()
                if curr:
                    new_name = self.prompt_input(stdscr, f"New directory inside '{curr.name}'")
                    if new_name:
                        new_path = os.path.join(curr.path, new_name)
                        try:
                            os.makedirs(new_path, exist_ok=True)
                            curr.expanded = True
                            curr.load_children(self.show_hidden)
                            self.update_visible_nodes()
                            for i, n in enumerate(self.visible_nodes):
                                if n.path == new_path:
                                    self.selected_index = i
                                    break
                            self.message = f"Created directory: {new_name}"
                            self.message_time = time.time()
                        except Exception as e:
                            self.message = f"Failed to create: {e}"
                            self.message_time = time.time()
            elif 65 <= mx <= 75: # Label
                curr = self.current_node()
                if curr:
                    custom = self.prompt_input(stdscr, "Workspace Label", curr.default_label)
                    if custom:
                        return self.execute_choice(stdscr, custom_label=custom)
            elif 76 <= mx <= 87: # Filter
                self.filter_mode = True
            elif 88 <= mx <= 98: # Quit
                return "__CANCEL__"
            return None

        # 6. Left Click on Bookmarks (row max_y - 1)
        if my == max_y - 1:
            if "1" in self.get_clicked_token(mx, " Bookmarks: [1] ~  [2] Work  [3] Projects  [4] 💾 Storage  [5] /  [.] Hidden "):
                self.navigate_to_path(os.path.expanduser("~"))
            elif "2" in self.get_clicked_token(mx, " Bookmarks: [1] ~  [2] Work  [3] Projects  [4] 💾 Storage  [5] /  [.] Hidden "):
                self.navigate_to_path(os.path.expanduser("~/Work"))
            elif "3" in self.get_clicked_token(mx, " Bookmarks: [1] ~  [2] Work  [3] Projects  [4] 💾 Storage  [5] /  [.] Hidden "):
                self.navigate_to_path(os.path.expanduser("~/Projects"))
            elif "4" in self.get_clicked_token(mx, " Bookmarks: [1] ~  [2] Work  [3] Projects  [4] 💾 Storage  [5] /  [.] Hidden "):
                # Jump to secondary storage (500GB drive or external)
                if len(self.roots) > 2:
                    self.navigate_to_path(self.roots[1].path)
            elif "5" in self.get_clicked_token(mx, " Bookmarks: [1] ~  [2] Work  [3] Projects  [4] 💾 Storage  [5] /  [.] Hidden "):
                self.navigate_to_path("/")
            elif "." in self.get_clicked_token(mx, " Bookmarks: [1] ~  [2] Work  [3] Projects  [4] 💾 Storage  [5] /  [.] Hidden "):
                self.show_hidden = not self.show_hidden
                for r in self.roots:
                    r.load_children(self.show_hidden)
                self.update_visible_nodes()
            return None

        return None

    def get_clicked_token(self, mx, line):
        if mx >= len(line):
            return ""
        # Find which bracketed token
        start = line.rfind("[", 0, mx + 1)
        end = line.find("]", mx)
        if start != -1 and end != -1:
            return line[start:end + 1]
        return ""

    def run(self, stdscr):
        curses.curs_set(0)
        curses.use_default_colors()

        # Enable full mouse capture
        curses.mousemask(curses.ALL_MOUSE_EVENTS)

        curses.init_pair(1, curses.COLOR_BLUE, -1)
        curses.init_pair(2, curses.COLOR_BLACK, curses.COLOR_CYAN)
        curses.init_pair(3, curses.COLOR_CYAN, -1)
        curses.init_pair(4, curses.COLOR_YELLOW, -1)
        curses.init_pair(5, curses.COLOR_WHITE, -1)
        curses.init_pair(6, curses.COLOR_GREEN, -1)
        curses.init_pair(7, curses.COLOR_YELLOW, -1)

        stdscr.keypad(True)
        stdscr.timeout(50)

        while True:
            max_y, max_x = stdscr.getmaxyx()
            stdscr.erase()

            tree_width = int(max_x * 0.52)
            if tree_width < 30:
                tree_width = max_x - 1

            self.draw_header(stdscr, max_x)
            self.draw_tree(stdscr, max_y, tree_width)
            if max_x > 60:
                self.draw_preview(stdscr, max_y, max_x, tree_width + 1)
            self.draw_footer(stdscr, max_y, max_x)

            stdscr.refresh()

            try:
                ch = stdscr.getch()
            except curses.error:
                continue

            if ch == -1:
                continue

            # MOUSE EVENT HANDLING
            if ch == curses.KEY_MOUSE:
                res = self.handle_mouse(stdscr, max_y, max_x, tree_width)
                if res == "__CANCEL__":
                    break
                elif res:
                    return res
                continue

            # Handle Escape sequences (focus in/out \033[I, mouse reports, etc.)
            if ch == 27:
                stdscr.nodelay(True)
                seq = []
                while True:
                    nxt = stdscr.getch()
                    if nxt == -1:
                        break
                    seq.append(nxt)
                stdscr.nodelay(False)

                if seq:
                    continue
                else:
                    if self.filter_mode:
                        self.filter_mode = False
                        self.filter_query = ""
                        self.update_visible_nodes()
                    elif self.filter_query:
                        self.filter_query = ""
                        self.update_visible_nodes()
                    else:
                        break
                    continue

            # Handle search/filter mode typing
            if self.filter_mode:
                if ch in (10, 13):
                    self.filter_mode = False
                elif ch in (curses.KEY_BACKSPACE, 127, 8):
                    if self.filter_query:
                        self.filter_query = self.filter_query[:-1]
                        self.update_visible_nodes()
                elif 32 <= ch <= 126:
                    self.filter_query += chr(ch)
                    self.update_visible_nodes()
                continue

            # Normal Navigation Keys
            if ch == ord('q'):
                if self.filter_query:
                    self.filter_query = ""
                    self.update_visible_nodes()
                else:
                    break

            elif ch in (curses.KEY_DOWN, ord('j')):
                if self.selected_index < len(self.visible_nodes) - 1:
                    self.selected_index += 1

            elif ch in (curses.KEY_UP, ord('k')):
                if self.selected_index > 0:
                    self.selected_index -= 1

            elif ch in (curses.KEY_RIGHT, ord('l')):
                curr = self.current_node()
                if curr:
                    if not curr.expanded:
                        curr.expanded = True
                        curr.load_children(self.show_hidden)
                        self.update_visible_nodes()
                    elif curr.children:
                        if self.selected_index + 1 < len(self.visible_nodes):
                            self.selected_index += 1

            elif ch in (curses.KEY_LEFT, ord('h')):
                curr = self.current_node()
                if curr:
                    if curr.expanded:
                        curr.expanded = False
                        self.update_visible_nodes()
                    elif curr.parent:
                        for i, n in enumerate(self.visible_nodes):
                            if n == curr.parent:
                                self.selected_index = i
                                break

            elif ch in (ord('\t'), 9):  # Tab toggles expand/collapse
                curr = self.current_node()
                if curr:
                    curr.expanded = not curr.expanded
                    if curr.expanded:
                        curr.load_children(self.show_hidden)
                    self.update_visible_nodes()

            elif ch in (curses.KEY_NPAGE,):  # Page Down
                self.selected_index = min(len(self.visible_nodes) - 1, self.selected_index + 15)

            elif ch in (curses.KEY_PPAGE,):  # Page Up
                self.selected_index = max(0, self.selected_index - 15)

            elif ch in (ord('g'), curses.KEY_HOME):
                self.selected_index = 0

            elif ch in (ord('G'), curses.KEY_END):
                self.selected_index = max(0, len(self.visible_nodes) - 1)

            elif ch in (10, 13, ord(' ')):  # Enter or Space = CHOOSE FOLDER
                res = self.execute_choice(stdscr)
                if res:
                    return res

            elif ch in (ord('L'), ord('l')):  # Custom Label
                curr = self.current_node()
                if curr:
                    custom = self.prompt_input(stdscr, "Workspace Label", curr.default_label)
                    if custom:
                        res = self.execute_choice(stdscr, custom_label=custom)
                        if res:
                            return res

            elif ch in (ord('n'), ord('N')):  # New Folder
                curr = self.current_node()
                if curr:
                    new_name = self.prompt_input(stdscr, f"New directory inside '{curr.name}'")
                    if new_name:
                        new_path = os.path.join(curr.path, new_name)
                        try:
                            os.makedirs(new_path, exist_ok=True)
                            curr.expanded = True
                            curr.load_children(self.show_hidden)
                            self.update_visible_nodes()
                            for i, n in enumerate(self.visible_nodes):
                                if n.path == new_path:
                                    self.selected_index = i
                                    break
                            self.message = f"Created directory: {new_name}"
                            self.message_time = time.time()
                        except Exception as e:
                            self.message = f"Failed to create: {e}"
                            self.message_time = time.time()

            elif ch in (ord('/'),):  # Search / Filter
                self.filter_mode = True

            elif ch in (ord('.'), ord('H')):  # Toggle hidden files
                self.show_hidden = not self.show_hidden
                for r in self.roots:
                    r.load_children(self.show_hidden)
                self.update_visible_nodes()
                self.message = f"Show hidden directories: {'ON' if self.show_hidden else 'OFF'}"
                self.message_time = time.time()

            elif ch in (ord('f'), ord('F')):  # Quick switch to fzf fuzzy picker
                return ("__FZF__", self.mode)

            # Bookmarks
            elif ch == ord('1'):
                self.navigate_to_path(os.path.expanduser("~"))
            elif ch == ord('2'):
                self.navigate_to_path(os.path.expanduser("~/Work"))
            elif ch == ord('3'):
                self.navigate_to_path(os.path.expanduser("~/Projects"))
            elif ch == ord('4'):
                if len(self.roots) > 2:
                    self.navigate_to_path(self.roots[1].path)
            elif ch == ord('5'):
                self.navigate_to_path("/")

        return None

def main():
    mode = "workspace"
    args = sys.argv[1:]
    if "--mode" in args:
        idx = args.index("--mode")
        if idx + 1 < len(args):
            mode = args[idx + 1]

    log_path = "/tmp/herdr_space_dir.log"
    try:
        app = TreeApp(mode=mode)
        result = curses.wrapper(app.run)
    except Exception as e:
        with open(log_path, "a") as f:
            f.write(f"Exception in TreeApp: {e}\n")
            traceback.print_exc(file=f)
        sys.exit(1)

    if not result:
        sys.exit(0)

    # Check if user requested fzf mode
    if result[0] == "__FZF__":
        script_dir = os.path.dirname(os.path.abspath(__file__))
        fzf_script = os.path.join(script_dir, "picker.py")
        os.execlp("python3", "python3", fzf_script, "--mode", result[1])
        return

    target_dir, label = result

    herdr_bin = get_herdr_bin()
    context = get_context()

    if mode == "workspace":
        cmd = [herdr_bin, "workspace", "create", "--cwd", target_dir, "--label", label, "--focus"]
        try:
            subprocess.run(cmd, check=True)
        except Exception as e:
            with open(log_path, "a") as f:
                f.write(f"Failed to create workspace: {e}\n")
            sys.exit(1)
    elif mode == "tab":
        cmd = [herdr_bin, "tab", "create", "--cwd", target_dir, "--label", label, "--focus"]
        try:
            subprocess.run(cmd, check=True)
        except Exception as e:
            with open(log_path, "a") as f:
                f.write(f"Failed to create tab: {e}\n")
            sys.exit(1)
    elif mode == "change":
        focused_pane_id = context.get("focused_pane_id")
        workspace_id = context.get("workspace_id")
        if focused_pane_id:
            subprocess.run([herdr_bin, "pane", "run", focused_pane_id, f"cd {shlex.quote(target_dir)} && clear"], check=True)
        if workspace_id and label != "~":
            subprocess.run([herdr_bin, "workspace", "rename", workspace_id, label], check=False)

    sys.exit(0)

if __name__ == "__main__":
    main()
