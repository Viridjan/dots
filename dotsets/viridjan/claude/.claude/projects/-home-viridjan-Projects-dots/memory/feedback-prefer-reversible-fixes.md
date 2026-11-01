---
name: feedback-prefer-reversible-fixes
description: user rejects package downgrades as a first-line system fix; prefers config-level/reversible fixes and root-cause diagnosis first
metadata: 
  node_type: memory
  type: feedback
  originSessionId: 1e5faa65-b6b4-4806-b221-c74d6068e54e
  modified: 2026-08-24T11:34:28.468Z
---

When diagnosing a system regression (e.g. graphics corruption after a pacman upgrade), the user explicitly declined a `pacman -U`-based mesa downgrade even after it was clearly diagnosed as the correlated package change ("I don't want to downgrade it. There should be something else").

**Why:** package downgrades are hard to keep working long-term (need `IgnorePkg` forever, block future security/bugfix updates for the whole stack) and the user prefers to keep the system current. They'd rather find a config-level or narrower fix, even if it takes more investigation.

**How to apply:** When a regression correlates with a package upgrade, keep digging for a narrower root cause (config file, a specific setting, an included-but-broken file, a live-vs-static mismatch) before proposing a downgrade. Downgrade + `IgnorePkg` is a last resort, not the default fix — offer it only after config-level options are exhausted, and flag it explicitly as "blocks future updates to this package" so the tradeoff is visible. See [[niri-gaming]] for the case this came from: the actual fix was an orphaned include (`cfg/display.kdl` never wired into `config.kdl`), not the mesa/kernel bump that looked like the obvious culprit.
