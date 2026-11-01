---
name: feedback-no-screenshots
description: "Don't use niri/dms screenshot tools to debug visual UI issues (bar, windows, layout) — user found it invasive"
metadata: 
  node_type: memory
  type: feedback
  originSessionId: a06595f9-fa30-4ffb-ba85-3b46ca53b022
  modified: 2026-08-18T12:20:31.543Z
---

Do not use `niri msg action screenshot`, `dms ipc call niri screenshotScreen`, or similar screen-capture tools to check UI state while debugging (e.g. checking whether the DMS bar is visible). User reacted strongly negative ("what the fuck is this screenshot thing, please don't do it again") when this was used mid-session to debug [[dots-dms-troubleshooting]]-style bar-visibility issues.

**Why:** Taking screenshots disrupts the user's screen (interactive screenshot-select overlays can get stuck open, requiring cleanup) and drops files into `~/Pictures/Screenshots/` that then need deleting. It's an invasive way to answer a question the user can answer directly by looking at their own screen.

**How to apply:** When debugging whether something is visually rendering (a bar, a window, a popup), ask the user to look and report back rather than capturing the screen. Rely on non-visual signals instead: compositor state (`niri msg windows`, `niri msg layers`, `niri msg --json layers`), IPC status calls, log files (`/run/user/1000/quickshell/by-id/*/log.log`), and settings dumps (`dms ipc call settings dump`). Only capture a screenshot if the user explicitly asks for one.
