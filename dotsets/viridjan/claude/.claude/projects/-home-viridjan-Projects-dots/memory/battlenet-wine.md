---
name: battlenet-wine
description: "Battle.net lives in ~/Games/battlenet (ex-Lutris prefix), launched by start-battlenet via umu-run + GE-Proton; app-id quirks"
metadata:
  node_type: memory
  type: project
  originSessionId: 0ae2152a-890a-40ff-9f64-d223322d9918
  modified: 2026-10-29T12:59:22.763Z
---

Battle.net installed in Wine prefix `~/Games/battlenet` (made by Lutris, whose game DB is empty; lutris is in `[paru].remove`). Launch: `start-battlenet` / `battlenet.desktop` (scripts pkg, 2026-10-29) → `umu-run` with newest Steam GE-Proton, fallback proton-cachyos.

- Under umu every window in the prefix gets app-id `steam_app_battlenet` (games too); niri rule tells launcher apart by title `^Battle\.net`.
- Battle.net login opens in Brave first ("Battle.net Login" tab) on some runs.
- Stale sessions (old Lutris installer run, mixed Proton versions on one prefix) block new launches with no window: fix `WINEPREFIX=~/Games/battlenet <GE-Proton>/files/bin/wineserver -k`. Never run two Proton versions on this prefix at once.
- Auto-mode classifier blocks pkill/wineserver -k unless the user explicitly asks to kill.

**Why:** cost a session of "launched but no window" confusion.
**How to apply:** "Battle.net won't open" → check `pgrep -af '\.exe'` for leftover sessions first. Related: [[niri-gaming]].
