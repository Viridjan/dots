# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

GNU Stow dotfiles for CachyOS + niri. All config files live here and are
symlinked into `$HOME` via stow. `vj` (Textual TUI, `vj/`) drives `vjupdate`
(bash backend). Machines are **profiles** (`profiles/*.toml`), configs are
**dotfile sets** (`dotsets/<name>/`), per-machine choices live in
`~/.config/vjupdate/config.toml` (not in git). Design:
`docs/superpowers/specs/2026-10-21-vjupdate-tui-design.md`.

## Commands

```bash
vj                                                                # the TUI (needs python-textual)
python3 -B -m vj plan /tmp/plan                                   # write the run plan vjupdate reads
vjupdate --actions sources,install                                # run menu IDs without a menu (what vj does)
python3 -B -m unittest discover -s tests -v                      # all tests (mocked; no system changes)
python3 -B -m unittest tests.test_vjupdate.HoldTests             # one class
python3 -B -m unittest tests.test_vjupdate.HoldTests.test_upgrade_holds_on_first_attempt_and_retry
VJUPDATE_SCRIPT=/path/to/snapshot python3 -B -m unittest ...     # run tests against a saved script copy
shellcheck -S warning scripts/.local/bin/vjupdate                 # pre-commit enforces -S error
bash -n scripts/.local/bin/vjupdate
niri validate -c ~/.config/niri/config.kdl; echo $?               # check exit code before reloading
```

Tests `source` vjupdate (main is guarded by a `BASH_SOURCE` check) with a
restricted `PATH` where pacman/paru/sudo/stow/git are mocks.

**Don't edit vjupdate in place while it runs** (`pgrep -af vjupdate`): bash reads
scripts by byte offset and `~/.local/bin/vjupdate` links to the repo file, so an
in-place write corrupts a live upgrade. Write a temp file and `mv` it over.

## Claude Code launch

Always open Claude Code from `~/Projects`, not `~/Projects/dots`:

```bash
cd ~/Projects && claude
```

Memory and project context are scoped to the working directory at launch. Opening from `~/Projects/dots` creates a separate scope — prior conversation context and memory won't load. When working on dots inside a Claude session, just `cd ~/Projects/dots` from within it.

## Repo layout

```
dots/
  packages.toml   ← package lists shared by every profile: [paru] install/remove/hold/skip, [flatpak] install
  profiles/       ← one TOML per machine type: description, hostname match, default dotset,
                    features (switches read by vjupdate's _has_feature), [paru]/[flatpak] install
  projects.toml   ← [[repo]] name/url cloned into ~/Projects by the sources phase
  build-times.tsv ← committed timing history: aur:<pkg>, @pacman-per-pkg, @flatpak-per-pkg (seconds)
  vj/             ← Python: config.py (repo + local config), resolve.py (lists, estimates, run plan),
                    state.py (everything the TUI shows/changes), ui.py (Textual),
                    progress.py (PTY-backed run screen), __main__.py (CLI)
  dotsets/
    viridjan/     ← my dotfile set; every subdir is a stow package except profile-named dirs:
      alacritty/      → ~/.config/alacritty/
      brave/          → /etc/brave/policies/managed/  (Brave managed policy; stow -t /)
      claude/         → ~/.claude/  (settings.json, keybindings.json, statusline.sh + segment scripts)
      DankMaterialShell/ → ~/.config/DankMaterialShell/
      desktop/        → ~/.config/niri/cfg/{display,input,autostart-machine,surface-layout}.kdl (profile desktop; ln, not stow)
      fish/           → ~/.config/fish/  (Arch logo override for fastfetch — see fish_greeting in config.fish;
                        functions/claude.fish wraps claude in claude-auto-retry: tmux + retry monitor,
                        npm 0.7.3 because npm 12 blocks git/tarball installs; StopFailure hook in claude/settings.json)
      fonts/          → ~/.local/share/fonts/  (user fonts)
      gtk-3.0/ gtk-4.0/ micro/ paru/ qt5ct/ qt6ct/ VSCodium/ → ~/.config/<same>/
      mpd/            → ~/.config/mpd/  (deployed since 2026-10-21; was never in the old stow list)
      mimeapps/       → ~/.config/mimeapps.list  (set via `xdg-mime default`; then `kbuildsycoca6` or Dolphin keeps old handler)
      niri/           → ~/.config/niri/  (file-level links, see below)
      spotify-player/ → ~/.config/spotify-player/  (app.toml + keymap.toml)
      surface/        → same files as desktop/, for profile surface
      systemd-user/   → ~/.config/systemd/user/  (vjupdate-check.timer: weekly report-only --check)
      vesktop/        → ~/.config/vesktop/  (settings.json + settings/)
      cave/           → ~/.cave/  (Cave AI agent config + ollama extension)
      caveman/        → ~/.config/caveman/  (caveman plugin defaultMode = ultra)
      ollama/         → /etc/systemd/system/ollama.service.d/  (rocm.conf + limits.conf ~40% cap; stow -t /)
      nirinit/        → ~/.config/nirinit/  (skip list: apps the niri autostart already opens)
      xdg-desktop-portal/ → ~/.config/xdg-desktop-portal/  (niri-portals.conf: copy of /usr/share's + ScreenCast=niri-autoselect)
  scripts/        → ~/.local/bin/ + ~/.local/lib/vjupdate/ (automount.sh)  (vjupdate, vj, start-windows, start-open-notebook, start-keep, start-battlenet, gamescope-media; stowed --no-folding,
                    always from the repo root — tooling, not part of a dotfile set)
                  + ~/.local/share/applications/  (.desktop launchers)
                  + ~/.local/share/ollama/  (<name>.Modelfile, rebuilt by setup_ollama)
  windows/        ← NOT a stow package — Docker Compose for Windows 11 VM (dockur/windows, port 8006)
  .githooks/      ← NOT a stow package — git hooks (secret scan + shellcheck); registered via core.hooksPath
  .github/        ← CI: unittest suite + shellcheck on push
  tests/          ← NOT a stow package — vjupdate + vj unittest suites (mocked system commands)
  docs/superpowers/ ← specs and plans
  graphify-out/   ← NOT a stow package — tracked /graphify knowledge graph; corpus filter in .graphifyignore
  surface-sync.sh ← TEMPORARY one-shot Surface catch-up (unfold ~/.local/bin, reset, relink from dotsets/); delete once TODO.md's checklist is ticked
```

Paths like `niri/.config/niri/…`, `desktop/…`, `claude/…` further down are
relative to `dotsets/viridjan/` (moved there 2026-10-21).

### Profiles, dotfile sets, local config (2026-10-21)

- **Run plan.** `python3 -m vj plan DIR` resolves `packages.toml` + profile +
  local config into `paru-install.list paru-remove.list paru-hold.list
  paru-skip.list flatpak-install.list projects.list stow.list env`. vjupdate
  reads only these (`VJ_PLAN_DIR`). vj passes its own plan; a standalone
  `vjupdate` builds a temporary one (`_ensure_plan`), choosing the profile from
  `config.toml`, else the profile whose `hostname` is a substring of the host,
  else dies with "run 'vj'". `env` sets `VJ_PROFILE` (= `MACHINE`),
  `VJ_DOTSET_DIR` (empty for `none`), `VJ_FEATURES`.
- **Resolution:** install = packages.toml + profile + local add − local remove
  − declined − skip. Declined ≠ removed. `[paru].remove` (repo) is
  force-removed (`pacman -Rdd`, conflict swaps); local `x` marks go to
  `paru-demote.list`: `pacman -D --asdeps`, then removed only if nothing needs
  them (`-Rns`), else kept with a "still required by" warning. Package swaps
  therefore belong in the repo list. `_PROTECTED_PKG_RE` (kernels, firmware,
  ucode, limine, base, glibc, pacman, keyrings…) is never removed by any path.
