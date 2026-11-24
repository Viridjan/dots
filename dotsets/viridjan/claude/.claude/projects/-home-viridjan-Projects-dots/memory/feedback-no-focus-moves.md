---
name: feedback-no-focus-moves
description: "Don't switch the user's niri workspace/focus in tests without saying so first; they can't reply mid-test"
metadata:
  node_type: memory
  type: feedback
  originSessionId: 2e55efe0-cf10-4777-8846-a5305cb430d3
  modified: 2026-11-24T11:45:15.733Z
---

Don't run `niri msg action focus-workspace` (or anything moving the user's view/focus) as part of a test without announcing it first. When a test needs the user elsewhere, move them yourself, state it up front, and move them back after a fixed delay — they can't switch and then type "go".

**Why:** 2026-11-24 launcher-ws test: silently switching workspace confused the user ("I got moved"); asking them to switch first and confirm didn't work either. The flow they asked for: "move me to workspace 1, open brave, move me back after 15 secs".

**How to apply:** UI tests on the live niri session → announce the move, do it, restore it. Related: [[feedback-no-screenshots]], [[niri-gaming]].
