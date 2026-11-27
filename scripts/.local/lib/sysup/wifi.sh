# shellcheck shell=bash
# Wifi passwords between machines through one Bitwarden secure note ("sysup wifi",
# body = JSON list of {ssid, key_mgmt, psk, hidden}). Sourced by sysup on first
# wifi_export/wifi_import call. Secrets travel only through pipes and shell
# variables: argv is world-readable in /proc, so no psk or note body goes on it.

_WIFI_NOTE="sysup wifi"
_BW_SESSION=""
_BW_UNLOCKED=false

_bw() { BW_SESSION="$_BW_SESSION" bw --nointeraction "$@"; }
_wifi_dir() { printf '%s' "${SYSUP_NM_DIR:-/etc/NetworkManager/system-connections}"; }
_wifi_py() { sudo python3 -I -B "$SYSUP_LIB/sysup.py" "$@" "$(_wifi_dir)"; }

# Unlocked vault (session in _BW_SESSION) or return 1 after a warn/failure.
_bw_open() {
    local id="$1" st=""
    command -v bw &>/dev/null || { warn "bitwarden-cli not installed — sysup --actions install"; return 1; }
    _BW_SESSION=${BW_SESSION:-}
    st=$(_bw status 2>/dev/null | jq -r '.status // empty' 2>/dev/null) || st=""
    case "$st" in
        unlocked) ;;
        locked)
            [[ -t 0 ]] || { warn "Bitwarden is locked — needs a terminal: sysup --actions $id"; return 1; }
            _BW_SESSION=$(bw unlock --raw) || _BW_SESSION=""
            [[ -n "$_BW_SESSION" ]] || { _failw "$id" "Bitwarden unlock failed"; return 1; }
            _BW_UNLOCKED=true ;;
        *) warn "Bitwarden CLI not logged in — run 'bw login' once, then sysup --actions $id"; return 1 ;;
    esac
    _bw sync >/dev/null 2>&1 || warn "bw sync failed — using the cached vault"
}
_bw_close() {
    if $_BW_UNLOCKED; then bw lock >/dev/null 2>&1 || true; fi
    _BW_SESSION=""; _BW_UNLOCKED=false
}

# Prints the note's item id, or nothing when it doesn't exist yet.
_wifi_note_id() {
    _bw list items --search "$_WIFI_NOTE" \
        | jq -r --arg n "$_WIFI_NOTE" '[.[] | select(.name == $n and .type == 2)][0].id // empty'
}

# Note body (JSON list) into WIFI_STORE; empty note → []. Returns 1 if unreadable.
_wifi_load() {
    WIFI_STORE='[]'
    [[ -z "$1" ]] || WIFI_STORE=$(_bw get item "$1" | jq -r '.notes // "[]"') || return 1
    printf '%s' "$WIFI_STORE" | jq -e 'type == "array"' >/dev/null 2>&1
}

wifi_export() {
    local id="" local_json merged names
    _bw_open wifi-export || return 0
    if ! id=$(_wifi_note_id) || ! _wifi_load "$id"; then
        _failw wifi-export "could not read the Bitwarden note '$_WIFI_NOTE' (must hold a JSON list)"
        _bw_close; return 0
    fi
    if ! local_json=$(_wifi_py wifi-read); then
        _failw wifi-export "could not read NetworkManager connections"
        _bw_close; return 0
    fi
    # Union by SSID; this machine wins.
    merged=$({ printf '%s\n' "$WIFI_STORE"; printf '%s\n' "$local_json"; } \
        | jq -c -s 'reduce (.[0][], .[1][]) as $e ({}; .[$e.ssid] = $e) | [.[]]')
    names=$(printf '%s' "$local_json" | jq -r '[.[].ssid] | join(", ")')
    if { printf '%s\n' "$WIFI_STORE"; printf '%s\n' "$merged"; } | jq -s -e '.[0] == .[1]' >/dev/null; then
        ok "wifi: Bitwarden already has every network here ($names)"
        _bw_close; return 0
    fi
    local base
    if [[ -n "$id" ]]; then base=$(_bw get item "$id"); else base=$(_bw get template item); fi
    if { printf '%s\n' "$base"; printf '%s\n' "$merged"; } \
        | jq -c -s --arg n "$_WIFI_NOTE" \
            '.[0] + {type: 2, name: $n, login: null, secureNote: {type: 0}, notes: (.[1] | tojson)}' \
        | _bw encode \
        | if [[ -n "$id" ]]; then _bw edit item "$id"; else _bw create item; fi >/dev/null; then
        _bw sync >/dev/null 2>&1 || true
        ok "wifi: $(printf '%s' "$merged" | jq length) networks in Bitwarden note '$_WIFI_NOTE' (from here: $names)"
    else
        _failw wifi-export "could not save the Bitwarden note '$_WIFI_NOTE'"
    fi
    _bw_close
}

wifi_import() {
    local id="" out
    _bw_open wifi-import || return 0
    if ! id=$(_wifi_note_id) || ! _wifi_load "$id"; then
        _failw wifi-import "could not read the Bitwarden note '$_WIFI_NOTE' (must hold a JSON list)"
        _bw_close; return 0
    fi
    _bw_close
    if [[ -z "$id" ]]; then
        warn "no Bitwarden note '$_WIFI_NOTE' yet — run sysup --actions wifi-export on a machine that has the networks"
        return 0
    fi
    if ! out=$(printf '%s\n' "$WIFI_STORE" | _wifi_py wifi-write); then
        _failw wifi-import "could not write NetworkManager connections"; return 0
    fi
    [[ -z "$out" ]] || sed 's/^/    /' <<<"$out"
    if grep -qE '^(added|updated) ' <<<"$out"; then
        sudo nmcli connection reload && ok "wifi: networks from Bitwarden applied" \
            || _failw wifi-import "nmcli connection reload failed"
    else
        ok "wifi: every network from Bitwarden already here"
    fi
}
