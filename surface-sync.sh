#!/usr/bin/env bash
# One-time catch-up for a machine whose dots clone predates 2026-09-25
# (the Surface). Safe to re-run: every step checks whether it is still needed.
#
#   1. migrate ~/.local/bin from a folded stow link into a real directory
#      (must happen BEFORE the checkout changes, or the tracked installer
#      links disappear from PATH);
#   2. bring the checkout to origin/main with `reset --hard` — this also covers
#      the 2026-08-15 history rewrite, after which a plain pull cannot work;
#   3. relink dotfiles from the 2026-10-21 layout (dotsets/viridjan/): drop
#      links into the old <repo>/<pkg>/ paths, write the vj config
#      (profile = this machine), run `vjupdate --actions stow-symlinks`
#      (asks for sudo for the /etc packages), validate niri.
#
# Nothing is lost: local commits get a backup branch, uncommitted work is
# stashed. Run from a copy outside the repo, since step 2 rewrites the repo:
#   cd ~/Projects/dots && git fetch origin &&
#   git show origin/main:surface-sync.sh > /tmp/surface-sync.sh && bash /tmp/surface-sync.sh
#
# Options: -y  answer yes to every prompt.
# Delete this file from the repo once every machine has run it.
set -euo pipefail

DOTS="${DOTS:-$HOME/Projects/dots}"
BIN="$HOME/.local/bin"
KEEP=" vjupdate vj start-windows start-open-notebook start-keep "
YES=false
[[ "${1:-}" == -y ]] && YES=true

LOG_DIR="${XDG_STATE_HOME:-$HOME/.local/state}/dots"
mkdir -p "$LOG_DIR"
LOG="$LOG_DIR/surface-sync-$(date +%Y%m%d-%H%M%S).log"
exec > >(tee -a "$LOG") 2>&1

step() { printf '\n\033[1;34m==> %s\033[0m\n' "$*"; }
ok()   { printf '\033[0;32m    ok: %s\033[0m\n' "$*"; }
warn() { printf '\033[0;33m    warn: %s\033[0m\n' "$*"; }
die()  { printf '\033[0;31m    ABORT: %s\033[0m\n    log: %s\n' "$*" "$LOG"; exit 1; }
ask()  {
    $YES && { echo "    $1 [y/N] y (-y)"; return 0; }
    local a; read -r -p "    $1 [y/N] " a </dev/tty; [[ "$a" == [yY]* ]]
}

case "${DOTS_HOST:-$(cat /etc/hostname 2>/dev/null || hostname)}" in
    *surface*) MACHINE=surface ;;
    *desktop*) MACHINE=desktop ;;
    *) die "hostname must contain 'surface' or 'desktop'" ;;
