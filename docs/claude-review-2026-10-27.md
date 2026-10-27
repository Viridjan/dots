# Claude handoff: second vjupdate review

Reviewed 2026-10-27 in `/home/viridjan/Projects/dots`.
Base HEAD: `dbf3f4bcc7e475882489f437cb433616d175fb38`, plus the current
uncommitted changes in `scripts/.local/bin/vjupdate` and
`tests/test_vjupdate_extras.py`. Preserve those changes.

## Scope and current state

The user requested another check and a file for Claude. This pass documents
remaining findings; it does not apply further production fixes.

The previous pass changed setup result recording, service failure tracking and
privilege escalation, and the mirror timer override. It added five tests.
Those changes remain uncommitted. The existing `CLAUDE.md` was left unchanged.

Read the current source before editing. Keep work inside this project. Do not
run live bootstrap, package installation, service management, or disk setup to
reproduce these findings. Use the isolated `FixtureCase` test harness instead.
If editing the executable, follow CLAUDE.md's instruction about avoiding
in-place writes while vjupdate is running.

## Findings, in priority order

### 1. P2: Partial enable success can leave a service permanently untracked

Location: `scripts/.local/bin/vjupdate:1252` and `:1265`, `enable_services()`.
This is an edge case introduced by the previous service-tracking fix.

`systemctl enable --now` has two effects: enable the unit, then start it. A
nonzero return can mean enable succeeded but start failed. The current failure
branch retains a unit only if it was already in `managed-units`. For a newly
enabled unit, the script loses the fact that it changed persistent state.
Removing that unit from the plan on a later run never disables it.

Reproduced with a stateful sudo mock: on `systemctl enable --now cups`, write
an enabled-state marker and return 1. Run `enable_services`, empty the system
list, then run it again. The marker remains and `managed-units` is empty.
The user-unit branch has the same structure; it needs equivalent coverage.
This probe models partial systemctl success; no real system service was used.

Suggested fix: separate enable from start and retain successfully enabled units
even when starting fails, or explicitly reconcile persistent enablement after a
failed combined command. Keep start failures recorded as failures. Preserve
retry of failed disables and do not claim a unit is enabled when nothing changed.

Regression requirements: partial success for system and user units, a later
removal from the plan, and a true enable failure with no persistent side effect.

### 2. P2: Flatpak installation/update failures still produce a successful run

Location: `scripts/.local/bin/vjupdate:805` and `:811`, `install_all()`.

A failed `flatpak install` only calls `warn`; the bootstrap Flatpak update
branch does the same. Neither records failure. When pacman installation and
other work succeed, `_FAILED` stays zero and `print_recap` returns 0 even though
a requested application was not installed. The recent `_act` guard does not
cover `phase_install`.

Reproduced by running the real `install_all()` with unrelated mutation helpers
stubbed to success, a one-app Flatpak list, `flatpak info` and install returning
1, and update succeeding. Output included `failed to install: org.example.App`,
but `print_recap` exited 0 and listed only successful package results.

Suggested fix: record per-app failures and bootstrap Flatpak update failures.
Continue independent work, then propagate failure through the final recap.
Add separate installation and update failure regressions, alongside success.

### 3. P2: Failed setup commands can still be classified as skipped, exit 0

Location: `scripts/.local/bin/vjupdate:1732`, `setup_caveman_code()`, and
`:2420`, `_act()`. Other setup helpers use similar warning-only handling.

The previous fix prevents an incorrect done stamp, but `_act` classifies any
new warning without an explicit failure record as `skip`. A real installation
failure therefore still leaves `_FAILED=0`. This breaks the documented promise
that a failed requested action produces a nonzero exit status.

Reproduced with an available npm mock returning 1, selecting `caveman-code`
through the real `phase_configure()`, then calling `print_recap`. Result:
`action:caveman-code skip`, exit 0, despite `caveman-code npm install failed`.

Suggested fix: distinguish genuine skips (missing optional tool, unsupported
profile, user declined) from failed commands. Add explicit failure records at
setup command failure sites and retain `_act` aggregation. Do not turn every
warning into a failure: some warnings are informational or intentional skips.
Audit fish, Claude plugins, DMS plugins, greeter, keyring PAM, Ollama and VM setup
for the same pattern; these additional sites were inspected but not individually
reproduced in this pass.

Regression requirements: a failed available installer records `fail` and yields
a nonzero recap; an intentional skip remains `skip`; successful setup still
records `ok`; a failure from an earlier action does not contaminate a later one.

## Reproduction harness

Use `tests/test_vjupdate.py::FixtureCase`, which creates a temporary HOME and
restricted PATH. It mocks system mutation commands by default. Example for
finding 3, runnable from the project root:

```python
import sys
sys.path.insert(0, "tests")
from test_vjupdate import FixtureCase

case = FixtureCase()
case.setUp()
try:
    case.mock("npm", "exit 1")
    result = case.shell('''
CONFIGURE_PROMPTED=true
CONFIGURE_ITEMS=caveman-code
phase_configure
print_recap
''')
    print(result.stdout)
    print("exit:", result.returncode)  # currently 0; should be nonzero
finally:
    case.doCleanups()
```

Turn the scenarios above into failing regression tests before applying fixes.
The probes used for this review were temporary and were not added to the suite.

## Verification and limits

Fresh results during this second pass:

- `python3 -B -m unittest discover -s tests -q`: **161 tests passed**.
- `shellcheck -S error scripts/.local/bin/vjupdate scripts/.local/lib/vjupdate/automount.sh .githooks/pre-commit`: passed.
- `bash -n scripts/.local/bin/vjupdate`: passed.
- `git diff --check`: passed before adding this handoff; recheck after edits.
- All three findings reproduced in isolated mocks despite the green suite.

Consulted `graphify-out/GRAPH_REPORT.md` and relevant nodes in
`graphify-out/graph.json` for navigation. Graph build commit is
`aa3021c0d7ac2c5c45d076c6ca43666cdd44b6d0`, so its line numbers are stale.
Graphify was not regenerated or executed. Findings were checked against current
source and runtime probes, rather than inferred from the graph.

No live system settings were changed. No measured performance bottleneck was
established; this pass prioritizes correctness over speculative optimization.
This is a focused review of vjupdate and its result/service/install paths, not
an exhaustive audit of every script or every dotfile in the repository.
