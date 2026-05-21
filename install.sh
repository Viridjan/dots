#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────
# dots/install.sh — fresh-install bootstrap for CachyOS
# Supports: desktop (tower) and surface (Surface Pro 9)
#
# Usage:
#   git clone git@github.com:Viridjan/dots.git ~/dots
#   cd ~/dots && bash install.sh
#
# Safe to re-run on an already-configured machine.
# ─────────────────────────────────────────────────────────
set -euo pipefail

RED='\033[0;31m'; YEL='\033[0;33m'; GRN='\033[0;32m'; BLU='\033[0;34m'; NC='\033[0m'
info()  { echo -e "${BLU}==> $*${NC}"; }
ok()    { echo -e "${GRN} ✓  $*${NC}"; }
warn()  { echo -e "${YEL}[!] $*${NC}"; }
die()   { echo -e "${RED}[✗] $*${NC}" >&2; exit 1; }

DOTS_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# ─── Phase 1: Machine detection ──────────────────────────
detect_machine() {
    local h; h=$(hostname)
    case "$h" in
        desktop) MACHINE="desktop" ;;
        surface) MACHINE="surface" ;;
        *)
            warn "Hostname '$h' is not 'desktop' or 'surface'."
            echo "Set hostname first:  sudo hostnamectl set-hostname desktop"
            echo "                 or: sudo hostnamectl set-hostname surface"
            echo ""
            read -rp "Continue anyway with which profile? [desktop/surface/abort]: " choice
            case "$choice" in
                desktop|surface) MACHINE="$choice" ;;
                *) die "Aborted." ;;
            esac
            ;;
    esac
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
    info "Resetting pacman keyrings..."
    sudo rm -rf /etc/pacman.d/gnupg/
    sudo pacman-key --init
    sudo pacman-key --populate
    sudo pacman-key --recv-keys F3B607488DB35A47 --keyserver keyserver.ubuntu.com
    sudo pacman-key --lsign-key F3B607488DB35A47
    ok "Keyrings reset"
}

# ─── Phase 3: Packages ───────────────────────────────────
_pkg_list() {
    # Read a package list file, stripping comments and blanks
    grep -v '^#' "$1" | grep -v '^$'
}

install_packages() {
    info "Installing common packages..."
    _pkg_list "$DOTS_DIR/.paru-S-common.list" | xargs paru -S --needed --noconfirm

    info "Installing $MACHINE-specific packages..."
    _pkg_list "$DOTS_DIR/.paru-S-${MACHINE}.list" | xargs paru -S --needed --noconfirm

    # Remove unwanted packages (ignore errors — may not be installed)
    if [[ -f "$DOTS_DIR/.paru-R.list" ]]; then
        info "Removing flagged packages..."
        _pkg_list "$DOTS_DIR/.paru-R.list" | xargs paru -R --noconfirm 2>/dev/null || true
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
    fi

    # psd is a user service
    systemctl --user enable --now psd 2>/dev/null && ok "enabled: psd (user)" || warn "skipped (not found): psd"

    ok "Services done"
}

# ─── Phase 7: Claude Code ────────────────────────────────
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
    echo "  9. Maintenance (db lock, cache, orphans):"
    echo "       maint"
    echo ""
    echo -e "${GRN}  Bootstrap complete for: $MACHINE${NC}"
    echo ""
}

# ─── Main ────────────────────────────────────────────────
main() {
    echo ""
    echo -e "${BLU}╔═════════════════════════════════════╗${NC}"
    echo -e "${BLU}║   dots/install.sh — CachyOS setup   ║${NC}"
    echo -e "${BLU}╚═════════════════════════════════════╝${NC}"
    echo ""

    detect_machine
    install_paru
    reset_keyrings
    install_packages
    deploy_dotfiles
    install_flatpaks
    enable_services
    setup_claude
    clone_projects
    print_manual_steps
}

main "$@"
