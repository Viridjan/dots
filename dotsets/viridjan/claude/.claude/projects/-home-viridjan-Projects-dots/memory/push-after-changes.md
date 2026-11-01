---
name: push-after-changes
description: User syncs desktop and Surface through GitHub; finished dots changes get committed and pushed
metadata:
  type: feedback
---

The user moves between the desktop and the Surface (vjsurface) and pulls on each, and repeatedly asked to "push" after changes on 2026-11-01. When a requested dots change is done and tests pass, commit and push in the same turn (leave the user's own uncommitted edits alone and say so).

**Why:** an unpushed fix is invisible on the other machine.
**How to apply:** end change requests with commit + push; still ask before destructive git operations. Related: [[scripts-never-abort]].
