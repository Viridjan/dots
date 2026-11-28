---
name: desktop-suspend-amdgpu
description: Desktop suspend broken = RX 6700 XT SMU resume bug (RunDcBtc -62), pending AMD patch; CachyOS GitHub issue drafted, not posted
metadata:
  type: project
---

Desktop (RX 6700 XT, MP1 11.0.11, ASRock H670M-ITX/ax BIOS 17.03): every suspend → `SMU: No response msg_reg: 36` / `RunDcBtc failed!` / `resume of IP block <smu> failed -62`, black screen; real `deep` often powers off. Proven 2026-11-28: both kernels (7.3.6, 6.18.65 LTS), deep + s2idle, `pm_test=devices`, perf level high + auto. Worked ~2026-09.

Cause: AMD patch "drm/amd/pm: Fix SMU messages after system resume for smu 11.0.x" (Yang Wang, v2 2026-08-18, drm/amd work item 5620), not merged in mainline or amd-staging-drm-next as of 2026-11-28. Same log: SteamOS #2894. Not #916 (USB abort) / #564 (IOMMU). Firmware rollback dropped (bug predates the 10-24 firmware).

User chose to ask CachyOS to carry the patch (not build a patched kernel). Reports in `~/Documents/amdgpu-suspend-report/` (Discord text, upstream text, GitHub issue draft, MAC-redacted logs). GitHub issue waits for the user's `cachyos-bugreport.sh` link; then post with gh to CachyOS/linux-cachyos (user approved posting). Done when a kernel update makes `pm_test devices` come back.

**How to apply:** don't re-derive; check whether the patch landed (`gh api` torvalds/linux commits on `drivers/gpu/drm/amd/pm/swsmu/amdgpu_smu.c`) before new tests. Related: [[feedback-prefer-reversible-fixes]].
