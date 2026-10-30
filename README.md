# dots

GNU Stow dotfiles for CachyOS + niri.
Supports two machines: **desktop** (tower, RX 6700 XT) and **surface** (Surface Pro 9).

```bash
bash ~/Projects/dots/scripts/.local/bin/vjupdate
```

---

## Fresh install

### 1. Set hostname

```bash
sudo hostnamectl set-hostname desktop   # or: surface
```

### 2. SSH key → GitHub

```bash
ssh-keygen -t ed25519 -C "viridjan"
cat ~/.ssh/id_ed25519.pub   # add this to github.com/settings/keys
```

### 3. Clone and run the bootstrap script

```bash
git clone git@github.com:Viridjan/dots.git ~/Projects/dots
cd ~/Projects/dots && bash scripts/.local/bin/vjupdate
```

`vjupdate` does everything:
- installs the package lists for the machine's profile via paru / flatpak
- deploys the chosen dotfile set via stow (profile auto-detected from hostname
  until you pick one in `vj`)
- enables systemd services
- sets up Claude Code plugins

Afterwards, use `vj` (see below) for day-to-day maintenance.

LibreOffice is excluded from installation. Both `libreoffice-fresh` and
`libreoffice-still` are in `packages.toml`'s removal list, so the install and
update actions remove either edition when installed. The LibreOffice niri
window rule has also been removed.

### 4. Manual steps (after the script)

```bash
# Git identity
git config --global user.name 'Viridjan'
git config --global user.email 'viridjan@users.noreply.github.com'

# Fingerprint enrollment
fprintd-enroll

# DankMaterialShell — required before starting niri
# generates ~/.config/niri/dms/*.kdl (niri won't start without them)
dms setup

# YubiKey FIDO2 PIN — set/change the PIN on the hardware key
# ykman is the YubiKey Manager CLI (package: yubikey-manager)
# The FIDO2 PIN protects resident keys and passkeys stored on the YubiKey
ykman fido access change-pin

# Bitwarden — log in to unlock vault and browser extension
# Launch from app menu or: flatpak run com.bitwarden.desktop

# Open Notebook (if needed)
cd ~/Projects/Open_notebook && docker compose up -d

# Windows VM — desktop only (web UI: http://localhost:8006, RDP: localhost:3389)
cd ~/Projects/dots/windows && docker compose up -d
# Shared folder: ~/Shared on host → \\host.lan\Data inside Windows (map as network drive)
```

**Surface only:**
- Enroll the linux-surface Secure Boot MOK key so the kernel boots with Secure Boot on
- Follow: https://github.com/linux-surface/linux-surface/wiki/Installation-and-Setup

---

## vj — terminal UI

```bash
vj        # needs python-textual (in packages.toml)
```

One screen. Each menu row shows what will happen, on the same line:

```
Maintenance actions     │ run 9 of 12 actions
Packages                │ install 1 package < 10 s · 1 declined
Git repositories        │ clone missing · 8 of 8 repos
Dotfiles                │ link 21 of 21 from viridjan
One-time setup          │ 14 never run
DMS & Git               │ nothing
Profile / dotfile set   │ desktop · viridjan
▶ Run                   │ press r · install time < 10 s (upgrades/actions extra)
```

Enter opens a submenu below the menu (Space ticks, `/` filters, `a` all,
`n` none, `d` repo defaults, Esc closes). `r` runs everything selected by
handing the terminal to `vjupdate --actions …`; `q` quits.

- **Profiles** (`profiles/<name>.toml`): hardware + package lists + feature
  switches. `desktop` and `surface` ship; add a file for another machine.
- **Dotfile sets** (`dotsets/<name>/`): stow packages. `viridjan` is mine; a
  friend adds `dotsets/<their-name>/` with the same shape and picks it in vj.
  `none` = don't touch dotfiles.
- **Local config** `~/.config/vjupdate/config.toml` (not in git): chosen
  profile/set, your own extra packages (`+` in Packages) and removals (`x`:
  marked as a dependency, removed only if nothing needs it), declined packages
  (unticked once, never pre-ticked again), ignored unlisted installs, one-time
  tasks done/skipped (`D` / `s`), last selections.
