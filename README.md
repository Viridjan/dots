# dots

GNU Stow dotfiles for CachyOS + niri.

## Initial setup on a new device

```bash
ssh-keygen -t ed25519 -C "viridjan@users.noreply.github.com"
# add the public key to GitHub, then:
git clone git@github.com:Viridjan/dots.git ~/dots
cd ~/dots
stow */
```

`stow */` symlinks all packages at once. Each package maps to `$HOME`:
`dots/fish/.config/fish/` → `~/.config/fish/`

---

## Stow operations

### Add a new config package (app not yet tracked)

```bash
# 1. Create the package structure
mkdir -p ~/dots/<pkg>/.config/<pkg>

# 2. Copy the live config into the package
cp -r ~/.config/<pkg>/. ~/dots/<pkg>/.config/<pkg>/

# 3. Remove the real directory so stow can create a clean symlink
rm -rf ~/.config/<pkg>

# 4. Stow it
cd ~/dots && stow <pkg>
```

Result: `~/.config/<pkg>` becomes a directory-level symlink to `~/dots/<pkg>/.config/<pkg>`.
Any file the app writes inside it will land directly in the repo.

### Add files to an existing package (e.g. a new subdir)

```bash
# 1. Copy the new files/dir into the existing package
cp -r ~/.config/niri/dms ~/dots/niri/.config/niri/dms

# 2. Remove the real copy
rm -rf ~/.config/niri/dms

# 3. Restow the package to pick up the new entries
cd ~/dots && stow --restow niri
```

### Sync changes back to the repo (after an app auto-updates its config)

Nothing to do — because the configs are symlinks into `~/dots`, any write
by an app goes directly into the repo. Just `git add` and commit.

### Remove a package from stow (stop tracking it)

```bash
cd ~/dots && stow -D <pkg>   # removes symlinks, leaves real files in ~/dots
rm -rf ~/dots/<pkg>          # optionally delete from repo too
```

### Verify symlinks are healthy

```bash
# Check that all managed dirs are symlinks, not real directories
ls -la ~/.config/ | grep '^l'

# Re-apply all packages (safe to run repeatedly; won't overwrite existing symlinks)
cd ~/dots && stow */
```

---

## Current packages

| Package | Config location |
|---|---|
| `niri` | `~/.config/niri/` (cfg/ and dms/ subdirs, individual file symlinks) |
| `fish` | `~/.config/fish/` |
| `ghostty` | `~/.config/ghostty/` |
| `DankMaterialShell` | `~/.config/DankMaterialShell/` |
| `cava` | `~/.config/cava/` |
| `gtk-3.0` | `~/.config/gtk-3.0/` |
| `gtk-4.0` | `~/.config/gtk-4.0/` |
| `Kvantum` | `~/.config/Kvantum/` |
| `qt5ct` | `~/.config/qt5ct/` |
| `qt6ct` | `~/.config/qt6ct/` |
| `rofi` | `~/.config/rofi/` |
| `waybar` | `~/.config/waybar/` |
| `micro` | `~/.config/micro/` |
| `discord` | `~/.config/discord/settings.json` (file-level symlink) |
| `mimeapps` | `~/.config/mimeapps.list` |
| `bkg` | `~/Pictures/Wallpapers/` |

**Note:** `niri` uses file-level symlinks (the cfg/ and dms/ dirs are real,
individual `.kdl` files are symlinked). All other packages use directory-level
symlinks.

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
