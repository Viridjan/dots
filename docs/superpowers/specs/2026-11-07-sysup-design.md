# sysup: vjupdate without the TUI

Date: 2026-11-07. Replaces the vj half of `2026-10-21-vjupdate-tui-design.md`.

## Goal

One command-line tool, `sysup`, instead of `vjupdate` (bash) driven by `vj`
(Textual TUI). Less to maintain, no `python-textual`. Every vj feature the
user chose to keep survives as a flag or as a hand-edited config value.

Decided with the user:

- Rename `vjupdate` → `sysup`. Delete the `vj/` package and `scripts/.local/bin/vj`.
- Data stays TOML (`packages.toml`, `profiles/*.toml`, `projects.toml`, local
  config). Pure bash was rejected: it needs a TOML-subset parser or a data
  format change. The TOML work stays in Python (`tomllib`, stdlib).
- The Python lives in one helper file, `scripts/.local/lib/sysup/sysup.py`
  (next to `automount.sh`), not a heredoc: importable by tests, not hidden
  from shellcheck.
- Kept: unused-app report, add-to-list, one-time done dates, local
  add/remove/declined.
- Bare `sysup` prints help.

## Non-goals

- No menu of any kind (bash or Python). No progress screen.
- No change to phases, actions (`MENU_ORDER` IDs), stamps, package
  resolution rules, or the post-run fixes / update check added 2026-11-07.
- No change to `packages.toml` / profile / projects file formats.

## Components

### `scripts/.local/bin/sysup` (bash, was vjupdate)

`git mv`, then rename user-facing names:

| Old | New |
|---|---|
| `vjupdate` (command, usage text, messages) | `sysup` |
| `~/.config/vjupdate/config.toml` | `~/.config/sysup/config.toml` |
| `$STAMP_DIR/vjupdate.log`, `vjupdate.lock` | `sysup.log`, `sysup.lock` (`STAMP_DIR` stays `~/.local/state/dots`, so stamps, build history, backups carry over) |
| `scripts/.local/lib/vjupdate/` | `scripts/.local/lib/sysup/` |
| env `VJ_*` (`VJ_PLAN_DIR`, `VJ_CONFIG`, `VJ_FEATURES`, `VJ_MIN_FREE_GB`, `VJ_SELF_UPDATED`, …) | `SYSUP_*` |
| `VJUPDATE_SCRIPT` (tests) | `SYSUP_SCRIPT` |

Python calls go through one wrapper, `_py() { python3 -B "$SYSUP_LIB/sysup.py" "$@"; }`,
with `SYSUP_LIB` resolved like `_AUTOMOUNT_LIB` today (`${BASH_SOURCE%/*}/../lib/sysup`).
It replaces `_vj` and the `python3 -m vj` calls (`plan`, `unused`, `add`).

The remaining inline `python3 -c` JSON one-liners (Bitwarden, Claude plugin
list, one more) switch to `jq`, which is already installed and used by the
statusline. Python is then used only through `sysup.py`.

Config migration, once, at runtime init: if `~/.config/vjupdate/config.toml`
exists and `~/.config/sysup/config.toml` doesn't, `mv` it and say so.
`[last].dotfiles` / `[last].repos` become `[select] dotfiles` / `repos`
(see below); other `[last]` keys are dropped.

### New flags

| Flag | Does | Replaces |
|---|---|---|
| (none) | print usage, exit 0 | `exec vj` |
| `--profile NAME [--dotset NAME]` | validate against `profiles/` and `dotsets/`, write to config, exit | vj initial setup screen |
| `--pkg {shared,profile,local,remove,ignore} NAME…` | sort packages: `packages.toml`, active profile file, local `[paru|flatpak] add`, local `remove` (demote; paru only), local `[ignored]`. Flatpak when the name is an installed flatpak app ID, else paru. Repo files keep their comments (`add_to_list`); remind to commit. | vj Unlisted keys p/f/m/x/i |
| `--status` | profile, dotset, features; each one-time action the profile offers with `done <date>` / `skipped` / `never run`; last `--check` summary | vj main screen rows |
| `--skip-once ID` | mark a one-time action `skip` | vj "skip" on a one-time task |