- **Unlisted packages**: explicit installs (pacman + flatpak) that are in no
  list. Sort them with `p` (add to `packages.toml`), `f` (add to the profile),
  `m` (this machine only), `x` (remove) or `i` (ignore). Keys act on ticked
  rows, else the highlighted one. `p`/`f` edit tracked files: commit afterwards.
- **Flatpak apps**: untick an app to exclude it from installation. Removal with `x`
  is supported only for pacman packages; Flatpak apps are never uninstalled by `vj`.
- **Times**: package estimates come from `build-times.tsv` (committed): green
  < 10 s, yellow < 1 min, orange longer; `?` = no history yet.

---

## Claude Code

Always open Claude Code from `~/Projects`, not from `~/Projects/dots`:

```bash
cd ~/Projects && claude
```

Memory and project context are scoped to the working directory at launch.
Opening from `~/Projects/dots` creates a separate scope — prior conversation context
and memory won't load.

When working on dots inside a Claude session, just `cd ~/Projects/dots` from within it.

### Statusline

The statusline is assembled by `~/.claude/statusline.sh`, which runs each segment
script (caveman, ponytail, model, topic + directory) and glues the output together.
`[TOPIC: …]` uses the latest nonempty manual `/rename` title, falling back to
an automatic title only when no manual title exists. Transcript JSON spacing
is irrelevant; incomplete or malformed lines are skipped.
`[DIR: …]` abbreviates the home directory and its descendants with `~`, while
similarly named sibling directories retain their full paths. Both tags need `jq`. Plugin paths are
resolved at runtime, so a plugin update never requires touching `settings.json`.

To add a segment, add one line to `statusline.sh` — nothing else needs changing.

---

## Contributing to this repo

A `pre-commit` hook first blocks staged secrets (token/private-key patterns and
paths like `auth.json`, `.credentials.json`, `id_ed25519`; it prints only a
6-character prefix), then runs `shellcheck` on staged shell scripts and blocks
the commit on errors. It is registered automatically by `vjupdate` (via
`core.hooksPath`), or by hand:

```bash
git -C ~/Projects/dots config core.hooksPath .githooks
```

ShellCheck warnings are advisory; only errors block. If `shellcheck` isn't
installed that step does nothing, so commits still work on a fresh clone.

GitHub Actions (`.github/workflows/test.yml`) runs the unittest suite and
ShellCheck on every push. The CI runner has Stow 2.3, whose conflict messages
are worded differently from Stow 2.4; `vjupdate` parses both.

Fish completions for `vjupdate` (flags, and `--actions` IDs read live from the
script) and `vj` ship in the `fish` package.

---

## Re-applying dotfiles (existing machine)

After pulling new changes from this repo:

```bash
vjupdate --actions stow-symlinks     # or tick "Refresh configuration links" in vj
```

By hand (packages live in the dotfile set, `scripts` at the repo root):

```bash
cd ~/Projects/dots && stow --no-folding --restow -t ~ scripts   # keeps ~/.local/bin a real dir
cd ~/Projects/dots/dotsets/viridjan
stow --restow -t ~ alacritty DankMaterialShell fish fonts gtk-3.0 gtk-4.0 \
     micro mimeapps mpd paru qt5ct qt6ct spotify-player vesktop VSCodium claude \
     cave caveman
# niri is NOT stowed — it uses file-level symlinks (DMS owns ~/.config/niri/),
# including the machine files from dotsets/viridjan/<profile>/. Re-run vjupdate.
```

`-t ~` is required: the repo lives at `~/Projects/dots`, so stow's default target
(the parent dir) would be `~/Projects`, not `~`. Always pass `-t ~`.

Or just re-run `bash scripts/.local/bin/vjupdate` — it's idempotent.

### Preview first

`vjupdate --dry-run` (`-n`) previews the requested action and changes nothing.
`--update` and `--check` show their own operations. Bootstrap previews honor
`SKIP_PHASES` and show missing packages, Stow simulations and cleanup. Interactive
choices are not known yet, so that preview explicitly shows the `--yes` baseline;
it does not claim that optional services were selected.
It takes no lock, rotates no log, writes no stamps and fetches nothing — facts
that would need network or root are shown as `[unknown]` rather than guessed.

