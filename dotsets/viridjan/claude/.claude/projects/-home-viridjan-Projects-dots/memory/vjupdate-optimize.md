---
name: vjupdate-optimize
description: vjupdate --optimize automates CachyOS system tuning (configure phase item)
metadata: 
  node_type: memory
  type: project
  originSessionId: 7c8969fe-be25-4259-b949-842f5d0e3b44
---

`vjupdate --optimize` (also `optimize` item in configure phase / TUI menus) applies CachyOS/Arch tuning idempotently. Function `optimize_system()` in scripts/.local/bin/vjupdate.

Steps (each checks state, skips if applied):
1. CPU governor → performance (desktop only) — edits /etc/default/cpupower-service.conf
2. disable NetworkManager-wait-online.service
3. mask lvm2-monitor.service if no LVM2_member partitions
4. cachyos-rate-mirrors.timer OnBootSec=2h override drop-in
5. AMD GPU performance level → high via /etc/udev/rules.d/99-amdgpu-performance.rules (desktop + AMD GPU detected)
6. pacman: comment out VerbosePkgLists in /etc/pacman.conf → compact upgrade list (no Net Change/Download Size cols)

GOTCHA: `setup_caveman_code` does `ln -sfn` into ~/.local/bin which is a stow dir-symlink to repo scripts/.local/bin — so the caveman/caveman-code symlinks (abs paths into ~/.local/lib node_modules) LEAK into the repo. Gitignored (scripts/.local/bin/caveman*). Same trap for any future ~/.local/bin symlink created at runtime.

Deliberately NOT automated: greetd autologin (README §8 — conflicts with DMS greeter setup), EFI boot entry cleanup (README §7 — needs manual efibootmgr review). Both stay manual in README §System optimisations.

These mirror README §"System optimisations" which now points users to `--optimize` first, keeping per-step docs for manual review.

See [[project-state]].