- **Other plan lists:** `systemd-enable.list`/`systemd-user.list` (`[systemd]
  enable/user`), `npm-install.list` (`[npm]`), `uv-install.list` (`[uv]`) —
  repo + profile, no local overrides. `ignore.list` = local `[ignored]`.
  `known-packages.list` contains all declared shared/profile/local install
  names before declined selections are filtered out. The audit reads it to
  match the menu's definition of unlisted; unticked does not mean unknown.
- **In-app runs:** `RunScreen` (`vj/progress.py`) starts vjupdate on a controlling
  PTY and polls output without blocking Textual. The overall bar counts the five
  phase results in `result.tsv`; the current-task bar shows activity, not an
  estimated percentage. Prompt replies go to the PTY, with masking when terminal
  echo is disabled. Ctrl+C sends an interrupt; Ctrl+T explicitly hands over the
  terminal for editors, Ctrl+] returns, Escape dismisses a finished run. The plan
  stays available until dismissal, then results are applied and it is removed.
- **Setup checks:** MPD's data directory (`~/.local/share/mpd`) must exist before
  its user service starts. Claude setup checks `plugin list --json` at user scope
  before installing plugins; Graphify is a CLI-installed skill, checked via
  `${CLAUDE_CONFIG_DIR:-$HOME/.claude}/skills/graphify/SKILL.md`, not a marketplace
  plugin. Keep installation error output visible. Empty `[once]` history does
  not prove that a system feature is unconfigured.
- **Package failures:** conflict removal/demotion require an exact installed
  package name, not merely a provider. Install conflicts skip mirror retries;
  other failures retain the retry and include the last package error in the
  recap. CachyOS package names are `dux-shell` and `dux-gop`; binaries/service
  names such as `dms` remain unchanged.
