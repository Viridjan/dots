# TODO

- [ ] Switch `vectorcraft-bin` to Flathub once `ai.storyteller.vectorcraft` is published (pacman > flatpak > AUR; Flatpak adds a sandbox).
- [ ] Once desktop and Surface both run the `*craft-bin` packages (`pacman -Q vectorcraft-bin`), delete the 9 source `*craft` names from `packages.toml` [paru].remove (2026-10-25 swap).
- [ ] Surface: no Ollama (decided 2026-11-10; profile has no `ollama-model`). If `pacman -Qs ollama` lists anything installed by hand: `sudo pacman -Rns <pkg>` and `rm -rf ~/.ollama`.
- [ ] Surface/Plancia: Dux Calendar replaces Thunderbird's calendar (2026-11-10). After `sysup --actions install,stow-symlinks,services`:
      `dcal account add google` (browser sign-in), confirm `dcal account list` shows `ok`, then add the Thunderbird `user.js` from README "Calendar" (calendars + alarms off). Confirm `xdg-mime query default text/calendar` = `dev.duxlabs.calendar.desktop`.
- [ ] Make MailCraft (`mailcraft-bin`, `io.github.billsecond.mailcraft.desktop`) the default mail app: `x-scheme-handler/mailto` in `mimeapps`, Mod+Alt+M bind in `dms/binds.kdl`, Thunderbird in desktop `autostart-machine.kdl`.


## Desktop: suspend powers the PC off (since ~2026-11-10)

Every logged suspend ends at `PM: suspend entry (deep)` with no resume; next start is a cold boot
showing a white screen with three dots. ASRock H670M-ITX/ax BIOS 17.03, RX 6700 XT. Suspects:
linux-cachyos 7.3.3 (11-08), systemd 262.2 (11-10), mesa 26.2.6 (11-06). One test per suspend:

- [x] Suspend test 1 (2026-11-28): `linux-cachyos-lts` 6.18.65, deep → powered off too. Not a 7.3.x
  regression. The log stops at `Starting System Suspend...` (rest never flushed).
- [ ] Suspend test 4: find the stage that kills it with `pm_test` (no real sleep; each level returns after 5 s):
  `echo devices | sudo tee /sys/power/pm_test; systemctl suspend`, then `platform`, `processors`, `core`.
  The first level that powers off is the culprit (devices = a driver, likely amdgpu; platform/core = BIOS/ACPI).
  `echo none | sudo tee /sys/power/pm_test` afterwards.
  Result 2026-11-28 (LTS 6.18.65, level `devices`): the system came back, the GPU didn't. Same
  `RunDcBtc failed!` / `resume of IP block <smu> failed -62`, then `GPU mode1 reset failed`. The fault
  is in amdgpu suspend/resume (RX 6700 XT SMU), on both kernels, before BIOS/ACPI sleep is reached.
  Shared by both kernels: `linux-firmware-amdgpu 20261019` (since 2026-10-24), mesa, BIOS.
  Suspend last worked ~2026-09. cachyos-settings 1.4.1→1.4.4 (11-08..10) checked: no amdgpu/sleep files.
- [ ] Suspend test A: `echo auto | sudo tee /sys/class/drm/card1/device/power_dpm_force_performance_level`
  (udev rule `99-amdgpu-performance.rules` forces `high`), then `pm_test devices` + `systemctl suspend`.
- [ ] Suspend test B (if A fails): boot once with `linux-firmware-amdgpu 20260916` (prime suspect, 10-24 update).
- [ ] Check ASRock for a BIOS newer than 17.03 for H670M-ITX/ax.
- [x] Suspend test 2 (2026-11-28, 7.3.6-3): s2idle failed differently. The system woke after 20 s,
  but the GPU did not: `amdgpu: RunDcBtc failed!` / `Failed to setup smc hw!` / `resume of IP block <smu> failed -62`,
  then sdma ring timeouts, device wedged, black screen. So the RX 6700 XT's SMU fails on resume;
  not S3-only. Firmware unchanged since 2026-10-24 (`linux-firmware-amdgpu 20261019`) → test 1 next.
