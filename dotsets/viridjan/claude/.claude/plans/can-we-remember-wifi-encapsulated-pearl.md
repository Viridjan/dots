# Wifi passwords synced via Bitwarden

## Context
NetworkManager keeps wifi PSKs in plaintext root-only keyfiles
(`/etc/NetworkManager/system-connections/*.nmconnection`). Desktop knows
`vj-wifi`, `WiFimodem-6FBCE`, `GUEST-Effe.Di. srl`; Surface/Plancia must re-type them.
Goal: sysup carries them between machines. User chose Bitwarden as store: nothing
secret in git.

## Design
Two actions, same shape as `dms-export`/`dms-import`:
- `wifi-export`: local wifi networks → Bitwarden secure note `sysup wifi` (local wins per SSID).
- `wifi-import`: note → local keyfiles (store wins per SSID: password changed on router
  → export on one machine, import on the others).

Note body = JSON list `[{ssid, key_mgmt, psk, hidden}]`. Only `wpa-psk`, `sae`, open
(`none`/no security). `wpa-eap` (802.1x) skipped with a warn.

### Safety rules
- Secrets never on argv (world-readable `/proc/*/cmdline`): only pipes/stdin. `bw encode`
  and `bw create item` / `bw edit item ID` read stdin.
- `BW_SESSION` kept in a local shell var, passed only to `bw` calls; never written to disk/log.
  If sysup unlocked the vault, `bw lock` at the end.
- `bw status`: `unauthenticated` → warn "run `bw login` once" + record fail; `locked` → `bw unlock --raw`
  (terminal only; no terminal → warn, skip). `bw sync` before read and after write.
- Keyfiles written by root helper: mode 600, owner root, atomic (temp + rename in same dir),
  then `sudo nmcli connection reload`.
- Update of existing connection changes only `[wifi-security] psk` / `key-mgmt` — keeps per-machine
  settings (autoconnect, MAC, priority, uuid).
- Logs: never print psk; print SSIDs + added/updated/unchanged counts only. Run under `set +x`.

## Files
- `scripts/.local/lib/sysup/wifi.sh` (new, sourced lazily like `automount.sh` via stub
  in sysup): `wifi_export`, `wifi_import`, `_bw_session`.
- `scripts/.local/lib/sysup/sysup.py`: subcommands
  - `wifi-read [DIR]` (run as `sudo python3 -I`): parse keyfiles (configparser, `optionxform=str`,
    no interpolation), print JSON list to stdout.
  - `wifi-write [DIR]` (sudo): JSON list on stdin → create missing keyfile (`[connection]`
    id=SSID, uuid4, type=wifi; `[wifi]` mode/ssid/hidden; `[wifi-security]`; ipv4/ipv6 auto) or
    update psk of the connection whose `[wifi] ssid` matches. Prints `added/updated/unchanged` SSIDs.
  - `wifi-merge` : stdin `{"base": [...], "over": [...]}` → merged list by SSID, `over` wins.
  - DIR default `/etc/NetworkManager/system-connections` (override for tests).
  - `ACTIONS` entries `wifi-export`, `wifi-import` (group `accounts`).
- `scripts/.local/bin/sysup`: `MENU_ORDER` + `_sel ... && _act wifi-export wifi_export` (and import);
  stub sourcing `wifi.sh`.
- `packages.toml`: `bitwarden-cli` in `[paru].install` (cachyos-extra-v3 / extra).
- Tests:
  - `tests/test_sysup_py.py`: read/write/merge on temp dir — create, update keeps other keys,
    eap skipped, file mode 600, hidden flag, SSID with spaces/dots.
  - `tests/test_sysup_extras.py`: mocked `bw`/`sudo`/`nmcli` logging argv; assert fake psk never in
    any argv log; unauthenticated → fail recorded, nothing written; locked + no TTY → skip;
    unlock → `bw lock` called.
- Docs: CLAUDE.md section (sysup behaviour notes) + `TODO.md`: Surface/Plancia →
  `bw login` once, then `sysup --actions install,wifi-import`. Desktop first: `sysup --actions wifi-export`.

## Verification
1. `python3 -B -m unittest discover -s tests -v`, `shellcheck -S warning` on sysup + wifi.sh, `bash -n`.
2. Live (desktop, needs user's master password): `bw login` (user, `! bw login`), then
   `sysup --actions wifi-export` → `bw get item "sysup wifi"` shows 3 SSIDs (check only names).
3. `wifi-import` on desktop → all "unchanged" (round-trip proof), `nmcli con show` unchanged.
4. Surface run left as TODO.
