# vjupdate de-duplication plan

Written 2026-10-27 against the working tree on top of `dbf3f4b`, including the
uncommitted `_failw` fixes (handoff `docs/claude-review-2026-10-27.md`).
Line numbers are for `scripts/.local/bin/vjupdate` at that point; they will
drift, so find code by function name.

Goal: remove repeated code without changing behaviour. Total gain is about
85 lines out of ~2900. Every item is independent; do them in any order, one
commit each.

Implementation status (2026-10-27): items 1–8 applied. Banner extraction keeps
the original box style and spacing; the upgrade helper keeps both progress
messages and the conflict warning's original position. User-tool commands use
function callbacks and separate arguments rather than shell command strings.
Added a Claude plugin failure/continuation regression, including a mutation
check that rejects lost failure tracking. Changes are left uncommitted alongside
the pre-existing failure-reporting edits rather than combining those edits into
the planned commits.

## Procedure (every item)

1. `pgrep -af vjupdate` must be empty. Never write the live script in place
   (CLAUDE.md: bash reads it by byte offset while running).
2. Copy to a scratch file, edit the copy.
3. `bash -n COPY && shellcheck -S warning COPY`
4. `VJUPDATE_SCRIPT=COPY python3 -B -m unittest discover -s tests -q`.
   Two automount tests fail from a scratch path because the library resolves
   relative to the script (`../lib/vjupdate/automount.sh`); ignore those two
   there, they must pass after step 5.
5. `cp -p COPY scripts/.local/bin/.vjupdate.new && mv scripts/.local/bin/.vjupdate.new scripts/.local/bin/vjupdate`
6. Full suite again in place, `git diff --check`, commit.

Failures must keep going through `_failw NAME MSG` (records `fail`, makes the
recap exit nonzero). Plain `warn` is only for intentional skips. Do not
reintroduce `_record ... fail` + `warn` pairs.

---

## 1. `enable_services`: system and user branches are copies (~25 lines)

**Where:** `enable_services()` (~1243). The enable loop exists twice (system
list, user list) and the disable step has an `if user … else …` with two copies.
Only the `systemctl` invocation and the label differ.

**Fix:** one wrapper that picks the invocation from the unit kind, one enable
loop fed by both lists, one disable body.

```bash
# kind = system|user
_sc() {
    local kind="$1"; shift
    if [[ "$kind" == user ]]; then systemctl --user "$@"; else sudo systemctl "$@"; fi
}

    # replaces both enable loops
    while read -r kind u; do
        [[ -n "$u" ]] || continue
        local tag="$u"; [[ "$kind" == user ]] && tag="$u (user)"
        if _sc "$kind" enable --now "$u"; then
            ok "enabled: $tag"
            now+="$kind $u"$'\n'
        else
            _failw "service:$kind:$u" "could not enable: $tag"
            # enable --now may enable and then fail to start: keep tracking it.
            if _sc "$kind" is-enabled --quiet "$u" 2>/dev/null \
                || { [[ -f "$managed" ]] && grep -qxF "$kind $u" "$managed"; }; then
                now+="$kind $u"$'\n'
            fi
        fi
    done < <(_pkg_list "$sys" | sed 's/^/system /'; _pkg_list "$usr" | sed 's/^/user /')
```

`is-enabled` goes through `_sc` too; `sudo` is harmless there (a read-only query).

Disable body becomes:

```bash
            if _sc "$kind" disable "$u"; then
                ok "disabled (no longer listed): $tag"
            else
                _failw "service:$kind:$u" "could not disable: $tag (will retry)"
                now+="$kind $u"$'\n'
            fi
```

`_enable()` (one line, only caller is this loop) can then be deleted.

**Gotchas**

- `_pkg_list` failure: today a failed read of either list is caught earlier by
  the `-r` check. Keep that check; the process substitution hides exit codes.
- Keep the order: system units first, then user units (tests check calls).
- The `desktop-services` block (daemon-reload, usermod) stays between the
  enable loop and the disable step.

**Tests:** `tests.test_vjupdate_extras.ServiceTests` (5 tests: list/disable,
partial enable, true failure, failed disable retry, first run). The tests
expect `sudo systemctl …` for system units and `systemctl --user …` for user units.

## 2. `install_user_tools`: npm and uv blocks are copies (~15 lines)

**Where:** `install_user_tools()` (~940). Two 18-line blocks; they differ in:
list file, binary, how installed names are listed, install command.

**Fix:** one inner function, called twice.

