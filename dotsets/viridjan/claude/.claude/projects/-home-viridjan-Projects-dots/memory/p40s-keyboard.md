---
name: p40s-keyboard
description: "X.Tips P40S keyboard firmware — stays QMK; both P40 repos dropped locally 2026-11-26, kept on GitHub"
metadata:
  node_type: memory
  type: project
  originSessionId: 01e1a154-ba14-47ec-8c9f-5e414cf22a79
  modified: 2026-11-25T23:08:23.710Z
---

X.Tips P40S (STM32F072, 40 direct pins, v2 matrix). Firmware repos stay on GitHub only: `Viridjan/p40-qmk` (Crosses ZMK keymap ported to QMK, no Vial, never compiled) and `Viridjan/P40S-Keyboard` (archived 2026-11-25; prebuilt v1/v2 Vial .bin for recovery + v1 matrix). 2026-11-26: p40-qmk removed from projects.toml and ~/Projects at user request; user declined deleting them on GitHub.

Vendor: X.Tips sells only on Xianyu (umux.com redirects to goofish.com seller page); upstream firmware incl. p40s in github.com/X-Tips/QMK-Keyboard.

ZMK port rejected 2026-11-25: user chose to stay on QMK.
**Why:** F072 has no BLE (no ZMK benefit), 16KB RAM likely too tight for ZMK, RGB pin A13 has no ZMK driver.
**How to apply:** don't propose ZMK for this board again; don't re-add the repos to projects.toml unless asked. Related: crosses-zmk repo is the ZMK keymap source.
