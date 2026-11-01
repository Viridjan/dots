---
name: feedback-lowest-maintenance
description: "When the user defers a design choice, pick the option with least ongoing maintenance"
metadata: 
  node_type: memory
  type: feedback
  originSessionId: 74ac168d-fad3-4549-8662-ad28e7e617d5
  modified: 2026-08-25T10:41:52.046Z
---

When presented with options the user has no opinion on, they say so and delegate:
"i don't have the answer to this ... please do the thing that needs less mantainance."

**Why:** this is a single-user dotfiles repo. Ongoing upkeep is paid by one person
forever, so recurring maintenance cost dominates one-time implementation cost. An
option that is slightly more work now but never needs touching again wins.

**How to apply:**
- Don't hand back a two-option question when both options carry recurring cost — look
  for the third option that removes the coupling entirely. Concrete case: rather than
  "hardcode the statusline plugin paths and regenerate them" vs "don't regenerate and
  let them go stale," resolve the paths at runtime so nothing ever regenerates. Deleted
  ~20 lines from `vjupdate` and made plugin updates a no-op.
- Prefer deleting the generator over guarding it. If a function can clobber
  hand-edits, removing its reason to exist beats adding a preserve-check.
- Compare options by "what must a human do when X changes," not by lines of code.
- **Don't leave dead files in place with an explanatory comment — delete them.** 2026-08-25: after un-including `dms/outputs.kdl` I left the file, reasoning it was inert and harmless. User pushed back: *"ok why not removing it?"* They were right — an inert file that still *reads* as authoritative (a full `output "DP-1"` block) makes "just re-add the include" the obvious fix for the next person, which silently recreates the original bug. A note saying "don't use this" is weaker than the file not existing. Check nothing references it, then delete.
- Corollary: deleting also *tests* assumptions. Removing that file proved DMS recreates it as a 0-byte stub, correcting a claim the repo had carried for months.

Consistent with the always-on ponytail mode. See [[dots-shell-conventions]], [[niri-gaming]].
