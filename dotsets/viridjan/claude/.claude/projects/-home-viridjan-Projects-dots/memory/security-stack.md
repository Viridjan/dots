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

**Later 2026-11-24:** Lynis `custom.prf` skips every decided-against test → index 74, 0 suggestions (a new suggestion = something new). `snitch-report [HOURS]` / `--follow` reads OpenSnitch's file DB. OpenSnitch caught Brave's 1clickVPN extension (proxy + all-site webRequest) → removed + `ExtensionInstallBlocklist`; Brave Cast off (`EnableMediaRouter false`). Open Notebook removed everywhere; GitHub repo `Viridjan/open_notebook` archived (private), not deleted. OpenSnitch allow-always rules for system daemons are written by `_system_hardening` (`_SNITCH_ALLOW`).

**aur_check false positive (2026-11-24):** its systemd heuristic (Restart=always + RestartSec=30 in /etc/systemd) matched the enabled opensnitchd link and aborted `--update`. sysup clears only links to unaltered repo-package units (`_benign_systemd_hit`). Before calling any scanner hit a false positive, verify ownership + `pacman -Qkk` as done here. Lynis screen lines like NONE/NOT FOUND/NON DEFAULT are inventory; user walked through many — `sysup --actions lynis` now copies `lynis.log` to `~/.local/state/dots/` for line-by-line review.

**OpenSnitch rules in git (2026-11-24):** only "forever" pop-up answers become files in /etc/opensnitchd/rules; 12h ones are memory-only (the user had used 12h for everything, so nothing was savable). `sysup --actions snitch-export` → repo `opensnitch/rules/` (commit), `_system_hardening` restores them everywhere. User interrupted a status check when they only asked a name — answer the literal question first.