### Stow conflicts are no longer adopted automatically

**Behaviour change.** `vjupdate` used to deploy every package with
`stow --adopt`. When a real file already sat at a target path, `--adopt` moved
that file *into the repo* — overwriting the tracked copy with whatever was live
— and then symlinked to it. On a machine whose config had drifted this silently
replaced repo content, and the only evidence was an unexplained `git diff`.

Now a conflict is reported and left alone. Nothing is overwritten and no user
file is deleted. To take the live files over deliberately:

```bash
vjupdate --adopt      # backs up every conflicting file first
```

Backups go to unique `~/.local/state/dots/adopt-backup-<timestamp>-<suffix>/`
directories, outside the tracked tree. `live/` and `repo/` preserve both versions
before anything is moved. A failed backup, missing source or unrecognised Stow
conflict cancels adoption for that package.

Common packages are restowed in one operation each. Stow checks for conflicts
before changing links, so a conflicting file does not remove that package's
already-working symlinks.

### Review and upload changes

Running `vjupdate` with no arguments opens `vj`, which is the only menu;
it hands your choices back as `vjupdate --actions …`.

**Refresh configuration links** starts checked so new tracked settings get linked.
It does not copy DMS overrides; conflicts remain untouched unless `--adopt` was
explicitly passed. Optional **DMS settings & Git** actions are:

- **Save live DMS settings to repository** — copy overrides except curated colors.
- **Apply repository DMS settings** — overwrite all seven live overrides, including colors.
- **Review and upload Git changes** — review changes, commit and push with confirmations.
- **Install DMS plugins** — install configured plugins.

There is one DMS import entry. Save/export runs before Git upload, followed by
configuration links and DMS import. DMS import neither pulls Git nor deploys links.
Noninteractive `--yes` retains its existing dotfiles phase (links plus DMS import).

Upload first asks whether to stage **all non-ignored repository changes**, then
shows the staged diff, asks for a commit message, and confirms commit/push to
the branch's configured upstream. Existing local commits are pushed too.
Cancelling after staging leaves changes staged. Commit failures prevent pushing;
push failures preserve local commits, and rerunning upload can retry a clean
working tree. It never force-pushes and does not run automatically with `--yes`.

### AUR build-time estimate

Bootstrap and `--update` print it right before upgrading. It shows how long pending AUR builds should take, e.g. `12 AUR builds pending — est. ~75 min (…); no history: newpkg`.
The figure is each package's last build time, recorded automatically in
the repo's `build-times.tsv` (commit it to share history between machines). Nothing shows when no unheld AUR updates are pending. Held packages are excluded; packages
never built under this feature show as "no history" until their first upgrade.

### Only one run at a time

`vjupdate` takes an flock on `~/.local/state/dots/vjupdate.lock` before it
rotates the log or touches anything. A second invocation exits immediately with
a clear message. The lock is held on an open file descriptor, so the kernel
releases it however the process ends. `--help` and `--dry-run` never take it.

Exit status is nonzero if any requested action failed; the end-of-run summary
lists each action as succeeded, failed, or skipped (with the reason, so an
intentional skip is distinguishable from one caused by an earlier failure).
Unexpected command failures stop the run and print the failure recap. They do
not continue into dependent operations; explicitly handled recoverable failures
can still permit independent cleanup.

Installer pipelines report download failures even when the receiving shell
exits successfully. Failed cache cleanup is recorded in the recap and does not
print “caches cleaned”; independent work can continue, with a nonzero final
status. AUR sources remain preserved unless `--clean-aggressive` is selected.

Kernel removal checks which package owns the running kernel image. It refuses
to remove that package, or to proceed when ownership cannot be determined.
After a kernel upgrade, reboot before trying again if the old image is gone.

Run isolated regression and preservation checks with:

```bash
python3 -B -m unittest discover -s tests -v
```

Set `VJUPDATE_SCRIPT=/path/to/snapshot` to run the same tests against an older
script. Tests use a temporary home and restricted PATH with mocked system tools.