```bash
# _user_tools TOOL LIST "LIST-INSTALLED CMD" "INSTALL CMD"
_user_tools() {
    local tool="$1" list="$VJ_PLAN_DIR/$2" have pkg
    [[ -s "$list" ]] || return 0
    command -v "$tool" &>/dev/null || { warn "$tool not found — $tool tools skipped"; return 0; }
    have=$(bash -c "$3" 2>/dev/null || true)
    while IFS= read -r pkg; do
        [[ -n "$pkg" ]] || continue
        if grep -qxF -- "$pkg" <<< "$have"; then
            ok "already installed: $pkg ($tool)"
        elif $4 "$pkg" >/dev/null 2>&1; then
            ok "installed: $pkg ($tool)"
        else
            _failw "$tool:$pkg" "failed to install: $pkg ($tool)"
        fi
    done < <(_pkg_list "$list")
}
install_user_tools() {
    _user_tools npm npm-install.list \
        "npm ls -g --depth=0 --parseable | sed -n 's|.*/node_modules/||p'" "npm i -g"
    _user_tools uv uv-install.list "uv tool list | awk '\$1 !~ /^-/ {print \$1}'" "uv tool install"
}
```

**Gotchas**

- `$4` is unquoted on purpose (word-split into command + subcommand). The
  values are fixed literals in this file, never user input. Add a `ponytail:`
  comment saying so, or pass the install command as an array name instead.
- `bash -c "$3"` runs the listing in a child shell. It inherits PATH, so the
  test mocks still apply. Alternative without `bash -c`: pass a function name
  (`_npm_have`, `_uv_have`) instead of a string; that is two one-line functions
  and no quoting traps. **Prefer the function-name version** if the string
  quoting gets ugly.
- Record names stay `npm:<pkg>` / `uv:<pkg>`.
- Today the failure note is "npm i -g failed"/"uv tool install failed"; with
  `_failw` the note becomes the warn text. No test reads the note.

**Tests:** grep `install_user_tools` / `npm-install.list` in `tests/` and run
those classes; there is coverage in `test_vjupdate_extras.py`.

## 3. Banner boxes (~15 lines)

**Where:** `update()` and `check()` (~2565, ~2584) each print a 5-line blue
`╔═╗` box; `print_recap` (2 boxes, ~2229 and ~2248) and
`print_manual_steps` (~2265) print 4-line `════` boxes in cyan/yellow.
`section()` (line 23) already does the same job for phase titles.

**Fix:**

```bash
# _banner COLOR TITLE
_banner() {
    echo ""
    echo -e "$1════════════════════════════════════════════${NC}"
    echo -e "$1  $2${NC}"
    echo -e "$1════════════════════════════════════════════${NC}"
}
```

Use `_banner "$CYN" Results`, `_banner "$YEL" "⚠  Warnings / Errors (${#WARNINGS[@]})"`,
`_banner "$YEL" "Manual steps required after this script"`,
`_banner "$BLU" "vjupdate — update"`, `_banner "$BLU" "vjupdate — check"`.

**Decision for the user:** this replaces the `╔═╗` double-box style of
`update`/`check` with the plain `═` rule. If the box style must stay, give
`_banner` a third style argument instead; that costs back about half the gain.
Check whether `print_manual_steps` and `print_recap` print a trailing `echo ""`
after the box. Keep it at the call site if so.

**Tests:** no test asserts the box characters (verify with
`grep -rn '═' tests/`). Run the full suite.

## 4. `setup_claude`: four plugin blocks (~12 lines)

**Where:** `setup_claude()` (~1690). Four times: optional
`claude plugin marketplace add <repo>`, then `claude plugin install <id> --scope user`,
then `ok` / `_failw claude "<id> plugin install failed — run manually: …"`.

**Fix:**

```bash
    local entry market plugin hint
    # "marketplace-repo plugin-id"; "-" = official marketplace, no add needed
    for entry in "JuliusBrussee/caveman caveman" \
                 "- superpowers@claude-plugins-official" \
                 "safishamsi/graphify graphify" \
                 "DietrichGebert/ponytail ponytail"; do
        read -r market plugin <<< "$entry"
        hint="claude plugin install $plugin --scope user"
        [[ "$market" == - ]] || {
            claude plugin marketplace add "$market" 2>/dev/null || true
            hint="claude plugin marketplace add $market && $hint"
        }
        claude plugin install "$plugin" --scope user 2>/dev/null \
            && ok "installed: ${plugin%@*}" \
            || _failw claude "${plugin%@*} plugin install failed — run manually: $hint"
    done
```

The `ok` and failure texts stay identical to today (`${plugin%@*}` strips
`@claude-plugins-official`). Keep the comment block about statusline wiring.

**Tests:** add one: mock `claude` that exits 1 on `plugin install graphify`
only; assert one `fail` record with the graphify hint and `ok` for the other
three. There is currently no `setup_claude` test.

## 5. `install_all` / `system_update`: shared upgrade lead-up (~10 lines)

**Where:** `install_all()` (~751–765) and `system_update()` (~1775–1791) both
run `_remove_conflicts; _demote_packages; _check_disk_space;
_review_aur_updates; _estimate_aur_builds`, then
`if _syuu; then _record full-upgrade ok; ok MSG; else _record_upgrade_failure; fi`.

**Fix:**

