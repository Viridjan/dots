---
name: claude-auto-retry
description: claude-auto-retry 0.7.3 via fish `claude` function + StopFailure hook; npm 12 blocks git/tarball installs
metadata:
  type: project
---

Installed 2026-10-30: `claude-auto-retry` (npm, `[npm].install`) + `tmux` (`[paru].install`). Fish function `dotsets/viridjan/fish/.config/fish/functions/claude.fish` runs claude through its launcher (falls back to plain claude without tmux/package). `install-hook` added a StopFailure hook (matcher overloaded|server_error) to the tracked `claude/.claude/settings.json`. Reconcile timer not installed.

**Why 0.7.3 from npm:** GitHub HEAD (37efe8b, reviewed) has native-auto-continue coordination, but npm 12 defaults `allow-git=none` and also refuses remote tarballs (EALLOWREMOTE) — didn't override those defaults. Known gap: may type an extra "continue" alongside Claude Code's native auto-continue. Upgrade when npm publishes >0.7.3.

**How to apply:** live fish functions are file-level links — a new function needs `stow --restow -t ~ fish` from the dotset. Related: [[ollama-limits]].
