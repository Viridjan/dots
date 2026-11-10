---
name: linux-hacks-upstream
description: "pasadoorian/Linux_Hacks is sysup's origin; last reviewed 2026-11-10 at commit 3c5109a — what was ported and what was skipped"
metadata:
  node_type: memory
  type: reference
  originSessionId: 29e0d0ad-b4de-4895-bbf0-cb130174499d
  modified: 2026-11-10T22:01:15.172Z
---

https://github.com/pasadoorian/Linux_Hacks — sysup began as a translation of its `update.sh` (commit e781f60, 2026-05-18). User periodically asks to "check it again" for things to add.

Reviewed 2026-11-10 up to upstream commit 3c5109a (2026-07-07). Ported: AUR maintainer audit (`check_aur_health`, maintainer-change holds), npm/bun/pnpm/yarn/npx in `_AUR_REVIEW_RE`, `paccheck` every 60 days, Secure Boot 2023-cert check (Surface only), CPU vulns. Already covered by lenucksi `aur_check --full`: package IOCs, npm/bun caches, eBPF, systemd persistence.

Skipped on purpose: mhwd-kernel (Manjaro), yay Lua hooks (paru has none; `_review_aur_updates` covers it), TPM/Intel ME/BIOS/hardware reports, output styling.

**How to apply:** next review, `git log --since=2026-07-07` upstream and only look at newer commits.