### Safety checks

Borrowed from aconfmgr, decman, metapac, dotbot and other dotfile repos (2026-10-27):

- **Preflight:** refuses to run as root, warns under 5 GiB free on `/`
  (`VJ_MIN_FREE_GB`), keeps an existing sudo ticket alive during long runs.
- **Protected packages:** kernels, firmware, microcode, limine, base, glibc,
  pacman and keyrings are never removed by any path.
- **AUR update review:** before each upgrade, every pending AUR update's
  PKGBUILD diff is saved to `~/.local/state/dots/aur-review/<pkg>.diff`.
  Diffs that add suspicious lines (curl, wget, base64, eval, `| sh`…) hold the
  package back unless an interactive run confirms it.
- **AUR source keys:** `validpgpkeys` from updated packages are imported into
  your user keyring, which is what makepkg checks.
- **niri validation:** new niri links are tested with `niri validate` in a
  temporary copy first; an invalid config leaves the live links unchanged.
- **Link cleanup:** packages unticked in vj → Dotfiles are unstowed, and broken
  links into the repo are removed from `~/.config`, `~/.local/bin` and
  `~/.local/share/applications`.
- **Pinned installers:** `@sh <url>` lines in `.install-scripts.list` run only
  if the script is unchanged since its last run. A change shows a diff and asks;
  `--yes` skips it.

---

## Stow operations

### Add a new config package (app not yet tracked)

```bash
# 1. Create the package structure
mkdir -p ~/Projects/dots/dotsets/viridjan/<pkg>/.config/<pkg>

# 2. Copy the live config into the package
cp -r ~/.config/<pkg>/. ~/Projects/dots/dotsets/viridjan/<pkg>/.config/<pkg>/

# 3. Remove the real directory so stow can create a clean symlink
rm -rf ~/.config/<pkg>

# 4. Stow it
cd ~/Projects/dots/dotsets/viridjan && stow -t ~ <pkg>
```

Result: `~/.config/<pkg>` becomes a directory-level symlink to `~/Projects/dots/dotsets/viridjan/<pkg>/.config/<pkg>`.
vjupdate picks up every folder in the set automatically (untick it in vj → Dotfiles to skip).
Any file the app writes inside it will land directly in the repo.

### Add files to an existing package (e.g. a new subdir)

```bash
# 1. Copy the new files/dir into the existing package
cp -r ~/.config/<pkg>/<subdir> ~/Projects/dots/dotsets/viridjan/<pkg>/.config/<pkg>/<subdir>

# 2. Remove the real copy
rm -rf ~/.config/<pkg>/<subdir>

# 3. Restow the package to pick up the new entries
cd ~/Projects/dots/dotsets/viridjan && stow --restow -t ~ <pkg>
```

(`niri` is the exception — its `dms/` dir is owned by DMS and is not stowed.)

### Sync changes back to the repo (after an app auto-updates its config)

Nothing to do — because the configs are symlinks into `~/Projects/dots`, any write
by an app goes directly into the repo. Just `git add` and commit.

### Remove a package from stow (stop tracking it)

```bash
cd ~/Projects/dots/dotsets/viridjan && stow -D -t ~ <pkg>   # removes symlinks, leaves real files in ~/Projects/dots
rm -rf ~/Projects/dots/dotsets/viridjan/<pkg>          # optionally delete from repo too
```

### Verify symlinks are healthy

```bash
# Check that all managed dirs are symlinks, not real directories
ls -la ~/.config/ | grep '^l'

# Re-apply all packages (safe to run repeatedly; won't overwrite existing symlinks).
# Use vjupdate, not `stow */` — the latter would fold ~/.config/niri into a
# symlink and break DMS, and would target ~/Projects instead of ~.
bash scripts/.local/bin/vjupdate
```

---

## Packages

Stow packages of the `viridjan` dotfile set (`dotsets/viridjan/<pkg>/`); `scripts` lives at the repo root.
Package *lists* (what gets installed) are in `packages.toml` and `profiles/<name>.toml`:
`[paru]` / `[flatpak]` packages, `[systemd]` units to enable (dropping one
disables it on the next run), and `[npm]` / `[uv]` global tools.

