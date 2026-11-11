# 🌲 Herdr Space Directory (`herdr-space-dir`)

[![Herdr Plugin](https://img.shields.io/badge/herdr-plugin-blue.svg)](https://herdr.dev)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

An interactive, visual directory tree explorer and workspace creator plugin for [Herdr](https://herdr.dev).

By default, Herdr initializes new workspaces in `~`. **`herdr-space-dir`** replaces the default blank workspace creation with a centered, interactive tree GUI that lets you explore project folders, inspect live Git details, and start workspaces directly inside the intended project directory.

```text
 🌲 HERDR SPACE DIRECTORY NAVIGATOR                   [WORKSPACE MODE] 
 📂 ~ › Work › marker
 ▾ 📁 ~                                  │ DETAILS & PREVIEW
   ▸ 📁 Documents                         │ Path: /home/mahan/Work/marker
   ▸ 📁 Downloads                         │ Space Label: marker
   ▸ 📁 Projects                          │
   ▼ 📁 Work                              │ Git Branch: master
     ▸ 📁 jev-ultrafast-service           │ Last Commit: 71dd5fd Merge PR #1136
     ▸ 📁 kev                             │ Changes: 2 modified files
     ▼ 📁 marker                          │──────────────────────────────────────
       ▸ 📁 benchmarks                    │ Contents:
       ▸ 📁 data                          │ 📁 benchmarks
       ▸ 📁 docker                        │ 📁 data
       ▸ 📁 marker                        │ 📁 docker
   ▸ 📁 Videos                            │ 📄 README.md
──────────────────────────────────────────────────────────────────────────
 [Enter/Space] Choose  [→/Tab] Expand  [←] Collapse  [n] New Dir  [l] Label  [/] Filter  [q] Quit 
 Bookmarks: [1] ~  [2] ~/Work  [3] ~/Projects  [4] Root /  [.] Hidden Dirs 
```

---

## ✨ Features

- **🌳 Interactive Directory Tree**:
  - Full hierarchical folder tree with expand/collapse indicators (`▼` / `▶` / `📁`).
  - Smooth navigation with arrow keys or vim keys (`j`/`k` for vertical movement, `l`/`→` to expand, `h`/`←` to collapse or jump to parent).
  - Fast, lazy-loaded folder scanning (only scans directories upon expansion, automatically skipping heavy directories like `node_modules`, `.venv`, `.git`, and `__pycache__`).
- **📊 Live Details & Preview Panel**:
  - Displays full path and default space label.
  - Live Git information: active branch, last commit summary, and dirty/modified file counts.
  - Formatted file & directory preview of the highlighted folder.
- **⚡ One-Key Workspace Creation**:
  - Press `Enter` or `Space` on any folder to immediately create and focus a Herdr space rooted in that directory, using the directory name as the workspace label.
- **🏷️ Custom Space Labels**:
  - Press `l` or `L` to edit or customize the workspace label with an inline prompt before opening.
- **📁 Create Subfolders on the Fly**:
  - Press `n` or `N` to create a new folder under the currently selected directory and instantly open a workspace inside it.
- **🔍 Real-Time Filter & Search**:
  - Press `/` to search and filter visible tree nodes in real time.
- **⚡ FZF Fuzzy Finder Integration**:
  - Press `f` in the tree view to switch into an ultra-fast `fzf` fuzzy finder across all discovered project folders.
  - Press `Ctrl-T` inside fuzzy mode to jump straight back to the tree explorer.
- **🔖 Quick-Jump Bookmarks**:
  - Jump instantly to common project roots: `1` for `~`, `2` for `~/Work`, `3` for `~/Projects`, `4` for `~/.config`, `5` for `/`.
- **👁️ Toggle Hidden Folders**:
  - Press `.` or `H` to toggle hidden dot-directories.
- **🪶 Zero Pip Dependencies**:
  - Pure Python + Curses standard library implementation. Runs out of the box on Linux and macOS without extra packages.

---

## 📦 Installation

### From GitHub (Herdr Plugin Marketplace)

```bash
herdr plugin install mahan2079/herdr-space-dir
```

### From Local Source

```bash
git clone https://github.com/mahan2079/herdr-space-dir.git
herdr plugin link ./herdr-space-dir
```

---

## ⌨️ Keybindings Setup

To make `prefix + shift + c` (or your preferred workspace key) open the directory tree picker instead of creating an empty workspace in `~`, configure `~/.config/herdr/config.toml`:

```toml
[keys]
# Disable the built-in blank workspace creation
new_workspace = ""

# Bind your workspace key to the space-dir plugin
[[keys.command]]
key = "prefix+shift+c"
type = "plugin_action"
command = "space-dir.new-space"
description = "new space in chosen directory"

# (Optional) Bind a key to open a new tab in a chosen directory
[[keys.command]]
key = "prefix+shift+t"
type = "plugin_action"
command = "space-dir.new-tab"
description = "new tab in chosen directory"
```

Reload Herdr configuration without restarting panes:

```bash
herdr server reload-config
```

---

## 🎮 Tree Navigator Controls

| Key | Action |
|---|---|
| `↑` / `k` | Move cursor up |
| `↓` / `j` | Move cursor down |
| `→` / `l` | Expand folder (or step into first child) |
| `←` / `h` | Collapse folder (or jump to parent folder) |
| `Tab` | Toggle expand / collapse on current folder |
| `Enter` or `Space` | **Select folder & create workspace in it** |
| `l` / `L` | Edit workspace label before opening |
| `n` / `N` | Create new subfolder under current selection |
| `/` | Live search / filter tree nodes |
| `f` | Switch to `fzf` fuzzy search mode |
| `1` – `5` | Quick-jump bookmarks (`~`, `Work`, `Projects`, `.config`, `/`) |
| `.` or `H` | Toggle hidden directories on / off |
| `PageUp` / `PageDown` | Scroll 15 lines up / down |
| `g` / `G` | Jump to top / bottom |
| `q` or `Esc` | Cancel and exit without creating anything |

---

## ⚙️ Configuration

A configuration file can be placed at:
`~/.config/herdr/plugins/config/space-dir/config.json`

```json
{
  "search_dirs": [
    "~/Work",
    "~/Projects",
    "~",
    "~/Documents",
    "~/Downloads"
  ],
  "search_depth": 3,
  "prompt_label": false,
  "preview": true
}
```

- `search_dirs`: Base paths scanned for Git projects and quick discovery.
- `search_depth`: Depth limit for directory discovery in fuzzy mode.
- `prompt_label`: If `true`, always prompts to confirm the workspace label. If `false` (default), uses the directory name immediately unless `L` is pressed.

---

## 📄 License

MIT © [Mahan Dashti](https://github.com/mahan2079)
