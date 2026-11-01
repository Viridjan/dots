---
name: dots-shell-conventions
description: "set -e and shellcheck gotchas in the dots shell scripts, plus the pre-commit guard"
metadata: 
  node_type: memory
  type: project
  originSessionId: 74ac168d-fad3-4549-8662-ad28e7e617d5
  modified: 2026-08-15T17:38:28.832Z
---

The dots shell scripts (`vjupdate`, `start-windows`, `start-open-notebook`) all run
`set -euo pipefail`. Established 2026-08-15 while fixing 18 bugs in `vjupdate`.

**The dominant bug class:** `var=$(cmd)` where *the failure is the signal*. Under
`set -e` the assignment exits immediately, so every error branch below it is
unreachable. Real instances found: `check_aur_malware` (aur_check exits non-zero
exactly when it finds malware — the `die` never printed, the gate aborted silently),
`check_pacman_db` (`rc=$?` never reached; whole warn branch dead), `install_dms_plugins`.
Guard with `|| true` or `|| rc=$?`.

**shellcheck gotcha:** a comment line starting with `# shellcheck ` parses as a
*directive*. It caused SC1072/SC1073 and made shellcheck skip all 1840 lines of
`vjupdate` while looking like it had almost passed. If output is only SC1072/SC1073,
nothing was checked.

**Deliberate disable:** `vjupdate` has a file-level `# shellcheck disable=SC2015` — all
~28 sites are the `cmd && ok "..." || warn "..."` logging idiom where the middle command
is a plain `echo`, so the pitfall needs `echo` itself to fail.

**Guard:** `.githooks/pre-commit` runs `shellcheck -S error` on staged scripts, selected
by **shebang not path** (`scripts/.local/bin/` holds 150 MB+ of vendored binaries — `uv`,
`uvx`, `claude-science`). No-ops when shellcheck is absent. Registered by
`deploy_dotfiles` via `core.hooksPath`.

**How to apply:** before hand-auditing any script here, run shellcheck. When editing,
never start a comment line with the linter's name, and treat any new `var=$(cmd)` as
needing a guard unless the command cannot meaningfully fail.

**Editing vjupdate while it runs:** bash reads a script incrementally by byte
offset, and `~/.local/bin/vjupdate` links to the repo file. An in-place write
(Edit tool, `open('w')`) can corrupt a running upgrade. Check `pgrep -af vjupdate`;
if it's live, write a temp file and `mv`/`os.replace` it over (new inode). Long AUR
runs (e.g. 12 ArtCraft Rust builds ≈ 75 min, 2026-10-18) make this common.

Related: [[feedback-verification-rigor]], [[vjupdate-optimize]].
