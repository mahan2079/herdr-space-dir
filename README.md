# 🌲 Herdr Space Directory (`herdr-space-dir`)

[![Herdr Plugin](https://img.shields.io/badge/herdr-plugin-blue.svg)](https://herdr.dev)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

An interactive, visual directory tree explorer and workspace creator plugin for [Herdr](https://herdr.dev).

By default, Herdr initializes new workspaces in `~`. **`herdr-space-dir`** replaces the default blank workspace creation with a centered, interactive tree GUI that lets you explore project folders across all storage drives (including secondary internal SSDs and external USB drives), inspect live Git details, and start workspaces directly inside the intended project directory with full mouse and keyboard support.

```text
 🌲 HERDR SPACE DIRECTORY NAVIGATOR                   [WORKSPACE MODE] 
 📂 💾 /run/media/mahan/1346aaae-0bbc-4cd9-a864-c589acdc572b/Isilcorp
 ▼ 🏠 Home (~)                           │ DETAILS & PREVIEW
   ▸ 📁 Work                              │ Path: /run/media/.../Isilcorp
   ▸ 📁 Projects                          │ Space Label: Isilcorp
 ▼ 💾 500GB Storage (476.9G)              │
   ▸ 📁 AI courses                        │ Git Branch: master
   ▸ 📁 Aspects of Life                   │ Last Commit: 3f1a0e2 Updated ERP config
   ▼ 📁 Isilcorp                          │ Changes: Working tree clean
     ▸ 📁 ERP                             │──────────────────────────────────────
     ▸ 📁 clients                         │ Contents (click to step in):
     ▸ 📁 internal-tools                  │ 📁 ERP
   ▸ 📁 phd studies                       │ 📁 clients
   ▸ 📁 the-complete-web-dev...           │ 📁 internal-tools
 ▶ 📁 Root (/)                            │ 📄 README.md
──────────────────────────────────────────────────────────────────────────
 [Enter/Click] Choose  [→/Tab] Expand  [←] Collapse  [n] New Dir  [l] Label  [/] Filter  [q] Quit 
 Bookmarks: [1] ~  [2] Work  [3] Projects  [4] 💾 Storage  [5] /  [.] Hidden 
```

---

## ✨ Features

- **🌳 Interactive Multi-Drive Directory Tree**:
  - Automatically discovers all storage partitions: Home `~`, secondary internal drives (e.g. 500GB SSD), and any connected external USB / SSD drives.
  - Full hierarchical folder tree with expand/collapse indicators (`▼` / `▶` / `📁`).
  - Fast, lazy-loaded folder scanning (only scans directories upon expansion, automatically skipping heavy directories like `node_modules`, `.venv`, `.git`, and `__pycache__`).
- **🖱️ Full Mouse Support**:
  - **Single Click**: Select a folder or drive. Click on an already-selected row (or its arrow) to expand or collapse.
  - **Double Click**: Double-click on any folder to immediately create and open a Herdr space inside it.
  - **Mouse Wheel**: Scroll up and down smoothly through the directory tree.
  - **Clickable Preview**: Click on any subfolder listed in the `Contents:` preview panel to step directly into it.
  - **Clickable Action Buttons**: Click footer buttons (`[Choose]`, `[Expand]`, `[Collapse]`, `[New Dir]`, `[Label]`, `[Filter]`, `[Quit]`) and bookmark pills directly with the mouse.
- **📊 Live Details & Preview Panel**:
  - Displays full path and default space label.
  - Live Git information: active branch, last commit summary, and dirty/modified file counts.
  - Formatted file & directory preview of the highlighted folder.
- **⚡ One-Key Workspace Creation**:
  - Press `Enter` or `Space` (or double-click) on any folder to immediately create and focus a Herdr space rooted in that directory, using the directory name as the workspace label.
- **🏷️ Custom Space Labels**:
  - Press `l` or `L` (or click `[l] Label`) to edit or customize the workspace label with an inline prompt before opening.
- **📁 Create Subfolders on the Fly**:
  - Press `n` or `N` (or click `[n] New Dir`) to create a new folder under the currently selected directory and instantly open a workspace inside it.
- **🔍 Real-Time Filter & Search**:
  - Press `/` (or click `[/] Filter`) to search and filter visible tree nodes in real time.
- **⚡ FZF Fuzzy Finder Integration**:
  - Press `f` in the tree view to switch into an ultra-fast `fzf` fuzzy finder across all discovered project folders (including the 500GB drive and external drives).
  - Press `Ctrl-T` inside fuzzy mode to jump straight back to the tree explorer.
- **🔖 Quick-Jump Bookmarks**:
  - Jump instantly to common project roots: `1` for `~`, `2` for `~/Work`, `3` for `~/Projects`, `4` for `💾 Storage` (500GB / external drive), `5` for `/`.
- **👁️ Toggle Hidden Folders**:
  - Press `.` or `H` (or click `[.] Hidden`) to toggle hidden dot-directories.
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

## ⌨️ How It Works

You can trigger the Tree Directory Navigator in two ways:

1. **Mouse Click in Sidebar**: Click `+ new workspace` beside **spaces** in Herdr's sidebar. The plugin intercepts the new workspace event and immediately opens the tree popup to let you choose where to root the space.
2. **Keyboard Shortcut**: Press `prefix + shift + c` (default prefix is `ctrl+a`, so `ctrl+a shift+c`) to open the directory tree directly.

Reload Herdr configuration after modifying keybindings:

```bash
herdr server reload-config
```

---

## 🎮 Tree Navigator Controls

### Keyboard Controls

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
| `1` – `5` | Quick-jump bookmarks (`~`, `Work`, `Projects`, `💾 Storage`, `/`) |
| `.` or `H` | Toggle hidden directories on / off |
| `PageUp` / `PageDown` | Scroll 15 lines up / down |
| `g` / `G` | Jump to top / bottom |
| `q` or `Esc` | Cancel and exit without creating anything |

### Mouse Controls

| Gesture | Action |
|---|---|
| **Left Click** | Select folder; click an already selected folder (or arrow) to toggle expand/collapse |
| **Double Click** | **Immediately open workspace in the clicked folder** |
| **Mouse Wheel** | Scroll up and down through the directory tree |
| **Click on Preview** | Click any subfolder in the `Contents:` list to step into it |
| **Click on Footer** | Click any button (`[Choose]`, `[Expand]`, `[Collapse]`, `[New Dir]`, `[Label]`, `[Filter]`, `[Quit]`) |
| **Click on Bookmark** | Click any bookmark (`[1] ~`, `[2] Work`, `[3] Projects`, `[4] 💾 Storage`, `[5] /`, `[.] Hidden`) |

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
