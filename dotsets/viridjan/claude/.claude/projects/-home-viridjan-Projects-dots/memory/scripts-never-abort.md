---
name: scripts-never-abort
description: Helper scripts for dots must be idempotent and never abort; warn and continue, summary at the end
metadata:
  type: feedback
---

For maintenance helpers (e.g. `vjsurface`), the user asked: "make it so that doesn't fail". Every step checks state first and is a no-op when done; a failing step warns and the next step still runs; exit 0 with a summary of what needs attention. Under vjupdate's `set -euo pipefail`, guard `var=$(cmd | …)` with `|| true` when cmd can exit nonzero harmlessly (bootctl without root exits 1 — killed a run on 2026-11-01).

**Why:** a half-run repair script on the Surface left the machine in a worse state than either end.
**How to apply:** new scripts/steps follow this shape; test with mocks that exit nonzero like the real tool. See [[push-after-changes]].
