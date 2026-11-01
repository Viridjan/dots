---
name: project-state
description: System state as of 2026-08-18; vjupdate launcher hygiene, rebuild automation, package list audit
metadata: 
  node_type: memory
  type: project
  originSessionId: 6f526ee9-e2af-4c62-a0cf-1fb32cfc6529
  modified: 2026-09-15T12:18:09.465Z
---

Fresh install completed on 2026-06-18. System functional.

**Pending:**
- SSH key not set up → repos not cloned (crosses-zmk, Tournaments, lamp, open_notebook), graphify plugin not installed
- ollama: deepseek-r1:7b pulled + capped 2026-10-30, see [[ollama-limits]]
- **niri config drift (found AND resolved 2026-08-24):** `cfg/animation.kdl`, `cfg/autostart.kdl`, `cfg/keybinds.kdl`, `cfg/layout.kdl`, `cfg/misc.kdl`, `cfg/rules.kdl` were symlinked live but never `include`d in `config.kdl`. Diffed each against its live equivalent: `misc`/`autostart` were pure duplicates (deleted); `keybinds`/`rules` had a mix of genuinely-missing content (ported: `Mod+E`/`Mod+B`/`Mod+TAB` keybinds → `dms/binds.kdl`; dgop-monitor/spotify-player/vesktop/libreoffice widths + thunderbird/whatsie/telegram social-workspace + steam VRR/fullscreen rules → inline `config.kdl` window-rules) and risky broad overrides that were dropped (a global `open-focused false` catch-all, and layout/animation values that conflicted with what's actually live — user chose to keep current gaps=4/focus-ring=2/corner-radius=12 over the file's 13/4/15). Machine-pkg `cfg/input.kdl` (`layout "us" variant "intl"`) was genuinely missing and got restored via a new `include`. `niri/.config/niri/cfg/` is now empty; vjupdate's now-dead symlink loop for it was removed too. Full detail in CLAUDE.md's "Resolved 2026-08-24" note. See [[niri-gaming]] for the related VRR/display-mode fix from the same session.

**2026-08-25 — display flicker finally root-caused; DMS export bug fixed:**
- The 2026-08-24 "fix" never worked. `dms/outputs.kdl` was included *before* `cfg/display.kdl`, and niri takes the FIRST occurrence of a duplicate keyed node — so every display edit was inert. Deleted the file + its include; `cfg/display.kdl` is now the sole output source. Trigger was VRR, not the refresh rate; 165Hz native restored, VRR off. **Verified across a real reboot.** Full detail + all the debugging traps in [[niri-gaming]].
- `vjupdate`'s `dms_export` blanket-copied DMS's regenerated files into the repo, asymmetric with `dms_import`. Added `DMS_AUTO=(colors.kdl)`; export skips it, import pushes it live. See [[dms-export-clobbers-overrides]].
- `dms/wpblur.kdl` was tracked and imported but never included — now included (inert until DMS blur is enabled).
- CLAUDE.md + README carried a wrong include-merge rule for months; corrected with the experiments that prove it.

**2026-06-22 — Matrix/gomuks removed, WhatsApp via whatsie:**
- Self-hosted Matrix stack (Synapse + mautrix-whatsapp + mautrix-telegram bridges) was never bootstrapped (`/mnt/data/matrix-data` empty, containers stuck `Created`). User chose to abandon it entirely. Ripped out: `matrix/` dir, `setup_matrix()`/menu entries in vjupdate, `start-matrix` script, gomuks stow pkg + `gomuks.desktop`, autostart entry, CLAUDE.md sections, docker containers+images, `/mnt/data/matrix-data`.
- gomuks history: installed legacy terminal `gomuks` 0.3.1 → user wanted new web gomuks (`gomuks-web-bin`, github.com/gomuks/gomuks) → then dropped gomuks entirely. WhatsApp now via `whatsie` (AUR, Qt WebEngine WA-Web wrapper) — lighter than bridge stack. whatsie in `.paru-S-common.list`.
- **Lesson:** user's `pacman -R` removals don't always stick — verify `pacman -Q <pkg>` after, don't trust "done". gomuks-web-bin removal needed 3 attempts.

