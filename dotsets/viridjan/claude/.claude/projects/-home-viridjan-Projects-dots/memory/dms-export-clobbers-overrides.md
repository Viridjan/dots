---
name: dms-export-clobbers-overrides
description: "vjupdate --dms-export used to blanket-copy DMS auto-generated files into the repo, silently destroying manual theme overrides"
metadata: 
  node_type: memory
  type: project
  originSessionId: 1e5faa65-b6b4-4806-b221-c74d6068e54e
  modified: 2026-08-25T10:14:48.210Z
---

`vjupdate --dms-export` used to run a blanket `cp "$DMS_LIVE"/*.kdl "$DMS_REPO/"`, copying **every** live DMS file into the repo — including the ones DMS regenerates on every session start (`colors.kdl`, `outputs.kdl`). `dms_import` meanwhile correctly restricted itself to the `DMS_MANUAL` array. That asymmetry meant any hand-tuned value in `colors.kdl` survived only until the next `--dms-export`.

**It already cost a real regression:** the green focus-ring (`#4caf50`) and forest shadow (`#0d3320CC`) overrides were reverted to DMS defaults (`#d0bcff` / `#00000070`) by commit `ff2cd4e` (2026-06-17) — a commit whose message was about unrelated vjupdate changes, so the theme change was invisible in review. It went unnoticed for **two months** while CLAUDE.md kept documenting green as the current value.

**Fixed 2026-08-25:** added a `DMS_AUTO=(colors.kdl)` array. `dms_export` now iterates `DMS_MANUAL` only (repo copy of auto-generated files is authoritative); `dms_import` pushes `DMS_MANUAL` + `DMS_AUTO` live, which also automates the manual `cp` re-apply step CLAUDE.md used to describe.

**Why:** files an app rewrites itself must never be exported live→repo, or the repo stops being the source of truth for them. Export and import must agree on which files are which.

**How to apply:** to change DMS colors, edit the **repo** copy then `vjupdate --dms-import` + `niri msg action load-config-file` — never edit `~/.config/niri/dms/colors.kdl` live, DMS overwrites it within seconds. User chose to keep the DMS-default purple rather than restore green (2026-08-25). See [[niri-gaming]] for the related `dms/outputs.kdl` include-order bug found in the same audit.
