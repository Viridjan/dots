---
name: device-missing-after-kernel-upgrade
description: "Device not detected" on desktop → check running kernel vs /usr/lib/modules first; upgrade without reboot deletes running kernel's modules
metadata:
  type: project
---

2026-10-03: Facecam invisible to Brave. Two layers: (1) camera not enumerated at all — replug fixed USB; (2) `uvcvideo` couldn't load because `uname -r` (7.2.6) had no `/usr/lib/modules/` dir — vjupdate/paru upgrade installed 7.2.8 and removed it. Fix = reboot.

**Why:** user often runs many days without reboot after updates; any not-yet-loaded driver fails silently.
**How to apply:** for any "X not detected" on the desktop, check `lsusb`, then `uname -r` vs `ls /usr/lib/modules` + `modinfo <drv>` before app-level debugging. Related: [[user-profile]], [[vjupdate-log-triage]].
