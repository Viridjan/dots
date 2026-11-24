---
name: feedback-no-git-pull-hint
description: "Don't tell the user to `git pull` before sysup on other machines — sysup pulls itself"
metadata:
  node_type: memory
  type: feedback
  originSessionId: 600be91c-ae17-441b-a0a2-bb82815e5311
  modified: 2026-11-24T15:51:21.973Z
---

Don't instruct "git pull, then sysup ..." for Surface/Plancia. Just give the `sysup` command.

**Why:** user said (2026-11-24) "git pull is not useful anymore": any sysup run with a terminal runs `_check_repo_current` (fetch, `--ff-only` pull, exec relaunch) before doing anything.

**How to apply:** other-machine steps = `sysup --update` / `sysup --actions ...` only. Exception: the old one-time ~/.local/bin unfold migration ([[local-bin-unfolded]]) still has its own pull ordering. Related: [[sysup-rename]].
