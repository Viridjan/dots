---
name: wifi-bitwarden-sync
description: sysup wifi-export/wifi-import via Bitwarden note "sysup wifi" (2026-11-27); not yet run live; pacman DisableDownloadTimeout removed
metadata:
  type: project
---

2026-11-27: wifi passwords sync through Bitwarden secure note `sysup wifi` (user chose Bitwarden over age-in-repo / age+YubiKey). Code `scripts/.local/lib/sysup/wifi.sh` + `sysup.py wifi-read|wifi-write` (root). Not yet run live: needs `bitwarden-cli` installed, `bw login` per machine (TODO.md has the checklist).

Same day: `_pacman_download_timeout` comments out CachyOS `DisableDownloadTimeout` before every upgrade — a dead phone hotspot (`vj_hotspot`) hung `paru -Syuu` at 0 B/s for 15+ min.

**Why:** secrets never in git; secrets never on argv (user once leaked the hotspot password into the journal via `sudo nmcli ... password X`).
**How to apply:** suggest `nmcli --ask` for manual connects; on a stalled update check network before blaming pacman. Related: [[dms-wifi-password-focus]], [[security-stack]].
