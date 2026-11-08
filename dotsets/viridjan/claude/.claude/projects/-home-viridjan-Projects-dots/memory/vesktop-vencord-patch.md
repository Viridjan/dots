---
name: vesktop-vencord-patch
description: 2026-11-08 Vesktop transparent/black window = Vencord wreq.d vs Discord's 3-arg d(); local patch in sessionData, lost on Vencord update
metadata:
  type: project
---
2026-11-08: Vesktop showed a transparent then black window. Cause: Vencord's webpack `wreq.d` override doesn't handle Discord's new 3-arg `d(exports, getters, values)`. Cache moves and disabling hardware acceleration did nothing. User rejected waiting for an upstream fix.

Fix: patched `~/.config/vesktop/sessionData/vencordDesktopRenderer.js` (untracked, holds the Discord token dir) so `this.d` also defines `values` as plain value properties. Debugged via `--remote-debugging-port` + CDP.

**Why:** a Vencord auto-update overwrites the patch; if the window goes blank again, check whether upstream fixed it before re-patching.
**How to apply:** blank Vesktop → check Vencord version / `this.d=` in that file first.
