---
name: feedback-offline-runbooks
description: "For steps the user must run elsewhere (other machine), ship a standalone tested script + a manual-confirm TODO checklist, not chat instructions"
metadata:
  node_type: memory
  type: feedback
  originSessionId: 56a37e3a-1df0-4b5b-9e28-6c130ab2771b
  modified: 2026-09-29T10:09:19.086Z
---

When work has to be finished on another machine (e.g. the Surface), the user asked for a **standalone script they can run without a Claude window**, then for a **TODO.md checklist to confirm its execution manually**. Chat-only step lists weren't enough.

**Why:** they run those steps later, away from the session; the chat is gone by then.

**How to apply:** for cross-machine or deferred work, write a self-contained, skip-if-done script (backups before destructive steps, log to `~/.local/state/dots/`), smoke-test it in a sandbox HOME, commit + push it, and add a checkbox section in `TODO.md` that ends with "delete the script". See [[local-bin-unfolded]] (surface-sync.sh) for the worked example. Related: [[working-with-codex-in-dots]] — the user also likes plans handed off as files for Codex review.