**Resolved 2026-06-20:**
- Both data partitions now in /etc/fstab (via `vjupdate --automount`): nvme0n1p3 (UUID 51058f01-..., label "data") at /mnt/data; sda1 (UUID 895fc252-..., label "ext_data") at /mnt/ext_data. Both have UUID bind mounts under /run/media/viridjan/. No more polkit auth prompts.
- Steam library was at dead udisks path `/run/media/viridjan/data/steam library` (label-based, gone after fstab switch) → cloud sync failed (error 2 ENOENT). Fixed: edited libraryfolders.vdf (config/ + steamapps/) to `/mnt/data/steam library`. MUST quit Steam before editing — it rewrites vdf on exit. `.steam/steam` + `.steam/root` symlink to `.local/share/Steam`.
- caveman plugin defaultMode set to ultra: `~/.config/caveman/config.json` `{"defaultMode":"ultra"}`. Now tracked as `caveman` stow pkg.

**2026-06-30 — niri workspace layout reworked:**
- Removed "main" workspace concept from niri config. Thunderbird moved to "social" workspace alongside Whatsie + Telegram. Steam correctly placed under "media" (autostart comment was wrong).
- Autostart (desktop): Social = thunderbird, whatsie, Telegram; Media = steam, dgop-monitor, spotify-player.
- rules.kdl: single social rule covers thunderbird (app-id), whatsie (app-id), TelegramDesktop (app-id), Discord (title). Ferdium match removed entirely (app no longer used).
- `settings.json` `tui: fullscreen` added (pre-existing change, tracked now).

**2026-06-24 — Codex CLI added, slides repo tracked:**
- Codex CLI (OpenAI) installed via `curl -fsSL https://chatgpt.com/codex/install.sh | sh`; binary lives at `~/.codex/packages/standalone/current/bin/codex` (self-updating). Added to `.install-scripts.list`.
- `slides` repo (`git@github.com:Viridjan/slides.git`) added to `projects.list` — was missing.
- Claude Code default model switched from `opus` → `sonnet` in `claude/.claude/settings.json`.

**2026-08-15 — vjupdate hardening, shellcheck guard, statusline rework:**
- Fixed 18 bugs in `vjupdate`, mostly the `set -e` + `var=$(cmd)` class — see [[dots-shell-conventions]].
- `shellcheck` added to `.paru-S-common.list`; `.githooks/pre-commit` added and registered via `core.hooksPath` in `deploy_dotfiles`.
- Statusline reworked: `~/.claude/statusline.sh` aggregates segments and globs plugin paths at runtime. `settings.json` is now a static one-liner and `setup_claude` no longer wires the statusline at all (it used to clobber hand-edits, and emitted a version that piped stdin only to the first segment). `model-statusline.sh` is now tracked — it previously existed only on this machine.
- Claude Code default model switched back `sonnet` → `opus`.
- Known unrelated breakage: the caveman installer in `.install-scripts.list` fails with `npm error code EALLOWGIT` — npm config blocks git-type fetches, so that line can never succeed as written.
- Repo history rewritten to purge VSCodium Chromium caches: `.git` 104MB → 19MB, all SHAs changed. **Surface machine must `git reset --hard origin/main`** — see [[dots-history-purge]]. VSCodium no longer dirties 24 files per commit.

**2026-08-18 — vjupdate launcher hygiene + rebuild automation:**
- `setup_steam_launchers`: icon was always falling back to generic "steam" icon — modern Steam client stores librarycache images in hashed per-appid subfolders, not the flat `${appid}_icon.jpg` path the script checked. Fixed to use `Icon=steam_icon_${appid}` (icon-name form; Steam already populates `~/.local/share/icons/hicolor/*/apps/steam_icon_<id>.png`). Also fixed SteamVR skip-regex (`Steam VR` → `Steam ?VR`, actual manifest name has no space) and added stale-launcher removal (games uninstalled → `.desktop` deleted).
- New `check_app_launchers` (menu: `+app-launchers`, flag `--app-launchers`): removes non-Steam `.desktop` launchers whose `Exec=` binary no longer resolves; reports (informational only) installed apps not mirrored into `~/.local/share/applications/`. Skips anything Steam-related (`steam_app_*` and any `Exec=steam...`).
- Menu: "Gaming" section (only had steam-launchers) merged into new "Launchers" section alongside app-launchers.
- `check_rebuilds` had two bugs: (1) `warn "header:"` + separate `echo "$out"` meant the actual package names never reached the `WARNINGS[]` recap — fixed by folding into one `warn` call; (2) `checkrebuild` output is `<repo>\tpkgname` per line — code was flattening the whole line (including the `foreign`/repo-name column) into pacman targets, causing `error: could not find all required packages: foreign (target)`. Fixed with `awk -F'\t' '{print $2}'`.
- Added actual rebuild action: `AUDIT_REBUILD` flag, `+rebuild` menu item (checked by default), `vjupdate --rebuild` flag — runs `paru -S --noconfirm` on flagged packages, mirroring the existing python-rebuild/orphan-removal pattern.
- Root-caused a real build failure (`lib32-libid3tag`/`lib32-imlib2` AUR builds failing): `gperf` makedepend was missing from the system and untracked in any package list. Added `gperf`, plus separately-discovered untracked-but-installed apps `git`, `cmake`, `gparted`, `samba`, `firefox`, `nicotine+` to `.paru-S-common.list`.

