---
name: feedback-user-commands-fish
description: commands handed to the user run in fish — wrap POSIX syntax in bash -c; downloaded binaries must be run by the user
metadata:
  type: feedback
---

The user's interactive shell is fish: a POSIX one-liner (`d=$(mktemp -d) && …`) failed with "Unsupported use of '='" (2026-11-24). Fish autocompletion also turned `$d` into `$DBUS_SESSION_BUS_ADDRESS` inside an `rm -rf`.

**Why:** the user pastes commands into their own fish terminal, not always via `!`.
**How to apply:** give commands with variables or `$(…)` as `bash -c '…'` and quote paths; ask them to check `rm -rf` targets before Enter. Running a downloaded binary (e.g. testing a repo package from a temp extract) is blocked for Claude by the auto-mode classifier, so hand the command to the user instead of working around it. Related: [[go-pinned-extra]].
