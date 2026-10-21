# vj — TUI front end for vjupdate: profiles, dotfile sets, local config

Date: 2026-10-21. Status: approved layout, awaiting spec review.

## Goal

Turn `vjupdate` from a single bash script with hard-coded `desktop`/`surface`
machines into a terminal app (TUI) that:

- lets the user pick a **profile** (hardware + packages) and a **dotfile set**
  (configs), both selectable and extendable by friends;
- keeps per-machine choices in one sorted local config file
  (`~/.config/vjupdate/config.toml`), never scattered on disk;
- runs a **setup submenu** (profile + dotfile set) when that file is missing;
- shows every batch action (packages, repos, dotfiles, one-time setup) as a
  checklist, pre-ticked from repo defaults, then from the user's last choices;
- remembers declined packages and never pre-ticks them again;
- tracks one-time setup tasks and offers the ones never done at startup;
- shows what will be installed and an estimated time before running;
- stores build/install time history **in git**.

## Non-goals

- No GUI. No non-Arch distros. No package manager other than pacman/paru/flatpak.
- No rewrite of the bash system logic (keyrings, mirrors, stow, audit,
  kernels, DMS sync…). Bash stays the backend; porting is a later, separate
  decision per action.
- No external git repos for dotfile sets (sets live in this repo; friends PR).

## Decisions taken

| Question | Decision |
|---|---|
| Language | Python 3 + Textual (`python-textual`, Arch `extra`) |
| Bash logic | Stays; becomes the backend the TUI runs |
| Local config | `~/.config/vjupdate/config.toml` (TOML, read with stdlib `tomllib`) |
| Dotfile sets | Folder per set inside this repo: `dotsets/<name>/` |
| Profile ↔ set | Independent; profile names a default set, user may pick any or `none` |
| Package lists | Seven `.list` files → `packages.toml` + `profiles/<name>.toml` |
| Build times | Moved from `~/.local/state/dots/` into repo `build-times.tsv` |

## 1. Repo layout

```
dots/
  packages.toml          common lists (was .paru-S-common/.paru-R/.paru-hold/
                         .paru-skip/.flatpak-S .list files)
  profiles/
    desktop.toml         was .paru-S-desktop.list + hard-coded `MACHINE == desktop`
    surface.toml         was .paru-S-surface.list + hard-coded `MACHINE == surface`
  projects.toml          git repos to clone (was projects.list)
  dotsets/
    viridjan/            every current stow package moves here unchanged:
      alacritty/ brave/ cave/ caveman/ claude/ DankMaterialShell/ fish/ fonts/
      gtk-3.0/ gtk-4.0/ micro/ mimeapps/ mpd/ niri/ ollama/ paru/ qt5ct/ qt6ct/
      spotify-player/ vesktop/ VSCodium/
      desktop/ surface/  machine-specific niri files (keyed by profile name)
  build-times.tsv        install/build duration history (committed)
  vj/                    Python package: the TUI
  scripts/               stays at repo root — it is tooling, not a dotfile set
    .local/bin/vjupdate  bash backend (still runnable directly)
    .local/bin/vj        launcher for the TUI
  windows/ tests/ .githooks/ TODO.md README.md CLAUDE.md   unchanged
```

`.dms-plugins.list` and `.install-scripts.list` stay where they are (not part
of this change).

### packages.toml

```toml
[paru]
install = ["fish", "niri", ...]   # was .paru-S-common.list
remove  = [...]                   # was .paru-R.list (force-removed before install)
hold    = ["vectorcraft"]         # was .paru-hold.list
skip    = []                      # was .paru-skip.list

[flatpak]
install = [...]                   # was .flatpak-S.list
```

Comments from the `.list` files are carried over as TOML comments.

### profiles/<name>.toml

```toml
description = "Tower — AMD RX 6700 XT, i5-13400F"
dotset      = "viridjan"          # default set offered on the setup submenu
hostname    = "desktop"           # substring; setup submenu pre-selects a match
features    = ["amd-gpu-tuning", "ollama-model", "steam-launchers"]

[paru]
install = [...]
[flatpak]
install = []
```

`features` replaces every `[[ $MACHINE == desktop|surface ]]` check in bash
(~12 sites: surface linux repo, AMD udev rule, ollama pull, start-windows
sizing, etc.). The exact feature names are fixed during implementation by
reading each site; one feature per distinct behaviour.

The machine-specific niri files are looked up as
`dotsets/<set>/<profile>/` — same files as today's `desktop/` and `surface/`
stow packages. A profile with no such folder in the chosen set gets no
machine niri files (the includes point at absent files; implementation must
create empty stubs, since niri errors on a missing include).

### projects.toml

```toml
[[repo]]
name = "dots"
url  = "git@github.com:Viridjan/dots.git"
```

