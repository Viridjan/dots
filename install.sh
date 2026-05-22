#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────
# dots/install.sh — bootstrap + maintenance for CachyOS
# Supports: desktop (tower) and surface (Surface Pro 9)
#
# Usage:
#   bash install.sh              # full bootstrap
#   bash install.sh --update     # system update + maintenance
#   bash install.sh --help
# ─────────────────────────────────────────────────────────
set -euo pipefail

RED='\033[0;31m'; YEL='\033[0;33m'; GRN='\033[0;32m'; BLU='\033[0;34m'; NC='\033[0m'
info()  { echo -e "${BLU}==> $*${NC}"; }
ok()    { echo -e "${GRN} ✓  $*${NC}"; }
warn()  { echo -e "${YEL}[!] $*${NC}"; }
die()   { echo -e "${RED}[✗] $*${NC}" >&2; exit 1; }

DOTS_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
STAMP_DIR="${XDG_STATE_HOME:-$HOME/.local/state}/dots"
mkdir -p "$STAMP_DIR"

# Returns 0 (run it) if stamp is absent or older than 48h, else 1 (skip).
_needs_run() {
    local stamp="$STAMP_DIR/$1"
    [[ ! -f "$stamp" ]] && return 0
    local age=$(( $(date +%s) - $(date -r "$stamp" +%s) ))
    (( age > 172800 ))
}
_mark_done() { touch "$STAMP_DIR/$1"; }

# ─── Phase 1: Machine detection ──────────────────────────
detect_machine() {
    local h; h=$(hostname)
    if [[ "$h" == *desktop* ]]; then
        MACHINE="desktop"
    elif [[ "$h" == *surface* ]]; then
        MACHINE="surface"
    else
        warn "Hostname '$h' contains neither 'desktop' nor 'surface'."
        echo "Set hostname first:  sudo hostnamectl set-hostname desktop"
        echo "                 or: sudo hostnamectl set-hostname surface"
        echo ""
        read -rp "Continue anyway with which profile? [desktop/surface/abort]: " choice
        case "$choice" in
            desktop|surface) MACHINE="$choice" ;;
            *) die "Aborted." ;;
        esac
    fi
    ok "Machine profile: $MACHINE"
}

# ─── Phase 2: Paru ───────────────────────────────────────
install_paru() {
    if command -v paru &>/dev/null; then
        ok "paru already installed"
        return
    fi
    info "Installing paru..."
    sudo pacman -S --needed base-devel git
    local tmp; tmp=$(mktemp -d)
    git clone https://aur.archlinux.org/paru.git "$tmp/paru"
    (cd "$tmp/paru" && makepkg -si --noconfirm)
    rm -rf "$tmp"
    ok "paru installed"
}

# ─── Phase 2b: Keyrings ──────────────────────────────────
reset_keyrings() {
    if ! _needs_run keyrings; then
        ok "Keyrings reset skipped (< 48h ago)"
        return
    fi
    info "Resetting pacman keyrings..."
    sudo rm -rf /etc/pacman.d/gnupg/
    sudo pacman-key --init
    sudo pacman-key --populate
    sudo pacman-key --recv-keys F3B607488DB35A47 --keyserver keyserver.ubuntu.com
    sudo pacman-key --lsign-key F3B607488DB35A47
    if [[ "${MACHINE:-}" == surface ]]; then
        sudo pacman-key --recv-keys 87DEFA4AB94A99A4C8C3112556C464BAAC421453 --keyserver keyserver.ubuntu.com
        sudo pacman-key --lsign-key 87DEFA4AB94A99A4C8C3112556C464BAAC421453
        ok "linux-surface key imported"
    fi
    _mark_done keyrings
    ok "Keyrings reset"
}

# ─── Phase 3: Packages ───────────────────────────────────
_pkg_list() {
    grep -v '^#' "$1" | grep -v '^$'
}

