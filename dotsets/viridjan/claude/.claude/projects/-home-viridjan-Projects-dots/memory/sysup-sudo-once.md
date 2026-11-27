---
name: sysup-sudo-once
description: sysup asks one password per run (run-only NOPASSWD drop-in) and skips the fingerprint only for its own prompt — user choices 2026-11-27
metadata:
  type: project
---

sudo tickets are per tty and `_paru` runs paru in a `script` pty, so each paru call re-prompted. User chose a **run-only** grant: after the password, `/etc/sudoers.d/zz-sysup-run` (`NOPASSWD: ALL`) until `_cleanup`, 6h `systemd-run` expiry. Rejected: permanent `timestamp_type=global`, dropping the pty (progress bars). `timestamp_type=global` as a run drop-in fails: applies only from the next auth (second password).
Fingerprint (chwd's `pam_fprintd` in `/etc/pam.d/sudo`, Elan swipe sensor): user chose **sysup-only** removal — `/etc/pam.d/sudo-nofinger` + `pam_askpass_service` + `sudo -A` with `lib/sysup/askpass`. Other sudo keeps the finger; greeter/lock never had it.
**Why:** user wants one prompt, password only, without weakening sudo outside runs.
**How to apply:** don't propose global sudo changes for this; new root steps inside a pty are covered only while the grant exists. Related: [[security-stack]].
