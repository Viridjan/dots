---
name: feedback-focus-policy
description: Window focus/placement exceptions apply only to what the user opens via ⌘Space or shortcuts; script/agent-opened windows keep open-focused false
metadata:
  type: feedback
---

New windows never take focus (global niri `open-focused false`). Exceptions the user asks for (e.g. terminal/browser take focus, launcher workspace placement) apply **strictly** to windows opened from the ⌘Space launcher or a keybind — never to windows opened as a consequence of scripts or agents (2026-11-24: "everything that is opened as consequence of other stuff should follow the old rule").

**Why:** a first attempt used a niri `open-focused true` rule by app-id; that also focused script-opened terminals/browsers, which the user rejected.

**How to apply:** don't express such exceptions as niri window rules (they can't see who launched a window). Route the keybind through `launcher-ws run [--app-id RE] CMD` and act in `launcher-ws watch` on the first window after the record. Apps opened by Claude/Codex go unfocused to the agent's workspace. Also user actions inside an app count: a non-floating Brave/terminal window opened while the same app is focused (Ctrl+N, Ctrl+Shift+N) takes focus (2026-11-24); PiP/dialogs (floating) don't. Related: [[feedback-no-focus-moves]], [[niri-gaming]].
