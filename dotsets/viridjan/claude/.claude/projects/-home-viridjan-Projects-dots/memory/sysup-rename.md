---
name: sysup-rename
description: 2026-11-08 vjupdate→sysup, vj TUI deleted, sysup.py helper, dotset backup tags; Surface/Plancia runbook pending
metadata:
  type: project
---
2026-11-08: `vjupdate` renamed `sysup`; vj TUI + python-textual removed. TOML logic in `scripts/.local/lib/sysup/sysup.py`. Config moved to `~/.config/sysup/config.toml` (desktop migrated; pre-move copy at `~/.local/state/dots/vjupdate-config.pre-sysup.toml`). Dotset backups = local tags `backup/<set>/1|2`, `sysup --restore`. Timer now `sysup-check.timer`.

**Why:** user wanted no TUI, better name.
**How to apply:** Surface/Plancia still need `~/Projects/dots/scripts/.local/bin/sysup --actions stow-symlinks,services` after pull (TODO.md). Supersedes [[vj-tui-rewrite]].