esac
[[ "$(realpath "$0")" == "$DOTS"/* ]] && die "run a copy outside the repo (see header), not $0"
cd "$DOTS" || die "no repo at $DOTS"
TS=$(date +%Y%m%d-%H%M%S)
echo "machine: $MACHINE   repo: $DOTS   log: $LOG"

# ── 1. Fetch + decide what the checkout update will cost ─────────────────────
step "Fetching origin"
git fetch origin || die "git fetch failed"
HEAD_SHA=$(git rev-parse HEAD); ORIGIN_SHA=$(git rev-parse origin/main)
ok "HEAD $(git log -1 --format='%h %s' HEAD)"
ok "origin/main $(git log -1 --format='%h %s' origin/main)"

NEED_RESET=true BACKUP_BRANCH=""
if [[ "$HEAD_SHA" == "$ORIGIN_SHA" ]]; then
    NEED_RESET=false; ok "checkout already at origin/main"
elif ! git merge-base HEAD origin/main >/dev/null 2>&1; then
    warn "no common history with origin/main — this clone predates the 2026-08-15 rewrite (expected)"
    BACKUP_BRANCH="pre-sync-backup-$TS"
elif ! git merge-base --is-ancestor HEAD origin/main; then
    warn "local commits not on origin/main:"
    git log --oneline origin/main..HEAD | sed 's/^/        /'
    BACKUP_BRANCH="pre-sync-backup-$TS"
fi
if [[ -n "$BACKUP_BRANCH" ]]; then
    echo "    Current HEAD will be kept as branch '$BACKUP_BRANCH' (cherry-pick anything new from it later)."
    ask "Continue?" || die "stopped by user"
fi

# Uncommitted work outside scripts/.local/bin (the migration below owns that dir).
DIRTY=$(git status --porcelain -- . ':!scripts/.local/bin')
if $NEED_RESET && [[ -n "$DIRTY" ]]; then
    warn "uncommitted changes (will be stashed, not lost):"
    printf '%s\n' "$DIRTY" | sed 's/^/        /'
    ask "Stash them and continue?" || die "stopped by user — commit or stash, then re-run"
fi

# ── 2. Apps whose niri window rules were removed ─────────────────────────────
step "Checking apps whose niri window rules were removed"
found=""
for a in wezterm ghostty kitty zen-browser zoom; do command -v "$a" >/dev/null && found+=" $a"; done
if [[ -n "$found" ]]; then
    warn "installed here:$found — their window rules are gone after the update"
    ask "Continue anyway?" || die "stopped by user"
else
    ok "none installed"
fi

# ── 3. Migrate ~/.local/bin (BEFORE the checkout changes) ────────────────────
step "Migrating ~/.local/bin"
if [[ -L "$BIN" ]]; then
    B="$DOTS/scripts/.local/bin"
    T=$(mktemp -d "$HOME/.local/bin-migrate.XXXX")
    echo "    staging: $T"
    for f in "$B"/* "$B"/.[!.]*; do
        [[ -e "$f" || -L "$f" ]] || continue
        n=${f##*/}; [[ "$KEEP" == *" $n "* ]] && continue
        mv -n -- "$f" "$T/"
        [[ -e "$f" || -L "$f" ]] && die "could not move $n (staging kept: $T)"
        echo "    moved: $n"
    done
    stow --no-folding --restow -t "$HOME" scripts || die "stow failed (installer files are safe in $T)"
    [[ -L "$BIN" ]] && die "$BIN is still a link after stow (files safe in $T)"
    shopt -s nullglob dotglob; staged=("$T"/*); shopt -u nullglob dotglob
    if ((${#staged[@]})); then
        mv -n -- "${staged[@]}" "$BIN/"
    fi
    rmdir "$T" || die "some files could not be moved back — they are in $T"
    ok "$BIN is a real directory"
else
    ok "already a real directory — skipped"
fi

# ── 4. Update the checkout ───────────────────────────────────────────────────
step "Updating checkout to origin/main"
if $NEED_RESET; then
    [[ -n "$BACKUP_BRANCH" ]] && { git branch "$BACKUP_BRANCH" "$HEAD_SHA"; ok "backup branch: $BACKUP_BRANCH"; }
    if [[ -n "$(git status --porcelain -- . ':!scripts/.local/bin')" ]]; then
        git stash push -u -m "surface-sync $TS" -- . ':!scripts/.local/bin'
        ok "stashed local changes: 'git stash list' → surface-sync $TS"
    fi
    git reset --hard origin/main
    ok "now at $(git log -1 --format='%h %s')"
else
    ok "nothing to do"
fi

# ── 5. Relink dotfiles from dotsets/viridjan ─────────────────────────────────
step "Relinking dotfiles (dotsets/viridjan, profile $MACHINE)"
# After the reset, links into the old layout (<repo>/<pkg>/...) dangle; stow
# refuses to replace links it does not own, so remove exactly those first.
n=0
while IFS= read -r -d '' l; do
    case "$(readlink "$l")" in *Projects/dots/dotsets/*) continue ;; esac
    rm -- "$l"; n=$((n + 1))
done < <(find "$HOME" -maxdepth 5 -path "$HOME/Projects" -prune -o -xtype l -lname '*Projects/dots/*' -print0 2>/dev/null)
ok "removed $n dangling links into the old layout"
for l in /etc/brave /etc/systemd/system/ollama.service.d; do
    if [[ -L "$l" && ! -e "$l" ]]; then
        sudo rm -- "$l" && ok "removed dangling $l" || warn "could not remove $l"
    fi
done
CFG="${XDG_CONFIG_HOME:-$HOME/.config}/vjupdate/config.toml"
if [[ -f "$CFG" ]]; then
    ok "vj config exists: $CFG"
else
    mkdir -p "$(dirname "$CFG")"
    printf 'profile = "%s"\ndotset = "viridjan"\n' "$MACHINE" > "$CFG"
    ok "wrote $CFG (profile $MACHINE, dotset viridjan)"
fi
stow --no-folding --restow -t "$HOME" scripts && ok "scripts" || warn "stow scripts reported conflicts"
"$DOTS/scripts/.local/bin/vjupdate" --actions stow-symlinks \
    && ok "dotfiles linked" || warn "vjupdate --actions stow-symlinks reported problems (see its recap)"

# ── 6. niri ──────────────────────────────────────────────────────────────────
step "Validating niri config"
if command -v niri >/dev/null; then
    if niri validate -c "$HOME/.config/niri/config.kdl" >/dev/null 2>&1; then
        ok "config valid"
        niri msg action load-config-file >/dev/null 2>&1 && ok "reloaded" \
            || warn "not reloaded (no running niri session?) — applies at next login"
    else
        warn "niri validate FAILED — run: niri validate -c ~/.config/niri/config.kdl"
    fi
else
    warn "niri not found — skipped"
fi

# ── 7. Verify ────────────────────────────────────────────────────────────────
step "Verifying"
fail=0
[[ -d "$BIN" && ! -L "$BIN" ]] && ok "$BIN is a real dir" || { warn "$BIN is not a real dir"; fail=1; }
[[ "$(readlink -f "$BIN/vjupdate")" == "$DOTS/scripts/.local/bin/vjupdate" ]] \
    && ok "vjupdate links into the repo" || { warn "vjupdate link wrong"; fail=1; }
dangling=$(find "$BIN" -maxdepth 1 -xtype l -printf '%f ' 2>/dev/null)
old=$(find "$HOME" -maxdepth 5 -path "$HOME/Projects" -prune -o -xtype l -lname '*Projects/dots/*' -print 2>/dev/null | head -5)
[[ -z "$old" ]] && ok "no dangling dotfile links" || { warn "dangling dotfile links remain: $old"; fail=1; }
[[ -z "$dangling" ]] && ok "no dangling links in ~/.local/bin" || warn "dangling (pre-existing? remove if unused): $dangling"
[[ "$(git rev-parse HEAD)" == "$(git rev-parse origin/main)" ]] \
    && ok "checkout = origin/main ($(git log -1 --format=%h))" || { warn "checkout differs from origin/main"; fail=1; }
leftover=$(git ls-files scripts/.local/bin | grep -v -E '/(vjupdate|vj|start-windows|start-open-notebook|start-keep)$' || true)
[[ -z "$leftover" ]] && ok "no installer links tracked" || { warn "unexpected tracked files: $leftover"; fail=1; }

echo
if ((fail)); then
    die "finished with problems — see warnings above"
fi
printf '\033[1;32mDone.\033[0m Log: %s\n' "$LOG"
[[ -n "$BACKUP_BRANCH" ]] && echo "Old HEAD kept as branch $BACKUP_BRANCH (delete with: git branch -D $BACKUP_BRANCH)"
git stash list | grep -q "surface-sync $TS" && echo "Stashed work: git stash list  (restore with git stash pop)"
exit 0