```bash
# _upgrade_system OK-MESSAGE
_upgrade_system() {
    _remove_conflicts
    _demote_packages
    _check_disk_space
    _review_aur_updates
    _estimate_aur_builds
    info "Upgrading packages..."
    if _syuu; then
        _record "full-upgrade" ok
        ok "$1"
    else
        _record_upgrade_failure
    fi
}
```

**Gotchas — keep these outside the helper, they differ:**

- `system_update` calls `refresh_mirrors` before, and warns about
  `REMOVED_CONFLICTS` between `_demote_packages` and `_check_disk_space`.
  Either keep that warning inside the helper behind a flag, or (simpler) emit
  it after the helper returns; the order of output changes slightly but no
  logic depends on it. Check `grep -n REMOVED_CONFLICTS tests/`.
- `install_all` checks `paru`/`flatpak` before; leave that there.
- The two `info` texts differ ("Upgrading existing packages..." /
  "Updating all packages..."). Either pass it as `$2` or unify; grep tests
  for both strings first.
- Keep the comment explaining why a failed upgrade must not abort the run.

**Tests:** `HoldTests`, upgrade/retry tests in `tests/test_vjupdate.py`
(grep `_syuu`, `full-upgrade`).

## 6. `dms_export` / `dms_import`: mirror-image copy loops (~10 lines)

**Where:** ~1466–1505. Same shape: check `$DMS_LIVE`, `_dms_repo`, `info`,
then for each file `cp FROM/f TO/f && ok "<verb>: f"` or `warn "<missing>: f"`.

**Fix:**

```bash
# _dms_copy FROM TO VERB MISSING-TEXT FILE...
_dms_copy() {
    local from="$1" to="$2" verb="$3" missing="$4" f; shift 4
    for f in "$@"; do
        if [[ -f "$from/$f" ]]; then cp "$from/$f" "$to/$f"; ok "$verb: $f"
        else warn "$missing: $f"; fi
    done
}
# export: _dms_copy "$DMS_LIVE" "$DMS_REPO" exported "not live, not exported" "${DMS_MANUAL[@]}"
# import: _dms_copy "$DMS_REPO" "$DMS_LIVE" imported "not in repo" "${DMS_MANUAL[@]}" "${DMS_AUTO[@]}"
```

**Must keep:** both comments explaining the colors asymmetry (export skips
`DMS_AUTO` because of the ff2cd4e regression; import includes it on purpose).
They are the reason this code looks the way it does. The two different
"live dir not found" warnings also stay in each function.

**Tests:** grep `dms_export`/`dms_import` in `tests/`.

## 7. Phase-skip test written 12 times (readability, ~0 lines)

**Where:** `[[ " ${SKIP_PHASES:-} " == *" X "* ]]` (or `!=`) at `_run_phase`
(~211), the bootstrap preflight (~2540–2552) and `dry_run` (~2760–2832).

**Fix:**

```bash
_skipped() { [[ " ${SKIP_PHASES:-} " == *" $1 "* ]]; }
```

then `if ! _skipped install; then`, `_skipped "$name"`, etc.

**Gotcha:** the inline space padding is required. `SKIP_PHASES` is *not*
kept padded globally: `_enable_audit_action` (~105) pads it only temporarily
to remove ` audit ` and then trims the leading space again. Keep the padding
inside `_skipped`.

**Tests:** `SKIP_PHASES` tests in `tests/test_vjupdate.py`, dry-run tests.

## 8. `paru -Qua` fetched three ways (optional, ~3 lines)

**Where:** `_aur_estimate_text` (~400), `check_held_updates` (~501),
`_review_aur_updates` (~888).

They use the result differently (names minus holds; holds only; full lines
with holds checked inside the loop), so only the fetch is shared:
`_pending_aur() { paru -Qua 2>/dev/null || true; }`. Gain is tiny; the
benefit is one place to change if paru's output or flags change. Fine to skip.

## Not worth fixing

- `start-keep`, `start-open-notebook`, `start-windows`: same hostname →
  window-size `case` (3 copies) and wait-for-URL loop (2 copies). Sharing them
  needs a sourced library for three small standalone launchers. Revisit if a
  4th launcher appears.
- `command -v X &>/dev/null || { warn "X not found — skipping"; return; }`
  (8 sites) and `while IFS= read -r` loops (31): standard shell idioms; a
  helper would hide more than it saves.
- `vj/state.py` repeated tuples: data tables, not logic.
- `tests/`: not scanned for de-duplication.

## How the duplicates were found

Sliding 4-line window over normalized lines (whitespace collapsed, string
literals replaced, comments and lone `fi`/`done`/`}` dropped) across
`vjupdate`, `automount.sh`, `start-*`, `gamescope-media`, `vj/*.py`, plus
`grep -c` counts of idioms that differ in more than strings. Fuzzier repeats
(same shape, different commands) are possible but were not found by this method.