| Package | What it stows |
|---|---|
| `niri` | `~/.config/niri/` — common kdl files (cfg/ minus display+input) |
| `desktop` | `~/.config/niri/cfg/display.kdl` + `input.kdl` + `surface-layout.kdl` (empty) + `autostart-machine.kdl` (Thunderbird, Telegram, Steam) for the tower |
| `surface` | `~/.config/niri/cfg/display.kdl` + `input.kdl` + `surface-layout.kdl` (50% default window width) + empty `autostart-machine.kdl` for Surface Pro 9 |
| `fish` | `~/.config/fish/` |
| `alacritty` | `~/.config/alacritty/` |
| `micro` | `~/.config/micro/` |
| `VSCodium` | `~/.config/VSCodium/` |
| `DankMaterialShell` | `~/.config/DankMaterialShell/` |
| `gtk-3.0` | `~/.config/gtk-3.0/` |
| `gtk-4.0` | `~/.config/gtk-4.0/` |
| `qt5ct` | `~/.config/qt5ct/` |
| `qt6ct` | `~/.config/qt6ct/` |
| `vesktop` | `~/.config/vesktop/` — settings.json + settings/ (Vencord config + quickCss) |
| `mimeapps` | `~/.config/mimeapps.list` |
| `paru` | `~/.config/paru/paru.conf` |
| `claude` | `~/.claude/settings.json` + `statusline.sh` + skills (incl. `pixel-art-studio`) |
| `caveman` | `~/.config/caveman/config.json` — caveman plugin `defaultMode: ultra` |
| `cave` | `~/.cave/` — Cave AI agent config + ollama extension |
| `brave` | `/etc/brave/policies/managed/` — Brave managed policy (stowed to `/` with sudo) |
| `ollama` | `/etc/systemd/system/ollama.service.d/` — ROCm + 40% resource-limit drop-ins (stowed to `/` with sudo) |
| `fonts` | `~/.local/share/fonts/` — user fonts (Luminari) |
| `mpd` | `~/.config/mpd/mpd.conf` |
| `spotify-player` | `~/.config/spotify-player/keymap.toml` |
| `scripts` | `~/.local/bin/{vjupdate,vj,start-windows,start-open-notebook,start-keep,start-battlenet,gamescope-media}` + `.desktop` launchers — stowed `--no-folding`, so installers own the rest of `~/.local/bin` |

**niri note:** `cfg/display.kdl`, `cfg/input.kdl`, and `cfg/surface-layout.kdl` are NOT in the `niri` package —
they come from `dotsets/viridjan/desktop/` or `…/surface/`, matching the profile name.
The `dms/` directory is auto-generated by `dms setup` and not tracked.

---

## niri workspaces and helpers

| # | Workspace | Gets |
|---|---|---|
| 1 | social | Thunderbird, WhatSie, Telegram, Vesktop |
| 2 | media | dgop, Spotify, game launchers (Steam, Lutris, Bottles, Battle.net) |
| 3 | games | empty at login; games open here without taking focus |
| 4 | main | everything else |

