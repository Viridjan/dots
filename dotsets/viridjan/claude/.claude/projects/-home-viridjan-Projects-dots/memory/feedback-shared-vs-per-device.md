---
name: feedback-shared-vs-per-device
description: New dots settings default to shared on every device; only hardware/role-specific ones go per profile
metadata:
  type: feedback
---

General features are enabled on every device; only genuinely device-specific ones are per device (user, 2026-11-24).

**Why:** user wants one config everywhere, with per-machine differences explicit and minimal.

**How to apply:** place a new setting in the shared layer (`packages.toml`, shared dotset package, ungated sysup code) unless it depends on hardware/role → profile feature + `_has_feature`, profile `[paru]`, or a `<pkg>@<profile>` variant (added 2026-11-24; full copy, so use sparingly). One machine only → local `config.toml`. When unsure which, ask. Related: [[feedback-lowest-maintenance]].