- **Unlisted packages** (vj menu row): explicit installs (`pacman -Qeq` +
  flatpak apps) in no list, not skipped/removed/ignored. Keys act on ticked
  rows, else the highlighted one: `p` → `packages.toml`, `f` → active profile
  file (both via `config.add_to_list`, which keeps comments and refuses to
  write TOML that doesn't parse — commit afterwards), `m` → local add, `x` →
  local remove (demote; paru only), `i` → `[ignored]`. Audit reports the
  remaining count via `vj unused`.
- **Features** replace every old `MACHINE == desktop|surface` check:
  `linux-surface`, `desktop-services`, `cpu-performance`, `amd-gpu-tuning`,
  `ollama-model`, `windows-vm`. New machine-dependent behaviour → new feature
  name in the profile + `_has_feature <name>` in vjupdate.
- **Stow** deploys `stow.list` (vj's Dotfiles ticks, default every package in
  the set) from `VJ_DOTSET_DIR`; `scripts` always from the repo root. Dotset
  `none` → only `scripts`; DMS import/export warn and skip.
- **`--actions A,B`** runs exactly those action IDs (`MENU_ORDER`),
  no menu; unknown IDs die. `_record` also appends `name\tstate` to
  `VJ_RESULT_FILE`; configure actions record `action:<id> ok` via `_act`, which
  vj uses to stamp one-time tasks.
- **Local config** keys: `profile`, `dotset`, `[paru]/[flatpak] add/remove`,
  `[declined]`, `[ignored]` (unlisted installs not to report), `[once]` (date
  or "skip"), `[last]` (maint/repos/dotfiles ticks). Saved atomically on every change. Override path with `VJ_CONFIG`.
- **Adding a friend:** `profiles/<name>.toml` for their hardware and/or
  `dotsets/<name>/` with their stow packages (+ `<profile>/` dirs for niri
  machine files). `.gitignore` secret rules use `dotsets/*/`, so they apply to
  every set.

`niri` uses **file-level symlinks** — the `cfg/` and `dms/` directories are real, but individual `.kdl` files are symlinked. `scripts` is stowed `--no-folding`: `~/.local/bin` is a real directory with per-file links to the tracked scripts (incl. `vj`), so installers (npm -g, uv, codex, AppImages) write there and never into the repo. All other packages use directory-level symlinks.

Before 2026-09-25 `~/.local/bin` was a folded link into `scripts/.local/bin/`, so every installer wrote into the repo. One-time migration per machine (on the Surface: run it **before** `git pull`, since the pull deletes the tracked installer links it still serves from PATH):
```bash
bash <<'EOF'
set -eu
B=~/Projects/dots/scripts/.local/bin
KEEP=" vjupdate start-windows start-open-notebook start-keep "
[ -L ~/.local/bin ] || { echo "already unfolded"; exit 0; }
T=$(mktemp -d ~/.local/bin-migrate.XXXX)
for f in "$B"/* "$B"/.[!.]*; do
  [ -e "$f" ] || [ -L "$f" ] || continue
  n=${f##*/}; case "$KEEP" in *" $n "*) continue;; esac
  mv -n -- "$f" "$T/" && [ ! -e "$f" ] && [ ! -L "$f" ] || { echo "FAILED: $n (staging: $T)"; exit 1; }
done
cd ~/Projects/dots && stow --no-folding --restow -t ~ scripts
mv -n -- "$T"/* ~/.local/bin/ && rmdir "$T"
EOF
```

`claude` may need `vjupdate --adopt` on a fresh machine (absorbs existing real files, backing them up first).

`desktop/` and `surface/` inside a set are not stow packages: `_stow_niri_cfg` links the files of the dir named after the active profile.

## Niri config structure

**IPC helpers (2026-10-28, from awesome-niri):** `config.kdl` starts
`niriusd` and `nirinit` (oniri, which auto-maximized a lone window, was dropped
2026-10-31 at user request and is in `[paru].remove`). No vertical stacking: niri_tilemod (auto-stack) was
dropped and the `consume-or-expel` binds removed; `Mod+Period` still expels. Surface
also runs `iio-niri listen --monitor eDP-1`. `niri-autoselect-portal` removes the
screencast picker: pick the target with `Mod+Ctrl+S` (window) /
`Mod+Ctrl+Shift+S` (monitor), clear with `Mod+Ctrl+X`. nirinit 0.1.x relaunches
saved windows by app_id; add autostarted apps to its skip list.

```
niri/.config/niri/
  config.kdl          ← entry point; layout/animations/input/misc/keybinds/window-rules
                        mostly live INLINE here (see "Resolved 2026-08-24" note below) +
                        `include` for machine-specific and dms/ overrides
  cfg/                ← empty as of 2026-08-24; only machine-pkg files symlink here (below)
    display.kdl         (NOT in niri pkg — comes from desktop/ or surface/; SOLE output source for DP-1)
    input.kdl           (NOT in niri pkg — comes from desktop/ or surface/; keyboard layout)
    surface-layout.kdl  (NOT in niri pkg — comes from desktop/ or surface/; machine-specific overrides)
  dms/                ← DankMaterialShell overrides; NOT stow-symlinked (copied via vjupdate --dms-export/--dms-import)
    alttab.kdl        (recent-windows corner-radius — REGENERATED by DMS every start, don't hand-edit)
    binds.kdl         (keybinds — the live source; genuinely NOT regenerated, safe to hand-edit)
    colors.kdl        (Material You focus-ring/border colors — DMS regenerates live; the REPO copy is
                       authoritative and is pushed back live by --dms-import; --dms-export skips it)
    cursor.kdl        (not regenerated, safe to hand-edit)
    layout.kdl        (gaps, border/focus-ring widths, corner-radius — REGENERATED every start, DO NOT EDIT)
    outputs.kdl       (deleted from the repo 2026-08-25 + include removed. DMS recreates it at every
                       start as a 0-BYTE EMPTY file — the old `output "DP-1"` block with unconditional
                       VRR does NOT return on its own. Real content is written only when display
                       settings are applied via DMS's Display panel. See the one-click trap below.)
    windowrules.kdl   (0 bytes; imported by vjupdate but not included — harmless)
    wpblur.kdl        (layer-rule for namespace `dms:blurwallpaper`; included since 2026-08-25.
                       Currently matches NOTHING live — DMS only creates that layer when
                       `blurredWallpaperLayer`/`blurEnabled` are true in DankMaterialShell/settings.json,
                       and both are false. Included so it works if blur is ever switched on.)
```

### Include order in config.kdl

```
cfg/autostart-machine → cfg/surface-layout → cfg/input  (machine-specific; from desktop/ or surface/ pkg)
→ dms/colors → dms/layout → dms/alttab → dms/binds → dms/cursor → dms/wpblur
→ cfg/display  (sole output source; dms/outputs is deliberately NOT included)
```

**Merge semantics differ by node kind — this is a trap (corrected 2026-08-25):**

| Node kind | Example | Duplicate across includes | Duplicate in ONE file |
|---|---|---|---|
| Keyed | `output "DP-1"` | **FIRST wins**, silently | allowed |
| Singleton | `layout`, `input` | fields merge; **LATER wins** on conflict | **hard error**, `duplicate node` |

This file previously documented one blanket rule ("later includes override earlier ones... verified for `output` blocks specifically"). That was **wrong for `output`** and cost days of misdiagnosis — every edit to `cfg/display.kdl` was silently inert because `dms/outputs.kdl` was included first and won. Fix was to drop the `dms/outputs.kdl` include entirely.

Both rows were proven empirically on 2026-08-25, not assumed:
- **Keyed/first-wins:** injected `output "DP-1" { position x=0 y=777 }` *before* the `cfg/display.kdl` include (which sets `y=0`); `niri msg outputs` reported `Logical position: 0, 777` — the earlier block.
- **Singleton/later-wins:** added a temp include with `layout { gaps 40 }` *after* `dms/layout.kdl` (which sets `gaps 4`); tile height went 1432 → 1360 (= 1440 − 2×40) — the later include.

**Verifying an output change live is tricky** — `niri msg action load-config-file` does *not* force a modeset on an already-connected output, so an ignored `mode` looks identical to an unapplied one. Use `position` (applies live) as the probe when testing which block wins, not `mode`. See `[[niri-gaming]]`.

**Resolved 2026-08-24 (previously "KNOWN DRIFT"):** `niri/.config/niri/cfg/` used to hold `animation.kdl`, `autostart.kdl`, `keybinds.kdl`, `layout.kdl`, `misc.kdl`, `rules.kdl` — all real files, correctly symlinked live, but never `include`d in `config.kdl`, so niri never read them. Diffed each against its live equivalent and resolved per-file:
- `cfg/misc.kdl`, `cfg/autostart.kdl` — pure duplicates of `config.kdl`'s inline `environment{}`/`hotkey-overlay{}`/`screenshot-path`/`prefer-no-csd` and the (empty, points to `autostart-machine.kdl`) stub. **Deleted**, no functional loss.
- `cfg/keybinds.kdl` — heavy overlap with `dms/binds.kdl` plus real conflicts (e.g. `Mod+Shift+Left` bound to `focus-monitor-left` here vs `move-column-left` in `dms/binds.kdl` — re-including as-is would have hit the duplicate-keybind silent-reload-failure trap below). **Deleted**; ported the 3 genuinely-missing binds (`Mod+E` dolphin, `Mod+B` brave-browser, `Mod+TAB` focus-workspace-previous) into `dms/binds.kdl` instead.
- `cfg/rules.kdl` — had a mix of genuinely-missing rules (dgop-monitor/spotify-player-TUI/vesktop/libreoffice column widths, thunderbird/whatsie/TelegramDesktop → social workspace, steam-game fullscreen+VRR) and one broad, risky global rule (`open-focused false` with no `match` — would've silently stopped *any* newly-opened window from grabbing focus unless a more specific rule said otherwise). **Deleted**; ported the safe additive rules into `config.kdl`'s existing inline `window-rule` blocks, skipped the global-focus rule per user decision (see `[[niri-gaming]]` memory).
- `cfg/layout.kdl`, `cfg/animation.kdl` — real value conflicts with what's actually live via `dms/layout.kdl`/inline `config.kdl` (gaps 13px vs live 4px, focus-ring 4px vs live 2px, corner-radius 15px vs live 12px, snappier critically-damped springs vs live's bouncier ones). User chose to keep the current look/feel rather than restore these. **Deleted**.
- machine-pkg `cfg/input.kdl` (`desktop/`/`surface/`) — set `layout "us" variant "intl"`, genuinely missing (inline `input{}`'s `xkb{}` was empty, silently falling back to system locale instead of the documented "us intl"). **Restored** — added `include "cfg/input.kdl"` to `config.kdl`.

`niri/.config/niri/cfg/` is now empty (nothing left to symlink there); `_stow_niri_cfg` in vjupdate no longer has a loop for it — only the machine-pkg loop (`display`/`input`/`autostart-machine`/`surface-layout`) remains.

### What to edit

- **Output config** (resolution, refresh rate, VRR): edit `cfg/display.kdl` (desktop/surface pkg) directly — it is the **only** `output` block in the tree, because `dms/outputs.kdl` is no longer included. Do **not** re-add that include hoping "last wins": keyed nodes take the FIRST occurrence, so re-adding it before this file would silently make every edit here inert again (see Merge semantics above). Reload live without a relogin: `niri msg output <name> mode "<mode>"` / `niri msg output <name> vrr [--on-demand] on|off` — **temporary**, not saved to file, and it *outlives a config reload* (niri keeps the override until the file's output config actually changes), so it is easy to mistake a stale CLI override for a working config. A plain `niri msg action load-config-file` reloads the config but does **not** force a live modeset on an already-connected output. Validate first with `niri validate -c ~/.config/niri/config.kdl` and **check its exit code** — a parse error aborts the reload silently, leaving the last-good config running and making a broken test look like "nothing changed".
- **Layout/animations/misc/screenshot-path**: edit inline in `config.kdl` directly (the `layout {}`, `animations {}`, `input {}`, `environment {}` blocks near the top, `screenshot-path` near the bottom). Nothing under `cfg/` handles these anymore — see "Resolved 2026-08-24" above for why.
- **Keybinds**: edit `dms/binds.kdl` — the sole live source. Confirmed *not* regenerated by DMS (unlike `colors`/`layout`/`alttab`/`wpblur`/`outputs` — see the regeneration table below), so hand edits stick. But it's a live *copy* under `~/.config/niri/dms/`, not a symlink — edit the repo file then `cp` it live (or `vjupdate --dms-import`) to apply.
- **Workspaces** (2026-10-29): 1 social, 2 media (dgop, Spotify, Steam/Bottles/Battle.net launchers),
  3 games (empty at login, games open unfocused; `steam_app_*`, Dota 2, Wine `*.exe`, `gamescope-media`), 4 main.
  `start-battlenet` (umu) gives launcher and games one app-id, `steam_app_battlenet`: title `^Battle\.net` → media
  and excluded from the `^steam_app_` fullscreen rule, the rest → games.
  A workspace added by reload lands at index 1 live; `niri msg action move-workspace-to-index --reference <name> <n>`.
- **Window rules**: edit the inline `window-rule {}` blocks in `config.kdl` (per-app column widths, workspace assignments, gaming fullscreen/VRR rules are all there together, in file order — later rules override earlier ones for the same property on a matching window).
- **Machine-specific niri overrides**: both `desktop/` and `surface/` packages provide identically-named `.kdl` files under `cfg/`. `vjupdate` symlinks the active machine's version into `~/.config/niri/cfg/`. `config.kdl` includes them unconditionally — the machine-specific content differs, or one side is empty. Current files:
  - `autostart-machine.kdl` — desktop has `spawn-at-startup` entries (thunderbird, whatsie, Telegram, steam, dgop monitor in alacritty (TMOG tried and dropped 2026-10-27), daemons) plus `flatpak run com.spotify.Client` for real Spotify, and a `niri msg output DP-1 vrr off` belt-and-suspenders line (2026-08-25); surface is empty (no autorun). Vesktop launches via XDG autostart (`~/.config/autostart/vesktop.desktop`), not here. Terminal for spawned TUIs is `alacritty`.
  - `input.kdl` — sets keyboard `layout "us" variant "intl"` (both machines); surface additionally tunes touchpad/touchscreen/stylus.
  - `surface-layout.kdl` — surface sets `proportion 0.5` **twice**: once in a `layout { default-column-width }` (singleton — wins over `config.kdl`'s inline empty one, since later-wins) and once in a bare `window-rule { default-column-width }` (repeatable — included after the inline per-app width rules, so it overrides all of them). Desktop is a comment-only stub.
  - To add a new machine-specific override: create the `.kdl` in both `desktop/` and `surface/` packages, add `include "cfg/<name>.kdl"` to `config.kdl`, and add `<name>` to the `for f in ...` loop in `vjupdate`'s `_stow_niri_cfg` (the machine-pkg loop — `display input autostart-machine surface-layout`).
  - Content common to both machines but that needs to differ slightly: put shared parts in `config.kdl` inline, machine-specific delta in the per-machine file.
- **DMS overrides** — direction depends on whether DMS regenerates the file:
  - `DMS_MANUAL` (`alttab` `binds` `cursor` `layout` `windowrules` `wpblur`): edit **live** under `~/.config/niri/dms/`, then `vjupdate --dms-export` to copy into the repo and commit. Note the array name overstates things — only `binds`, `cursor` and `windowrules` are truly hand-editable; `layout`, `alttab` and `wpblur` get regenerated from `settings.json` at every DMS start, so hand edits there are lost (change the DMS setting instead). They stay in this list because regeneration is deterministic, so exporting them is a harmless no-op.
  - `DMS_AUTO` (`colors.kdl`): edit the **repo** copy, then `vjupdate --dms-import` to push it live. Export skips it on purpose — see below.
  - Either way, reload with `niri msg action load-config-file`.
- **Do not** hand-edit `dms/colors.kdl` *live* — DMS regenerates it and your edit is lost. To change colors, edit the **repo** copy and run `vjupdate --dms-import` (pushes repo→live) + `niri msg action load-config-file`. `--dms-export` deliberately skips `colors.kdl` so DMS's regenerated version can't overwrite your curated one.

  **Why that matters (2026-08-25 audit):** `dms_export` used to blanket-`cp` every live `*.kdl` into the repo, including auto-generated ones. That silently reverted the repo's green focus-ring (`#4caf50`) and forest shadow (`#0d3320CC`) to DMS defaults in commit `ff2cd4e` (2026-06-17) — a commit whose message was about unrelated vjupdate changes — and it went unnoticed for two months while this file kept documenting green as current. `dms_export` is now restricted to `DMS_MANUAL`, and `dms_import` additionally pushes `DMS_AUTO` (`colors.kdl`) back live. Current colors are DMS-default purple; that's the deliberate choice as of 2026-08-25, not drift.

  **⚠ The one-click trap (verified 2026-08-25):** with `include "dms/outputs.kdl"` removed, `dms config resolve-include niri outputs.kdl` reports `included:false`, so DMS's **Settings → Display** shows a *"First Time Setup"* box: *"Click 'Setup' to create the outputs config and add include to your compositor config."* That button calls `fixOutputsInclude()`, which backs up `config.kdl`, **re-adds the include**, and regenerates a full `output` block. Since keyed nodes take the FIRST occurrence, the re-added include lands before `cfg/display.kdl` and silently makes it inert — **one click restores the flicker bug**. Don't press it; if pressed, delete the include line again. It is only ever triggered by that button, never automatically.

  **Which files DMS actually regenerates (measured by restarting `dms.service`, not assumed):**

  | Regenerated every start | Only on settings change | Never (truly hand-edited) |
  |---|---|---|
  | `layout.kdl`, `alttab.kdl`, `wpblur.kdl` (journal logs "Generated … config at …"), plus `outputs.kdl` as a 0-byte stub | `colors.kdl` (theme change), `outputs.kdl` content (Display panel) | `binds.kdl`, `cursor.kdl`, `windowrules.kdl` |

  The three regenerated files are rebuilt **deterministically from `DankMaterialShell/settings.json`** — after a restart they came back byte-identical to the repo copies, so `--dms-export` round-trips them harmlessly. But editing them by hand is pointless: the next DMS start overwrites your edit. The older blanket claim that DMS rewrites its files "within seconds of every session start regardless of content" was too broad — `binds.kdl` and `cursor.kdl` are genuinely untouched.

## Stow operations

The repo lives at `~/Projects/dots`, so stow's default target (the parent dir) is `~/Projects`, not `~`. Always pass `-t ~`.

```bash
# Full bootstrap or re-apply everything (idempotent)
bash scripts/.local/bin/vjupdate

# Same, non-interactive (no prompts)
vjupdate --yes

# Update packages + clean caches
vjupdate --update

# Audit installed software: orphans, rebuilds, pacnew, firmware
vjupdate --check

# Interactively install/remove CachyOS kernels
vjupdate --kernels

# Detect internal partitions and add to /etc/fstab interactively
vjupdate --automount

# Apply CachyOS tuning (idempotent): CPU governor, disable NM-wait-online,
# mask lvm2-monitor, rate-mirrors 2h delay, AMD GPU performance udev rule
vjupdate --optimize

# Add pam_gnome_keyring.so to /etc/pam.d/greetd (idempotent; fixes keyring unlock prompt)
vjupdate --keyring-pam

# Sync DMS overrides: live ~/.config/niri/dms/*.kdl → repo (then commit)
vjupdate --dms-export

# Sync DMS overrides: repo → live (skips auto-generated files)
vjupdate --dms-import

# Create .desktop launchers for all installed Steam games
vjupdate --steam-launchers

# Rebuild packages flagged by rebuild-detector
vjupdate --rebuild

# Interactively merge .pacnew files (pacdiff; overwrites keep a .bak)
vjupdate --pacnew

# Preview the resolved plan; changes nothing, takes no lock, fetches nothing
vjupdate --dry-run          # combine with any bootstrap/update/check action

# Let stow adopt conflicting files (backs them up to
# ~/.local/state/dots/adopt-backup-<ts>/ first)
vjupdate --adopt

# Also wipe ~/.cache/paru and ~/.cache/yay during cleanup
vjupdate --clean-aggressive

# Remove stale non-Steam app launchers, report apps not mirrored locally
vjupdate --app-launchers

# Skip specific bootstrap phases (space-separated).
# ONLY these five names work — they are matched against the phase names passed
# to _run_phase. `SKIP_PHASES="mirrors keyrings"` (documented here until
# 2026-09-15) matched nothing and silently skipped no phases: mirrors/keyrings
# are stamp names, throttled by _needs_run, not phases.
SKIP_PHASES="sources install dotfiles configure audit" vjupdate

# Re-apply all packages at once (scripts, the chosen set incl. niri links + /etc packages)
vjupdate --actions stow-symlinks

# By hand
cd ~/Projects/dots && stow --no-folding --restow -t ~ scripts   # keeps ~/.local/bin a real dir
cd ~/Projects/dots/dotsets/viridjan && stow --restow -t ~ <pkg>
sudo stow -d ~/Projects/dots/dotsets/viridjan --restow -t / ollama brave   # root target

# Remove a package
cd ~/Projects/dots/dotsets/viridjan && stow -D -t ~ <pkg>
```

`niri` is not stowed — DMS owns `~/.config/niri/`. Re-run `vjupdate` to refresh symlinks.

### Adding a new config package

```bash
# 1. Create package structure mirroring the target path
mkdir -p ~/Projects/dots/dotsets/viridjan/<pkg>/.config/<pkg>

# 2. Copy live config into the package
cp -r ~/.config/<pkg>/. ~/Projects/dots/dotsets/viridjan/<pkg>/.config/<pkg>/

# 3. Remove the real directory so stow can create the symlink
rm -rf ~/.config/<pkg>

# 4. Stow it
cd ~/Projects/dots/dotsets/viridjan && stow -t ~ <pkg>
```

Result: `~/.config/<pkg>` becomes a directory symlink into the repo. App writes go directly into the repo from then on. vjupdate deploys every dir in the set unless unticked in vj → Dotfiles.

## Package lists and project cloning

**LibreOffice removal (2026-10-30).** Neither edition belongs in `[paru].install`.
Both `libreoffice-fresh` and `libreoffice-still` are in the shared `[paru].remove`
list, consumed by `_remove_conflicts` during install and update actions. The
LibreOffice window rule was removed from niri's `config.kdl`. The direct
uninstall attempt in this session required an interactive sudo password and
did not run; do not assume the local package is already uninstalled.

**Unused-app cleanup (2026-10-30).** Judged by DMS launcher `lastUsed` + newest
mtime of each app's config/data dirs (`vj unused` idle verdicts need 60 days of
wellbeing, from 2026-12-22). Dropped from the lists and uninstalled: kicad +
kicad-library (also in `[paru].remove`), goverlay, protonup-qt, meld, gwenview,
zathura(-pdf-poppler), btop, unsloth, nicotine+, kolourpaint, firefox, geany,
vial-appimage, flatpaks xemu/Supermodel/melonDS/RetroArch/PPSSPP/ScummVM/
protonmail-bridge/xclicker (+ unlisted OrcaSlicer). Kept on purpose: gparted,
pavucontrol, emudeck-bin (`fuse2` now explicit — it was only a vial-appimage
dep), the `*craft-bin` suite, Dolphin, PrimeHack.

`projects.toml` — `[[repo]]` entries (name + SSH URL) cloned into `~/Projects/` during the `clone_projects` bootstrap phase (missing ones only; vj → Git repositories selects which).

`TODO.md` — pending work tracked in the repo (manual-confirm checklists for other-machine work, pending package migrations).

Package install priority: **pacman > flatpak > paru**. If a package is available in official Arch/CachyOS repos, prefer pacman. Flatpak over AUR when both exist. AUR only as last resort. Within AUR, `-bin` is fine (it updates through paru like
any AUR package; source builds only cost build time). Swapping an installed
package for its `-bin`/source twin: list the old name in `[paru].remove`, since
`--noconfirm` declines paru's conflict prompt. Never install a name on the malware blocklist: install aborts if any listed package
appears in `~/.local/share/aur-malware-check/data/campaigns/*/packages*.txt`
(refreshed each run; e.g. `alvr`, hijacked June 2026). Check new AUR names there first.

Package lists are TOML (`#` comments inside the arrays are fine):

| Where | Purpose |
|---|---|
| `packages.toml` `[paru].install` | Installed on every profile |
| `profiles/<name>.toml` `[paru].install` / `[flatpak].install` | Profile-only packages |
| `packages.toml` `[paru].remove` | Force-removed (`pacman -Rdd`) before install (conflict resolution) |
| `packages.toml` `[paru].skip` | Skipped by install + audit even if listed above |
| `packages.toml` `[paru].hold` | Installed normally but excluded from automatic upgrades and rebuilds |
| `packages.toml` `[flatpak].install` | Flatpak apps |
| `packages.toml` / profile `[systemd].enable` / `.user` | Units enabled by "Enable system services"; dropping one disables it next time (state: `~/.local/state/dots/managed-units`; first run disables nothing) |
| `packages.toml` `[npm].install` / `[uv].install` | Global npm / uv tools, installed if missing (install phase) |
| `~/.config/vjupdate/config.toml` | This machine's add/remove/declined (vj writes it) |
| `.dms-plugins.list` | DankMaterialShell plugins |
| `.install-scripts.list` | Scripts run during bootstrap |

## .gitignore policy

Ignore **secrets**, plus **artifacts that regenerate continuously**. Everything else is tracked so a fresh clone carries maximum config/state (machine-specific state, generated logs, themes, app settings all committed on purpose). Before adding an ignore entry, ask "is this a secret, or does it rewrite itself every session?"; if neither, default to tracking.

The second test is about **churn rate, not size** — a payload written once is fine to track however big, but anything an app rewrites on each launch grows history forever. Concretely: `vesktop/ExtensionCache/` (3MB of React DevTools, written once) is **tracked**, while VSCodium's Chromium caches (same order of size, rewritten every launch) are **ignored**. They reached 41.5MB of 60MB of history — 68% — and dirtied 24 files on every commit before being purged 2026-08-15.

Currently ignored (secrets audited 2026-06-21, no secrets found elsewhere):
- Credentials: `claude/.claude/.credentials.json`, `cave/.cave/agent/auth.json`
- Session/auth tokens: `cave/.cave/agent/sessions/`, `vesktop/.config/vesktop/sessionData/` (Discord token)
- VSCodium cookie/token/web-storage stores; `fish_history`; `Crashpad/` dirs (memory dumps)
- Continuously regenerated: `VSCodium/.config/VSCodium/{Cache,CachedData,CachedProfilesData,CachedExtensionVSIXs,GPUCache,DawnGraphiteCache,DawnWebGPUCache,Code Cache}/` — VSCodium rebuilds them on first start; `User/` keeps the real config
- Claude Code synced account skills: `claude/.claude/skills/synced/` — re-downloaded by Claude Code per account (UUID-keyed dirs)
- Non-secret exceptions kept ignored: `vesktop/.config/vesktop/Singleton*` (stale single-instance lock breaks launch), `vesktop/.config/vesktop/state.json` (window-bounds churn)

If tracked bloat is ever found again, the two-step fix is `git rm -r --cached` + ignore (stops growth), then `git filter-repo --invert-paths` to purge history. The second step rewrites every SHA and needs a force-push — **take a `git bundle create ... --all` backup first, and the other machine then needs `git fetch && git reset --hard origin/main`.**

**`.gitignore` does NOT support inline `#` comments after a path** — comments go on their own line.

## VM webapps

`windows/` is a standalone Docker Compose project, not a stow package. Launch via script:

```bash
start-windows   # starts Windows 11 VM, opens noVNC at http://localhost:8006
```

Opens Chromium `--app` at 75% of screen size (100% on Surface). Window size is machine-aware via `hostname` (start-windows, not the vj profile).

**Windows storage**: VM disk lives at `/mnt/data/windows-vm-storage` (symlinked to `windows/storage`) — kept on the data partition to avoid filling root.

**Windows shared folder**: `~/Shared` on host is mounted into the VM via Samba. Inside Windows, map `\\host.lan\Data` as a network drive (This PC → Map network drive).

Stop Windows VM: `cd ~/Projects/dots/windows && docker compose down`

## vjupdate behaviour notes

- **Input and failure handling.** Package lists and installed-package queries
  must be read successfully before installation. Malware package matching reads
  definitions once per batch and fails if a required input cannot be read.
  A partial paru failure invalidates
  the installed-package index so retries query the actual installed state.
  Installer lists use a separate file descriptor, closed in child shells, so
  installers cannot consume subsequent commands. Installer stdin stays available.
- **Audit results.** Pacman database errors record failed results. Firmware
  refresh/query failures are reported separately; fwupdmgr exit 2 means successful
  execution with nothing to do. Independent checks continue, but the recap exits
  nonzero for failed checks. Update and bootstrap both show AUR failure details.
- **Automount paths.** Mount points must be absolute, without newlines, carriage
  returns or commas. Escape spaces, tabs and backslashes in fstab fields and
  preserve those escapes when writing bind entries. Ownership options use the
  selected user's actual UID/GID rather than assuming 1000.

- **Borrowed from aconfmgr/decman/metapac/dotbot/Lavender-Night (2026-10-27).**
  - *AUR update review* (`_review_aur_updates`, before every `_syuu`): paru has
    SkipReview, so each pending AUR update's `~/.cache/paru/clone/<base>` is
    fetched and `HEAD..@{u}` saved to `~/.local/state/dots/aur-review/<base>.diff`.
    Added lines matching `_AUR_REVIEW_RE` (curl/wget/base64/eval/`| sh`…) put
    the package in `_AUR_FLAGGED`, which `_syuu` adds to `--ignore` unless an
    interactive run confirms. Upgrading it by hand moves HEAD and clears it.
  - *AUR source keys* (`_import_aur_keys`): `validpgpkeys` from the updated
    `.SRCINFO` are imported into the USER keyring (`gpg --recv-keys`), which
    is what makepkg checks — `pacman-key` never covered it.
  - *Staged niri validation*: `_stow_niri_cfg` builds a temp mirror of
    `~/.config/niri` with the new links (includes resolve against link paths,
    verified) and runs `niri validate` first; invalid → links unchanged,
    `niri-config` recorded failed.
  - *Unticked packages are unlinked*: `_unstow_unticked` unstows packages
    recorded in `~/.local/state/dots/stowed-pkgs` that are no longer in
    `stow.list` (never niri). Root packages now `--restow`.
  - *Dead links*: `_prune_dead_links` removes broken links under `~/.config`
    (depth 3), `~/.local/bin`, `~/.local/share/applications` — only ones
    resolving into `$DOTS_DIR`.
  - *Pinned installers*: `@sh <url>` lines in `.install-scripts.list` run only
    if the script is byte-identical to the last run's copy
    (`~/.local/state/dots/installers/`); a change shows a diff, interactive
    asks, `--yes` skips. First run records it (trust on first use).
  - *Audit additions*: `check_modified_configs` (`pacman -Qii` `[modified]`
    backup files; warns only on files new since the last audit, baseline in
    `modified-configs.txt`), `check_dms_owner` (dms.service enabled AND a niri
    spawn), `check_logins` (gh token, SSH key, claude/codex/spotify_player/
    vesktop credentials — only for installed tools, local checks only).
    `vjupdate --lostfiles` runs `pacreport --unowned-files` (~1 min, report).
  - *Preflight*: refuses to run as root; warns under 5 GiB free on `/`
    (`VJ_MIN_FREE_GB`); keeps an existing sudo ticket alive (`sudo -n -v`
    loop, terminal runs only, killed in `_cleanup`).
- **Held packages.** `[paru].hold` (packages.toml) excludes named packages from system
  upgrades (including retries) and both rebuild paths. First installation is
  unchanged. Audit and update runs warn about pending held AUR updates with
  review and manual upgrade commands; dry runs list the holds.
- **No bash menu (removed 2026-10-27).** The ~340-line `_multiselect` menu
  duplicated vj. Bare `vjupdate` / `-i` now `exec vj` (no terminal → dies with a
  hint); vj calls back with `--actions`. `MENU_ORDER` (top-level array) is the
  only ID list: `--actions` validates against it, fish completion reads it, and
  `vj/state.py` MAINT/ONCE/DMS must use the same IDs.
- **Audit list.** `AUDIT_CHECKS` is the one list `phase_audit` and `--check`
  run (`_run_audit_checks`). `phase_audit` also runs `check_flatpak_orphans`
  (uninstalls runtimes); `--check` stays report-only. `--check` saves its
  results (`name\tstate` + `@warnings\tN`) to `$STAMP_DIR/last-check.tsv`;
  vj's Maintenance row shows it (`state.last_check`).
- **Weekly check timer.** Dotset package `systemd-user` ships
  `vjupdate-check.{service,timer}` (weekly, Persistent, nice/idle);
  `packages.toml` `[systemd].user` enables the timer. On failure it calls
  `notify-send`.
- **Provider names (2026-10-31).** `pacman -Qq X` answers for a package that
  *provides* X (`vectorcraft` → `vectorcraft-bin`, `wine` → `wine-cachyos`), so
  `_remove_conflicts`/`_demote_packages` compare the printed name to X before
  acting; otherwise `-Rdd X` fails with "target not found". Same day CachyOS
  renamed DMS: `dms-shell` → `dux-shell`, `dgop` → `dux-gop` (same `dms` binary
  and `dms.service`); listing the old name made the install phase fail on the
  conflict. Lutris stays in `[paru].remove`: nothing uses it (Battle.net is umu).
- **Conflict swaps in `--update`.** `_remove_conflicts` (installed
  `[paru].remove` entries only) + `_demote_packages` run in both `install_all`
  and `system_update`; `--update` installs nothing, so it warns to run
  `vjupdate --actions install` for replacements. The old hardcoded
  `_swap_pkg libreoffice` is gone.
- **Automount lives in `scripts/.local/lib/vjupdate/automount.sh`**, sourced on
  first call by the `automount_disks` stub (path `${BASH_SOURCE%/*}/../lib`, so
  it resolves in the repo and via the stowed `~/.local/lib` link). Tests that need
  `_fstab_escape` first `source "$_AUTOMOUNT_LIB"`.
- **DMS and Git actions.** One `dms-import` entry applies the seven repository
  overrides including colors. It does not pull Git or deploy links. `dms-export`
  saves live settings except colors. Git export follows DMS export and precedes
  Stow and DMS import. It requires interactive staging, diff review, commit-message
  entry and push confirmation; normal hooks stay enabled and local commits survive
  push failures. Nothing commits or pushes without that confirmation. Configuration-link
  deployment starts selected; adoption requires explicit `--adopt`. Noninteractive
  `--yes` retains the legacy dotfiles phase (deploy and DMS import).
- **Ollama (2026-10-30).** `setup_ollama` pulls `qwen3.5` (`models=` array; DeepSeek
  and the `dsh` harness were removed the same day at user request). `limits.conf`: `CPUQuota=640%`, `MemoryHigh=40%` — user
  rejected `MemoryMax` because it OOM-kills — `OLLAMA_KEEP_ALIVE=1m`).
  ollama 0.40 IGNORES `OLLAMA_GPU_OVERHEAD` and `OLLAMA_MAX_LOADED_MODELS`
  (verified 2026-10-30: two runners, 11.7/12 GB VRAM, qwen warm-up hung), so
  the only VRAM cap is per model: `scripts/.local/share/ollama/qwen3.5.Modelfile`
  (`num_gpu 26`, ~30/70 CPU/GPU, ~19 vs 53 tok/s — the user chose the cap after
  trying both; no SYSTEM prompt). `setup_ollama` rebuilds every `<name>.Modelfile`
  as model `<name>` after the pulls. GPU compute cannot be capped. The drop-in dir is a folded link,
  so edits need a daemon-reload: `_reload_ollama` (in `deploy_dotfiles`) checks
  `NeedDaemonReload` and try-restarts the service.
  `update_ollama` (install phase + `--update`, silent without the feature or a
  running service) re-runs `setup_ollama`, so tags stay current.
- **Brave policy package (`brave/`, added 2026-10-11).** Stowed to `/` by the
  same root-target loop as `ollama` in `deploy_dotfiles`. It sets
  `LoopbackNetworkAllowedForUrls: ["https://discord.com"]` so Discord invite
  pages opened in Brave can hand the invite to Vesktop's arRPC on
  `127.0.0.1:6463` without a permission prompt. Brave's `Preferences` file is
  not tracked (rewritten every session), so policy is the only declarative
  route. Side effect: Brave shows "Managed by your organisation". Policy name
  and `/etc/brave/policies` path were read from the `brave-origin-bin` binary.
  Confirmed on the desktop 2026-10-11: `brave://policy` shows the policy with
  status OK, and invite links now open the join dialog in Vesktop.
- **Single instance.** An flock on `~/.local/state/dots/vjupdate.lock` is taken
  *before* log rotation; a second run exits with a message. `--help` and
  `--dry-run` skip runtime init entirely (no lock, no log rotation, no stamps),
  so they are genuinely read-only. Main execution is guarded by a
  `BASH_SOURCE` check so tests can source the file for its functions.
- **Stow no longer uses `--adopt` by default.** Conflicts are reported and left
  untouched; `--adopt` opts in and backs both live and repository versions up to
  unique `~/.local/state/dots/adopt-backup-<ts>-<suffix>/` directories first.
  Backup failures or unknown Stow conflict formats cancel adoption. Both
  conflict wordings are parsed: Stow 2.4 (`cannot stow X over existing target
  T since neither a link nor a directory…`) and Stow 2.3 on the Ubuntu CI
  runner (`existing target is neither a link nor a directory: T`). See README.
  Common packages use a single `stow --restow` invocation per package, not
  separate unstow/install calls. Stow checks the full plan before executing it,
  so a conflict preserves that package's working links. Do not restore the
  blanket `stow -D` loop: it removed links before discovering conflicts.
- **Cache cleanup keeps the AUR sources.** `~/.cache/paru` holds the git
  checkouts paru reuses; wiping it forces a full re-clone and rebuild of every
  AUR package. `--clean-aggressive` restores the old wipe-everything behaviour.
  Failed cleanup commands record `cache-cleanup` as failed and suppress the
  success message. Independent work can continue; the final recap returns
  nonzero. Both paccache operations are attempted even if the first fails.
- **Installer pipelines use `bash -o pipefail -c`.** Child shells do not
  inherit pipefail. Without it, a failed download piped into an empty successful
  installer was reported as done. Each installer outcome is recorded.
- **Running-kernel protection uses package ownership.** `manage_kernels` asks
  `pacman -Qoq /usr/lib/modules/$(uname -r)/vmlinuz` for the owning package.
  Comparing `uname -r` with `pacman -Q` version text is invalid: their formats
  differ. Removal is refused if ownership is unknown or matches the requested
  package. An upgrade may remove the old module tree; reboot before retrying.
- **Audit-dependent actions live in one table** (`AUDIT_ACTIONS`, top of the
  file) mapping checklist name → flag var. `_enable_audit_action` sets the flag
  *and* un-skips the audit phase, so an action can't be selected into a phase
  that never runs. Add new ones there only — the checklist, the CLI flag and the
  dry-run preview all read from it.
- **A failed `paru -Syuu` names its cause in the recap.** `_syuu` tees both the
  first attempt *and* the untrusted-key retry (the retry used to run unlogged, so
  its failure reported nothing), then `_syuu_fail_detail` pulls
  `error: packages failed to build: <pkgs>` out of the log into
  `SYUU_FAIL_DETAIL` — falling back to the last `error:` line when no package
  failed to build. `install_all` folds that into both the `full-upgrade` recap
  note and the `warn`, so one broken AUR package is visible at the end instead of
  buried in 2000 lines of upgrade output.
- **AUR build-time estimate.** `_aur_estimate_text` is printed by
  `_estimate_aur_builds` before each `_syuu`. It sums past build durations for pending `paru -Qua` upgrades (holds excluded)
  and names packages with no history. `_syuu` runs paru with `LC_TIME=C` so
  makepkg's `%c` timestamps parse; `_record_build_times` stores the first
  `Making package` → `Finished making` span per package (latest wins) as
  `aur:<pkg>` in the repo's `build-times.tsv`, including from failed runs.
  `_install_list` / the flatpak loop also record `@pacman-per-pkg` /
  `@flatpak-per-pkg` (one average per call). Commit the file to share history.
- **Unlisted/unused apps** (`check_unused_apps` → `python3 -m vj unused PLANDIR [DAYS]`,
  `vj/unused.py`) warns, never removes. Unlisted = every explicit package/flatpak
  in no plan list (incl. remove/demote/`ignore.list`); idle = only apps with a
  visible launcher. Usage = DMS's `~/.local/state/DankMaterialShell/appusage.json`
  (launcher) + `wellbeing/db` (focused seconds per window app_id, BoltDB read
  by regex). Root is `noatime`, so file access times are useless. Idle verdicts
  wait until wellbeing has DAYS (60) of history (began 2026-10-24); terminal apps
  are never judged idle.
- **Builds run at the lowest priority.** Every building `paru` call goes
  through `_paru` (`nice` to an absolute 19 + `ionice -c 3`). Shells from
  alacritty inherit ananicy-cpp's nice −4, so an unwrapped AUR build (rustc on
  all cores) outranked games — MTG Arena lagged during an update (2026-10-21).
  Use `_paru` for any new build call; plain `nice -n 19` is relative (→ 15).
- **Exit status is meaningful.** Phases record ok/fail/skip; `print_recap`
  prints the table and returns non-zero if anything failed. Unexpected phase
  failures abort and print a recap through the runtime ERR trap. Never wrap
  the phase invocation in `if` or `||`: that disables errexit for the whole
  call tree, allowing failed keyring operations to be stamped successful.
  Recoverable failures must be handled and recorded at their call sites.

New regressions should fail against the pre-fix script (`VJUPDATE_SCRIPT`
pointing at `git show HEAD:scripts/.local/bin/vjupdate`). Keep system-changing
commands mocked and fixtures temporary.

## vjupdate bootstrap phases

Phases use stamps in `~/.local/state/dots/` — heavy phases skip automatically if run recently: keyrings within 48h, mirror ranking within 30 days. A mirror run that fails on both arch and CachyOS is not stamped, so it retries next run.

The keyrings phase wipes `/etc/pacman.d/gnupg/`, so every third-party pacman repo key must be listed in `_REPO_KEYS` (repo name → key ID): `reset_keyrings` re-imports them all right after the wipe. Both `_syy` (mirror database sync) and `_syuu` (system upgrade) attempt one recovery for "unknown trust" using that map; unknown repo keys still require manual intervention.

```
sources → install → dotfiles → configure → audit
```

| Phase | Contains |
|---|---|
| `sources` | install paru, reset keyrings, surface repo, rank mirrors, add flathub remote, clone repos |
| `install` | conflict removal, demotions, disk check, AUR review, full upgrade, install pacman/flatpak/AUR packages, flatpak update, npm/uv tools, cache cleanup |
| `dotfiles` | stow symlinks, DMS config import |
| `configure` | system services, snapper, keyboard, greeter, keyring-pam (user-prompted); DMS plugins, install scripts, fish, claude, VMs (first-run prompted) |
| `audit` | (`AUDIT_CHECKS`) orphan packages, unlisted/unused apps (report only), flatpak cleanup, rebuild check, pacnew files, modified configs, DMS owner, logins, firmware updates |

Bare `vjupdate` (or `-i`) opens `vj`; choices come back as `--actions`.
`--yes` runs the legacy full bootstrap, `--update` and `--check` stay direct.

## Shell script linting

`.githooks/pre-commit` first blocks staged secrets (token/key patterns and
paths like `auth.json`, `.credentials.json`, `id_ed25519`; it scans the staged
blob and prints only a 6-char prefix), then runs `shellcheck -S error` on staged
shell scripts and blocks the commit on errors. `.github/workflows/test.yml` runs
the unittest suite + shellcheck on every push. Fish completions for `vjupdate`
(`--actions` IDs read live from `MENU_ORDER`) and `vj` live in the fish package. It selects files by **shebang, not path**, so non-shell files
(Python, KDL, binaries) are never scanned. It no-ops when shellcheck is absent, so a fresh clone can still commit.

`deploy_dotfiles` runs `git config core.hooksPath .githooks`, so a clone self-registers.
To register by hand: `git -C ~/Projects/dots config core.hooksPath .githooks`

Gotchas when linting these scripts:

- **A comment line starting with `# shellcheck ` parses as a directive.** It caused
  SC1072/SC1073 and made shellcheck skip all 1840 lines of `vjupdate` while still
  looking like it ran. If output is only SC1072/SC1073, nothing was checked.
- `vjupdate` carries a file-level `# shellcheck disable=SC2015` with justification: all
  ~28 sites are the `cmd && ok "..." || warn "..."` logging idiom where the middle
  command is a plain `echo`.
- The scripts are `set -euo pipefail`, so `var=$(cmd)` **exits before** any `rc=$?` or
  error branch below it. Where the failure is the signal (`pacman -Dk`, `aur_check`),
  guard with `|| true` or `|| rc=$?` — otherwise the handling code is unreachable.
- `warn()` only captures its own `$*` into the `WARNINGS[]` recap array — anything
  `echo`'d on a separate line after it is printed live but silently dropped from the
  end-of-run summary. Fold detail into the `warn` call itself (`warn "... : $detail"`),
  don't `warn` a header then `echo` the payload.
- `checkrebuild`'s output is `<repo>\tpkgname` per line (`repo` is `foreign` for
  AUR-installed packages). `check_rebuilds` extracts column 2 with
  `awk -F'\t' '{print $2}'` — don't flatten the raw line into the package list, the
  first column isn't a valid pacman target.

