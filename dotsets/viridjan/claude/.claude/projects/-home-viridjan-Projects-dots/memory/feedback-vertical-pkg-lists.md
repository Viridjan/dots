---
name: feedback-vertical-pkg-lists
description: user wants pacman/paru package lists one-per-row (VerbosePkgLists on); reversed the old compact choice
metadata:
  node_type: memory
  type: feedback
  originSessionId: 7a61ea6d-ff7c-4a56-8b25-402004496d61
  modified: 2026-11-14T09:44:57.204Z
---

User wants install/upgrade package lists shown one package per row, pacman-style table. sysup `optimize` step 6 now ENABLES `VerbosePkgLists` (it used to disable it for a "compact" list). paru reads the same pacman.conf setting.

**Why:** the default wraps every package onto one line, hard to read (2026-11-14).
**How to apply:** don't re-compact output; for new list-style output in sysup, prefer one item per line.
