---
name: feedback-update-does-all
description: User wants `sysup --update` to cover installs; don't hand them separate --actions install steps
metadata:
  type: feedback
---

`sysup --update` is the one routine command. It runs the install action (`install_all`) since 2026-11-24 at the user's request ("actions install should be included inside update").

**Why:** user rejected a warning telling them to run `sysup --actions install` for a replacement package; expected --update to handle it.

**How to apply:** new routine package/tool work belongs in the install action so --update reaches it; other-machine instructions = `sysup --update`, no extra install step, no `git pull` ([[feedback-no-git-pull-hint]]). Prefer fewer, merged actions (2026-11-24 merged launchers/export/rebuild; user declined merging greeter+keyring-pam and claude+caveman-code).