## Claude Code statusline

`~/.claude/statusline.sh` aggregates the segment scripts (caveman, ponytail, model, topic+dir) and
gives each its own copy of stdin — piping them in sequence lets the first consume the
input and starve the rest.

It **globs the plugin paths at runtime**, because the cache dirs carry version hashes
(`caveman/25d22f864ad6`, `ponytail/4.7.0`). So `settings.json` stays a static committed
one-liner and nothing needs regenerating after a plugin update. `setup_claude`
deliberately contains no statusline wiring. Add a segment by adding one line to
`statusline.sh`.

`topic-statusline.sh` parses transcript JSONL with jq, keeping the latest
nonempty manual title ahead of automatic titles regardless of record order.
Malformed/incomplete lines are skipped. Directory abbreviation applies only to
`$HOME` itself and paths below it, never a sibling sharing the same prefix.

## npm global prefix

Set to `~/.local` so global installs don't require sudo:

```bash
npm config set prefix ~/.local
```

Binaries land in `~/.local/bin/` (already in PATH). Required for `caveman-code` and any other global npm tools installed by `vjupdate`.

## Current key values (as of last sync)

| Setting | Value | Source |
|---|---|---|
| Display mode (desktop) | 3440x1440@165, VRR off entirely | cfg/display.kdl (native monitor mode; refresh rate was never the trigger — VRR was: this monitor flickers/luminosity-pulses under VRR, even on-demand, see file header comment, 2026-08-25) |
| Gaps | 4px | dms/layout.kdl (auto-generated; user deliberately kept this over cfg/layout.kdl's 13px, 2026-08-24) |
| Focus-ring width | 2px | dms/layout.kdl |
| Focus-ring color | #d0bcff (Material You purple) | dms/colors.kdl (DMS-generated; green #4caf50 override was lost 2026-06-17 to the dms_export bug, kept purple by choice 2026-08-25) |
| Border width | 2px | dms/layout.kdl |
| Corner radius | 12px | dms/layout.kdl + dms/alttab.kdl |
| Shadow | on; softness 30, spread 5, offset x=0 y=5 | config.kdl (inline `layout{}`) — its `color "#0007"` is overridden, see next row |
| Shadow color | #00000070 | dms/colors.kdl (DMS-generated) — `layout` blocks merge across includes with later winning, so this beats config.kdl's inline `#0007` |
| Keyboard layout | us intl | cfg/input.kdl (desktop/surface pkg; restored 2026-08-24 — was silently inert before) |
| Screenshot path | ~/Pictures/Screenshots/ | config.kdl (inline `screenshot-path`) |
| Terminal keybind | ⌘⏎ | dms/binds.kdl |
| App keybinds (Dolphin / Brave / Spotify / Vesktop / Whatsie / Telegram / Thunderbird) | ⌘⌥E / ⌘⌥B / ⌘⌥S / ⌘⌥D / ⌘⌥W / ⌘⌥T / ⌘⌥M — `nirius focus-or-spawn` (jump to open window, else launch; 2026-10-28) | dms/binds.kdl |
| Overview keybind | ⌘D | dms/binds.kdl |
| Power menu keybind | ⌘X | dms/binds.kdl |
| Lock screen keybind | ⌘⌥L | dms/binds.kdl |
| Fullscreen keybind | ⌘⇧F (game-friendly); ⌘F = maximize-column | dms/binds.kdl |
| Media keys (Play/Pause/Next/Prev) | `playerctl --player=spotify` (bypasses DMS's generic mpris picker so it doesn't hand control to Brave/other players) | dms/binds.kdl |
| Keybinds cheatsheet | ⌘G | dms/binds.kdl |
| Toggle bar | ⌘⇧Space | dms/binds.kdl |
| Workspace-previous keybind | ⌘⇥ (Tab) | dms/binds.kdl (ported from the deleted cfg/keybinds.kdl, 2026-08-24) |

DMS actions from keybinds spawn `dms ipc call <target> <fn>` — the `call` subcommand is required (e.g. `dms ipc call powermenu toggle`, `dms ipc call lock lock`). Omitting `call` silently no-ops.

DMS bar and settings-panel state live in `~/.config/DankMaterialShell/settings.json` (stow-symlinked, `DankMaterialShell` package) — e.g. `barConfigs[0].enabled` toggles the top bar (bound to Mod+Shift+Space, so this shouldn't need hand-editing again — see below). `dms ipc call settings set <key> <value>` only supports scalar top-level keys (`SETTINGS_SET_FAILURE`/`Setting Objects and Arrays not supported` for anything nested); array/object fields like `barConfigs` must be hand-edited in `settings.json` directly. Stop `systemctl --user stop dms.service` before editing, then start it again — editing live risks the running shell overwriting your edit on its own next write.

The `bar` IPC target's `selector` arg is a type keyword, not the target itself: it must be literally `"id"`, `"name"`, or `"index"`, with the actual match value as the next arg (e.g. `dms ipc call bar toggle "id" "default"` — passing an output name like `"DP-1"` as the selector gives `BAR_INVALID_SELECTOR`).

**A duplicate keybind anywhere in the included KDL tree makes `niri msg action load-config-file` fail *silently from the user's perspective*** — niri rejects the whole reload and keeps running the last-good config, with zero indication in-session; the only trace is a KDL parse error in `journalctl --user -b 0` (search for `niri[<pid>]`). A newly-added bind that "does nothing" after a reload is more likely this than a broken IPC call — check the journal for `error parsing KDL` / `duplicate keybind` before assuming the target command is wrong. `dms/binds.kdl` already binds `Mod+H/J/K/L` to vim-style window-focus — don't reuse Mod+K.
