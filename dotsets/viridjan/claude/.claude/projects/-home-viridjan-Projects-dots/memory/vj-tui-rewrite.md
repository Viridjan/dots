---
name: vj-tui-rewrite
description: "2026-10-21 vj TUI + profiles + dotsets/viridjan move, pushed 2026-10-21; pending /etc relink, Surface runbook"
metadata:
  node_type: memory
  type: project
  originSessionId: b436ea82-8f8c-4247-8e30-f1b11d69198f
  modified: 2026-10-21T14:15:47.097Z
---

2026-10-21: built `vj` (Textual TUI) over bash `vjupdate` merged into main 2026-10-21 (3cbdebf), not pushed yet. Spec/plan in `docs/superpowers/`.

- Package lists → `packages.toml` + `profiles/{desktop,surface}.toml` (features replace MACHINE checks); `projects.toml`; `build-times.tsv` committed (keys `aur:`, `@pacman-per-pkg`).
- All stow packages moved to `dotsets/viridjan/`; live `~` links on the desktop were relinked there (verified 0 dangling, niri validate 0).
- Local per-machine state: `~/.config/vjupdate/config.toml` (not created yet on desktop — first `vj` run opens setup).

**Pending at end of session (check before assuming done):**
- `/etc/brave` and `/etc/systemd/system/ollama.service.d` were dangling (need user sudo to relink from `dotsets/viridjan`).
- Pushed to origin/main 2026-10-21 (f7c1386). Surface must run surface-sync.sh before/instead of a plain pull.
- Surface: `surface-sync.sh` updated to also relink from dotsets + write config; see TODO.md. Related: [[local-bin-unfolded]], [[dots-history-purge]].

**Why:** user asked for profiles/friends' dotfile sets, a TUI with inline submenus and per-row recap, declines remembered, one-time task tracking.
**How to apply:** UI feedback the user gave: per-row recap aligned with menu rows, submenus inline below the menu, single setup screen with stacked titled boxes, coloured times (green <10s, yellow <1min, orange). In this repo the Bash tool's shell is zsh — `$VAR` lists don't word-split; wrap loops in `bash -c`.
