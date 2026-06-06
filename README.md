# dots

GNU Stow dotfiles for CachyOS + niri.
Supports two machines: **desktop** (tower, RX 6700 XT) and **surface** (Surface Pro 9).

---

## Fresh install

### 1. Set hostname

```bash
sudo hostnamectl set-hostname desktop   # or: surface
```

### 2. SSH key → GitHub

```bash
ssh-keygen -t ed25519 -C "viridjan"
cat ~/.ssh/id_ed25519.pub   # add this to github.com/settings/keys
```

### 3. Clone and run the bootstrap script

```bash
git clone git@github.com:Viridjan/dots.git ~/Projects/dots
cd ~/Projects/dots && bash scripts/.local/bin/vjupdate
```

`vjupdate` does everything:
- installs common + machine-specific packages via paru
- deploys all dotfiles via stow (machine profile auto-detected from hostname)
- installs flatpak emulators
- enables systemd services
- sets up Claude Code plugins

### 4. Manual steps (after the script)

```bash
# Git identity
git config --global user.name 'Viridjan'
git config --global user.email 'viridjan@users.noreply.github.com'

# Fingerprint enrollment
fprintd-enroll

# DankMaterialShell — required before starting niri
# generates ~/.config/niri/dms/*.kdl (niri won't start without them)
dms setup

# YubiKey FIDO2 PIN — set/change the PIN on the hardware key
# ykman is the YubiKey Manager CLI (package: yubikey-manager)
# The FIDO2 PIN protects resident keys and passkeys stored on the YubiKey
ykman fido access change-pin

# Bitwarden — log in to unlock vault and browser extension
# Launch from app menu or: flatpak run com.bitwarden.desktop

# Open Notebook (if needed)
cd ~/Projects/Open_notebook && docker compose up -d

# Windows VM — desktop only (web UI: http://localhost:8006, RDP: localhost:3389)
cd ~/Projects/dots/windows && docker compose up -d
# Shared folder: ~/Shared on host → \\host.lan\Data inside Windows (map as network drive)
```

**Surface only:**
- Enroll the linux-surface Secure Boot MOK key so the kernel boots with Secure Boot on
- Follow: https://github.com/linux-surface/linux-surface/wiki/Installation-and-Setup

---

## Claude Code

Always open Claude Code from `~/Projects`, not from `~/Projects/dots`:

```bash
cd ~/Projects && claude
```

Memory and project context are scoped to the working directory at launch.
Opening from `~/Projects/dots` creates a separate scope — prior conversation context
and memory won't load.

When working on dots inside a Claude session, just `cd ~/Projects/dots` from within it.

---

## Re-applying dotfiles (existing machine)

After pulling new changes from this repo:

```bash
cd ~/Projects/dots
stow --restow -t ~ alacritty DankMaterialShell fish gtk-3.0 gtk-4.0 \
     micro mimeapps paru qt5ct qt6ct vesktop VSCodium scripts
stow --adopt --restow -t ~ claude   # --adopt absorbs existing real files
stow --restow -t ~ desktop          # or: surface
# niri is NOT stowed — it uses file-level symlinks (DMS owns ~/.config/niri/).
# Re-run vjupdate to refresh them.
```

`-t ~` is required: the repo lives at `~/Projects/dots`, so stow's default target
(the parent dir) would be `~/Projects`, not `~`. Always pass `-t ~`.

Or just re-run `bash scripts/.local/bin/vjupdate` — it's idempotent.

---

## Stow operations

### Add a new config package (app not yet tracked)

```bash
# 1. Create the package structure
mkdir -p ~/Projects/dots/<pkg>/.config/<pkg>

# 2. Copy the live config into the package
cp -r ~/.config/<pkg>/. ~/Projects/dots/<pkg>/.config/<pkg>/

# 3. Remove the real directory so stow can create a clean symlink
rm -rf ~/.config/<pkg>

# 4. Stow it
cd ~/Projects/dots && stow -t ~ <pkg>
```

Result: `~/.config/<pkg>` becomes a directory-level symlink to `~/Projects/dots/<pkg>/.config/<pkg>`.
Any file the app writes inside it will land directly in the repo.

