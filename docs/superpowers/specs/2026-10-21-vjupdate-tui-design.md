# vj — TUI front end for vjupdate: profiles, dotfile sets, local config

Date: 2026-10-21. Status: approved layout, awaiting spec review.

## Goal

Turn `vjupdate` from a single bash script with hard-coded `desktop`/`surface`
machines into a terminal app (TUI) that:

- lets the user pick a **profile** (hardware + packages) and a **dotfile set**
  (configs), both selectable and extendable by friends;
- keeps per-machine choices in one sorted local config file
  (`~/.config/vjupdate/config.toml`), never scattered on disk;
- runs a **first-run wizard** when that file is missing;
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
dotset      = "viridjan"          # default set offered in the wizard
hostname    = "desktop"           # substring; wizard pre-selects a match
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
    wizard.py     first-run
    home.py       main menu
    checklist.py  one generic checklist screen reused by every submenu
    review.py     pre-run summary + estimate
```

Launcher `scripts/.local/bin/vj` runs `python3 -m vj` with the repo on
`sys.path` (path found via its own symlink target, like vjupdate does).

### Screens

**Wizard** (only when `config.toml` is missing, or `vj --setup`):
1. Profile: list of `profiles/*.toml` with description; hostname match pre-selected.
2. Dotfile set: list of `dotsets/*/` + `none`; profile's default pre-selected.
3. Packages: resolved install list, all ticked; unticked → `[declined]`.
4. One-time setup: all once-tasks listed; user ticks what to run now, marks
   others "already done" or "skip".
5. Save config → Home.

**Home** — status line (profile, dotset, pending once-tasks count) and menu:

| Entry | Opens |
|---|---|
| Run maintenance | Checklist of routine actions (today's `routine` group) |
| Packages | Checklist: paru + flatpak, grouped; `a` adds a package locally, `x` marks for removal |
| Git repositories | Checklist of `projects.toml` repos to clone/pull |
| Dotfiles | Checklist of stow packages in the chosen set |
| One-time setup | Checklist of once-tasks with done date / skip status |
| DMS & Git | dms-import, dms-export, dotfiles-export |
| Settings | Change profile, dotset; re-run wizard |
| Review & run | Review screen |

**Checklist** (generic): items with id, label, detail, ticked. Keys: Space
toggle, `/` filter, `a` all, `n` none, `r` repo defaults, Enter/Esc back.
Initial ticks: `[last]` if present, else repo defaults; for packages,
`declined` overrides both.

**Review**: ordered list of actions; packages to install / remove (names, with
AUR packages marked); estimate per group and total:

| Estimate | Shown as |
|---|---|
| < 10 s | `< 10 s` |
| < 60 s | `< 1 min` |
| otherwise | `~N min`, plus names of packages with no history |

Enter runs, `b` back, `q` quit. On run, `[last]` and `[declined]` are saved.

### One-time tasks

Once-tasks = today's `system` group (services, snapper, automount, optimize,
keyboard, greeter, keyring-pam) + `tools` + `ai` groups + `dms-plugins`.
Kernels and manual-steps are not once-tasks (repeatable/informational).

At startup, if any once-task has no `[once]` entry, Home opens a prompt:
"N setup tasks never run on this machine" → the One-time setup checklist.
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
   Hostname detection moves to the wizard.
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
- `tests/test_vj_screens.py`: Textual `run_test()` pilot — wizard writes the
  expected config; checklist initial ticks follow last/declined/default.
- `tests/test_vjupdate.py`: new cases for `--actions`, `VJ_PLAN_DIR`,
  `_has_feature`, result file. Existing suite must stay green.
- No test touches the real system (existing mocked-PATH approach).

## 7. Build order (separate implementation stages)

| Stage | Delivers | Usable after? |
|---|---|---|
| A | TOML files, profiles, `vj/config.py` + `resolve.py`, bash reads plan dir / features / `--actions` | yes — `vjupdate` behaves as before on new files |
| B | Repo migration to `dotsets/viridjan/`, stow from dotset | yes |
| C | TUI: Home, Checklist, Review, bridge, `[last]`/`[declined]` | yes — `vj` usable |
| D | Wizard + once-tasks prompt | yes |
| E | Estimates in review + `build-times.tsv` in repo | yes |

Each stage: tests green, shellcheck clean, committed separately.

## Open risks

- **Big path move (stage B).** Every stow link changes. Mitigation: per-package
  restow with conflict report; Surface runbook; existing `git bundle` backup
  habit before the move.
- **`build-times.tsv` churn.** Committed on change only; per-package means
  pacman/flatpak keys change most runs. If noisy, round to 10 s buckets.
- **Textual version drift.** Pinned to whatever pacman ships; tests run against it.