### build-times.tsv

```
# key	seconds	updated
aur:godot	412	2026-10-21
@pacman-per-pkg	3	2026-10-21
@flatpak-per-pkg	9	2026-10-21
```

- `aur:<pkg>`: measured as today (`Making package` → `Finished making`).
- `@pacman-per-pkg` / `@flatpak-per-pkg`: last transaction time ÷ package
  count; used to estimate repo and Flatpak installs.
- Written only when a value changes; sorted by key so merges between
  machines stay line-local. Committed by the user via the existing
  "Review and upload Git changes" action (the app never commits on its own).

## 2. Local config: `~/.config/vjupdate/config.toml`

```toml
profile = "desktop"
dotset  = "viridjan"          # or "none" = don't manage dotfiles

[paru]                        # this machine's own changes, on top of the repo
add    = []
remove = []                   # added to the force-remove list
[flatpak]
add    = []
remove = []

[declined]                    # unticked repo defaults; never pre-ticked again
paru    = []
flatpak = []

[once]                        # one-time tasks: date done, or "skip"
fish        = 2026-10-21
keyring-pam = "skip"

[last]                        # last ticked IDs per submenu
actions  = ["sources", "install", "audit"]
repos    = ["dots"]
dotfiles = ["alacritty", "fish", "niri"]
```

Runtime data (logs, lock, keyring/mirror stamps) stays in
`~/.local/state/dots/`.

Writes are atomic (write temp file in same dir, `os.replace`). The file is
written by a small TOML writer in `vj/config.py` (stdlib has no TOML writer;
the schema is flat enough that ~40 lines suffice — no new dependency).

### Resolution order

```
install = packages.toml.install + profile.install + local.add
          − local.remove − declined − skip
remove  = packages.toml.remove + local.remove
hold    = packages.toml.hold
```

Pure function in `vj/resolve.py`; heavily unit-tested.

## 3. TUI (`vj/`)

```
vj/
  __main__.py     entry: `python3 -m vj`
  config.py       load/save local config, load repo TOML files
  resolve.py      resolution order, estimates
  bridge.py       writes the run plan, runs bash backend
  screens/
    home.py       the one screen: menu, inline submenu slot, recap
    setup.py      profile + dotfile set submenu panel
    checklist.py  generic checklist submenu panel
```

Launcher `scripts/.local/bin/vj` runs `python3 -m vj` with the repo on
`sys.path` (path found via its own symlink target, like vjupdate does).

### Screens

Everything happens on **one screen (Home)**, top to bottom:

1. **Status line:** profile, dotset, count of never-run one-time tasks.
2. **Menu box:** Maintenance actions · Packages · Git repositories · Dotfiles ·
   One-time setup · DMS & Git · Profile / dotfile set. Always visible.
3. **Submenu box:** Enter on a menu entry opens that submenu *inline, below
   the menu*, filling the space down to the recap. One submenu open at a
   time; opening another replaces it. Esc closes it and focus returns to the
   menu. Every change takes effect immediately (recap updates live).
4. **Recap box**, pinned to the bottom: always **10% of the terminal height**
   (minimum 5 rows), scrollable. Order: total estimate, packages to install
   (with per-package estimate), packages to remove, declined, actions in run
   order.

Keys: `r` = run everything in the recap (any time, unless typing in a filter),
`q` = quit.

**Profile / dotfile set submenu:** two titled boxes stacked — profiles
(`profiles/*.toml` + description; hostname match pre-highlighted) and dotfile
sets (`dotsets/*/` + `none`; profile's default pre-highlighted). Tab switches
box, Enter confirms. On first run (no `config.toml`) this submenu opens
automatically and can't be closed until a profile is confirmed; `r` is
refused until then. No separate wizard.

**Checklist submenu** (generic, used by all others): items with id, label,
ticked. Keys: Space toggle, `/` filter, `a` all, `n` none, `d` repo defaults,
Esc close. Packages checklist adds `+` add a local package, `x` mark for
removal. Initial ticks: `[last]` if present, else repo defaults; for packages,
`declined` overrides both.

Estimate format:

| Estimate | Shown as | Colour |
|---|---|---|
| < 10 s | `< 10 s` | green |
| < 60 s | `< 1 min` | yellow |
| otherwise | `~N min` | orange |

Shown per package in the Packages checklist (first column) and the
recap, plus the coloured total. Packages with no history use a flat guess
(paru 3 s, flatpak 10 s) marked with `?`; the review also shows the count of
guessed packages.

On run, `[last]` and `[declined]` are saved first.

### One-time tasks

Once-tasks = today's `system` group (services, snapper, automount, optimize,
keyboard, greeter, keyring-pam) + `tools` + `ai` groups + `dms-plugins`.
Kernels and manual-steps are not once-tasks (repeatable/informational).