### Add files to an existing package (e.g. a new subdir)

```bash
# 1. Copy the new files/dir into the existing package
cp -r ~/.config/<pkg>/<subdir> ~/Projects/dots/<pkg>/.config/<pkg>/<subdir>

# 2. Remove the real copy
rm -rf ~/.config/<pkg>/<subdir>

# 3. Restow the package to pick up the new entries
cd ~/Projects/dots && stow --restow -t ~ <pkg>
```

(`niri` is the exception — its `dms/` dir is owned by DMS and is not stowed.)

### Sync changes back to the repo (after an app auto-updates its config)

Nothing to do — because the configs are symlinks into `~/Projects/dots`, any write
by an app goes directly into the repo. Just `git add` and commit.

### Remove a package from stow (stop tracking it)

```bash
cd ~/Projects/dots && stow -D -t ~ <pkg>   # removes symlinks, leaves real files in ~/Projects/dots
rm -rf ~/Projects/dots/<pkg>          # optionally delete from repo too
```

### Verify symlinks are healthy

```bash
# Check that all managed dirs are symlinks, not real directories
ls -la ~/.config/ | grep '^l'

# Re-apply all packages (safe to run repeatedly; won't overwrite existing symlinks).
# Use vjupdate, not `stow */` — the latter would fold ~/.config/niri into a
# symlink and break DMS, and would target ~/Projects instead of ~.
bash scripts/.local/bin/vjupdate
```

---

## Packages

| Package | What it stows |
|---|---|
| `niri` | `~/.config/niri/` — common kdl files (cfg/ minus display+input) |
| `desktop` | `~/.config/niri/cfg/display.kdl` + `input.kdl` + `surface-layout.kdl` (empty) for the tower |
| `surface` | `~/.config/niri/cfg/display.kdl` + `input.kdl` + `surface-layout.kdl` (50% default window width) for Surface Pro 9 |
| `fish` | `~/.config/fish/` |
| `alacritty` | `~/.config/alacritty/` |
| `micro` | `~/.config/micro/` |
| `VSCodium` | `~/.config/VSCodium/` |
| `DankMaterialShell` | `~/.config/DankMaterialShell/` |
| `gtk-3.0` | `~/.config/gtk-3.0/` |
| `gtk-4.0` | `~/.config/gtk-4.0/` |
| `qt5ct` | `~/.config/qt5ct/` |
| `qt6ct` | `~/.config/qt6ct/` |
| `vesktop` | `~/.config/vesktop/` — settings.json + settings/ (Vencord config + quickCss) |
| `mimeapps` | `~/.config/mimeapps.list` |
| `paru` | `~/.config/paru/paru.conf` |
| `claude` | `~/.claude/settings.json` + `hooks/` (Claude Code + caveman plugin) |
| `scripts` | `~/.local/bin/vjupdate` — bootstrap + maintenance script |

**niri note:** `cfg/display.kdl`, `cfg/input.kdl`, and `cfg/surface-layout.kdl` are NOT in the `niri` package —
they come from `desktop/` or `surface/` depending on the machine.
The `dms/` directory is auto-generated by `dms setup` and not tracked.

---

## Gaming

Games open tiled by default. To force fullscreen via gamescope when a game doesn't handle it natively, set this in Steam → right-click game → Properties → Launch Options:

**Desktop (3440×1440 @ 165Hz):**
```
gamescope -f -W 3440 -H 1440 -r 165 -- %command%
```
Upscale from 1080p if game lacks ultrawide support:
```
gamescope -f -W 3440 -H 1440 -w 1920 -h 1080 -r 165 -- %command%
```

**Surface Pro 9 (2880×1920 @ 60Hz):**
```
gamescope -f -W 2880 -H 1920 -r 60 -- %command%
```

### VR — Pico 4 Ultra (desktop only)

Wireless PC VR via ALVR (`alvr-launcher-bin` in `.paru-S-desktop.list`).

