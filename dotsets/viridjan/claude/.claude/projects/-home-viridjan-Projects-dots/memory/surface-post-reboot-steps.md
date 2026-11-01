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

Done 2026-11-01 ~03:00: `~/.claude` moved onto dotsets/viridjan/claude (stow clean); old root `claude/` → `~/.local/state/dots/old-layout-backup-20261101/`; alacritty/fish/vesktop/micro/gtk-3.0 refolded (old unfolded dirs in `.../live-config/`); vjupdate now warns on unfolded packages, guards pacnew overwrites of pacman.conf/mirrorlist, and audits the surface kernel.

Still open:
1. Touchscreen: DONE 02:57 — GRUB_TOP_LEVEL set to linux-surface, booted 7.2.11-arch1-1-surface, iptsd@dev-hidraw3 running.
2. `surface-sync.sh` has uncommitted local edits — ask the user, don't touch. Delete once TODO.md checklist is ticked.
3. Expected/harmless warnings: Steam not installed; spotify-player + Vesktop need login.

**Why:** Surface catch-up spanned several sessions.
**How to apply:** on return, start from "Still open". Warn: in pacdiff never `o` pacman.conf/mirrorlist. Delete this memory when all steps are done.