If any once-task has no `[once]` entry, the status line shows
"N setup tasks never run" (highlighted); they are listed in the One-time
setup checklist, unticked. Unticking-and-leaving marks nothing; the checklist
has `s` = mark highlighted task "skip" and `d` = mark "already done".
A task is stamped with today's date only when its backend result is `ok`.

## 4. Bridge to bash

The app never reimplements system actions. It writes a **run plan** and runs
bash with the terminal handed over (`App.suspend()`), so sudo, pacman, paru,
pacdiff and other interactive prompts work exactly as today.

Run plan, in `$XDG_RUNTIME_DIR/vj-<pid>/`:

```
paru-install.list  paru-remove.list  paru-hold.list  paru-skip.list
flatpak-install.list  projects.list  stow.list
```
(same one-name-per-line format bash already reads).

Invocation:

```
VJ_PLAN_DIR=… VJ_PROFILE=desktop VJ_DOTSET_DIR=…/dotsets/viridjan \
VJ_FEATURES="amd-gpu-tuning ollama-model" VJ_RESULT_FILE=…/result.tsv \
vjupdate --actions sources,install,audit,stow-symlinks
```

Bash changes (kept small, all covered by the existing test suite + new tests):

1. `--actions <ids>`: skip the bash menu, run exactly these IDs (same IDs as
   `_menu_add`), same ordering logic as the menu path.
2. List paths read from `VJ_PLAN_DIR` when set. Without it, bash resolves
   `packages.toml`/profile itself via `python3 -m vj resolve` so
   `vjupdate --yes` keeps working standalone.
3. `MACHINE` comes from `VJ_PROFILE`; machine checks become `_has_feature X`.
   Hostname detection moves to the setup submenu.
4. Stow runs from `VJ_DOTSET_DIR` (skipped when dotset is `none`), restricted
   to `stow.list`. `scripts` is always stowed from repo root.
5. `_record` results additionally appended to `VJ_RESULT_FILE`
   (`id\tok|fail|skip`) so the app can stamp once-tasks.
6. Build-time recording writes `build-times.tsv` in the repo; adds
   `@pacman-per-pkg`/`@flatpak-per-pkg` from timed transactions.

After the run the app resumes, reads `result.tsv`, updates `[once]`, shows the
recap.

## 5. Migration (one commit set, run on desktop)

1. `git mv` stow packages → `dotsets/viridjan/`; `desktop/` `surface/` →
   `dotsets/viridjan/desktop|surface`.
2. Convert `.list` files → TOML (script, comments kept); delete old files.
3. Move `aur-build-times.tsv` → `build-times.tsv` (prefix keys `aur:`).
4. Re-stow everything from new paths (`stow -D` old, `stow` new, per package;
   conflicts reported as today).
5. Update CLAUDE.md, README, `.graphifyignore` paths.
6. **Surface:** add a TODO.md manual-confirm checklist + standalone tested
   script: pull, unstow old paths, stow new, write `config.toml` with
   `profile = "surface"`.

## 6. Testing

- `tests/test_vj_resolve.py`: resolution order, declined, local add/remove,
  estimate buckets.
- `tests/test_vj_config.py`: round-trip load/save, atomic write, missing file.
- `tests/test_vj_screens.py`: Textual `run_test()` pilot — setup submenu writes
  the expected config; checklist initial ticks follow last/declined/default.
- `tests/test_vjupdate.py`: new cases for `--actions`, `VJ_PLAN_DIR`,
  `_has_feature`, result file. Existing suite must stay green.
- No test touches the real system (existing mocked-PATH approach).

## 7. Build order (separate implementation stages)

| Stage | Delivers | Usable after? |
|---|---|---|
| A | TOML files, profiles, `vj/config.py` + `resolve.py`, bash reads plan dir / features / `--actions` | yes — `vjupdate` behaves as before on new files |
| B | Repo migration to `dotsets/viridjan/`, stow from dotset | yes |
| C | TUI: Home, Checklist, Review, bridge, `[last]`/`[declined]` | yes — `vj` usable |
| D | Setup submenu + once-task tracking | yes |
| E | Estimates in review + `build-times.tsv` in repo | yes |

Each stage: tests green, shellcheck clean, committed separately.

## Open risks

- **Big path move (stage B).** Every stow link changes. Mitigation: per-package
  restow with conflict report; Surface runbook; existing `git bundle` backup
  habit before the move.
- **`build-times.tsv` churn.** Committed on change only; per-package means
  pacman/flatpak keys change most runs. If noisy, round to 10 s buckets.
- **Textual version drift.** Pinned to whatever pacman ships; tests run against it.
