---
name: surface-post-reboot-steps
description: "Surface (vjsurface) catch-up after 2026-11-01: ~/.claude move pending, then cleanup + service checks"
metadata:
  node_type: memory
  type: project
  originSessionId: 548b146a-1130-4087-9a61-4cdbafca88e1
  modified: 2026-11-01T01:41:08.346Z
---

State at 2026-11-01 ~02:15 (vjsurface, checkout = origin/main 9bdbe52):

Done this session:
- A pacnew merge (00:42, pacdiff `o`) had overwritten `/etc/pacman.conf` (lost CachyOS repos + multilib) and `/etc/pacman.d/mirrorlist` (0 servers). Restored from `.bak`, `pacman -Syy` OK.
- vjupdate `--actions sources,install,audit,orphan-removal,rebuild,python-rebuild,pacnew-merge,stow-symlinks,steam-launchers,app-launchers,manual-steps` now passes except `stow:claude`.
- Temporary `/etc/sudoers.d/99-claude-tmp` (NOPASSWD + `verifypw=any`; paru SudoLoop's `sudo -v` needs verifypw=any) was REMOVED. If more unattended runs are needed, it must be recreated by the user.

Next, in order:
1. With Claude Code closed, user runs `cp ~/Projects/dots/surface-sync.sh /tmp/ && bash /tmp/surface-sync.sh` (script aborts if run from the repo; copy the working-tree file, origin's lacks the relink code). ALL claude processes must be closed (a stray one from 00:18 on pts/0 blocked the 02:17 run) — moves `~/.claude` (still a link to old `dots/claude/.claude`) onto `dotsets/viridjan/claude`. Verify: `readlink ~/.claude`, then `vjupdate --actions stow-symlinks` has no `stow:claude` conflict.
2. After that succeeds: untracked old `claude/` in repo root can go (move it to `~/.local/state/dots/old-layout-backup-20261101/`, like DankMaterialShell/ already was). Done 02:42: Discord uninstalled + data removed; dead discord/lutris niri rules removed (config.kdl, uncommitted); `gamescope-media`/`start-battlenet` restored in repo and stow-linked (were real files in ~/.local/bin).
3. `surface-sync.sh` had uncommitted local edits before the session — ask the user, don't touch. Delete it once TODO.md checklist is ticked.
4. Checked 02:45: docker, power-profiles-daemon, mpd, vjupdate-check.timer active; dux-greeter-git installed; zsh explicit; ~/.codex/skills OK. NOT OK: no iptsd@ units (touchscreen) — booted linux-cachyos, which lacks the `ithc` module; linux-surface is installed but not booted (GRUB default + maybe Secure Boot MOK enrol). User decides.
5. Expected/harmless warnings: Steam not installed; spotify-player + Vesktop need login.

**Why:** the session ended because `~/.claude` can't move while Claude runs.
**How to apply:** on return, check step 1 first, then continue. Warn: in pacdiff never `o` pacman.conf/mirrorlist. Delete this memory when all steps are done.