Windows never stack vertically on their own: there are no consume/expel binds
except `Mod+.` (expel, to undo a drag-and-drop stack). Helpers from
[awesome-niri](https://github.com/niri-wm/awesome-niri), installed via
`packages.toml` and started in `config.kdl`:

- **oniri** — a workspace's only window is maximized, un-maximized when a second opens.
- **nirius** — `Mod+Alt+E/B/S/D/W/T/M` focus Dolphin/Brave/Spotify/Vesktop/WhatSie/Telegram/Thunderbird, launching it if not open.
- **nirinit** — saves the window layout every 5 min and restores it at login; apps the autostart already opens are in `dotsets/viridjan/nirinit/` skip list.
- **niri-autoselect-portal** — screen sharing skips the picker: choose the target first with `Mod+Ctrl+S` (window) / `Mod+Ctrl+Shift+S` (monitor), clear with `Mod+Ctrl+X`.
- **iio-niri** (Surface) — rotates the screen with the accelerometer.

## Gaming

### Steam game launchers

Create `.desktop` entries for all installed Steam games (shows up in app menus).
Also removes launchers for games that were uninstalled:

```bash
vjupdate --steam-launchers
```

Re-run after installing new games. Launchers land in `~/.local/share/applications/`.
Ticked by default in vj → Maintenance actions.

### App launcher cleanup

Removes non-Steam `.desktop` launchers whose target no longer exists (uninstalled
app, deleted script), and reports installed apps not mirrored into
`~/.local/share/applications/` (informational — they're already visible via
`/usr/share/applications/`):

```bash
vjupdate --app-launchers
```

Also ticked by default in vj → Maintenance actions.

### Weekly health check

The `systemd-user` package installs `vjupdate-check.timer`: once a week it runs
`vjupdate --check` (report only, lowest priority) and shows a desktop
notification if anything failed. vj's Maintenance row shows the last result,
e.g. `check 2d ago: 1 failed (pacman-db)`. Run it now with
`systemctl --user start vjupdate-check.service`.

### Unlisted and unused apps

The audit (`vjupdate --check`, or "Check system health" in vj) reports, never removes:

- explicitly installed packages and flatpaks that are in no package list
  (`packages.toml`, profile, local config, ignored). Sort them in vj → Unlisted packages.
- apps with a launcher and no recorded use in 60 days

The audit also reports package config files you changed in `/etc` (only ones
new since the last audit), DMS started twice (service plus niri spawn), and
missing logins for installed tools (gh, SSH key, Claude, Codex,
spotify_player, Vesktop). `vjupdate --lostfiles` lists files no package owns
(takes about a minute).

Usage comes from DankMaterialShell (launcher history + per-window focus time in
`~/.local/state/DankMaterialShell/`). Focus tracking began 2026-10-24, so the
unused check prints its start date until 60 days of history exist. Terminal apps
are never flagged. Standalone: `python3 -m vj unused PLANDIR [DAYS]`.

### EmuDeck

Installed as `emudeck-bin` (AUR). After the first install, open **EmuDeck** from
the app menu and run its wizard: it downloads the emulators and creates the ROM
folders. The app itself updates through paru; emulators update via
`flatpak update` and EmuDeck's "Update emulators".

### MTG Arena Tool

Deck tracker / collection manager for MTG Arena. Not in any repo, AUR or Flathub —
upstream ships an AppImage that self-updates, so it is installed to `~/.local/bin/`
(outside the repo, 167MB). Only the `.desktop` entry and icon are tracked.

```bash
curl -fL -o ~/.local/bin/mtgatool \
  "$(curl -sL https://api.github.com/repos/mtgatool/mtgatool-desktop/releases/latest \
     | grep -o 'https://[^"]*\.AppImage')"
chmod +x ~/.local/bin/mtgatool
```

Arena runs under Proton (Steam app `2141910`), so the tool cannot auto-detect the
log. Point its **Settings → Logs** at:

```
/mnt/data/steam library/steamapps/compatdata/2141910/pfx/drive_c/users/steamuser/AppData/LocalLow/Wizards Of The Coast/MTGA/Player.log
```

Arena also needs **Options → Account → Detailed Logs (Plugin Support)** enabled, or
the tool sees almost nothing. Launch with `mtgatool` or from the app menu.

Note: `vjupdate --app-launchers` deletes any `.desktop` whose target binary is
missing — on a fresh clone, download the AppImage before running it, or the
launcher symlink gets removed (`stow --no-folding --restow -t ~ scripts` brings it back).

### Keyboard shortcut pass-through

`Mod+Escape` toggles keyboard shortcut inhibition — when active, all keys pass through to the focused app (useful in games where niri intercepts shortcuts like `Mod+F`). Press `Mod+Escape` again to restore normal keybinds.

### Battle.net

Installed in the Wine prefix `~/Games/battlenet` (originally by Lutris, which
is no longer used). Launch it from the app menu (**Battle.net**) or with
`start-battlenet`: it runs `umu-run` with the newest Steam GE-Proton, falling
back to `proton-cachyos`. The launcher window goes to `media`, games to `games`.
If it won't start, a stale session may hold the prefix:
`env WINEPREFIX=$HOME/Games/battlenet ~/.local/share/Steam/compatibilitytools.d/GE-Proton*/files/bin/wineserver -k`.

### Gamescope launch options

Steam games (`steam_app_*`) open fullscreen on the `games` workspace without
taking focus, via window rules in `config.kdl`. Games run through gamescope
can't match those rules: gamescope sets no app-id and its title arrives after
the window opens. For those, use the `gamescope-media` wrapper in Steam →
right-click game → Properties → Launch Options:

```
gamescope-media %command%
```

It runs `gamescope -f --adaptive-sync --expose-wayland` at the focused
output's native size (3440×1440 desktop, 2880×1920 Surface; same line on both
machines), then moves gamescope's windows to `games` without focus (the name predates
that workspace). It watches
for 120 s after launch; the window may flash on the current workspace first.
MTG Arena no longer uses it (2026-10-30): its launch options are
`niri msg action focus-workspace media; %command%`, so it opens as
`steam_app_2141910` and the normal rules apply.

