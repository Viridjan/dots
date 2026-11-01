# Fix the failures from the 2026-11-01 Surface vjupdate run

## Context
The `vjupdate` run on vjsurface (`~/.local/state/dots/vjupdate.log`) aborted the
configure phase and failed 14 items. The causes are listed below. Some are
repository bugs and some only need a manual step.

| Failure | Cause | Fix type |
|---|---|---|
| docker | upgrade removed the running kernel's modules (7.3.0-4 gone) → iptables nat missing | reboot only |
| VM setup aborts the phase | `setup_vms` runs without the `windows-vm` feature; `/mnt/data` missing | code |
| tlp | `power-profiles-daemon.service` has `Conflicts=tlp.service` | list (user chose ppd) |
| iptsd | only the template `iptsd@.service` exists | list |
| limine-snapper-sync | the Surface boots via GRUB; unit not installed there | list |
| greeter install/sync | installed `greetd-dms-greeter-git` is the old wrapper; DMS says to use `greetd-dms-greeter-bin` | package swap |
| mpd, vjupdate-check.timer | dotfiles phase not selected → `~/.config/mpd` and the systemd-user units are not linked | run only |
| 5 Codex skills | the installer runs right after Codex installs, before Codex unpacks `~/.codex/skills/.system/` (the script exists now) | rerun only |

## Code/list changes

1. **Gate VM setup on the feature** — `scripts/.local/bin/vjupdate` `setup_vms` (~line 1773):
   add `_has_feature windows-vm || { warn "no windows-vm feature — skipping VM setup"; return 0; }`
   at the top, following the `setup_nvidia_niri` pattern (~1465). In `vj/state.py`, extend
   `ONCE_FEATURE` with `"vms": "windows-vm"` so vj hides the item on Surface/plancia.
   Edit vjupdate through a temp file plus `mv` (CLAUDE.md: never edit it in place while it runs).

2. **Power daemon on Surface** — `profiles/surface.toml`: drop `"tlp"`, `"tlp-rdw"` from
   `[paru].install` and `"tlp"` from `[systemd].enable`. Add `tlp`, `tlp-rdw` to shared
   `packages.toml` `[paru].remove` so the installed ones go away. `enable_services` already
   disables the unlisted tlp because the unit is tracked in `managed-units`.

3. **iptsd** — `profiles/surface.toml` `[systemd].enable`: remove `"iptsd"`. The template is
   started by udev per device (`iptsd@<dev>`), so it doesn't need enabling. I'll check this
   after the reboot with `systemctl list-units 'iptsd@*'`. If no instance is running, enable
   `iptsd@` for the touchscreen's actual device name.

4. **limine-snapper-sync** — move `"limine-snapper-sync.service"` out of shared
   `packages.toml` `[systemd].enable` into `profiles/desktop.toml` and
   `profiles/plancia.toml` `[systemd].enable`. Plancia has no `[systemd]` section, so add
   one. I'll confirm limine is installed on those machines before committing. Profiles can
   only add units to the shared list, not remove them, so per-profile placement is the
   only option.

5. **Greeter package swap** — `packages.toml`: replace `"greetd-dms-greeter-git"` with
   `"greetd-dms-greeter-bin"` and add `greetd-dms-greeter-git` to `[paru].remove`, as
   CLAUDE.md requires for twin swaps. First check that `-bin` isn't on the malware
   blocklist (`~/.local/share/aur-malware-check/data/campaigns/*/packages*.txt`). After it
   installs, run `dms-greeter --help`. If `install`/`sync` exist, `setup_greeter` stays
   unchanged. If they're named differently (the README mentions `dms greeter enable/sync`),
   update the two commands in `setup_greeter` (~line 1432) to match.

6. **Codex skills** — no change. The installer script exists now, so a rerun works.

## Tests
- `tests/test_vjupdate.py`: add one test in the style of the `nvidia-niri` feature
  tests (~line 1312). Run `setup_vms` with `VJ_FEATURES="linux-surface"` and assert no
  failure and no `mkdir` of `/mnt/data`.
- `tests/test_vj.py` (~line 291): add an assert that `vms` is hidden without
  `windows-vm` and shown with it.

## Manual steps (on the Surface, in order)
1. Reboot (new kernel; fixes docker, and probably the tlp kill side effect).
2. `git pull`, then `vj` → run Install (swaps the greeter and removes tlp), Dotfiles (links
   mpd and the systemd-user timer), then Services, Greeter, and Install scripts.

## Verification
- `python3 -B -m unittest discover -s tests -v`, `bash -n` + `shellcheck -S warning` on vjupdate.
- `python3 -B -m vj plan /tmp/p` on the Surface: `systemd-enable.list` has no tlp, iptsd, or
  limine-snapper-sync.
- After the reboot and the run, check the recap: no service, greeter, VM, or installer failures.
  `systemctl is-active docker power-profiles-daemon`, `systemctl --user is-active mpd vjupdate-check.timer`,
  `ls ~/.codex/skills`.
