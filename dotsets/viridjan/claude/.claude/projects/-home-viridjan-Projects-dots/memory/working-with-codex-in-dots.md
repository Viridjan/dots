---
name: working-with-codex-in-dots
description: User runs Codex CLI against the dots repo between turns; re-read the working tree instead of assuming it matches what I left
metadata: 
  node_type: memory
  type: feedback
  originSessionId: ac57a7e8-5fae-476a-b3bd-a6ef89526086
  modified: 2026-09-26T10:28:39.575Z
---

The user runs Codex CLI (`codex`, self-updating, in `.install-scripts.list`) against `~/Projects/dots` **between my turns**, often asking me to write the review prompt for it and then asking me to check the result. The working tree can differ substantially from what I left — on 2026-09-15 Codex rewrote ~700 lines of `vjupdate` between two of my messages.

**Why:** treating my last-known state as current produces confidently wrong review. Files changed on disk arrive as system notes, but the safe move is always `git diff` / `git status` first.

**How to apply:**
- When told "Codex has done mods", start from `git diff`, not from memory of my own edits.
- Verify its technical claims against the local system rather than accepting the comment (e.g. it claimed `/usr/lib/modules/$(uname -r)/vmlinuz` identifies the running kernel — true on CachyOS, checked; but it resolved to nothing on this machine because a pending-reboot upgrade had deleted the tree).
- Expect my own scratchpad shell tests to go stale against its rewrites. Three did; all three were **my stale anchors**, not regressions. Distinguish "my test broke" from "the code broke" before reporting anything.
- The review is genuinely two-way and worth doing carefully: it caught a real errexit bug I introduced (`if "$@"` around a phase disables errexit for the whole call tree), and I caught a real one it introduced (a recoverable stow conflict aborting the entire run via the new ERR trap).
- Handing it my *plans* for review works too (2026-09-25): user asks me to write the plan as a file for Codex; it wrote `PLAN-*-review.md` with `§N: agree|object|simpler` lines and caught 5 real errors in my plan (unsafe Surface pull order, `git add -A` sweeping its own diff, deleting assets README said were deliberate, a match-only removal that would make a rule unconditional, blind-deleting unverified files). Verify each finding, then fold them in.
- Its regression tests are good — it proves each new test fails against a saved pre-fix snapshot. Hold my own tests to the same bar; see [[feedback-verification-rigor]].
- My scratchpad (`/tmp/claude-.../scratchpad`) dies with the session, so durable tests belong in the repo's `tests/`.