_install_list() {
    local list="$1" to_install=()
    while IFS= read -r pkg; do
        if pacman -Qi "$pkg" &>/dev/null; then
            ok "up to date: $pkg"
        else
            to_install+=("$pkg")
        fi
    done < <(_pkg_list "$list")
    if [[ ${#to_install[@]} -gt 0 ]]; then
        paru -S --needed --noconfirm "${to_install[@]}"
    fi
}

refresh_mirrors() {
    if ! _needs_run mirrors; then
        ok "Mirror refresh skipped (< 48h ago)"
        return
    fi
    info "Refreshing mirrors..."
    sudo cachyos-rate-mirrors 2>/dev/null \
        || sudo rate-mirrors --save /etc/pacman.d/cachyos-mirrorlist cachyos 2>/dev/null \
        || warn "Mirror refresh failed — continuing with existing mirrors"
    sudo pacman -Syy
    _mark_done mirrors
    ok "Mirrors refreshed"
}

install_packages() {
    # Force-remove known conflicting packages before installing.
    # -Rdd skips dep checks so replacements (e.g. wine→wine-cachyos) don't block.
    if [[ -f "$DOTS_DIR/.paru-R.list" ]]; then
        info "Removing flagged packages..."
        while IFS= read -r pkg; do
            local out
            if out=$(sudo pacman -Rdd --noconfirm "$pkg" 2>&1); then
                ok "removed: $pkg"
            elif echo "$out" | grep -q "target not found"; then
                ok "not installed, skipping: $pkg"
            else
                warn "failed to remove: $pkg — $out"
            fi
        done < <(_pkg_list "$DOTS_DIR/.paru-R.list")
    fi

    _do_install() {
        info "Installing common packages..."
        _install_list "$DOTS_DIR/.paru-S-common.list" || return 1
        info "Installing $MACHINE-specific packages..."
        _install_list "$DOTS_DIR/.paru-S-${MACHINE}.list" || return 1
    }

    if ! _do_install; then
        warn "Install failed — forcing mirror refresh and retrying..."
        rm -f "$STAMP_DIR/mirrors"
        refresh_mirrors
        _do_install || die "Package install failed after mirror refresh."
    fi

    ok "Packages done"
}

# ─── Phase 4: Dotfiles ───────────────────────────────────
COMMON_STOW_PKGS=(
    alacritty
    discord
    DankMaterialShell
    fish
    gtk-3.0
    gtk-4.0
    micro
    mimeapps
    niri
    paru
    qt5ct
    qt6ct
    scripts
    VSCodium
)

deploy_dotfiles() {
    info "Deploying dotfiles via stow..."
    cd "$DOTS_DIR"

    # Unstow first to handle moved files (display.kdl, input.kdl)
    for pkg in "${COMMON_STOW_PKGS[@]}"; do
        [[ -d "$pkg" ]] && stow -D "$pkg" 2>/dev/null || true
    done
    stow -D "$MACHINE" 2>/dev/null || true
    stow -D claude 2>/dev/null || true

    # Re-stow common packages
    for pkg in "${COMMON_STOW_PKGS[@]}"; do
        if [[ -d "$pkg" ]]; then
            stow --restow "$pkg"
            ok "stowed: $pkg"
        fi
    done

    # Machine-specific package (display.kdl + input.kdl)
    stow --restow "$MACHINE"
    ok "stowed: $MACHINE (machine-specific)"

    # Claude Code config — use --adopt so existing real files get absorbed into
    # the repo (idempotent on fresh installs, safe on re-runs)
    stow --adopt --restow claude
    ok "stowed: claude"

    # bkg (wallpapers) if it exists
    [[ -d bkg ]] && stow --restow bkg && ok "stowed: bkg"
}

# ─── Phase 5: Flatpaks ───────────────────────────────────
install_flatpaks() {
    if ! command -v flatpak &>/dev/null; then
        warn "flatpak not installed — skipping"
        return
    fi

    info "Adding Flathub remote..."
    flatpak remote-add --if-not-exists flathub https://flathub.org/repo/flathub.flatpakrepo

    info "Installing flatpak apps..."
    while IFS= read -r app; do
        flatpak install -y flathub "$app" || warn "Failed to install flatpak: $app"
    done < <(_pkg_list "$DOTS_DIR/.flatpak-S.list")

    ok "Flatpaks done"
}

# ─── Phase 6: Services ───────────────────────────────────
_enable() {
    # Enable a service, silently skip if unit doesn't exist
    systemctl enable --now "$1" 2>/dev/null && ok "enabled: $1" || warn "skipped (not found): $1"
}

enable_services() {
    info "Enabling common services..."
    _enable NetworkManager
    _enable bluetooth
    _enable cups
    _enable bpftune
    _enable ananicy-cpp
    _enable "dmemcg-booster-system"
    _enable systemd-oomd
    _enable power-profiles-daemon
    _enable "snapper-timeline.timer"
    _enable "snapper-cleanup.timer"
    _enable sddm
    _enable docker

    if [[ "$MACHINE" == surface ]]; then
        info "Enabling Surface-specific services..."
        _enable iptsd
        _enable tlp
        _enable iio-sensor-proxy
        _enable thermald
    fi

    # psd is a user service
    systemctl --user enable --now psd 2>/dev/null && ok "enabled: psd (user)" || warn "skipped (not found): psd"

    ok "Services done"
}

# ─── Phase 7: Snapper ────────────────────────────────────
setup_snapper() {
    info "Configuring snapper..."
    if [[ ! -f /etc/snapper/configs/root ]]; then
        sudo snapper -c root create-config / && ok "snapper: root config created"
    else
        ok "snapper: root config already exists"
    fi
}

# ─── Phase 8: Claude Code ────────────────────────────────
setup_claude() {
    if ! command -v claude &>/dev/null; then
        warn "claude-code not in PATH — skipping plugin setup"
        return
    fi

    info "Setting up Claude Code plugins..."
    # settings.json is already stowed and sets enabledPlugins.
    # These commands install the plugin assets (skills, hook scripts).
    claude plugin add github:JuliusBrussee/caveman --scope user --yes 2>/dev/null \
        && ok "plugin: caveman" \
        || warn "caveman plugin install failed — run manually: claude plugin add github:JuliusBrussee/caveman"

    claude plugin add superpowers@claude-plugins-official --scope user --yes 2>/dev/null \
        && ok "plugin: superpowers" \
        || warn "superpowers plugin install failed — run manually: claude plugin add superpowers@claude-plugins-official"
}

# ─── Phase 8: Projects ───────────────────────────────────
clone_projects() {
    local list="$DOTS_DIR/projects.list"
    [[ -f "$list" ]] || { warn "projects.list not found — skipping"; return; }

    info "Cloning projects into ~/Projects/..."
    mkdir -p "$HOME/Projects"
    while IFS= read -r repo; do
        [[ -z "$repo" || "$repo" == \#* ]] && continue
        local name; name=$(basename "$repo" .git)
        if [[ -d "$HOME/Projects/$name" ]]; then
            ok "already exists: $name"
        else
            git clone "$repo" "$HOME/Projects/$name" && ok "cloned: $name" || warn "failed: $repo"
        fi
    done < "$list"
}

# ─── Maintenance: swap broken packages ───────────────────
_swap_pkg() {
    local old="$1" new="$2"
    if pacman -Qi "$old" &>/dev/null; then
        info "Swapping $old → $new..."
        sudo pacman -Rdd --noconfirm "$old" 2>/dev/null || true
        paru -S --needed --noconfirm "$new"
        ok "swapped: $old → $new"
    fi
}

# ─── Maintenance: system update ──────────────────────────
system_update() {
    info "Swapping known broken/replaced packages..."
    _swap_pkg spotify            spotify-launcher
    _swap_pkg libreoffice-fresh  libreoffice-still

    refresh_mirrors

    info "Updating all packages..."
    paru -Syuu --noconfirm
    ok "System up to date"
}

# ─── Maintenance: cache cleanup ──────────────────────────
clean_caches() {
    info "Cleaning package caches..."
    sudo paccache -rk2
    sudo paccache -ruk0
    rm -rf "$HOME/.cache/paru/clone"
    ok "Caches cleaned"
}

# ─── Maintenance: orphan removal ─────────────────────────
remove_orphans() {
    info "Checking for orphaned packages..."
    local orphans
    orphans=$(paru -Qdtq 2>/dev/null || true)
    if [[ -z "$orphans" ]]; then
        ok "No orphans found"
        return
    fi
    echo "$orphans"
    read -rp "Remove the above orphans? [y/N]: " confirm
    [[ "$confirm" =~ ^[Yy]$ ]] || { warn "Skipped"; return; }
    echo "$orphans" | sudo pacman -Rns -
    ok "Orphans removed"
}

# ─── Maintenance: rebuild check ──────────────────────────
check_rebuilds() {
    if ! command -v checkrebuild &>/dev/null; then
        warn "checkrebuild not found — install rebuild-detector"
        return
    fi
    info "Checking for packages needing rebuild..."
    local out
    out=$(checkrebuild 2>/dev/null || true)
    if [[ -z "$out" ]]; then
        ok "No rebuilds needed"
    else
        warn "Packages needing rebuild:"
        echo "$out"
    fi
}

# ─── Maintenance: pacnew files ───────────────────────────
check_pacnew() {
    info "Checking for pacnew files..."
    if command -v pacdiff &>/dev/null; then
        pacdiff -o || true
    else
        warn "pacdiff not found — install pacman-contrib"
    fi
}

# ─── Maintenance: firmware updates ───────────────────────
check_firmware() {
    if ! command -v fwupdmgr &>/dev/null; then
        warn "fwupdmgr not found — install fwupd"
        return
    fi
    info "Checking firmware updates..."
    fwupdmgr refresh --force 2>/dev/null || true
    fwupdmgr get-updates 2>/dev/null || ok "No firmware updates available"
}

# ─── Phase 9: Summary ────────────────────────────────────
print_manual_steps() {
    echo ""
    echo -e "${YEL}════════════════════════════════════════════${NC}"
    echo -e "${YEL}  Manual steps required after this script   ${NC}"
    echo -e "${YEL}════════════════════════════════════════════${NC}"
    echo ""
    echo "  1. Git identity:"
    echo "       git config --global user.name 'Viridjan'"
    echo "       git config --global user.email 'viridjan@users.noreply.github.com'"
    echo ""
    echo "  2. SSH key:"
    echo "       ssh-keygen -t ed25519 -C viridjan"
    echo "       # Add ~/.ssh/id_ed25519.pub to GitHub"
    echo ""
    echo "  3. Fingerprint (if fprintd is installed):"
    echo "       fprintd-enroll"
    echo ""
    echo "  4. DankMaterialShell init (required before starting niri):"
    echo "       dms setup"
    echo "       # This generates ~/.config/niri/dms/*.kdl"
    echo "       # Without it niri will fail to start (missing dms includes)"
    echo ""
    echo "  5. Bitwarden: log in via the app or browser extension"
    echo ""
    echo "  6. YubiKey: set PIN if not already configured"
    echo "       ykman fido access change-pin"
    echo ""
    if [[ "${MACHINE:-}" == surface ]]; then
        echo "  7. Surface Secure Boot:"
        echo "       # Enroll linux-surface MOK key to allow the kernel to boot"
        echo "       # Follow: https://github.com/linux-surface/linux-surface/wiki/Installation-and-Setup"
        echo ""
    fi
    echo "  8. Open Notebook (if needed):"
    echo "       cd ~/Projects/Open_notebook && docker compose up -d"
    echo ""
    echo "  9. Maintenance (update, cache, orphans):"
    echo "       bash ~/Projects/dots/install.sh --update"
    echo ""
    echo -e "${GRN}  Bootstrap complete for: $MACHINE${NC}"
    echo ""
}

# ─── Main ────────────────────────────────────────────────
bootstrap() {
    echo ""
    echo -e "${BLU}╔═════════════════════════════════════╗${NC}"
    echo -e "${BLU}║   dots/install.sh — CachyOS setup   ║${NC}"
    echo -e "${BLU}╚═════════════════════════════════════╝${NC}"
    echo ""

    detect_machine
    install_paru
    reset_keyrings
    refresh_mirrors
    install_packages
    deploy_dotfiles
    install_flatpaks
    enable_services
    setup_snapper
    setup_claude
    clone_projects
    print_manual_steps
}

maintenance() {
    echo ""
    echo -e "${BLU}╔═════════════════════════════════════╗${NC}"
    echo -e "${BLU}║   dots/install.sh — maintenance     ║${NC}"
    echo -e "${BLU}╚═════════════════════════════════════╝${NC}"
    echo ""

    system_update
    clean_caches
    remove_orphans
    check_rebuilds
    check_pacnew
    check_firmware
}

usage() {
    echo "Usage: bash install.sh [--update | --help]"
    echo ""
    echo "  (no args)   Full bootstrap: packages, dotfiles, services"
    echo "  --update    Maintenance: update, clean caches, orphans, rebuilds"
    echo "  --help      Show this message"
}

case "${1:-}" in
    --update|-u) maintenance ;;
    --help|-h)   usage ;;
    "")          bootstrap ;;
    *)           die "Unknown option: $1. Use --help." ;;
esac
