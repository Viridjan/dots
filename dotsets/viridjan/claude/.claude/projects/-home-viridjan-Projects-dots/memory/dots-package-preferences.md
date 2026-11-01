---
name: dots-package-preferences
description: "dots repo (~/Projects/dots) package choices — -bin AUR fine (source rule dropped 2026-10-25), no third-party pacman repos; vjupdate needs sudo password so Claude can't install"
metadata:
  node_type: memory
  type: feedback
  originSessionId: a7e899a7-e05d-48d1-ae37-c63ee8ef8070
  modified: 2026-10-25T17:28:30.376Z
---

`-bin` AUR packages are fine. The user's old "source over -bin" rule (2026-10-16, ArtCraft apps swapped to source) existed only because they thought `-bin` packages couldn't be updated. Once told that `-bin` updates via paru like any AUR package, they dropped the rule (2026-10-25) and swapped the ArtCraft `*craft` apps back to `-bin` (source builds cost ~46 min).

Sublime Text was removed rather than keep its third-party pacman repo (its key was wiped by vjupdate's 48h keyring reset).

**Why:** the source preference was a misconception about updates, not a security/trust stance. Third-party repos fight the keyring reset.

**How to apply:** for AUR, `-bin` is acceptable; mention build time when choosing. Avoid third-party pacman repos (if unavoidable, list the key in vjupdate's `_REPO_KEYS`). Swapping an installed package for its twin: put the old name in `[paru].remove` (vjupdate's `--noconfirm` declines paru's conflict prompt; not-installed names are ignored). Never list both a pkg and its `-bin`. Check new AUR names against `~/.local/share/aur-malware-check/data/campaigns/*/packages*.txt` (e.g. `alvr` hijacked June 2026; `alvr-bin` is a TODO.md item). `sudo` needs a password in Claude's shell, so give the user `! paru ...` commands. Removal/install commands via `!` must carry `--noconfirm` (pacman) / `-y` (flatpak): the `!` prompt can't answer `[Y/n]`, so pacman aborts silently and the `&&` chain stops (2026-10-30). System flatpaks uninstall from Claude's shell without sudo (`flatpak uninstall --system --noninteractive -y`, polkit allows) — just do it. Unused-app audits: see CLAUDE.md "Unused-app cleanup" for the evidence method; user keeps rescue tools (gparted, pavucontrol) even when idle. Codex also edits dots in parallel — see [[working-with-codex-in-dots]].

**Provider-name trap (2026-10-31):** CachyOS renames packages under a provides (dms-shell→dux-shell, dgop→dux-gop); a list naming the old one fails the install phase on conflict. When vjupdate's log shows a conflict right after `Replace X with Y?`, update the list to Y. `pacman -Qq X` resolves provides — compare its output to X before treating X as installed.