One-time setup:
1. Enable developer mode on headset: Settings → General → About device → tap Software version 7×
2. Enable USB debugging in Developer options
3. Download ALVR client APK from [github.com/alvr-org/ALVR/releases](https://github.com/alvr-org/ALVR/releases) — match version to server
4. Sideload: `adb install alvr_client_android.apk`
5. Open ALVR app on headset → connect to server IP shown in ALVR dashboard
6. Launch SteamVR from ALVR dashboard

Both devices must be on the same WiFi network (WiFi 6 recommended).

---

## Btrfs snapshots

Handled automatically by `vjupdate`:

| Component | Role |
|---|---|
| `snapper` | Core snapshot tool — creates/manages/prunes btrfs snapshots |
| `snap-pac` | Pacman hooks — auto-snapshots root before/after every package operation |
| `btrfs-assistant` | GUI for browsing and restoring snapshots |
| `snapper-timeline.timer` | Systemd timer — takes periodic timeline snapshots |
| `snapper-cleanup.timer` | Systemd timer — prunes old snapshots per retention config |

`vjupdate` creates the snapper root config (`snapper -c root create-config /`) on first run and enables both timers.

To browse and restore snapshots:

```bash
btrfs-assistant         # GUI
snapper -c root list    # CLI list
snapper -c root diff <N> <M>   # diff between snapshots N and M
```

To restore a file from a snapshot:

```bash
# Snapshots live at /.snapshots/<N>/snapshot/
cp /.snapshots/<N>/snapshot/path/to/file ~/restored-file
```

---

## System optimisations (CachyOS / Arch)

Run these checks and apply what's relevant on each new install.

### 1. CPU governor

```bash
cat /sys/devices/system/cpu/cpu0/cpufreq/scaling_governor
# Should be 'performance' on a desktop. If 'powersave':
```

Edit `/etc/default/cpupower-service.conf`, uncomment:
```
GOVERNOR='performance'
```
Then:
```bash
sudo systemctl restart cpupower.service
sudo cpupower frequency-set -g performance
powerprofilesctl set performance   # if power-profiles-daemon is running
```

### 2. Disable NetworkManager-wait-online

Delays boot by waiting for full network. Not needed on desktop.

```bash
sudo systemctl disable NetworkManager-wait-online.service
```

### 3. Mask lvm2-monitor if no LVM

```bash
lsblk   # check for any lvm2 volumes
sudo systemctl mask lvm2-monitor.service
```

### 4. cachyos-rate-mirrors — delay post-boot run

The timer fires 10 min after every boot by default. Override to 2h:

```bash
sudo mkdir -p /etc/systemd/system/cachyos-rate-mirrors.timer.d
sudo tee /etc/systemd/system/cachyos-rate-mirrors.timer.d/override.conf << 'EOF'
[Timer]
OnBootSec=2h
EOF
sudo systemctl daemon-reload
```

### 5. AMD GPU performance level

```bash
cat /sys/class/drm/card*/device/power_dpm_force_performance_level
# If 'auto', create a persistent udev rule:
sudo tee /etc/udev/rules.d/99-amdgpu-performance.rules << 'EOF'
ACTION=="add", SUBSYSTEM=="pci", ATTR{vendor}=="0x1002", ATTR{class}=="0x030000", ATTR{power_dpm_force_performance_level}="high"
EOF
sudo udevadm control --reload-rules && sudo udevadm trigger
```

### 6. fstab — add noatime to non-btrfs mounts

btrfs mounts should already have `noatime` from the CachyOS installer.
Check any ext4 or other mounts:

```bash
grep -v noatime /etc/fstab | grep -v '^#' | grep -v tmpfs
# Add noatime to any data drives (e.g. defaults,noatime,nofail)
```

### 7. EFI boot entry cleanup

Duplicate entries from reinstalls slow firmware POST time.

```bash
efibootmgr   # review the list
# Keep: current boot entry, actual bootloader (Limine/systemd-boot), hard drive fallback
# Remove duplicates:
sudo efibootmgr -b <XXXX> -B   # repeat for each duplicate
```

### 8. Disable greetd greeter (autologin)

Edit `/etc/greetd/config.toml`:

```toml
[default_session]
user = "viridjan"
command = "niri-session"
```