`--pkg` and the post-run "unlisted" fix share the same `sysup.py add`
code. The fix's choices become `[p]ackages.toml / pro[f]ile / [m] local /
[i]gnore / [u]ninstall`.

### One-time stamps

Today vj reads `VJ_RESULT_FILE` after a run and stamps `[once]`. Now sysup
does it itself at the end of `--actions` (in `print_recap`'s caller, after
fixes): for each `action:<id> ok` result whose ID is in the ONCE list, call
`sysup.py once-done ID…`, which writes today's date. The ONCE list, its
labels and `ONCE_FEATURE` move from `vj/state.py` into `sysup.py`.
`_record` no longer writes a result file.

### `scripts/.local/lib/sysup/sysup.py`

One file, stdlib only, ~350 lines, ported from vj with UI code removed:

- from `config.py`: `load_repo`, `load_local`, `save_local`, `dumps`,
  `add_to_list`, `valid_choice`, `host_profile`, `ConfigError`
- from `resolve.py`: `resolve`, `features`, `write_plan` (drops the
  estimate/colour helpers, which only the TUI used)
- from `unused.py`: all of it (report text no longer mentions vj)
- from `state.py`: `ONCE`, `ONCE_FEATURE`, `last_check` (plain text, no
  Textual markup), `detect_explicit`
- CLI: `plan DIR`, `unused PLANDIR [DAYS]`, `add WHERE NAME…`,
  `choose PROFILE [DOTSET]`, `status`, `once-done ID…`, `once-skip ID`

Local config keys after the change: `profile`, `dotset`, `[display]`,
`[paru]/[flatpak] add/remove`, `[declined]`, `[ignored]`, `[once]`,
`[select] dotfiles/repos` (missing = all).
`[declined]` and `[select]` have no flag: hand-edit.

### Other files

- `scripts/.local/bin/vjsurface`: config path and lock name → sysup.
- `dotsets/viridjan/systemd-user/…/vjupdate-check.{service,timer}` →
  `sysup-check.*`; `packages.toml` `[systemd].user` entry renamed (the
  managed-units logic disables the old timer, enables the new).
- fish: delete `completions/vj.fish`, rename `completions/vjupdate.fish` →
  `sysup.fish`, add the new flags.
- `.github/workflows/test.yml`: drop `pip install textual`, shellcheck path.
- `packages.toml`: drop `python-textual`.
- `CLAUDE.md`, `README.md`: rename; delete the vj sections (In-app runs,
  Unlisted keys, vj rows); document the new flags.
- `docs/` history, memory files: left as is (historical).

## Data flow

```
sysup --update
  _check_repo_current → (pull + exec relaunch)
  _ensure_plan → sysup.py plan TMPDIR   (config + hostname fallback)
  phases / actions → _queue_fix …
  print_recap → _offer_fixes → stamp [once] (--actions only)
```

## Error handling

- `sysup.py` exits 2 with one line on invalid TOML (`ConfigError`) or a
  bad argument; bash `die`s with that line (same as today).
- `--profile` with an unknown name lists the valid ones and exits 2.
- `--pkg profile` with no active profile fails with "run sysup --profile".
- Migration never overwrites an existing `~/.config/sysup/config.toml`.

## Testing

- `tests/test_vjupdate*.py` → `test_sysup*.py`, `SYSUP_SCRIPT`; all current
  tests keep passing with renamed names.
- `tests/test_vj.py`: keep the resolve/plan/config/unused/add_to_list tests,
  retarget at `sysup.py` (import by path) → `tests/test_sysup_py.py`; delete
  TUI-state tests. `tests/test_vj_progress.py`: delete.
- New: `--profile` writes config; `--pkg` each target; `--status` output;
  once stamping after `--actions`; config migration; bare `sysup` = usage.

## Rollout

Desktop: after the commit, run `bash scripts/.local/bin/sysup --actions
stow-symlinks` once. Dead `vj`/`vjupdate` links are pruned by
`_prune_dead_links`, and the old timer is disabled by the services action.

Surface / Plancia (TODO.md checklist): after `git pull` the `vjupdate` link
is dead. Run `~/Projects/dots/scripts/.local/bin/sysup --actions
stow-symlinks,services` once; the config moves on that first run.
