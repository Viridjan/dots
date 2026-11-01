---
name: pacman-no-progress-under-tee
description: Why vjupdate shows no pacman progress bars/ILoveCandy; proposed script-pty fix (not implemented as of 2026-09-29)
metadata:
  node_type: memory
  type: project
  originSessionId: 3d4f5599-d6a3-4d74-877f-a14898f38bf6
  modified: 2026-09-29T10:24:46.262Z
---

pacman.conf has `Color` + `ILoveCandy`, but vjupdate installs show no bars/candy: pacman draws them only when stdout isatty, and vjupdate pipes everything (`exec > >(tee "$LOG_FILE")` in runtime init, plus `paru -Syuu ... | tee` in `_syuu`). No pacman flag forces bars; `--color=always` restores color only.

Proposed 2026-09-29, user did NOT yet accept: `_pty` helper wrapping paru in `script -qefc "$(printf '%q ' "$@")" /dev/null` when `[[ -t 0 ]]` (falls back to plain run for --yes/no tty). `-e` preserves exit code.

**Why:** user asked for pacman graphics during installs.
**How to apply:** if implemented, must strip ANSI/`\r` before `_syuu_fail_detail`'s `^error:` sed match, or build-failure detection silently breaks; log gets progress-redraw noise. Related: [[vjupdate-log-triage]], [[dots-shell-conventions]].
