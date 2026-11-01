---
name: vjupdate-2026-10-27-cleanup
description: 2026-10-27 vjupdate slimmed (bash menu deleted → bare vjupdate execs vj), shared AUDIT_CHECKS, weekly check timer, last-check.tsv in vj
metadata:
  type: project
---

2026-10-27 (graph-driven review, user said "do all of them" then "apply everything"):
- Bash `_multiselect` menu deleted; bare `vjupdate`/`-i` → `exec vj`. `MENU_ORDER` = only action-ID list (vj/state.py MAINT/ONCE/DMS must match).
- `AUDIT_CHECKS` + `_run_audit_checks` shared by `--check` and audit phase; `--check` writes `~/.local/state/dots/last-check.tsv`, vj Maintenance row shows it.
- `vjupdate-check.timer` (dotset pkg `systemd-user`) enabled on desktop; Surface gets it via "Enable system services" after stow.
- `_remove_conflicts` + demotions now also in `--update`; hardcoded libreoffice swap gone.
- automount code → `scripts/.local/lib/vjupdate/automount.sh` (lazy-sourced; needs `scripts` stowed so `~/.local/lib` link exists).

**Why:** user wants least-maintenance, single source of truth, no duplicate UIs ([[feedback-lowest-maintenance]]).
**How to apply:** graphify "no callers" list for bash is mostly false positives (indirect calls) — grep before deleting. Auto mode blocks `systemctl --user enable`; user must approve/run it. Related: [[vj-tui-rewrite]].
