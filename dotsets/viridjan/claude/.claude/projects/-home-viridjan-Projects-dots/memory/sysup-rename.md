---
name: sysup-rename
description: 2026-11-08 vjupdate→sysup, vj TUI deleted, sysup.py helper, dotset backup tags; Surface/Plancia runbook pending
metadata:
  type: project
---
2026-11-08: `vjupdate` renamed `sysup`; vj TUI + python-textual removed. TOML logic in `scripts/.local/lib/sysup/sysup.py`. Config moved to `~/.config/sysup/config.toml` (desktop migrated; pre-move copy at `~/.local/state/dots/vjupdate-config.pre-sysup.toml`). Dotset backups = local tags `backup/<set>/1|2`, `sysup --restore`. Timer now `sysup-check.timer`.

**Why:** user wanted no TUI, better name.
**How to apply:** Surface/Plancia still need `~/Projects/dots/scripts/.local/bin/sysup --actions stow-symlinks,services` after pull (TODO.md). Supersedes [[vj-tui-rewrite]].

**Menu back (2026-11-08, user request):** bare `sysup` in a TTY with fzf → `_menu` loop (update/check/actions/options/status/quit; Esc = back; each choice runs as child `bash sysup`, keypress returns). Actions = grouped `fzf --multi` over `sysup.py menu`; options toggle --dry-run/--adopt/--clean-aggressive. Labels in sysup.py `ACTIONS`. No TTY → help. Details in CLAUDE.md.
