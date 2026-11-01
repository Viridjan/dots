---
name: vjupdate-log-triage
description: "How to triage vjupdate.log — two-keyring gotcha for AUR sig failures, and the standing pacnew keep/discard verdicts for this machine"
metadata: 
  node_type: memory
  type: project
  originSessionId: ac57a7e8-5fae-476a-b3bd-a6ef89526086
  modified: 2026-09-14T17:37:31.088Z
---

Log lives at `~/.local/state/dots/vjupdate.log` (rotated `.1`–`.3`). Warnings recap at the tail; real causes are upstream in the body — grep `-iE "error|failed|WARNING"`.

**Two keyrings, not one (2026-09-14).** vjupdate's key handling (`scripts/.local/bin/vjupdate:148-178`) is all `pacman-key` — the *pacman* keyring, which only covers repo database and package signatures. That's what auto-recovers the recurring `sublime-text: signature ... unknown trust` → `Trusting sublime-text signing key (8A8F901A)` → retry. It does **nothing** for makepkg source-tarball verification, which uses the *user's own* `~/.gnupg`. So an AUR build dying with `FAILED (unknown public key <ID>)` is never fixed by rerunning vjupdate — fix it once by hand with plain `gpg --recv-keys <ID>`, no sudo, no pacman-key. Imported `D913FE7D4B61D39B` (Sam Lantinga, SDL upstream) this way for `lib32-sdl2-compat`. Side effect of such a failure: paru orphan-removes the build deps it pulled in (`ninja` went this time), so they come back on the retry.

**Standing pacnew verdicts** — `check_pacnew` reports by default (`pacdiff -o`). Resolving is opt-in: the unchecked `pacnew-merge` menu item or `vjupdate --pacnew` sets `AUDIT_PACNEW` and runs `pacdiff -s -b` (added 2026-09-14, mirrors the `AUDIT_REBUILD`/`--rebuild` pattern). It needs a tty, so `--yes` runs warn and skip. Do not blanket-overwrite; `pacman.conf.pacnew` in particular would drop the cachyos-v3/cachyos/sublime-text repos and re-comment `[multilib]`.

| pacnew | verdict | why |
|---|---|---|
| `pacman.conf` | discard | ours adds cachyos repos, sublime-text, multilib, Color/ILoveCandy, ParallelDownloads=10 |
| `locale.gen` | discard | ours keeps the Calamares-enabled en_GB/en_US/it_IT |
| `limine-snapper-sync.conf` | discard | diff is comments + `"Arch Linux"` vs `"CachyOS"` |
| `resolv.conf` | discard | ours is NetworkManager-generated |
| 4× mirrorlists (`mirrorlist`, `cachyos-*`) | discard | ours are rate-mirrors ranked; vjupdate re-ranks on its own 30-day stamp |
| 2× `tpm2-tss/fapi-profiles/P_*.json` | adopt | stock files never hand-edited; upstream just renamed `TPM2_ALG_ECC`→`ecc` etc. |

Deliberately **not** automated in vjupdate: resolving pacnew is a per-file judgment call and automating it would eventually clobber a customized config. Reporting-only is correct.

**Open item:** limine warns `Detected conflicting config: /boot/EFI/limine/limine.conf` on every kernel upgrade — two configs exist and `/boot/limine.conf` is being ignored in favour of the EFI one. Needs a `sudo diff` of the pair before deleting either; unresolved as of 2026-09-14. See [[project-state]].