- [ ] Suspend test 3: while suspended, are fans + power LED fully off (PSU/firmware) or on with a black screen (resume hang)?
- [ ] White boot screen: note whether it appears before or after the ASRock logo. If all tests fail: suspect PSU, CMOS battery, BIOS update.

## sysup rename (2026-11-08) — Surface and Plancia, once each

After `git pull` the old `vjupdate` and `vj` links in `~/.local/bin` point at
deleted files. Run by full path once:

```bash
~/Projects/dots/scripts/.local/bin/sysup --actions stow-symlinks,services
```

- [ ] Surface: run the command above. It links `sysup`, prunes the dead links,
      moves `~/.config/vjupdate/config.toml` to `~/.config/sysup/config.toml`, and the
      services action swaps `vjupdate-check.timer` for `sysup-check.timer`.
      Confirm: `sysup --status` shows profile `surface` and the old one-time dates;
      `systemctl --user list-timers | grep sysup-check`.
- [ ] Plancia: same command and checks (profile `plancia`).
- [ ] Both: `pacman -Q python-textual` — no longer listed; remove with
      `sudo pacman -Rns python-textual` if nothing else needs it.

## Italian spell check (2026-11-10) — Surface and Plancia, once each

- [ ] `sysup --actions install` (installs `hunspell-it`, `hunspell-en_gb`, `hunspell-en_us`).
- [ ] Joplin: add `"it"` to `spellChecker.languages` in `~/.config/joplin-desktop/settings.json` (Joplin closed).
- [ ] Whatsie: append `[spellcheck]` / `enabled=true` / `languages=en_GB, it_IT` to
      `~/.config/org.keshavnrj.ubuntu/WhatSie.conf` (Whatsie closed).
- [ ] Telegram: Settings → Advanced → Spell checker → Manage dictionaries → Italiano.

No Flatpak: `alacritty` (terminal sandboxing issues), `shelly`.

## 2026-11-24 changes — Surface and Plancia, once each

- [ ] `sysup --actions install`: swaps `dsearch-bin` (gone from the AUR) for `dux-search-bin`; next
      `--update` generates `it_IT.UTF-8` if missing (the `setlocale: LC_TIME` warning on the Surface).
- [ ] `sysup --actions stow-symlinks,dms-import`, then log out/in: `launcher-ws` binds + watcher.
- [ ] Ctrl+N in Brave opens a focused window; PiP opens floating.
- [ ] Security (2026-11-24): `sysup --actions install,services,optimize,stow-symlinks` (OpenSnitch, arch-audit,
      lynis, ClamAV + freshclam timer, /etc hardening), log out/in for the OpenSnitch UI, then
      `sysup --actions lynis` once.
- [ ] Open Notebook removed 2026-11-24 (SurrealDB root/root was LAN-reachable past ufw). Surface/Plancia, if present:
      `cd ~/Projects/open_notebook && docker compose down --rmi all; cd ~ && sudo rm -rf ~/Projects/open_notebook`.
- [ ] Craft Anything is desktop-only since 2026-11-24. Surface/Plancia: `flatpak uninstall ai.storyteller.craft-anything`.

## Wifi passwords via Bitwarden (2026-11-27)
- [ ] This machine (has the networks): `sysup --actions install` (bitwarden-cli), `bw login` once, then `sysup --actions wifi-export`.
- [ ] Other machines: `sysup --actions install`, `bw login` once, then `sysup --actions wifi-import`; check `nmcli connection show`.

## CachyOS 2026-11 release (2026-11-27)
- [ ] Every machine: `sysup --update`, then `sudo chwd -a -f` (cachyos-drm-awaiter replaces early KMS; drops the
      `kms` mkinitcpio hook), reboot. Desktop: check the new cachyos-recovery entry in the boot menu.
- [ ] One sudo password per run: on the run after the first `--update` with this change, the prompt asks for the
      password only (no swipe); afterwards `bash -c 'sudo ls /etc/sudoers.d/'` lists no `zz-sysup-run`.
