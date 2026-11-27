---
name: dms-wifi-password-focus
description: "DMS wifi password box from the right bar/island can't be typed in (two exclusive layers); works from DMS Settings"
metadata:
  node_type: memory
  type: project
  originSessionId: 369754d9-40a5-4947-be70-a130f1e3b010
  modified: 2026-11-27T08:15:15.769Z
---

dux-shell 2.1.2 (2026-11-27, Surface): wifi password box opened from the bar/dankisland can't take typing. `niri msg layers` showed both `dms:dankisland` and `dms:wifi-password` on Top with `keyboard_interactivity: exclusive`; niri gave the keyboard to the island. `PopoutService.showWifiPasswordModal` doesn't close the island first. DMS QML is extracted to `/run/user/1000/dms-shell/<hash>/` each start, so no persistent local patch.

**Why:** upstream DMS bug, not dots config.
**How to apply:** workaround = DMS Settings → Network (confirmed by user) or `nmcli --ask device wifi connect SSID`. Recheck after dux-shell updates.
