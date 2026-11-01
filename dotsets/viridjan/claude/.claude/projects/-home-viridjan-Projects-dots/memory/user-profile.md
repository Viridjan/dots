---
name: user-profile
description: "User's machine setup, GPU, and dotfiles context"
metadata: 
  node_type: memory
  type: user
  originSessionId: 6f526ee9-e2af-4c62-a0cf-1fb32cfc6529
---

CachyOS desktop (tower). GPU: AMD RX 6700 XT (Navi 22/gfx1031). Surface Pro 9 is second machine.

Runs niri + DankMaterialShell. Uses stow dotfiles from ~/Projects/dots. vjupdate is the bootstrap/maintenance script.

Email: bntfnc89@gmail.com. GitHub: Viridjan.

ROCm note: RX 6700 XT (gfx1031) not in official ROCm support list — needs `HSA_OVERRIDE_GFX_VERSION=10.3.0` in fish config for ROCm tools to work.

Webcam: Elgato Facecam (0fd9:0078, UVC → `uvcvideo`). Browser is `brave-origin-bin`. VIA VL813 hub ports `1-9.x` disconnect often in kernel log — suspect for flaky USB devices.