**2026-09-14 — vjupdate log triage, opt-in pacnew merge:**
- Triaged `~/.local/state/dots/vjupdate.log`. One real failure: `lib32-sdl2-compat` AUR build died on `FAILED (unknown public key D913FE7D4B61D39B)`. Fixed by importing the SDL upstream key (Sam Lantinga) into the **user** gpg keyring — vjupdate's key handling is all `pacman-key`, a different keyring that only covers repo/package sigs. Full detail + the standing pacnew keep/discard table in [[vjupdate-log-triage]].
- Added opt-in `pacnew-merge` menu item (unchecked) + `vjupdate --pacnew`, mirroring `AUDIT_REBUILD`/`--rebuild`. Runs `pacdiff -s -b`; guards on `$INTERACTIVE` since it needs a tty.
- Codex CLI self-updated 0.153.4 → 0.154.0.
- **Still open:** `lib32-sdl2-compat` not yet rebuilt (needs a sudo tty), and limine warns `Detected conflicting config: /boot/EFI/limine/limine.conf` on every kernel upgrade — `/boot/limine.conf` is being ignored. Diff the pair before deleting either.

**2026-09-15 — vjupdate hardening pass (two rounds, Claude + Codex):**
- Six review findings fixed: surface `natural-scroll false` parse error (aborted the whole surface config), `_install_list` swallowing paru failures, stale malware definitions + ungraded scanner verdicts, `check_app_launchers` dying on `.desktop` files with no `Exec=`, `ollama.ts` model id, and `rebuild`/`pacnew-merge` being silent no-ops when audit was unchecked.
- Then a reliability pass: flock single-instance guard, read-only `--dry-run`/`--help` (runtime init split from load), `--adopt` opt-in with backups, AUR cache preserved by default, per-action ok/fail/skip recap driving exit status.
- Codex found a real bug I introduced: calling a phase inside `if "$@"` disables errexit for its **entire call tree**, so a failed keyring step would be stamped successful. Fixed with bare call + `set -E` + ERR trap.
- I found a real bug Codex introduced: `deploy_dotfiles` returning 1 on a stow conflict tripped that ERR trap and aborted the whole run, so one drifted file skipped dms_import/configure/audit. Conflicts are already recorded at the call site, so it returns 0 now.
- **Dangerous bug found late:** `manage_kernels` compared `uname -r` against `pacman -Q` version text — different formats, so the guard never matched. On this machine it would have allowed removing `linux-cachyos`, the running kernel's package. Now resolves ownership via `pacman -Qoq /usr/lib/modules/$(uname -r)/vmlinuz`. Side effect: kernel removal is refused while a kernel upgrade is pending a reboot (the old module tree is gone, so ownership is unknowable).
- `CLAUDE.md`'s `SKIP_PHASES="mirrors keyrings"` example was wrong for as long as it existed — `SKIP_PHASES` is only matched against the five phase names; mirrors/keyrings are stamp names throttled by `_needs_run`. It silently skipped nothing.
- Repo now has `tests/test_vjupdate.py` (27 tests, temp homes + mocked package managers) — first test dir in the repo. Run: `python3 -B -m unittest discover -s tests -v`; `VJUPDATE_SCRIPT=<snapshot>` tests an older script. See [[working-with-codex-in-dots]].

**Established earlier:**
- caveman-code npm tool at ~/.local/bin/caveman-code (v0.65.2); npm global prefix ~/.local

**How to apply:** Data partitions at /mnt/data + /mnt/ext_data (canonical fstab paths). Any app with hardcoded `/run/media/viridjan/data` path needs repointing to `/mnt/data`. See [[niri-gaming]] for fullscreen.