For other gamescope options (e.g. upscaling from 1080p), call gamescope directly:
```
gamescope -f -W 3440 -H 1440 -w 1920 -h 1080 -r 165 -- %command%
```

---

## Local AI (ollama)

Desktop only (`ollama-model` feature). vjupdate enables `ollama.service`,
pulls `deepseek-r1:7b` and builds `deepseek-cave` from
`scripts/.local/share/ollama/deepseek-cave.Modelfile` (the base model plus a
condensed caveman + ponytail system prompt). Install and `--update` runs re-pull
the base and rebuild the variant, so a revised `7b` tag arrives automatically.
A newer DeepSeek generation is a new tag, so change `model=` in `setup_ollama`
for that. R1 distills follow system prompts loosely: the reasoning stays
verbose, only the answer is shortened.

```bash
ollama run deepseek-r1:7b                  # chat; /bye quits
ollama run deepseek-cave                    # same, caveman + ponytail rules
ollama run deepseek-r1:7b "question"       # one answer; --hidethinking hides reasoning
ollama ps                                  # loaded models, GPU vs CPU share
ollama stop deepseek-r1:7b                 # free VRAM now (idle unload is 5 min)
```

`ollama.service.d/limits.conf` caps it at about 40% of the machine:

| Resource | Limit | How |
|---|---|---|
| CPU | 40% of 16 threads | `CPUQuota=640%` |
| RAM | 40%, soft | `MemoryHigh=40%`: throttles and swaps above it, never kills |
| VRAM | about 4.8 of 12 GB | `OLLAMA_GPU_OVERHEAD` reserves 60%; the rest of a model runs on CPU |
| GPU compute | none | Linux has no GPU share control; it is only busy while answering |

The drop-in directory is a link into the repo, so an edit lands immediately but
applies only after `sudo systemctl daemon-reload && sudo systemctl restart ollama`.
vjupdate's dotfiles step does that when systemd reports the unit changed.

---

## Btrfs snapshots

Handled automatically by `vjupdate`:

| Component | Role |
|---|---|
| `snapper` | Core snapshot tool — creates/manages/prunes btrfs snapshots |
| `snap-pac` | Pacman hooks — auto-snapshots root before/after every package operation |
| `btrfs-assistant` | GUI for browsing and restoring snapshots |
| `snapper-timeline.timer` | Systemd timer — takes periodic timeline snapshots |
| `snapper-cleanup.timer` | Systemd timer — prunes old snapshots per retention config |

`vjupdate` creates the snapper root config (`snapper -c root create-config /`) on first run and enables both timers.

To browse and restore snapshots:

```bash
btrfs-assistant         # GUI
snapper -c root list    # CLI list
snapper -c root diff <N> <M>   # diff between snapshots N and M
```

To restore a file from a snapshot:

```bash
# Snapshots live at /.snapshots/<N>/snapshot/
cp /.snapshots/<N>/snapshot/path/to/file ~/restored-file
```

---

## System optimisations (CachyOS / Arch)

