#!/usr/bin/env bash
# Sourced by vjupdate on first use of automount_disks (one-time disk setup,
# kept out of the main script). Relies on vjupdate's info/ok/warn/die/_confirm.

# Escape an fstab field without interpreting existing backslashes.
_fstab_escape() {
    local field="$1"
    field="${field//\\/\\134}"
    field="${field// /\\040}"
    field="${field//$'\t'/\\011}"
    printf '%s' "$field"
}


automount_disks() {
    command -v lsblk >/dev/null || { warn "automount: lsblk not found — skipping"; return; }

    section "automount disks"
    echo ""
    lsblk -f
    echo ""

    local -A _mnt_at=()
    while IFS= read -r _line; do
        local _dev _mp
        _dev=$(echo "$_line" | awk '{print $1}')
        _mp=$(echo  "$_line" | awk '{print $2}')
        _mnt_at["$_dev"]="$_mp"
    done < <(lsblk -rno NAME,MOUNTPOINT | grep -v '^$')

    local -a _candidates=()
    while IFS= read -r _line; do
        # ponytail: regex capture, not eval — a malicious FS label (e.g. "$(rm -rf ~)")
        # must never reach a shell-execution context.
        local _name="" _fstype="" _label="" _uuid=""
        [[ "$_line" =~ NAME=\"([^\"]*)\" ]] && _name="${BASH_REMATCH[1]}"
        [[ "$_line" =~ FSTYPE=\"([^\"]*)\" ]] && _fstype="${BASH_REMATCH[1]}"
        [[ "$_line" =~ LABEL=\"([^\"]*)\" ]] && _label="${BASH_REMATCH[1]}"
        [[ "$_line" =~ UUID=\"([^\"]*)\" ]] && _uuid="${BASH_REMATCH[1]}"

        [[ -z "$_fstype" || -z "$_uuid" ]] && continue

        case "$_fstype" in
            swap|zram*|tmpfs|squashfs|iso9660) continue ;;
        esac
        [[ "$_name" == loop* ]] && continue

        local _curmnt="${_mnt_at[$_name]:-}"
        case "$_curmnt" in
            /|/boot|/boot/*|/efi|/efi/*) continue ;;
        esac

        if grep -qs "UUID=$_uuid" /etc/fstab; then
            ok "skipped: /dev/$_name (already in fstab)"
            continue
        fi

        _candidates+=("$_name|$_fstype|$_label|$_uuid")
    done < <(lsblk -Pno NAME,FSTYPE,LABEL,UUID)

    if [[ ${#_candidates[@]} -eq 0 ]]; then
        ok "no eligible partitions"
        return
    fi

    local -a _fstab_entries=() _mount_points=() _fstypes=() _entry_uuids=()

    for _entry in "${_candidates[@]}"; do
        IFS='|' read -r _name _fstype _label _uuid <<< "$_entry"

        echo "  ── /dev/$_name ──────────────────────────────────"
        echo "  FSTYPE : $_fstype"
        echo "  LABEL  : ${_label:-(none)}"
        echo "  UUID   : $_uuid"
        echo ""

        _confirm "  Automount /dev/$_name? [y/N]" || { echo "  Skipped."; echo ""; continue; }

        local _default_mp
        if [[ -n "$_label" ]]; then
            _default_mp="/mnt/$_label"
        else
            _default_mp="/mnt/$_uuid"
        fi

        read -rp "  Mount point [$_default_mp]: " _mp
        _mp="${_mp:-$_default_mp}"

        # Data mounts only: a typo like /usr or /mnt/../boot would shadow a
        # system path and can make the machine unbootable.
        if [[ "$_mp" != /mnt/?* && "$_mp" != /media/?* && "$_mp" != /run/media/?* ]] \
            || [[ "/$_mp/" == */./* || "/$_mp/" == */../* ]] \
            || [[ "$_mp" == *$'\n'* || "$_mp" == *$'\r'* || "$_mp" == *,* ]]; then
            warn "Mount point must be under /mnt, /media or /run/media, without . or .. components, newline, carriage return or comma"
            continue
        fi
        local _escaped_mp _uid _gid
        _escaped_mp=$(_fstab_escape "$_mp")
        _uid=$(id -u "$USER")
        _gid=$(id -g "$USER")
        local _opts _pass
        case "$_fstype" in
            ext4)
                _opts="defaults,noatime,nofail,x-systemd.device-timeout=5"
                _pass=2 ;;
            btrfs)
                _opts="defaults,noatime,compress=zstd,nofail,x-systemd.device-timeout=5"
                _pass=0 ;;
            ntfs|ntfs-3g)
                _opts="defaults,nofail,uid=$_uid,gid=$_gid,umask=022,x-systemd.device-timeout=5"
                _pass=0 ;;
            exfat|vfat)
                _opts="defaults,nofail,uid=$_uid,gid=$_gid,umask=022,x-systemd.device-timeout=5"
                _pass=0 ;;
            *)
                _opts="defaults,nofail,x-systemd.device-timeout=5"
                _pass=0 ;;
        esac

        local _fstab_line="UUID=$_uuid  $_escaped_mp  $_fstype  $_opts  0  $_pass"
        echo ""
        echo "  Entry: $_fstab_line"
        _confirm "  Confirm? [y/N]" || { echo "  Skipped."; echo ""; continue; }

        _fstab_entries+=("$_fstab_line")
        _mount_points+=("$_mp")
        _fstypes+=("$_fstype")
        _entry_uuids+=("$_uuid")
        echo ""
    done

    [[ ${#_fstab_entries[@]} -eq 0 ]] && { ok "nothing to add"; return; }

    local _backup
    _backup="/etc/fstab.backup.$(date +%Y%m%d-%H%M%S)"
    info "Backing up /etc/fstab → $_backup"
    sudo cp /etc/fstab "$_backup"

    for _mp in "${_mount_points[@]}"; do
        sudo mkdir -p "$_mp"
    done

    printf '\n# Added by vjupdate --automount on %s\n' "$(date)" | sudo tee -a /etc/fstab > /dev/null
    for i in "${!_fstab_entries[@]}"; do
        printf '%s\n' "${_fstab_entries[$i]}" | sudo tee -a /etc/fstab > /dev/null
        ok "added: ${_fstab_entries[$i]}"

        # Also create /run/media/$USER/<UUID> bind mount so udisks path persists.
        local _uuid="${_entry_uuids[$i]}"
        local _mp="${_mount_points[$i]}"
        local _media_path="/run/media/$USER/$_uuid"
        local _tmpfiles="/etc/tmpfiles.d/media-${_uuid}.conf"
        local _bind_line
        printf -v _bind_line '%s\t%s\tnone\tbind,nofail,x-systemd.requires-mounts-for=%s\t0\t0' \
            "$(_fstab_escape "$_mp")" "$(_fstab_escape "$_media_path")" "$(_fstab_escape "$_mp")"

        if ! grep -qs "$_media_path" /etc/fstab; then
            printf "d %s 0755 %s %s -\n" "$_media_path" "$USER" "$USER" | sudo tee "$_tmpfiles" > /dev/null
            printf '%s\n' "$_bind_line" | sudo tee -a /etc/fstab > /dev/null
            ok "bind mount: $_mp → $_media_path"
        fi
    done

    sudo systemctl daemon-reload
    sudo systemd-tmpfiles --create /etc/tmpfiles.d/media-*.conf 2>/dev/null || true
    local _mnt_err
    if _mnt_err=$(sudo mount -a 2>&1); then
        ok "mounted: all entries"
        for i in "${!_fstypes[@]}"; do
            # ponytail: ext4 root is owned by root after mkfs; vfat/ntfs/exfat use uid= mount opts
            if [[ "${_fstypes[$i]}" == ext4 ]]; then
                sudo chown "$USER:$USER" "${_mount_points[$i]}"
                ok "ownership: ${_mount_points[$i]} → $USER"
            fi
        done
    else
        warn "mount -a failed — check /etc/fstab"
        warn "Restore: sudo cp $_backup /etc/fstab"
        echo "$_mnt_err"
    fi
}
