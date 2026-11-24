---
name: security-stack
description: dots security tools (2026-11-24) — ufw, OpenSnitch allow-on-timeout, arch-audit, ClamAV weekly, Lynis action, sysctl hardening copied to /etc; what was rejected and why
metadata:
  type: project
---

Set up 2026-11-24 after a Lynis run (hardening index 65):
- **OpenSnitch** on every machine; unanswered pop-up **allows** (user choice: unattended sysup/games must not break). `_opensnitch_defaults` sets UI `default_action=1`.
- **arch-audit** in `sysup --check` (warn only for advisories with a fix).
- **ClamAV**: no clamd; weekly `clamscan` of Downloads/Shared/`/mnt/data/Downloads` in `--check`; `clamav-freshclam-once.timer`.
- **fail2ban** (user asked anyway, 2026-11-24): jail file written by `_system_hardening`, banaction ufw, sshd jail only.
- **Lynis**: `sysup --actions lynis`; 90-day reminder in the audit.
- **Hardening** (`_system_hardening`): sysctl + modprobe + coredump files **copied** to /etc, not stowed — /home is a separate btrfs subvol mounted after systemd-sysctl, so links would dangle at boot.

**Why rejected (don't re-propose without new reason):** umask 027 (paru/makepkg under user umask → packages with unreadable files), `modules_disabled`, `sysrq=0`, `bpf_jit_harden` (OpenSnitch eBPF), USB-storage block, rkhunter (Arch false positives; `paccheck` covers it), password ageing, /var partition.

**How to apply:** Lynis "Intrusion software" is green via fail2ban. New system /etc config that must apply at early boot → copy from sysup, never stow into /. Related: [[dots-package-preferences]], [[feedback-prefer-reversible-fixes]].

**Docker bypasses ufw (found 2026-11-24 via Lynis report):** published ports (`"8000:8000"`) bind 0.0.0.0 and Docker's own nft rules run before ufw, so they are LAN-reachable despite "deny incoming". Open Notebook exposed SurrealDB (root/root) that way → user removed Open Notebook everywhere. Any compose port must be `127.0.0.1:HOST:CONT` unless LAN access is wanted; check with `docker ps --format '{{.Names}} {{.Ports}}'` for `0.0.0.0`.
