---
name: feedback-fix-script-systematically
description: "fix the errors in the script" in dots means root-cause + whole bug class, not a one-off data patch
metadata:
  type: feedback
---

When the user asks to fix an issue/errors in a dots script (vjupdate, vj, vjsurface…), fix it systematically: find the root cause in the code, fix every site of the same bug class, add a regression test that fails against the pre-fix script, then fix the triggering data if needed.

**Why:** user said so explicitly (2026-11-01) while I was triaging a vjupdate log where an AUR conflict was failing installs.

**How to apply:** use superpowers:systematic-debugging; don't stop at editing packages.toml/[paru].remove to dodge one conflict. Related: [[feedback-verification-rigor]], [[dots-shell-conventions]].