Most of these are automated — run `vjupdate --optimize` (or tick **Apply system
tuning** in vj → One-time setup). It applies steps 1–5 below idempotently: CPU governor,
disabling NetworkManager-wait-online, masking lvm2-monitor, the rate-mirrors 2h
delay, and the AMD GPU performance udev rule. Steps 7 (EFI cleanup) and 8 (greetd
autologin) stay manual — EFI needs review, autologin conflicts with the DMS
greeter. Output mode/VRR is set in `dotsets/viridjan/desktop/.config/niri/cfg/display.kdl`
(`mode "3440x1440@165"`, VRR omitted entirely = off), which is the **only**
`output` block in the config tree — DankMaterialShell's auto-detected
`dms/outputs.kdl` is deliberately **not** included. Include order does not
save you here: for keyed nodes like `output "NAME"`, niri takes the *first*
occurrence, so re-adding that include ahead of this file would silently make
every edit to it inert (this cost days of misdiagnosis in Aug 2026 — see
CLAUDE.md "Merge semantics"). 165Hz is the monitor's real native mode and was
never the problem; VRR itself causes luminosity/brightness flicker on this
panel, even on-demand, so it's disabled outright (2026-08-25) — the
steam_app game window-rule no longer requests VRR either, and
`cfg/autostart-machine.kdl` re-asserts `vrr off` at session start.
`dms/outputs.kdl` was deleted outright rather than just un-included, so it
can't tempt anyone into re-adding the include and silently reintroducing the
bug. If DMS regenerates it, it stays inert — nothing includes it.

The sections below document what each step does, for manual application or review.

### 1. CPU governor

```bash
cat /sys/devices/system/cpu/cpu0/cpufreq/scaling_governor
# Should be 'performance' on a desktop. If 'powersave':
```

Edit `/etc/default/cpupower-service.conf`, uncomment:
```
GOVERNOR='performance'
```
Then:
```bash
sudo systemctl restart cpupower.service
sudo cpupower frequency-set -g performance
powerprofilesctl set performance   # if power-profiles-daemon is running
```

### 2. Disable NetworkManager-wait-online

Delays boot by waiting for full network. Not needed on desktop.

```bash
sudo systemctl disable NetworkManager-wait-online.service
```

### 3. Mask lvm2-monitor if no LVM

```bash
lsblk   # check for any lvm2 volumes
sudo systemctl mask lvm2-monitor.service
```

### 4. cachyos-rate-mirrors — delay post-boot run

The timer fires 10 min after every boot by default. Override to 2h:

```bash
sudo mkdir -p /etc/systemd/system/cachyos-rate-mirrors.timer.d
sudo tee /etc/systemd/system/cachyos-rate-mirrors.timer.d/override.conf << 'EOF'
[Timer]
OnBootSec=2h
EOF
sudo systemctl daemon-reload
```

### 5. AMD GPU performance level

```bash
cat /sys/class/drm/card*/device/power_dpm_force_performance_level
# If 'auto', create a persistent udev rule:
sudo tee /etc/udev/rules.d/99-amdgpu-performance.rules << 'EOF'
ACTION=="add", SUBSYSTEM=="pci", ATTR{vendor}=="0x1002", ATTR{class}=="0x030000", ATTR{power_dpm_force_performance_level}="high"
EOF
sudo udevadm control --reload-rules && sudo udevadm trigger
```

### 6. fstab — add noatime to non-btrfs mounts

btrfs mounts should already have `noatime` from the CachyOS installer.
Check any ext4 or other mounts:

```bash
grep -v noatime /etc/fstab | grep -v '^#' | grep -v tmpfs
# Add noatime to any data drives (e.g. defaults,noatime,nofail)
```

### 7. EFI boot entry cleanup

Duplicate entries from reinstalls slow firmware POST time.

```bash
efibootmgr   # review the list
# Keep: current boot entry, actual bootloader (Limine/systemd-boot), hard drive fallback
# Remove duplicates:
sudo efibootmgr -b <XXXX> -B   # repeat for each duplicate
```

### 8. Disable greetd greeter (autologin)

Edit `/etc/greetd/config.toml`:

```toml
[default_session]
user = "viridjan"
command = "niri-session"
```
