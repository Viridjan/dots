"""Isolated regressions. SYSUP_SCRIPT can point at a pre-fix snapshot."""
import os
import fcntl
from pathlib import Path
import shlex
import shutil
import subprocess
import tempfile
import unittest


SCRIPT = Path(os.environ.get("SYSUP_SCRIPT", Path(__file__).resolve().parents[1]
                             / "scripts/.local/bin/sysup")).resolve()


class FixtureCase(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="sysup-test-")
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.home = self.root / "home"
        self.home.mkdir()
        self.bin = self.root / "bin"
        self.bin.mkdir()
        # Restricted PATH: system/package commands cannot accidentally run.
        for name in ("bash", "cat", "grep", "sed", "awk", "cut", "tail", "head",
                     "tr", "sort", "tee", "date", "mkdir", "cp", "rm", "dirname",
                     "basename", "mktemp", "python3", "readlink", "jq", "flock", "mv", "ln", "du", "xargs", "echo",
                     "nice", "ionice"):
            (self.bin / name).symlink_to(Path("/usr/bin") / name)
        for name in ("pacman", "paru", "sudo", "systemctl", "stow", "git",
                     "flatpak", "paccache", "curl", "pacman-key", "makepkg"):
            self.mock(name, 'printf "%s\\n" "$0 $*" >> "$CALLS"; exit 97')
        self.mock("codex", "exit 0")
        self.env = {**os.environ, "HOME": str(self.home), "PATH": str(self.bin),
                    "HOSTNAME": "desktop", "XDG_STATE_HOME": str(self.home / ".state"),
                    "CALLS": str(self.root / "calls"), "SCRIPT": str(SCRIPT)}
        self.env.pop("BASH_ENV", None)
        self.env.pop("SKIP_PHASES", None)
        # Run plan written by `vj plan`; tests write the list files directly.
        self.plan_dir = self.root / "plan"
        self.plan_dir.mkdir()
        self.env["SYSUP_PLAN_DIR"] = str(self.plan_dir)
        # Existing tests treat the repo root as the dotfile set (the pre-dotsets layout).
        self.env["SYSUP_DOTSET_DIR"] = str(self.home / "Projects/dots")
        (self.plan_dir / "env").write_text(f"SYSUP_PROFILE=desktop\nSYSUP_DOTSET_DIR={self.env['SYSUP_DOTSET_DIR']}\n")

    def plan(self, name, content):
        path = self.plan_dir / name
        path.write_text(content)
        return path

    def mock(self, name, body):
        f = self.bin / name
        if f.is_symlink():
            f.unlink()
        # paru -Si (conflict lookup) answers nothing; a body starting "#si" handles it itself.
        if name == "paru" and not body.startswith("#si"):
            body = '[ "$1" = -Si ] && exit 0\n' + body
        f.write_text("#!/bin/bash\n" + body + "\n")
        f.chmod(0o755)

    def shell(self, body):
        return subprocess.run(["/usr/bin/bash", "-c", 'source "$SCRIPT"\n' + body],
                              env=self.env, text=True, capture_output=True, timeout=10,
                              stdin=subprocess.DEVNULL)

    def cli(self, *args):
        return subprocess.run(["/usr/bin/bash", str(SCRIPT), *args], env=self.env,
                              text=True, capture_output=True, timeout=10,
                              stdin=subprocess.DEVNULL)

    def fixture_repo(self):
        repo = self.home / "Projects/dots"
        (repo / "sample").mkdir(parents=True)
        (repo / "sample/config file").write_text("repo original")
        (self.home / "config file").write_text("live original")
        return repo

    def conflict_mock(self):
        self.mock("stow", '''
case " $* " in
  *" -n "*) echo '  * cannot stow sample/config file over existing target config file since neither a link nor a directory and --adopt not specified' >&2; exit 1 ;;
  *" --adopt "*) echo adopted >> "$CALLS" ;;
esac
''')


class ReviewTests(FixtureCase):
    def test_phase_stops_after_keyring_failure(self):
        r = self.shell('''
_needs_run() { return 0; }
sudo() { echo "sudo $*"; [[ "$*" != "pacman-key --init" ]]; }
_mark_done() { echo BAD_STAMP; }
_run_phase sources reset_keyrings
echo BAD_CONTINUED
''')
        self.assertNotEqual(r.returncode, 0, r.stdout)
        self.assertNotIn("BAD_STAMP", r.stdout)
        self.assertNotIn("BAD_CONTINUED", r.stdout)

    def test_update_failure_reaches_nonzero_recap(self):
        r = self.shell('''
_init_runtime
detect_machine() { :; }
check_aur_malware() { :; }
refresh_mirrors() { :; }
_syuu() { return 42; }
flatpak_update() { :; }
check_flatpak_orphans() { :; }
clean_caches() { echo CLEANUP_REACHED; }
update
''')
        self.assertIn("CLEANUP_REACHED", r.stdout)
        self.assertNotEqual(r.returncode, 0, r.stdout)
        self.assertEqual(r.stdout.count("  Results"), 1, r.stdout)

    def test_backup_failure_prevents_adoption(self):
        self.fixture_repo()
        self.conflict_mock()
        r = self.shell('''
echo sample > "$SYSUP_PLAN_DIR/stow.list"
STOW_ADOPT=true
git() { :; }
_stow_niri_cfg() { :; }
cp() { return 42; }
deploy_dotfiles
print_recap
''')
        calls = Path(self.env["CALLS"])
        self.assertFalse(calls.exists() and "adopted" in calls.read_text(), r.stdout)
        self.assertNotEqual(r.returncode, 0)

    def test_only_scripts_is_stowed_unfolded(self):
        # A folded ~/.local/bin made every installer write into the repo.
        repo = self.fixture_repo()
        (repo / "scripts").mkdir()
        self.mock("stow", 'printf "%s\\n" "$*" >> "$CALLS"')
        r = self.shell('''
echo sample > "$SYSUP_PLAN_DIR/stow.list"
git() { :; }
_stow_niri_cfg() { :; }
deploy_dotfiles
''')
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        calls = Path(self.env["CALLS"]).read_text().splitlines()
        self.assertIn("--restow --no-folding -t %s scripts" % self.home, calls)
        self.assertIn("--restow -t %s sample" % self.home, calls)
        self.assertEqual(sum("--no-folding" in c for c in calls), 1, calls)

    def test_unrecognised_conflict_aborts_backup(self):
        self.fixture_repo()
        self.mock("stow", "echo 'new unrecognised conflict format' >&2; exit 1")
        r = self.shell('_adopt_backup -t "$HOME" sample')
        self.assertNotEqual(r.returncode, 0, r.stdout)

    def test_backup_uses_target_and_preserves_both_versions(self):
        repo = self.fixture_repo()
        target = self.root / "other-target"
        target.mkdir()
        (target / "config file").write_text("other live")
        self.conflict_mock()
        self.env["TARGET"] = str(target)
        r = self.shell('cd "$DOTS_DIR"\n_adopt_backup -t "$TARGET" sample')
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        contents = [p.read_text() for p in (self.home / ".state").rglob("*") if p.is_file()]
        self.assertIn("other live", contents)
        self.assertIn("repo original", contents)
        self.assertEqual((repo / "sample/config file").read_text(), "repo original")

    def test_missing_backup_source_aborts(self):
        self.fixture_repo()
        (self.home / "config file").unlink()
        self.conflict_mock()
        r = self.shell('cd "$DOTS_DIR"\n_adopt_backup -t "$HOME" sample')
        self.assertNotEqual(r.returncode, 0, r.stdout)

    def test_check_preview_omits_mutations(self):
        r = self.cli("--dry-run", "--check")
        self.assertEqual(r.returncode, 0, r.stderr)
        for unwanted in ("Packages that would be installed", "Dotfile deployment:",
                         "Services that would be enabled:", "paccache -rk2"):
            self.assertNotIn(unwanted, r.stdout)

    def test_update_preview_omits_bootstrap(self):
        r = self.cli("--update", "--dry-run")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertNotIn("Dotfile deployment:", r.stdout)
        self.assertNotIn("Services that would be enabled:", r.stdout)
        self.assertIn("paccache", r.stdout)

    def test_preview_respects_skipped_phases(self):
        self.env["SKIP_PHASES"] = "sources install dotfiles configure audit"
        r = self.cli("--yes", "--dry-run")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertNotIn("Packages that would be installed", r.stdout)
        self.assertNotIn("Dotfile deployment:", r.stdout)
        self.assertNotIn("paccache -rk2", r.stdout)

    def test_preview_does_not_claim_failed_stow_probe_is_clean(self):
        self.fixture_repo()
        r = self.cli("--yes", "--dry-run")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertNotIn("no stow conflicts detected", r.stdout)
        self.assertIn("[unknown]", r.stdout)

    def test_malformed_scanner_cannot_print_partial_clean_verdict(self):
        (self.home / ".local/share/aur-malware-check").mkdir(parents=True)
        r = self.shell('''
_update_malware_defs() { :; }
python() { echo '{"exit_code":0,"warnings":["bad schema"]}'; }
check_aur_malware
''')
        self.assertNotEqual(r.returncode, 0, r.stdout)
        self.assertNotIn("check: clean", r.stdout)

    def test_unselected_pacnew_is_successful_skip(self):
        self.mock("pacdiff", "exit 0")
        r = self.shell('check_pacnew\necho SKIPPED_OK')
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("SKIPPED_OK", r.stdout)

    def test_runtime_failure_reports_before_exit(self):
        r = self.shell('''
_init_runtime
broken_step() { false; echo BAD_CONTINUED; }
_run_phase fixture broken_step
''')
        self.assertNotEqual(r.returncode, 0, r.stdout)
        self.assertNotIn("BAD_CONTINUED", r.stdout)
        self.assertIn("remaining work aborted", r.stdout)

    def test_rebuild_scans_before_mutation(self):
        self.mock("checkrebuild", "printf 'foreign\\texample\\n'")
        self.mock("paru", 'echo BAD_REBUILD >> "$CALLS"')
        # No definitions can be refreshed: git is the default failing mock.
        r = self.cli("--actions", "rebuild")
        self.assertNotEqual(r.returncode, 0, r.stdout)
        calls = Path(self.env["CALLS"])
        self.assertFalse(calls.exists() and "BAD_REBUILD" in calls.read_text())

    def test_configure_kernel_action_scans_first(self):
        r = self.shell('''
SYSUP_ACTIONS=kernels
detect_machine() { MACHINE=desktop; }
_ensure_dots_repo() { :; }
_check_packages_against_malware() { :; }
check_aur_malware() { echo GATE; exit 7; }
manage_kernels() { echo BAD_KERNEL; }
bootstrap
''')
        self.assertEqual(r.returncode, 7, r.stdout + r.stderr)
        self.assertNotIn("BAD_KERNEL", r.stdout)


class FollowupFixTests(FixtureCase):
    def test_conflict_preserves_working_symlink(self):
        repo = self.fixture_repo()
        (repo / 'sample/working').write_text('working config')
        link = self.home / 'working'
        link.symlink_to(repo / 'sample/working')
        self.mock('stow', '''
case " $* " in
  *" -D "*) rm -f "$HOME/working"; exit 0 ;;
  *) echo 'conflicting existing target config file' >&2; exit 1 ;;
esac
''')
        r = self.shell('''
echo sample > "$SYSUP_PLAN_DIR/stow.list"
git() { :; }
_stow_niri_cfg() { :; }
deploy_dotfiles
print_recap
''')
        self.assertNotEqual(r.returncode, 0, r.stdout)
        self.assertTrue(link.is_symlink(), r.stdout + r.stderr)
        self.assertEqual(link.read_text(), 'working config')

    def test_running_kernel_cannot_be_removed(self):
        r = self.shell('''
uname() { echo 6.12.1-1-cachyos; }
pacman() {
    if [[ "$1" == -Qoq ]]; then echo linux-cachyos;
    else echo 'linux-cachyos 6.12.1-1'; fi
}
_confirm() { [[ "$1" == Remove* ]]; }
sudo() { echo BAD_REMOVAL; }
manage_kernels <<< linux-cachyos
''')
        self.assertNotIn('BAD_REMOVAL', r.stdout)
        self.assertIn('Cannot remove running kernel', r.stdout)

    def test_unknown_running_kernel_owner_blocks_removal(self):
        r = self.shell('''
uname() { echo 6.12.1-1-cachyos; }
pacman() {
    [[ "$1" == -Qoq ]] && return 1
    echo 'linux-cachyos 6.12.2-1'
}
_confirm() { [[ "$1" == Remove* ]]; }
sudo() { echo BAD_REMOVAL; }
manage_kernels <<< linux-cachyos
print_recap
''')
        self.assertNotIn('BAD_REMOVAL', r.stdout)
        self.assertNotEqual(r.returncode, 0, r.stdout)

    def test_failed_installer_pipeline_is_not_success(self):
        repo = self.fixture_repo()
        (repo / '.install-scripts.list').write_text('false | true\n')
        r = self.shell('run_install_scripts\nprint_recap')
        self.assertNotEqual(r.returncode, 0, r.stdout)
        self.assertNotIn('done: false | true', r.stdout)

    def test_failed_cache_cleanup_is_not_success(self):
        r = self.shell('''
sudo() { echo "attempt $*"; return 42; }
clean_caches
echo CLEANUP_RETURNED
print_recap
''')
        self.assertNotEqual(r.returncode, 0, r.stdout)
        self.assertIn('attempt paccache -rk2', r.stdout)
        self.assertIn('attempt paccache -ruk0', r.stdout)
        self.assertIn('CLEANUP_RETURNED', r.stdout)
        self.assertNotIn('caches cleaned', r.stdout)


class UploadTests(FixtureCase):
    def setUp(self):
        super().setUp()
        self.mock('git', '''
printf '%s\\n' "$*" >> "$CALLS"
shift 2
case "$1" in
  symbolic-ref) echo main ;;
  config) case "$3" in *.remote) echo origin ;; *.merge) echo refs/heads/main ;; esac ;;
  status) printf '%s' "${UPLOAD_CHANGES-M config}" ;;
  commit) [[ "${UPLOAD_FAIL:-}" != commit ]] ;;
  push) [[ "${UPLOAD_FAIL:-}" != push ]] ;;
esac
''')

    def test_menu_uses_stable_ids_and_one_dms_import(self):
        r = self.shell('''
printf '%s\\n' "${MENU_ORDER[@]}"
''')
        self.assertEqual(r.returncode, 0, r.stderr)
        ids = r.stdout.splitlines()
        self.assertIn('stow-symlinks', ids)
        self.assertIn('dms-export', ids)
        self.assertIn('dotfiles-export', ids)
        self.assertEqual(ids.count('dms-import'), 1)
        self.assertNotIn('dotfiles-import', ids)
        self.assertNotIn('dotfiles', ids)

    def test_declined_staging_does_not_modify_or_push(self):
        r = self.shell('_confirm() { return 1; }\nexport_dotfiles\nprint_recap')
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        calls = Path(self.env['CALLS']).read_text()
        for action in (' add ', ' commit ', ' push '):
            self.assertNotIn(action, calls)

    def test_upload_commits_before_pushing_configured_branch(self):
        r = self.shell('_confirm() { return 0; }\nexport_dotfiles <<< "Sync dotfiles"\nprint_recap')
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        calls = Path(self.env['CALLS']).read_text()
        self.assertLess(calls.index(' add -A'), calls.index(' commit -m Sync dotfiles'))
        self.assertLess(calls.index(' commit -m Sync dotfiles'), calls.index(' push origin HEAD:refs/heads/main'))
        self.assertNotIn('--force', calls)

    def test_commit_failure_never_pushes(self):
        self.env['UPLOAD_FAIL'] = 'commit'
        r = self.shell('_confirm() { return 0; }\nexport_dotfiles <<< "Sync dotfiles"\nprint_recap')
        self.assertNotEqual(r.returncode, 0, r.stdout)
        self.assertNotIn(' push ', Path(self.env['CALLS']).read_text())

    def test_push_failure_is_reported(self):
        self.env['UPLOAD_FAIL'] = 'push'
        r = self.shell('_confirm() { return 0; }\nexport_dotfiles <<< "Sync dotfiles"\nprint_recap')
        self.assertNotEqual(r.returncode, 0, r.stdout)
        self.assertIn('local commits preserved', r.stdout)

    def test_clean_tree_can_retry_push_without_commit(self):
        self.env['UPLOAD_CHANGES'] = ''
        r = self.shell('_confirm() { return 0; }\nexport_dotfiles\nprint_recap')
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        calls = Path(self.env['CALLS']).read_text()
        self.assertNotIn(' commit ', calls)
        self.assertIn(' push origin HEAD:refs/heads/main', calls)

    def test_upload_runs_after_export(self):
        r = self.shell('''
CONFIGURE_PROMPTED=true
CONFIGURE_ITEMS=$'dms-export — export\\ndotfiles-export — upload'
dms_export() { echo EXPORTED; }
export_dotfiles() { echo UPLOADED; }
phase_configure
''')
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertLess(r.stdout.index('EXPORTED'), r.stdout.index('UPLOADED'))

    def test_services_run_after_stow(self):
        # user units (sysup-check.timer) are stow links: enabling before stow fails
        r = self.shell('''
CONFIGURE_PROMPTED=true
CONFIGURE_ITEMS=$'services — svc\\nstow-symlinks — stow'
enable_services() { echo SERVICES; }
deploy_dotfiles() { echo STOWED; }
phase_configure
''')
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertLess(r.stdout.index('STOWED'), r.stdout.index('SERVICES'))

    def test_noninteractive_upload_is_skipped(self):
        r = self.shell('INTERACTIVE=false\nexport_dotfiles\nprint_recap')
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertFalse(Path(self.env['CALLS']).exists())

    def test_dotfiles_import_copies_overrides_without_git_or_stow(self):
        repo = self.fixture_repo()
        source = repo / 'niri/.config/niri/dms'
        source.mkdir(parents=True)
        live = self.home / '.config/niri/dms'
        live.mkdir(parents=True)
        names = ('alttab', 'binds', 'cursor', 'layout', 'windowrules', 'wpblur', 'colors')
        for name in names:
            (source / (name + '.kdl')).write_text('repo ' + name)
            (live / (name + '.kdl')).write_text('old live')
        r = self.shell('''
CONFIGURE_PROMPTED=true
CONFIGURE_ITEMS='dotfiles-import — import'
deploy_dotfiles() { echo BAD_STOW; }
phase_configure
''')
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertNotIn('BAD_STOW', r.stdout)
        self.assertFalse(Path(self.env['CALLS']).exists())
        for name in names:
            self.assertEqual((live / (name + '.kdl')).read_text(), 'repo ' + name)

    def test_stow_selection_does_not_import_dms(self):
        r = self.shell('''
CONFIGURE_PROMPTED=true
CONFIGURE_ITEMS='stow-symlinks — deploy'
deploy_dotfiles() { echo DEPLOYED; }
dms_import() { echo BAD_DMS_IMPORT; }
phase_configure
''')
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn('DEPLOYED', r.stdout)
        self.assertNotIn('BAD_DMS_IMPORT', r.stdout)

    def test_import_aliases_run_once_after_stow(self):
        r = self.shell('''
CONFIGURE_PROMPTED=true
CONFIGURE_ITEMS=$'dotfiles-import — import\\nstow-symlinks — deploy\\ndms-import — dms'
deploy_dotfiles() { echo STOWED; }
dms_import() { echo DMS_COPIED; }
phase_configure
''')
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertEqual(r.stdout.count('DMS_COPIED'), 1)
        self.assertLess(r.stdout.index('STOWED'), r.stdout.index('DMS_COPIED'))


class SafetyChecks(FixtureCase):
    # Preservation checks, not regressions claimed to fail pre-fix.
    def test_nonrunning_kernel_can_be_removed(self):
        r = self.shell('''
uname() { echo 6.12.1-1-cachyos; }
pacman() {
    if [[ "$1" == -Qoq ]]; then echo linux-cachyos;
    else echo 'linux-cachyos-lts 6.6.1-1'; fi
}
_confirm() { [[ "$1" == Remove* ]]; }
sudo() { echo "REMOVAL: $*"; }
manage_kernels <<< linux-cachyos-lts
''')
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn('REMOVAL: pacman -R linux-cachyos-lts linux-cachyos-lts-headers', r.stdout)

    def test_successful_install_and_cleanup(self):
        repo = self.fixture_repo()
        (repo / '.install-scripts.list').write_text('true | true\n')
        r = self.shell('''
sudo() { return 0; }
run_install_scripts
clean_caches
print_recap
''')
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn('done: true | true', r.stdout)
        self.assertIn('caches cleaned', r.stdout)

    def test_lock_precedes_log_rotation_and_releases(self):
        state = self.home / ".state/dots"
        state.mkdir(parents=True)
        log = state / "sysup.log"
        log.write_text("original log")
        (self.home / "Projects/dots").mkdir(parents=True, exist_ok=True)
        with (state / "sysup.lock").open("w") as lock:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            r = self.cli("--actions", "app-launchers")
            self.assertNotEqual(r.returncode, 0)
            self.assertIn("already running", r.stderr)
            self.assertEqual(log.read_text(), "original log")
            self.assertFalse((state / "sysup.log.1").exists())
        r = self.cli("--actions", "app-launchers")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertEqual((state / "sysup.log.1").read_text(), "original log")

    # Children that outlive a run must not hold the lock: an orphaned `sleep 60`
    # from the sudo loop blocked the next menu run for up to a minute.
    FD_DUMP = 'for f in /proc/$$/fd/*; do readlink "$f"; done >> "$CALLS.fds"\n'

    def assert_lock_dropped(self):
        fds = Path(self.env["CALLS"] + ".fds").read_text()
        self.assertTrue(fds)
        self.assertNotIn("sysup.lock", fds)

    def test_log_tee_does_not_hold_lock(self):
        (self.home / "Projects/dots").mkdir(parents=True, exist_ok=True)
        self.mock("tee", self.FD_DUMP + 'exec /usr/bin/tee "$@"')
        r = self.cli("--actions", "app-launchers")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assert_lock_dropped()

    def test_sudo_keepalive_does_not_hold_lock(self):
        self.mock("sleep", self.FD_DUMP + 'kill "$PPID"')
        r = self.shell('exec {_LOCK_FD}>"$HOME/sysup.lock"\n( _sudo_keepalive "$$" ) || true')
        self.assert_lock_dropped()

    def test_bitwarden_launch_does_not_hold_lock(self):
        self.mock("bitwarden-desktop", "exit 0")
        self.mock("setsid", self.FD_DUMP)
        r = self.shell('exec {_LOCK_FD}>"$HOME/sysup.lock"\nWAYLAND_DISPLAY=w setup_bitwarden')
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assert_lock_dropped()

    def test_stow_23_conflict_format(self):
        # Ubuntu (CI) ships Stow 2.3, which words the conflict line differently.
        repo = self.fixture_repo()
        self.assertTrue((repo / "sample/config file").exists())
        out = ("WARNING! stowing sample would cause conflicts:\n"
               "  * existing target is neither a link nor a directory: config file\n"
               "All operations aborted.\n")
        self.mock("stow", "printf '%s' " + shlex.quote(out) + "; exit 1")
        r = self.shell('cd "$DOTS_DIR"\n_adopt_backup -t "$HOME" sample')
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        copies = [p.read_text() for p in (self.home / ".state").rglob("*") if p.is_file()]
        self.assertIn("live original", copies)
        self.assertIn("repo original", copies)

    @unittest.skipUnless(Path("/usr/bin/stow").exists(), "installed Stow unavailable")
    def test_installed_stow_conflict_format(self):
        repo = self.fixture_repo()
        # The real Stow is only allowed to simulate against temporary fixtures.
        r = subprocess.run(["/usr/bin/stow", "-n", "-d", str(repo), "-t",
                            str(self.home), "sample"], env=self.env,
                           text=True, capture_output=True, timeout=10,
                              stdin=subprocess.DEVNULL)
        self.assertEqual(r.returncode, 1, r.stdout + r.stderr)
        self.mock("stow", "printf '%s' " + shlex.quote(r.stdout + r.stderr) + "; exit 1")
        r = self.shell('cd "$DOTS_DIR"\n_adopt_backup -t "$HOME" sample')
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        copies = [p.read_text() for p in (self.home / ".state").rglob("*") if p.is_file()]
        self.assertIn("live original", copies)
        self.assertIn("repo original", copies)

    def test_read_only_entry_points(self):
        self.fixture_repo()
        for args in (("--help",), ("--dry-run", "--check"),
                     ("--update", "--dry-run"), ("--yes", "--dry-run", "--adopt"),
                     ("--dry-run", "--clean-aggressive")):
            with self.subTest(args=args):
                before = {str(p.relative_to(self.home)): p.read_bytes()
                          for p in self.home.rglob("*") if p.is_file()}
                self.mock("stow", '[[ " $* " == *" -n "* ]] || { echo BAD >> "$CALLS"; exit 98; }')
                r = self.cli(*args)
                self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
                after = {str(p.relative_to(self.home)): p.read_bytes()
                         for p in self.home.rglob("*") if p.is_file()}
                self.assertEqual(before, after)
                self.assertFalse((self.home / ".state").exists())
                self.assertFalse(Path(self.env["CALLS"]).exists())

    def test_audit_action_membership(self):
        r = self.shell('''
for action in "${!AUDIT_ACTIONS[@]}"; do
    SKIP_PHASES='sources audit dotfiles'
    _enable_audit_action "$action"
    [[ " $SKIP_PHASES " != *" audit "* ]]
    [[ " $SKIP_PHASES " == *" sources "* ]]
    var=${AUDIT_ACTIONS[$action]}
    [[ ${!var} == true ]]
done
''')
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)

    def test_scanner_verdicts(self):
        (self.home / ".local/share/aur-malware-check").mkdir(parents=True)
        for verdict, rc, message in ((0, 0, "check: clean"), (0, 7, "inconsistent"),
                                      (1, 1, "INCOMPLETE"), (2, 2, "INFECTION"),
                                      (3, 3, "scanner reported an error")):
            with self.subTest(verdict=verdict, rc=rc):
                body = '_update_malware_defs() { :; }\n'
                body += f'''python() {{ echo '{{"exit_code":{verdict},"warnings":[]}}'; return {rc}; }}\n'''
                r = self.shell(body + 'check_aur_malware')
                self.assertEqual(r.returncode == 0, verdict == 0 and rc == 0)
                self.assertIn(message, r.stdout + r.stderr)


class ScannerJsonTests(FixtureCase):
    """The jq parser must fail closed: any odd shape is 'unreadable', never clean."""

    def verdict(self, json_text):
        (self.home / ".local/share/aur-malware-check").mkdir(parents=True, exist_ok=True)
        body = "_update_malware_defs() { :; }\npython() { printf '%s' " + shlex.quote(json_text) + "; }\ncheck_aur_malware"
        return self.shell(body)

    def test_odd_shapes_never_pass(self):
        for text in ('{"exit_code":"0","warnings":[]}', '{"exit_code":true,"warnings":[]}',
                     '{"exit_code":0.5,"warnings":[]}', '{"warnings":[]}', '[0]', 'not json',
                     '{"exit_code":0,"warnings":{"a":{"kind":"x"}}}'):
            with self.subTest(text=text):
                r = self.verdict(text)
                self.assertNotEqual(r.returncode, 0, r.stdout)
                self.assertNotIn("check: clean", r.stdout)

    def test_warning_kinds_listed(self):
        r = self.verdict('{"exit_code":1,"warnings":[{"kind":"log","detail":"missing"},{"kind":""}]}')
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("?, log", r.stdout + r.stderr)
        self.assertIn("- log: missing", r.stdout + r.stderr)


class UpgradeFailureReportingTests(FixtureCase):
    """A failed paru -Syuu must name the cause in the end-of-run recap."""

    def test_recap_names_failed_aur_package(self):
        self.mock("paru", "\n".join([
            'echo "resolving dependencies..."',
            "echo \"error: failed to download sources for 'unsloth-0.1.808.beta-1': \"",
            'echo "error: packages failed to build: unsloth-0.1.808.beta-1"',
            "exit 1",
        ]))
        r = self.shell('_syuu || true\n'
                       '_record "full-upgrade" fail "$SYUU_FAIL_DETAIL"\n'
                       'print_recap || true')
        self.assertIn("AUR build failed: unsloth-0.1.808.beta-1", r.stdout + r.stderr)

    def test_detail_survives_untrusted_key_retry(self):
        # The retry used to run unlogged, so its failure reported nothing.
        self.mock("paru", "\n".join([
            'if [[ -f "$CALLS.tried" ]]; then',
            '  echo "error: packages failed to build: somepkg-2"',
            "else",
            '  : > "$CALLS.tried"',
            '  echo "error: foo: signature from X is unknown trust"',
            "fi",
            "exit 1",
        ]))
        r = self.shell('_fix_untrusted_keys() { return 0; }\n'
                       '_syuu || true\n'
                       'echo "DETAIL=$SYUU_FAIL_DETAIL"')
        self.assertIn("DETAIL=AUR build failed: somepkg-2", r.stdout)

    def test_falls_back_to_last_error_line(self):
        self.mock("paru", 'echo "error: failed to synchronize all databases"\nexit 1')
        r = self.shell('_syuu || true\necho "DETAIL=$SYUU_FAIL_DETAIL"')
        self.assertIn("DETAIL=failed to synchronize all databases", r.stdout)

    def test_successful_upgrade_leaves_no_detail(self):
        self.mock("paru", 'echo "there is nothing to do"\nexit 0')
        r = self.shell('_syuu\necho "DETAIL=[$SYUU_FAIL_DETAIL]"')
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("DETAIL=[]", r.stdout)


class BuildTimeEstimateTests(FixtureCase):
    """Past makepkg spans drive the pre-upgrade AUR time estimate."""

    def times(self):
        return (self.home / "Projects/dots/build-times.tsv").read_text()

    def write_times(self, text):
        repo = self.home / "Projects/dots"
        repo.mkdir(parents=True, exist_ok=True)
        (repo / "build-times.tsv").write_text(text)

    def test_upgrade_records_first_making_to_finished_span(self):
        self.mock("paru", "\n".join([
            'echo "==> Making package: foo 1-1 (Sun Oct 18 14:00:00 2026)"',
            'echo "==> Making package: foo 1-1 (Sun Oct 18 14:00:05 2026)"',
            'echo "==> Finished making: foo 1-1 (Sun Oct 18 14:06:00 2026)"',
            'echo "==> Making package: bar 2-1 (Sun Oct 18 14:06:10 2026)"',
            'echo "==> Finished making: bar 2-1 (Sun Oct 18 14:07:10 2026)"',
            'echo "==> Making package: broken 1-1 (Sun Oct 18 14:08:00 2026)"',
            'echo "error: packages failed to build: broken-1-1"',
            "exit 1",
        ]))
        r = self.shell('_syuu || true')
        self.assertEqual(self.times(), "aur:bar\t60\naur:foo\t360\n", r.stdout + r.stderr)
        # Rerun replaces, never duplicates.
        self.mock("paru", "\n".join([
            'echo "==> Making package: foo 1-2 (Sun Oct 18 15:00:00 2026)"',
            'echo "==> Finished making: foo 1-2 (Sun Oct 18 15:02:00 2026)"',
        ]))
        self.shell('_syuu')
        self.assertEqual(self.times(), "aur:bar\t60\naur:foo\t120\n")

    def test_estimate_sums_history_skips_holds_and_names_unknown(self):
        self.plan("paru-hold.list", "held\n")
        self.write_times("aur:foo\t360\naur:bar\t60\naur:held\t9999\n@pacman-per-pkg\t3\n")
        self.mock("paru", 'printf "foo 1 -> 2\nbar 1 -> 2\nnew 0 -> 1\nheld 1 -> 2\n"')
        r = self.shell('_estimate_aur_builds')
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("3 AUR builds pending — est. ~7 min (foo 6m, bar 1m); no history: new",
                      r.stdout)

    def test_record_time_merges_and_sorts(self):
        self.write_times("aur:zed\t5\n@pacman-per-pkg\t9\n")
        r = self.shell('_record_time @pacman-per-pkg 4; _record_time @flatpak-per-pkg 12')
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(self.times(), "@flatpak-per-pkg\t12\n@pacman-per-pkg\t4\naur:zed\t5\n")

    def test_package_install_records_per_package_time(self):
        self.plan("pkgs.list", "one\ntwo\n")
        self.mock("pacman", "exit 0")
        self.mock("paru", "exit 0")
        r = self.shell('_install_list "$SYSUP_PLAN_DIR/pkgs.list"')
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertRegex(self.times(), r"^@pacman-per-pkg\t[1-9][0-9]*\n$")

    def test_estimate_silent_when_nothing_pending(self):
        self.mock("paru", "exit 1")
        r = self.shell('_estimate_aur_builds')
        self.assertEqual((r.returncode, r.stdout), (0, ""), r.stderr)


class SyyRecoveryTests(FixtureCase):
    """The mirrors-step database sync must recover from an untrusted repo key."""

    def test_retries_after_trusting_key(self):
        self.mock("sudo", '"$@"')
        self.mock("pacman", "\n".join([
            'printf "%s\\n" "$*" >> "$CALLS"',
            'if [[ ! -f "$CALLS.tried" ]]; then',
            '  : > "$CALLS.tried"',
            '  echo "error: sublime-text: signature from \\"Sublime HQ\\" is unknown trust"',
            "  exit 1",
            "fi",
        ]))
        r = self.shell('_fix_untrusted_keys() { echo "FIX:$1" | grep -q sublime-text; }\n_syy')
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertEqual(Path(self.env["CALLS"]).read_text().splitlines(), ["-Syy", "-Syy"])

    def test_other_failures_propagate_without_retry(self):
        self.mock("sudo", '"$@"')
        self.mock("pacman", 'printf "%s\\n" "$*" >> "$CALLS"; echo "error: network"; exit 1')
        r = self.shell('_syy')
        self.assertNotEqual(r.returncode, 0)
        self.assertEqual(Path(self.env["CALLS"]).read_text().splitlines(), ["-Syy"])


class HoldTests(FixtureCase):
    def holds(self, content="vectorcraft-bin\n"):
        return self.plan("paru-hold.list", content)

    def calls(self):
        return Path(self.env["CALLS"]).read_text().splitlines()

    def test_upgrade_holds_on_first_attempt_and_retry(self):
        self.holds("# review manually\n\nvectorcraft-bin\nother-held\n")
        self.mock("paru", '''
printf '%s\\n' "$*" >> "$CALLS"
if [[ ! -f "$CALLS.tried" ]]; then
    touch_marker="$CALLS.tried"
    : > "$touch_marker"
    echo 'error: foo: signature from X is unknown trust'
    exit 1
fi
''')
        r = self.shell('_fix_untrusted_keys() { return 0; }\n_syuu')
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertEqual(self.calls(),
                         ["-Syuu --noconfirm --ignore vectorcraft-bin,other-held"] * 2)

    def test_empty_and_missing_holds_preserve_upgrade_argv(self):
        self.mock("paru", 'printf "%s\\n" "$*" >> "$CALLS"')
        path = self.holds()
        r = self.shell('_syuu')
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(self.calls(), ["-Syuu --noconfirm --ignore vectorcraft-bin"])
        for content in ("# no holds\n\n", None):
            with self.subTest(content=content):
                if content is None:
                    path.unlink()
                else:
                    path.write_text(content)
                Path(self.env["CALLS"]).unlink()
                r = self.shell('_syuu')
                self.assertEqual(r.returncode, 0, r.stderr)
                self.assertEqual(self.calls(), ["-Syuu --noconfirm"])

    def test_rebuild_filters_holds_and_avoids_empty_install(self):
        self.holds()
        self.mock("checkrebuild", "printf 'foreign\\tvectorcraft-bin\\nforeign\\tsafe-pkg\\n'")
        self.mock("paru", 'printf "%s\\n" "$*" >> "$CALLS"')
        r = self.shell('AUDIT_REBUILD=true\ncheck_rebuilds')
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertEqual(self.calls(), ["-S --noconfirm safe-pkg"])
        Path(self.env["CALLS"]).unlink()
        self.mock("checkrebuild", "printf 'foreign\\tvectorcraft-bin\\n'")
        r = self.shell('AUDIT_REBUILD=true\ncheck_rebuilds')
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertFalse(Path(self.env["CALLS"]).exists())

    def test_python_rebuild_filters_holds(self):
        self.holds()
        python_root = self.root / "python-libs"
        (python_root / "python3.1").mkdir(parents=True)
        self.env["PYTHON_ROOT"] = str(python_root)
        self.mock("python3", 'echo 3.2')
        self.mock("pacman", "printf 'vectorcraft-bin\\nsafe-pkg\\n'")
        self.mock("paru", 'printf "%s\\n" "$*" >> "$CALLS"')
        r = self.shell(r'''
# Redirect the directory scan into a temporary filesystem fixture.
fn=$(declare -f check_python_rebuilds)
eval "${fn//\/usr\/lib/$PYTHON_ROOT}"
AUDIT_PYTHON_REBUILD=true
check_python_rebuilds
''')
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertEqual(self.calls(), ["-S --noconfirm safe-pkg"])

    def audit_body(self):
        return '''
check_foreign_orphans() { :; }
check_unused_apps() { :; }
check_flatpak_orphans() { :; }
check_rebuilds() { :; }
check_python_rebuilds() { :; }
check_pacnew() { :; }
check_modified_configs() { :; }
check_dms_owner() { :; }
check_logins() { :; }
check_firmware() { :; }
check_aur_malware() { :; }
check_pacman_db() { :; }
phase_audit
echo RECAP_START
print_recap
'''

    def test_audit_warning_reaches_recap_and_empty_query_is_safe(self):
        self.holds()
        self.mock("paru", '''
printf '%s\\n' "$*" >> "$CALLS"
[[ "$*" == '-Qua' ]] || exit 97
echo 'vectorcraft-bin 0.9.0-1 -> 0.9.1-1'
echo 'safe-pkg 1-1 -> 2-1'
''')
        r = self.shell(self.audit_body())
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        detail = ('held package has update: vectorcraft-bin 0.9.0-1 -> 0.9.1-1 '
                  '(review: paru -Gp vectorcraft-bin; upgrade: paru -S vectorcraft-bin)')
        self.assertIn(detail, r.stdout.split("RECAP_START")[1])
        self.assertNotIn("held package has update: safe-pkg", r.stdout)
        self.mock("paru", 'printf "%s\\n" "$*" >> "$CALLS"; exit 1')
        r = self.shell(self.audit_body())
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertNotIn("held package has update", r.stdout)
        self.holds().unlink()
        Path(self.env["CALLS"]).unlink()
        r = self.shell(self.audit_body())
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertFalse(Path(self.env["CALLS"]).exists())

    def test_first_install_kept_and_dry_run_lists_hold_without_writes(self):
        self.holds()
        self.plan("packages.list", "vectorcraft-bin\n")
        self.mock("pacman", 'exit 0')
        self.mock("paru", 'printf "%s\\n" "$*" >> "$CALLS"')
        r = self.shell('_install_list "$SYSUP_PLAN_DIR/packages.list"')
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertEqual(self.calls(), ["-S --needed --noconfirm --useask --ask=4 vectorcraft-bin"])
        Path(self.env["CALLS"]).unlink()
        self.mock("hostname", 'echo desktop')
        before = sorted(str(p.relative_to(self.home)) for p in self.home.rglob("*"))
        r = self.cli("--dry-run", "--update")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("vectorcraft-bin", r.stdout)
        self.assertEqual(before, sorted(str(p.relative_to(self.home)) for p in self.home.rglob("*")))
        self.assertFalse(Path(self.env["CALLS"]).exists())


class FollowupReviewTests(FixtureCase):
    def repo(self):
        repo = self.home / "Projects/dots"
        repo.mkdir(parents=True, exist_ok=True)
        return repo

    def test_missing_list_and_failed_index_do_not_install(self):
        repo = self.repo()
        self.mock("pacman", "exit 0")
        r = self.shell('_install_list "$DOTS_DIR/missing.list"')
        self.assertNotEqual(r.returncode, 0)
        (repo / "packages.list").write_text("wanted\n")
        self.mock("pacman", "exit 19")
        r = self.shell('if _install_list "$DOTS_DIR/packages.list"; then echo BAD; fi; echo "READY:$_PKG_INDEX_READY"')
        self.assertNotIn("BAD", r.stdout)
        self.assertIn("READY:false", r.stdout)
        self.assertFalse(Path(self.env["CALLS"]).exists())

    def test_retry_requeries_partial_install(self):
        (self.repo() / "packages.list").write_text("first\nsecond\n")
        self.mock("pacman", '[[ ! -f "$CALLS.partial" ]] || echo first; exit 0')
        self.mock("paru", '''
printf '%s\n' "$*" >> "$CALLS"
if [[ ! -f "$CALLS.partial" ]]; then
    : > "$CALLS.partial"
    exit 1
fi
''')
        r = self.shell('if _install_list "$DOTS_DIR/packages.list"; then exit 99; fi; _install_list "$DOTS_DIR/packages.list"')
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertEqual(Path(self.env["CALLS"]).read_text().splitlines(),
                         ["-S --needed --noconfirm --useask --ask=4 first second", "-S --needed --noconfirm --useask --ask=4 second"])

    def test_installer_cannot_consume_next_command(self):
        (self.repo() / ".install-scripts.list").write_text(
            'read -r consumed || true; echo FIRST\necho SECOND')
        r = self.shell('run_install_scripts; print_recap')
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("\nFIRST\n", r.stdout)
        self.assertIn("\nSECOND\n", r.stdout)
        self.assertEqual(r.stdout.count("✓ installer:"), 2)

    def test_malware_gate_requires_lists_and_detects_campaign(self):
        repo = self.repo()
        campaign = self.home / ".local/share/aur-malware-check/data/campaigns/example"
        campaign.mkdir(parents=True)
        (campaign / "packages.txt").write_text("bad.pkg\n")
        common = self.plan("paru-install.list", "safe\n# comment\nbad.pkg\n")
        body = '_update_malware_defs() { :; }; _check_packages_against_malware'
        r = self.shell(body)
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("MALWARE GATE", r.stderr)
        common.write_text("safe\nsafe-too\n")
        r = self.shell(body)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        common.unlink()
        r = self.shell(body)
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("cannot read", r.stderr)

    def test_database_failure_reaches_recap(self):
        self.mock("pacman", 'echo "error: broken dependency"; exit 1')
        r = self.shell('check_pacman_db; echo CONTINUED; print_recap')
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("CONTINUED", r.stdout)
        self.assertIn("✗ pacman-database", r.stdout)
        self.assertIn("broken dependency", r.stdout)

    def test_firmware_exit_codes_and_refresh_failure(self):
        for refresh, query, failed in [(0, 0, False), (0, 2, False), (2, 2, False),
                                        (1, 2, True), (0, 1, True), (0, 3, True)]:
            with self.subTest(refresh=refresh, query=query):
                self.mock("fwupdmgr", f'if [[ "$1" == refresh ]]; then exit {refresh}; fi; echo QUERY; exit {query}')
                r = self.shell('check_firmware; echo CONTINUED; print_recap')
                self.assertEqual(r.returncode != 0, failed, r.stdout + r.stderr)
                self.assertIn("CONTINUED", r.stdout)
                if query not in (0, 2):
                    self.assertNotIn("no firmware updates", r.stdout)

    def test_update_preserves_failure_detail(self):
        r = self.shell('''
refresh_mirrors() { :; }
_syuu() { SYUU_FAIL_DETAIL="AUR build failed: example"; return 1; }
system_update
print_recap
''')
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("(AUR build failed: example)", r.stdout)

    def test_batch_malware_matching_is_literal_and_fails_on_missing_file(self):
        definitions = self.root / "definitions"
        definitions.write_text("bad.pkg\nother\n")
        body = f'_infected_packages {shlex.quote(str(definitions))} <<< $\'badXpkg\\nbad.pkg\\nsafe\''
        r = self.shell(body)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(r.stdout, "bad.pkg\n")
        r = self.shell('_infected_packages "$HOME/missing" <<< safe')
        self.assertNotEqual(r.returncode, 0)

    def test_automount_escapes_fields_and_uses_user_ids(self):
        self.mock("id", '[[ "$1" == -u ]] && echo 1234 || echo 2345')
        self.mock("lsblk", '''
case "$*" in
    '-rno NAME,MOUNTPOINT') echo 'testdrive /unused' ;;
    '-Pno NAME,FSTYPE,LABEL,UUID') echo 'NAME="testdrive" FSTYPE="vfat" LABEL="Test" UUID="sysup-test-unique-uuid"' ;;
esac
''')
        self.mock("sudo", '''
if [[ "$1" == tee ]]; then
    cat >> "$CALLS"
fi
exit 0
''')
        r = self.shell('_confirm() { return 0; }; automount_disks <<< "/mnt/My Disk"')
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        written = Path(self.env["CALLS"]).read_text()
        self.assertIn(r"/mnt/My\040Disk", written)
        self.assertNotIn("/mnt/My Disk", written)
        self.assertIn("uid=1234,gid=2345", written)
        r = self.shell("source \"$_AUTOMOUNT_LIB\"; _fstab_escape $'/mnt/a\\tb\\\\c'")
        self.assertEqual(r.stdout, r"/mnt/a\011b\134c")


class ReviewFollowupTests(FixtureCase):
    def test_bootstrap_without_actions_lists_ids(self):
        r = self.shell('detect_machine() { MACHINE=desktop; }\n_ensure_dots_repo() { echo BAD_CONTINUED; }\nbootstrap')
        self.assertNotEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("sysup --actions A,B (IDs: sources install", r.stderr)
        self.assertNotIn('BAD_CONTINUED', r.stdout)

    def test_bare_invocation_prints_usage(self):
        self.mock("vj", 'echo BAD_VJ')
        r = self.cli()
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("Usage: sysup", r.stdout)
        self.assertNotIn('BAD_VJ', r.stdout)
        self.assertFalse(Path(self.env["CALLS"]).exists())

    def _menu_fzf(self):
        # Single-select screens answer the next word of $KEYS (ESC = Esc key);
        # the action list answers the IDs in $PICK (ESC as PICK = Esc).
        self.mock("fzf", 'echo "fzf $*" >> "$CALLS"\n'
                         'if [[ " $* " == *" --no-multi "* ]]; then\n'
                         '  n=$(cat "$CALLS.n" 2>/dev/null || echo 0); echo $((n+1)) > "$CALLS.n"\n'
                         '  k=$(echo $KEYS | cut -d" " -f$((n+1))); [ "$k" = ESC ] && exit 130\n'
                         '  grep -- "^$k\t"; exit 0\n'
                         'fi\n'
                         '[ "$PICK" = ESC ] && exit 130\n'
                         'in=$(cat); [ -n "${HDR:-}" ] && grep -e "^\t" -e "^RUN\t" <<< "$in"\n'
                         'for id in $PICK; do grep "^$id\t" <<< "$in"; done')

    MENU_PY = ('_py() { [ "$1" = menu ] || return 1\n'
               "  printf 'sources\\troutine\\tRefresh\\t\\tdesc\\nfish\\ttools\\tFish\\tnever run\\tdesc2\\n'"
               '\n  printf "py %s\\n" "$*" >> "$CALLS"; }\n'
               '_menu_run() { printf "run %s\\n" "${*:2}" >> "$CALLS"; }\n'
               '_menu_pause() { :; }\n')

    def menu(self, keys, pick=""):
        self._menu_fzf()
        self.env.update(KEYS=keys, PICK=pick, HDR="1")  # RUN/header rows are dropped
        r = self.shell(self.MENU_PY + '_menu\necho MENU_RETURNED')
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("MENU_RETURNED", r.stdout)
        return [l for l in Path(self.env["CALLS"]).read_text().splitlines() if not l.startswith("fzf ")]

    def test_menu_runs_actions_then_comes_back(self):
        calls = self.menu("actions check quit", pick="sources fish")
        self.assertIn("py menu sources install", calls[0])  # whole MENU_ORDER
        self.assertEqual(calls[1:], ["run --actions sources,fish", "run --check"])

    def test_menu_first_run_adds_never_run_once_actions(self):
        # fish is "never run" in MENU_PY; sources has no state
        calls = self.menu("first quit")
        self.assertEqual(calls[1:], ["run --actions sources,install,stow-symlinks,dms-import,services,fish"])

    def test_menu_options_toggle_and_pass_through(self):
        # adopt on, dry-run on, adopt off again, back, update
        calls = self.menu("options --adopt --dry-run --adopt ESC update quit")
        self.assertEqual(calls, ["run --update --dry-run"])

    def test_menu_escape_goes_back_or_quits(self):
        calls = self.menu("actions quit", pick="ESC")  # Esc in the action list: back, nothing run
        self.assertEqual([c for c in calls if c.startswith("run")], [])
        Path(self.env["CALLS"]).unlink(); Path(self.env["CALLS"] + ".n").unlink()
        self.assertEqual(self.menu("ESC"), [])  # Esc on the main screen quits

    def test_removed_flags_die_before_any_work(self):
        self.mock("git", 'echo "git $*" >> "$CALLS"')
        for flag in ("-i", "--interactive", "--pacnew", "--kernels", "--lostfiles"):
            r = self.cli(flag)
            self.assertNotEqual(r.returncode, 0, flag)
            self.assertIn(f"Unknown option: {flag}", r.stderr, flag)
        self.assertFalse(Path(self.env["CALLS"]).exists())  # no fetch, no plan

    def test_unreadable_conflict_and_flatpak_lists_fail(self):
        self.plan("paru-remove.list", "conflict\n")
        self.mock("flatpak", 'echo "flatpak $*" >> "$CALLS"')
        r = self.shell('''
_pkg_list() { return 1; }
_syuu() { return 0; }
_install_list() { return 0; }
clean_caches() { :; }
MACHINE=desktop
install_all
print_recap
''')
        self.assertNotEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("cannot read paru-remove.list", r.stdout)
        self.assertIn("cannot read flatpak-install.list", r.stdout)
        calls = Path(self.env["CALLS"])
        self.assertFalse(calls.exists() and "flatpak install" in calls.read_text())

    def test_automount_rejects_system_paths(self):
        self.mock("id", 'echo 1000')
        self.mock("lsblk", '''
case "$*" in
    '-rno NAME,MOUNTPOINT') echo 'testdrive /unused' ;;
    '-Pno NAME,FSTYPE,LABEL,UUID') echo 'NAME="testdrive" FSTYPE="vfat" LABEL="Test" UUID="sysup-test-unique-uuid"' ;;
esac
''')
        self.mock("sudo", '[[ "$1" != tee ]] || cat >> "$CALLS"; exit 0')
        for bad in ("/usr", "/", "/mnt", "/mnt/../boot", "/mnt/./x", "/home/data"):
            r = self.shell(f'_confirm() {{ return 0; }}; automount_disks <<< {shlex.quote(bad)}')
            calls = Path(self.env["CALLS"])
            self.assertFalse(calls.exists() and "UUID=" in calls.read_text(), bad)
            self.assertIn("must be under /mnt", r.stdout + r.stderr, bad)


class RunPlanTests(FixtureCase):
    """sysup reads package lists and profile features from the vj run plan."""

    def fixture_vj_repo(self):
        repo = self.home / "Projects/dots"
        (repo / "profiles").mkdir(parents=True)
        (repo / "vj").symlink_to(Path(__file__).resolve().parents[1] / "vj")
        (repo / "packages.toml").write_text('[paru]\ninstall = ["fish"]\n')
        (repo / "profiles/desktop.toml").write_text(
            'hostname = "desktop"\ndotset = "none"\nfeatures = ["amd-gpu-tuning", "windows-vm"]\n')
        del self.env["SYSUP_PLAN_DIR"]
        return repo

    def test_has_feature(self):
        r = self.shell('SYSUP_FEATURES="amd-gpu-tuning windows-vm"\n'
                       '_has_feature windows-vm && echo YES; _has_feature windows && echo BAD; _has_feature linux-surface || echo NO')
        self.assertEqual(r.stdout.split(), ["YES", "NO"], r.stderr)

    def test_ensure_plan_generates_plan_and_profile(self):
        self.fixture_vj_repo()
        r = self.shell('_ensure_plan; echo "M=$MACHINE F=$SYSUP_FEATURES"; cat "$SYSUP_PLAN_DIR/paru-install.list"')
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("M=desktop F=amd-gpu-tuning windows-vm", r.stdout)
        self.assertIn("fish", r.stdout)

    def test_unknown_host_without_config_stops_with_hint(self):
        self.fixture_vj_repo()
        self.env["HOSTNAME"] = "friends-laptop"
        r = self.cli("--check")
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("sysup --profile", r.stdout + r.stderr)
        self.assertFalse(Path(self.env["CALLS"]).exists())

    def test_existing_plan_env_is_sourced(self):
        self.plan("env", "SYSUP_PROFILE=surface\nSYSUP_FEATURES=linux-surface\n")
        r = self.shell('_ensure_plan; echo "M=$MACHINE"; _has_feature linux-surface && echo SURF')
        self.assertEqual(r.stdout.split(), ["M=surface", "SURF"], r.stderr)

    def test_install_all_installs_plan_list_honouring_skip(self):
        self.plan("paru-install.list", "fish\nskipped\n")
        self.plan("paru-skip.list", "skipped\n")
        self.plan("paru-remove.list", "")
        self.plan("flatpak-install.list", "")
        self.mock("pacman", 'exit 0')
        self.mock("paru", 'printf "%s\\n" "paru $*" >> "$CALLS"; exit 0')
        r = self.shell('_syuu() { return 0; }\n_estimate_aur_builds() { :; }\nclean_caches() { :; }\n'
                       'command() { [[ "$2" == flatpak ]] && return 1; builtin command "$@"; }\n'
                       'MACHINE=desktop; install_all')
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        calls = Path(self.env["CALLS"]).read_text()
        self.assertIn("paru -S --needed --noconfirm --useask --ask=4 fish", calls)
        self.assertNotIn("skipped", calls.replace("skipped (skip list)", ""))

    def test_warn_unfolded_flags_real_dir_not_folded_link(self):
        for name in ("find", "realpath"):
            (self.bin / name).symlink_to(Path("/usr/bin") / name)
        dotset = self.root / "set"
        (dotset / "app/.config/app/sub").mkdir(parents=True)
        (dotset / "ok/.config/ok").mkdir(parents=True)
        (self.home / ".config/app/sub").mkdir(parents=True)  # unfolded: real dirs
        (self.home / ".config/ok").symlink_to(dotset / "ok/.config/ok")
        r = self.shell(f'cd "{dotset}"; _warn_unfolded app; _warn_unfolded ok')
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("'app' is unfolded at ~/.config/app ", r.stdout)
        self.assertNotIn("~/.config/app/sub", r.stdout)  # top-most dir only
        self.assertNotIn("'ok'", r.stdout)

    def test_pacnew_overwrite_losing_repos_is_restored(self):
        (self.bin / "comm").symlink_to("/usr/bin/comm")
        self.mock("sudo", '"$@"')
        conf, mirrors = self.root / "pacman.conf", self.root / "mirrorlist"
        conf.write_text("[options]\n[cachyos]\nInclude = x\n[core]\n")
        mirrors.write_text("Server = https://a/$repo\n")
        snap = self.root / "snap"
        snap.mkdir()
        r = self.shell(f'_PACMAN_CONF_FILES=("{conf}" "{mirrors}"); _snapshot_pacman_conf "{snap}"\n'
                       f'printf "[options]\\n[core]\\n" > "{conf}"; printf "#Server = x\\n" > "{mirrors}"\n'
                       f'_restore_lost_repos "{snap}"')
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("[cachyos]", conf.read_text())
        self.assertIn("Server = https://a", mirrors.read_text())
        self.assertIn("dropped [cachyos]", r.stdout)
        self.assertIn("dropped every Server line", r.stdout)
        r = self.shell(f'_restore_lost_repos "{snap}"')  # nothing lost now → silent
        self.assertNotIn("dropped", r.stdout)

    def test_surface_kernel_check(self):
        self.mock("uname", 'echo 7.3.1-1-cachyos')
        self.mock("pacman", 'exit 0')
        r = self.shell('SYSUP_FEATURES=linux-surface; check_surface_kernel; SYSUP_FEATURES=; check_surface_kernel')
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertEqual(r.stdout.count("not linux-surface"), 1)
        self.mock("uname", 'echo 7.2.11-arch1-1-surface')
        r = self.shell('SYSUP_FEATURES=linux-surface; check_surface_kernel')
        self.assertIn("running the surface kernel", r.stdout)

    def test_git_identity_kept_or_filled_with_defaults(self):
        (self.bin / "git").unlink()
        self.mock("git", 'f="$HOME/gitcfg"; k=$4; [ "$3" = user.name ] || [ "$3" = user.email ] || exit 1\n'
                         'if [ $# -eq 3 ]; then grep -m1 "^$3=" "$f" 2>/dev/null | cut -d= -f2-; exit 0; fi\n'
                         'echo "$3=$4" >> "$f"')
        r = self.shell('INTERACTIVE=false; setup_git_identity; setup_git_identity')
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        cfg = (self.home / "gitcfg").read_text()
        self.assertEqual(cfg, "user.name=Viridjan\nuser.email=viridjan@users.noreply.github.com\n")  # written once
        self.assertIn("git identity: Viridjan", r.stdout)

    def test_personal_steps_without_terminal_warn_instead_of_prompting(self):
        self.mock("fprintd-list", 'echo "Fingerprints for user x on Goodix:"; echo " - #0: right-index-finger"')
        self.mock("ykman", 'echo "PIN: Not set"')
        r = self.shell('INTERACTIVE=false; setup_fingerprint; setup_yubikey_pin')
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("fingerprint already enrolled", r.stdout)
        self.assertIn("YubiKey has no FIDO PIN — needs a terminal", r.stdout)
        self.mock("fprintd-list", 'echo "No devices available"')
        self.mock("ykman", 'echo "PIN: 8 attempt(s) remaining"')
        r = self.shell('INTERACTIVE=false; setup_fingerprint; setup_yubikey_pin')
        self.assertIn("no fingerprint reader", r.stdout)
        self.assertIn("FIDO PIN is set", r.stdout)

    def test_surface_secureboot_off_needs_nothing(self):
        self.mock("bootctl", 'echo "   Secure Boot: disabled (setup)"; exit 1')  # real one exits 1 here
        r = self.shell('SYSUP_FEATURES=linux-surface; setup_surface_secureboot; SYSUP_FEATURES=; setup_surface_secureboot')
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("Secure Boot disabled (setup) — no key to enroll", r.stdout)
        self.assertIn("not a Surface profile", r.stdout)
        self.assertNotIn("pacman", Path(self.env["CALLS"]).read_text() if Path(self.env["CALLS"]).exists() else "")

    def test_apply_display_sets_text_scale_only_when_given(self):
        self.mock("gsettings", 'echo "gsettings $*" >> "$CALLS"')
        r = self.shell('SYSUP_TEXT_SCALE=1.3 _apply_display; SYSUP_TEXT_SCALE= _apply_display')
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertEqual(Path(self.env["CALLS"]).read_text(),
                         "gsettings set org.gnome.desktop.interface text-scaling-factor 1.3\n")

    def test_protected_conflict_disables_auto_removal(self):
        self.plan("paru-install.list", "newkernel\nfish\n")
        self.mock("pacman", '[ "$1 $2" = "-Qq linux" ] && echo linux && exit 0\nexit 0')
        self.mock("paru", '#si\nif [ "$1" = -Si ]; then printf "Name : newkernel\\nConflicts With  : linux>=6  None\\nMaintainer : x\\n"; exit 0; fi\n'
                          'printf "%s\\n" "paru $*" >> "$CALLS"; exit 0')
        r = self.shell('_install_list "$SYSUP_PLAN_DIR/paru-install.list"')
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("not auto-removing protected conflicts: linux", r.stdout + r.stderr)
        self.assertIn("paru -S --needed --noconfirm newkernel fish", Path(self.env["CALLS"]).read_text())

    def test_flatpak_remove_list_uninstalls_installed_apps(self):
        self.plan("paru-install.list", "")
        self.plan("paru-remove.list", "")
        self.plan("flatpak-install.list", "")
        self.plan("flatpak-remove.list", "old.App\nabsent.App\n")
        self.mock("pacman", 'exit 0')
        self.mock("flatpak", 'echo "flatpak $*" >> "$CALLS"\n[ "$1 $2" = "info absent.App" ] && exit 1\nexit 0')
        r = self.shell('_syuu() { return 0; }\n_estimate_aur_builds() { :; }\nclean_caches() { :; }\nupdate_ollama() { :; }\n'
                       'MACHINE=desktop; install_all')
        calls = Path(self.env["CALLS"]).read_text()
        self.assertIn("flatpak uninstall -y --noninteractive old.App", calls, r.stdout + r.stderr)
        self.assertNotIn("uninstall -y --noninteractive absent.App", calls)


    def test_update_removes_only_installed_conflicts_and_demotes(self):
        self.plan("paru-remove.list", "gone\nhere\n")
        self.mock("pacman", '[[ "$1" == -Qq ]] && { [[ "$2" == here ]] && echo here || exit 1; }; exit 0')
        self.mock("sudo", 'echo "sudo $*" >> "$CALLS"')
        r = self.shell('refresh_mirrors() { :; }\n_demote_packages() { echo DEMOTED; }\n'
                       '_check_disk_space() { :; }\n_review_aur_updates() { :; }\n'
                       '_estimate_aur_builds() { :; }\n_syuu() { return 0; }\nsystem_update')
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        calls = Path(self.env["CALLS"]).read_text()
        self.assertIn("pacman -Rdd --noconfirm here", calls)
        self.assertNotIn("gone", calls)
        self.assertIn("DEMOTED", r.stdout)
        self.assertIn("sysup --actions install", r.stdout)

    def test_check_saves_results_for_vj(self):
        r = self.shell('detect_machine() { :; }\n'
                       'AUDIT_CHECKS=(a b)\na() { _record pacman-db fail; }\nb() { warn w1; _record firmware ok; }\n'
                       'check')
        self.assertNotEqual(r.returncode, 0, r.stdout + r.stderr)
        saved = (self.home / ".state/dots/last-check.tsv").read_text()
        self.assertEqual(saved, "pacman-db\tfail\nfirmware\tok\n@warnings\t1\n")

class ActionsTests(FixtureCase):
    """`--actions` runs exactly the given menu IDs without the menu (used by vj)."""

    STUBS = ('_ensure_dots_repo() { :; }\n_check_packages_against_malware() { :; }\n'
             'check_aur_malware() { :; }\nprint_recap() { :; }\n'
             'run_install_scripts() { echo BAD_INSTALLERS; }\n')

    def test_runs_only_selected_and_records_result(self):
        result = self.root / "result.tsv"
        r = self.shell(self.STUBS + f'SYSUP_RESULT_FILE={shlex.quote(str(result))}\n'
                       'setup_fish() { echo RAN_FISH; }\nSYSUP_ACTIONS=fish\nbootstrap')
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("RAN_FISH", r.stdout)
        self.assertNotIn("BAD_INSTALLERS", r.stdout)
        self.assertIn("action:fish\tok", result.read_text())

    def test_unknown_action_dies(self):
        r = self.shell(self.STUBS + 'SYSUP_ACTIONS="fish,bogus"\nbootstrap; echo BAD_CONTINUED')
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("unknown action: bogus", r.stderr)
        self.assertNotIn("BAD_CONTINUED", r.stdout)

    def test_phases_follow_selected_ids(self):
        r = self.shell(self.STUBS + '_run_phase() { [[ " $SKIP_PHASES " == *" $1 "* ]] || echo "RUN:$1"; }\n'
                       'SYSUP_ACTIONS="sources,audit"\nbootstrap')
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertEqual([l for l in r.stdout.split() if l.startswith("RUN:")], ["RUN:sources", "RUN:audit"])

    def test_cli_rejects_unknown_and_missing_value(self):
        for args in (("--actions=bogus",), ("--actions", "bogus")):
            with self.subTest(args=args):
                r = self.cli(*args)
                self.assertNotEqual(r.returncode, 0)
                self.assertIn("unknown action: bogus", r.stdout + r.stderr)
        r = self.cli("--actions")
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("--actions needs", r.stdout + r.stderr)


class DotsetTests(FixtureCase):
    """Stow packages come from the chosen dotfile set; scripts always from the repo."""

    def setup_set(self):
        repo = self.home / "Projects/dots"
        (repo / "scripts").mkdir(parents=True)
        dotset = self.root / "set"
        for pkg in ("alpha", "beta"):
            (dotset / pkg).mkdir(parents=True)
        self.plan("stow.list", "alpha\n")
        self.mock("stow", 'printf "%s %s\\n" "$PWD" "$*" >> "$CALLS"')
        return repo, dotset

    def test_deploy_stows_selected_set_packages_and_scripts(self):
        repo, dotset = self.setup_set()
        r = self.shell(f'git() {{ :; }}\nSYSUP_DOTSET_DIR={shlex.quote(str(dotset))}\ndeploy_dotfiles')
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        calls = Path(self.env["CALLS"]).read_text().splitlines()
        self.assertIn(f"{repo} --restow --no-folding -t {self.home} scripts", calls)
        self.assertIn(f"{dotset} --restow -t {self.home} alpha", calls)
        self.assertFalse(any("beta" in c for c in calls), calls)

    def test_dead_links_are_pruned_before_stow(self):
        # Stale links from the pre-dotsets layout made stow fail with "not owned".
        repo, dotset = self.setup_set()
        for name in ("find", "realpath"):
            (self.bin / name).symlink_to(Path("/usr/bin") / name)
        (self.home / ".config").mkdir(exist_ok=True)
        dead = self.home / ".config/gtk-4.0"
        dead.symlink_to(repo / "gtk-4.0/.config/gtk-4.0")
        self.mock("stow", f'[ -L {shlex.quote(str(dead))} ] && echo STALE >> "$CALLS"; :')
        r = self.shell(f'git() {{ :; }}\nSYSUP_DOTSET_DIR={shlex.quote(str(dotset))}\ndeploy_dotfiles')
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        calls = Path(self.env["CALLS"])
        self.assertFalse(calls.exists() and "STALE" in calls.read_text(), r.stdout)
        self.assertFalse(dead.is_symlink())

    def test_dotset_none_links_only_scripts(self):
        repo, _ = self.setup_set()
        r = self.shell('git() { :; }\nSYSUP_DOTSET_DIR=""\ndeploy_dotfiles')
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        calls = Path(self.env["CALLS"]).read_text().splitlines()
        self.assertEqual(calls, [f"{repo} --restow --no-folding -t {self.home} scripts"])

    def test_niri_links_point_into_set_and_profile_dir(self):
        dotset = self.root / "set"
        (dotset / "niri/.config/niri").mkdir(parents=True)
        (dotset / "niri/.config/niri/config.kdl").write_text("main")
        (dotset / "surface/.config/niri/cfg").mkdir(parents=True)
        (dotset / "surface/.config/niri/cfg/display.kdl").write_text("disp")
        r = self.shell(f'SYSUP_DOTSET_DIR={shlex.quote(str(dotset))}\nMACHINE=surface\n_stow_niri_cfg')
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        live = self.home / ".config/niri"
        self.assertEqual(Path(os.readlink(live / "config.kdl")), dotset / "niri/.config/niri/config.kdl")
        self.assertEqual(Path(os.readlink(live / "cfg/display.kdl")), dotset / "surface/.config/niri/cfg/display.kdl")

    def test_dms_sync_without_dotset_warns_and_copies_nothing(self):
        live = self.home / ".config/niri/dms"
        live.mkdir(parents=True)
        (live / "binds.kdl").write_text("live")
        r = self.shell('SYSUP_DOTSET_DIR=""\ndms_import; dms_export')
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertEqual(r.stdout.count("no dotfile set"), 2, r.stdout)
        self.assertEqual((live / "binds.kdl").read_text(), "live")


class BuildPriorityTests(FixtureCase):
    """Package builds must not outrank games: lowest CPU and idle I/O priority."""

    def setUp(self):
        super().setUp()
        self.mock("paru", 'echo "paru NICE=$(nice) LC=${LC_TIME:-unset} $*" >> "$CALLS"; exit 0')
        self.mock("pacman", "exit 0")

    def calls(self):
        return [l for l in Path(self.env["CALLS"]).read_text().splitlines() if l.startswith("paru ")]

    def test_install_runs_paru_at_lowest_priority(self):
        self.plan("pkgs.list", "one\n")
        r = self.shell('_install_list "$SYSUP_PLAN_DIR/pkgs.list"')
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("paru NICE=19", self.calls()[0])

    def test_upgrade_runs_at_lowest_priority_with_c_time(self):
        r = self.shell('_estimate_aur_builds() { :; }\n_syuu')
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertTrue(self.calls()[0].startswith("paru NICE=19 LC=C -Syuu"), self.calls())


class OllamaUpdateTests(FixtureCase):
    """Updates re-pull the models, then rebuild each Modelfile, only where wanted."""

    def setUp(self):
        super().setUp()
        self.mock("ollama", 'printf "%s\\n" "ollama $*" >> "$CALLS"; exit 0')
        self.mock("systemctl", 'exit 0')
        mf = self.home / "Projects/dots/scripts/.local/share/ollama"
        mf.mkdir(parents=True)
        (mf / "qwen3.5.Modelfile").write_text("FROM x\n")

    def calls(self):
        f = Path(self.env["CALLS"])
        return [l.split(" -f ")[0] for l in f.read_text().splitlines()
                if l.startswith("ollama ")] if f.exists() else []

    def test_update_pulls_then_rebuilds_modelfile(self):
        r = self.shell('SYSUP_FEATURES="ollama-model"; update_ollama')
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertEqual(self.calls(), ["ollama pull qwen3.5", "ollama create qwen3.5"])

    def test_failed_pull_is_recorded(self):
        self.mock("ollama", 'printf "%s\\n" "ollama $*" >> "$CALLS"; exit 1')
        r = self.shell('SYSUP_FEATURES="ollama-model"; update_ollama; printf "%s\\n" "${WARNINGS[@]}"')
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("ollama pull qwen3.5", r.stdout)

    def test_update_skips_without_feature_or_service(self):
        r = self.shell('SYSUP_FEATURES=""; update_ollama')
        self.assertEqual((r.returncode, self.calls()), (0, []), r.stdout + r.stderr)
        self.mock("systemctl", 'exit 3')
        r = self.shell('SYSUP_FEATURES="ollama-model"; update_ollama')
        self.assertEqual((r.returncode, self.calls()), (0, []), r.stdout + r.stderr)

class MpdServiceTests(FixtureCase):
    def test_services_creates_mpd_data_directory_before_start(self):
        self.plan('systemd-enable.list', '')
        self.plan('systemd-user.list', 'mpd\n')
        self.mock('systemctl', '''
[[ "$*" == "--user enable --now mpd" ]] || exit 1
[[ -d "$HOME/.local/share/mpd" ]] || exit 1
''')
        r = self.shell('enable_services; print_recap')
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertTrue((self.home / '.local/share/mpd').is_dir())


class InstallFailureDetailTests(FixtureCase):
    def run_install(self, error):
        self.plan("paru-install.list", "dms-shell\n")
        self.plan("flatpak-install.list", "")
        self.mock("pacman", "exit 0")
        self.mock("flatpak", "exit 0")
        self.mock("paru", 'echo attempt >> "$CALLS"\nprintf "%s\\n" ' + shlex.quote(error) + '\nexit 1')
        return self.shell('''
_upgrade_system() { :; }
refresh_mirrors() { echo REFRESHED; }
update_ollama() { :; }
install_user_tools() { :; }
clean_caches() { echo CLEANED; }
if install_all; then :; fi
print_recap
''')

    def test_conflict_skips_mirror_retry_and_reports_cause(self):
        r = self.run_install("error: failed to prepare transaction (conflicting dependencies)")
        self.assertNotEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertNotIn("REFRESHED", r.stdout)
        self.assertEqual(Path(self.env["CALLS"]).read_text().count("attempt"), 1)
        self.assertIn("CLEANED", r.stdout)
        recap = r.stdout.split("Results")[-1]
        self.assertIn("conflicting dependencies", recap)

    def test_paru_aur_conflict_skips_mirror_retry(self):
        # paru's own AUR conflict check, not pacman's wording (2026-11-01 log).
        r = self.run_install("error: can not install conflicting packages with --noconfirm")
        self.assertNotIn("REFRESHED", r.stdout)
        self.assertEqual(Path(self.env["CALLS"]).read_text().count("attempt"), 1)
        self.assertIn("conflicting packages", r.stdout.split("Results")[-1])

    def test_recorded_package_failure_does_not_abort_the_run(self):
        # A failure already recorded in the recap must not trip errexit/the ERR
        # trap and skip later phases ("remaining work aborted").
        self.plan("paru-install.list", "dms-shell\n")
        self.plan("flatpak-install.list", "")
        self.mock("pacman", "exit 0")
        self.mock("flatpak", "exit 0")
        self.mock("paru", 'echo "error: failed to prepare transaction (conflicting dependencies)"; exit 1')
        r = self.shell('''
_upgrade_system() { :; }
update_ollama() { :; }
install_user_tools() { :; }
clean_caches() { :; }
install_all
echo NEXT_PHASE
print_recap
''')
        self.assertIn("NEXT_PHASE", r.stdout, r.stdout + r.stderr)
        self.assertNotEqual(r.returncode, 0, r.stdout + r.stderr)

    def test_download_failure_retries_and_reports_cause(self):
        r = self.run_install("error: failed retrieving file 'example.pkg.tar.zst'")
        self.assertNotEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("REFRESHED", r.stdout)
        self.assertEqual(Path(self.env["CALLS"]).read_text().count("attempt"), 2)
        self.assertIn("failed retrieving file", r.stdout.split("Results")[-1])


class ProvidedNameTests(FixtureCase):
    """A listed name answered by a provider (vectorcraft → vectorcraft-bin) is not installed."""

    def setUp(self):
        super().setUp()
        # pacman -Qq resolves provides: asking for X prints the provider's name.
        self.mock("pacman", '''
printf "%s\\n" "pacman $*" >> "$CALLS"
case "$*" in
  "-Qq vectorcraft"|"-Qqe vectorcraft") echo vectorcraft-bin ;;
  "-Qq sddm"|"-Qqe sddm") echo sddm ;;
  *) exit 1 ;;
esac''')
        self.mock("sudo", 'printf "%s\\n" "sudo $*" >> "$CALLS"; exit 0')

    def calls(self):
        return Path(self.env["CALLS"]).read_text()

    def test_remove_skips_provider_and_removes_exact_name(self):
        self.plan("paru-remove.list", "vectorcraft\nsddm\n")
        r = self.shell('_remove_conflicts; printf "W:%s\\n" "${WARNINGS[@]}"')
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("sudo pacman -Rdd --noconfirm sddm", self.calls())
        self.assertNotIn("-Rdd --noconfirm vectorcraft", self.calls())
        self.assertNotIn("failed to remove", r.stdout)

    def test_demote_skips_provider(self):
        self.plan("paru-demote.list", "vectorcraft\n")
        r = self.shell('_demote_packages')
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertNotIn("Demoting", r.stdout)


class NvidiaNiriTests(FixtureCase):
    """One-time niri VRAM fix: written via sudo only on profiles with the nvidia feature."""

    def setUp(self):
        super().setUp()
        self.mock("sudo", 'printf "%s\\n" "sudo $*" >> "$CALLS"; [[ "$1" == tee ]] && cat > "$CALLS.tee"; exit 0')

    def test_writes_profile_with_feature(self):
        r = self.shell('SYSUP_FEATURES="nvidia"; _act nvidia-niri setup_nvidia_niri; printf "%s\\n" "${_RESULT_STATES[@]}"')
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        calls = Path(self.env["CALLS"]).read_text()
        self.assertIn("sudo tee /etc/nvidia/nvidia-application-profiles-rc.d/", calls)
        written = Path(self.env["CALLS"] + ".tee").read_text()
        self.assertIn('"GLVidHeapReuseRatio", "value": 0', written)
        self.assertIn('"matches": "niri"', written)
        self.assertTrue(r.stdout.strip().endswith("ok"), r.stdout)

    def test_skips_without_feature(self):
        r = self.shell('SYSUP_FEATURES="amd-gpu-tuning"; _act nvidia-niri setup_nvidia_niri; printf "%s\\n" "${_RESULT_STATES[@]}"')
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertFalse(Path(self.env["CALLS"]).exists())
        self.assertTrue(r.stdout.strip().endswith("skip"), r.stdout)


class VmSetupFeatureTests(FixtureCase):
    """setup_vms must not touch /mnt/data on profiles without windows-vm."""

    def test_skips_without_feature(self):
        self.mock("docker", 'printf "%s\\n" "docker $*" >> "$CALLS"; exit 0')
        self.mock("mkdir", 'printf "%s\\n" "mkdir $*" >> "$CALLS"; exit 0')
        r = self.shell('SYSUP_FEATURES="linux-surface"; _act vms setup_vms; printf "%s\\n" "${_RESULT_STATES[@]}"')
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        calls = Path(self.env["CALLS"]).read_text() if Path(self.env["CALLS"]).exists() else ""
        self.assertNotIn("/mnt/data", calls)
        self.assertNotIn("docker", calls)
        self.assertTrue(r.stdout.strip().endswith("skip"), r.stdout)


if __name__ == "__main__":
    unittest.main()


class MissingManagersTests(FixtureCase):
    def test_npm_is_installed_before_global_tools(self):
        self.plan("npm-install.list", "example-tool\n")
        self.mock("sudo", '''[[ "$*" == "pacman -S --needed --noconfirm npm" ]] || exit 91; cat > "$(dirname "$0")/npm" <<'EOF'
#!/bin/bash
[[ "$1" == ls ]] && exit 0
echo "npm $*" >> "$CALLS"
EOF
chmod +x "$(dirname "$0")/npm"''')
        (self.bin / "chmod").symlink_to("/usr/bin/chmod")
        r = self.shell('install_user_tools')
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        calls = Path(self.env["CALLS"])
        self.assertTrue(calls.exists(), r.stdout + r.stderr)
        self.assertIn("npm i -g example-tool", calls.read_text())

    def test_flatpak_is_installed_and_flathub_added_before_apps(self):
        self.plan("flatpak-install.list", "org.example.App\n")
        (self.bin / "flatpak").unlink()
        (self.bin / "chmod").symlink_to("/usr/bin/chmod")
        self.mock("sudo", '''[[ "$*" == "pacman -S --needed --noconfirm flatpak" ]] || exit 91; cat > "$(dirname "$0")/flatpak" <<'EOF'
#!/bin/bash
[[ "$1" == info ]] && exit 1
echo "flatpak $*" >> "$CALLS"
EOF
chmod +x "$(dirname "$0")/flatpak"''')
        r = self.shell('_upgrade_system() { :; }; _install_list() { :; }; clean_caches() { :; }; install_all')
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        calls = Path(self.env["CALLS"])
        self.assertTrue(calls.exists(), r.stdout + r.stderr)
        lines = calls.read_text().splitlines()
        self.assertIn("flatpak install -y flathub org.example.App", lines)
        self.assertLess(lines.index("flatpak remote-add --if-not-exists flathub https://flathub.org/repo/flathub.flatpakrepo"), lines.index("flatpak install -y flathub org.example.App"))

    def test_failed_npm_install_is_recorded_without_running_tools(self):
        self.plan("npm-install.list", "example-tool\n")
        self.mock("sudo", "exit 42")
        r = self.shell('install_user_tools; print_recap')
        self.assertNotEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("npm-prerequisite", r.stdout)

    def test_existing_npm_is_used_without_system_install(self):
        self.plan("npm-install.list", "example-tool\n")
        self.mock("npm", '[[ "$1" == ls ]] && exit 0; [[ "$*" == "config get prefix" ]] && { echo "$HOME/.local"; exit 0; }; echo "npm $*" >> "$CALLS"')
        r = self.shell('install_user_tools')
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertEqual(Path(self.env["CALLS"]).read_text(), "npm i -g example-tool\n")

    def test_npm_prefix_moved_to_local_before_installs(self):
        # npm's default prefix /usr makes `npm i -g` fail EACCES without sudo.
        self.plan("npm-install.list", "example-tool\n")
        self.mock("npm", '[[ "$1" == ls ]] && exit 0; [[ "$*" == "config get prefix" ]] && { echo /usr; exit 0; }; echo "npm $*" >> "$CALLS"')
        r = self.shell('install_user_tools')
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        home = self.env["HOME"]
        self.assertEqual(Path(self.env["CALLS"]).read_text().splitlines(),
                         [f"npm config set prefix {home}/.local", "npm i -g example-tool"])

    def test_failed_npm_prefix_skips_installs(self):
        self.plan("npm-install.list", "example-tool\n")
        self.mock("npm", '[[ "$1" == ls ]] && exit 0; [[ "$*" == "config get prefix" ]] && { echo /usr; exit 0; }; echo "npm $*" >> "$CALLS"; [[ "$1" == config ]] && exit 1; exit 0')
        r = self.shell('install_user_tools; print_recap')
        self.assertNotEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("npm-prefix", r.stdout)
        self.assertNotIn("npm i -g", Path(self.env["CALLS"]).read_text())

    def test_failed_tool_install_shows_error_output(self):
        self.plan("npm-install.list", "example-tool\n")
        self.mock("npm", '[[ "$1" == ls ]] && exit 0; [[ "$*" == "config get prefix" ]] && { echo "$HOME/.local"; exit 0; }; echo "npm error code EACCES" >&2; exit 1')
        r = self.shell('install_user_tools; printf "W:%s\\n" "${WARNINGS[@]}"')
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("      npm error code EACCES", r.stdout)
        self.assertIn("W:failed to install: example-tool (npm): npm error code EACCES", r.stdout)

    def test_empty_lists_do_not_install_managers(self):
        self.plan("npm-install.list", "")
        r = self.shell('install_user_tools')
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertFalse(Path(self.env["CALLS"]).exists())

    def test_caveman_action_attempts_to_install_missing_npm(self):
        self.mock("sudo", 'echo "sudo $*" >> "$CALLS"; exit 42')
        r = self.shell('setup_caveman_code; print_recap')
        self.assertNotEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertEqual(Path(self.env["CALLS"]).read_text(), "sudo pacman -S --needed --noconfirm npm\n")


class NiriFreshDeploymentTests(FixtureCase):
    def test_fresh_surface_deployment_provides_dms_includes_before_validation(self):
        import shutil
        niri = shutil.which("niri")
        if not niri:
            self.skipTest("niri is required for real configuration validation")
        (self.bin / "niri").symlink_to(niri)
        dotset = SCRIPT.parents[3] / "dotsets/viridjan"
        r = self.shell(f'SYSUP_DOTSET_DIR={shlex.quote(str(dotset))}; MACHINE=surface; _stow_niri_cfg')
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        live = self.home / ".config/niri"
        self.assertTrue((live / "config.kdl").exists(), r.stdout + r.stderr)
        self.assertTrue((live / "dms/colors.kdl").is_file())
        result = subprocess.run([niri, "validate", "-c", str(live / "config.kdl")], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


class CodexBootstrapTests(FixtureCase):
    def test_package_install_runs_codex_standalone_installer(self):
        (self.bin / "codex").unlink()
        r = self.shell('''
_upgrade_system() { :; }
_install_list() { :; }
install_user_tools() { :; }
clean_caches() { :; }
_run_pinned_sh() {
    echo "INSTALLER:$1"
    mkdir -p "$HOME/.local/bin"
    printf '#!/bin/bash\\necho codex-cli-test\\n' > "$HOME/.local/bin/codex"
    /usr/bin/chmod +x "$HOME/.local/bin/codex"
}
install_all
''')
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("INSTALLER:https://chatgpt.com/codex/install.sh", r.stdout)
        self.assertTrue((self.home / ".local/bin/codex").is_file())


class ProjectBuildTests(FixtureCase):
    """projects.toml `build`: pull fast-forward, rebuild only when HEAD moved."""

    def setUp(self):
        super().setUp()
        self.git = shutil.which("git", path="/usr/bin:/bin")
        self.origin = self.home / "origin"
        self.work = self.home / "Projects/app"
        g = lambda *a, cwd=None: subprocess.run([self.git, *a], cwd=cwd, check=True,
                                               capture_output=True, env={**self.env, "PATH": "/usr/bin:/bin"})
        self.g = g
        g("init", "-q", "-b", "main", str(self.origin))
        g("-c", "user.name=t", "-c", "user.email=t@t", "commit", "-q", "--allow-empty", "-m", "one", cwd=self.origin)
        g("clone", "-q", str(self.origin), str(self.work))
        self.plan("project-builds.list", 'app\techo built >> "$CALLS"\n')

    def run_update(self):
        return self.shell(f'git() {{ {self.git} "$@"; }}\nupdate_projects\nprint_recap')

    def builds(self):
        calls = Path(self.env["CALLS"])
        return calls.read_text().count("built") if calls.exists() else 0

    def test_builds_once_then_only_after_new_commit(self):
        r = self.run_update()
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertEqual(self.builds(), 1)
        self.run_update()
        self.assertEqual(self.builds(), 1)
        self.g("-c", "user.name=t", "-c", "user.email=t@t", "commit", "-q", "--allow-empty", "-m", "two", cwd=self.origin)
        r = self.run_update()
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertEqual(self.builds(), 2)

    def test_local_changes_are_not_pulled_or_built(self):
        (self.work / "wip.txt").write_text("mine")
        r = self.run_update()
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertEqual(self.builds(), 0)
        self.assertIn("local changes", r.stdout)

    def test_failed_build_is_recorded_without_aborting(self):
        self.plan("project-builds.list", "app\tfalse\n")
        r = self.shell(f'git() {{ {self.git} "$@"; }}\nupdate_projects\necho AFTER\nprint_recap')
        self.assertIn("AFTER", r.stdout)
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("build:app", r.stdout)
        self.assertFalse((self.home / ".local/state/dots/builds/app").exists())


class PostRunFixTests(FixtureCase):
    """Fixes offered after the recap: answers come from stdin, _fix_tty is forced."""

    def answer(self, body, answers):
        return subprocess.run(["/usr/bin/bash", "-c", 'source "$SCRIPT"\n_fix_tty() { return 0; }\n' + body],
                              env=self.env, text=True, capture_output=True, timeout=10, input=answers)

    def stow_fixture(self, live, repo_text="same"):
        repo = self.home / "Projects/dots"
        (repo / "sample").mkdir(parents=True)
        (repo / "sample/config file").write_text(repo_text)
        (self.home / "config file").write_text(live)
        # -n reports the conflict while the live file exists; a real stow logs its args.
        self.mock("stow", '''
case " $* " in
  *" -n "*) [[ -f "$HOME/config file" ]] && { echo '  * cannot stow sample/config file over existing target config file since neither a link nor a directory and --adopt not specified' >&2; exit 1; }; exit 0 ;;
  *) printf 'stow %s\\n' "$*" >> "$CALLS" ;;
esac''')
        for name in ("cmp", "diff", "realpath"):
            (self.bin / name).symlink_to(Path("/usr/bin") / name)
        return repo

    def queue_stow(self):
        return 'cd "$HOME/Projects/dots"; _queue_fix stow "$PWD"$\'\\x1f--restow\\x1f-t\\x1f\'"$HOME"$\'\\x1fsample\'\nprint_recap\n'

    def test_identical_conflict_becomes_link(self):
        self.stow_fixture("same")
        r = self.answer("_init_runtime\n" + self.queue_stow(), "\n")
        self.assertFalse((self.home / "config file").exists(), r.stdout + r.stderr)
        self.assertIn("stow --restow -t", Path(self.env["CALLS"]).read_text())
        self.assertIn("1 applied", r.stdout)

    def test_live_wins_copies_into_repo_with_backup(self):
        repo = self.stow_fixture("live edit", "repo text")
        r = self.answer("_init_runtime\n" + self.queue_stow(), "l\n")
        self.assertEqual((repo / "sample/config file").read_text(), "live edit", r.stdout + r.stderr)
        backups = list((self.home / ".state/dots").glob("fix-backup-*/repo/config file"))
        self.assertEqual([b.read_text() for b in backups], ["repo text"])

    def test_skip_leaves_conflict_alone(self):
        self.stow_fixture("live edit", "repo text")
        r = self.answer("_init_runtime\n" + self.queue_stow(), "\n")
        self.assertEqual((self.home / "config file").read_text(), "live edit")
        self.assertIn("0 applied, 1 left", r.stdout)

    def test_no_terminal_offers_nothing(self):
        self.stow_fixture("same")
        r = self.shell("_init_runtime\n" + self.queue_stow())
        self.assertTrue((self.home / "config file").exists())
        self.assertNotIn("Fixes (", r.stdout)

    def test_unlisted_goes_to_packages_toml(self):
        repo = self.home / "Projects/dots"
        repo.mkdir(parents=True)
        (repo / "vj").symlink_to(Path(__file__).resolve().parents[1] / "vj")
        (repo / "packages.toml").write_text('[paru]\ninstall = [\n    "a",  # keep\n]\n')
        self.mock("pacman", '[[ "$1" == -Qq ]] && echo "$3"')
        r = self.answer('_queue_fix unlisted newpkg\n_offer_fixes\n', "p\n")
        text = (repo / "packages.toml").read_text()
        self.assertIn('"newpkg"', text, r.stdout + r.stderr)
        self.assertIn("# keep", text)

    def test_conflict_names_only_installed_exact(self):
        log = self.root / "log"
        log.write_text(":: foo-bin-1.2-1 and foo-1.0-1 are in conflict\n"
                       ":: Conflicts found:\n    bar-bin: bar\nerror: unresolvable package conflicts detected\n")
        self.mock("pacman", 'case "$3" in foo|bar) echo "$3" ;; *) exit 1 ;; esac')
        r = self.shell(f'_conflict_names "{log}"')
        self.assertEqual(r.stdout.split(), ["bar", "foo"], r.stderr)

    def test_failed_build_is_queued(self):
        log = self.root / "log"
        log.write_text("error: packages failed to build: broken-pkg-1.0-1\n")
        r = self.shell(f'_init_runtime\n_queue_aur_fails "{log}"\nprintf "%s\\n" "${{_FIXES[@]}}"')
        self.assertIn("aur\tbroken-pkg", r.stdout, r.stderr)


class RepoCurrentTests(FixtureCase):
    def run_check(self, behind, answer):
        self.mock("git", f'''
case "$*" in
  *"rev-parse"*) echo origin/main ;;
  *"rev-list"*) echo {behind} ;;
  *" pull "*) echo pull >> "$CALLS" ;;
esac''')
        self.mock("timeout", 'shift; "$@"')
        return subprocess.run(["/usr/bin/bash", "-c", 'source "$SCRIPT"\n_fix_tty() { return 0; }\n'
                               'exec() { echo "EXEC $*"; }\n_check_repo_current --update\necho DONE'],
                              env=self.env, text=True, capture_output=True, timeout=10, input=answer)

    def test_behind_pull_relaunches(self):
        r = self.run_check(3, "p\n")
        self.assertIn("pull", Path(self.env["CALLS"]).read_text())
        self.assertIn("EXEC " + str(self.home / "Projects/dots/scripts/.local/bin/sysup") + " --update", r.stdout)

    def test_behind_continue_does_not_pull(self):
        r = self.run_check(3, "c\n")
        self.assertFalse(Path(self.env["CALLS"]).exists())
        self.assertNotIn("EXEC", r.stdout)
        self.assertIn("DONE", r.stdout)

    def test_current_repo_asks_nothing(self):
        r = self.run_check(0, "p\n")
        self.assertFalse(Path(self.env["CALLS"]).exists())
        self.assertNotIn("behind", r.stdout + r.stderr)


class DmsRestartTests(FixtureCase):
    def run_upgrade(self, before, after, active=True):
        # pacman -Q prints the "before" versions until the upgrade writes a marker.
        self.mock("pacman", f'''[[ "$1" == -Q ]] || exit 1
[[ -f "$CALLS.upgraded" ]] && printf '{after}' || printf '{before}' ''')
        self.mock("systemctl", f'''[[ "$*" == *is-active* ]] && exit {0 if active else 3}
printf 'systemctl %s\\n' "$*" >> "$CALLS"''')
        return self.shell('''
_remove_conflicts() { :; }; _demote_packages() { :; }; _check_disk_space() { :; }
_review_aur_updates() { :; }; _estimate_aur_builds() { :; }
_syuu() { : > "$CALLS.upgraded"; }
_upgrade_system done upgrading''')

    def calls(self):
        p = Path(self.env["CALLS"])
        return p.read_text() if p.exists() else ""

    def test_restart_after_dms_upgrade(self):
        r = self.run_upgrade("dux-shell 1-1\\nquickshell 1-1\\n", "dux-shell 2-1\\nquickshell 1-1\\n")
        self.assertIn("systemctl --user restart dms.service", self.calls(), r.stdout + r.stderr)
        self.assertIn("updated: dux-shell", r.stdout)

    def test_no_restart_when_unchanged(self):
        self.run_upgrade("dux-shell 1-1\\n", "dux-shell 1-1\\n")
        self.assertNotIn("restart", self.calls())

    def test_no_restart_when_dms_not_running(self):
        self.run_upgrade("dux-shell 1-1\\n", "dux-shell 2-1\\n", active=False)
        self.assertNotIn("restart", self.calls())


class ClaudePluginUpdateTests(FixtureCase):
    def test_updates_each_user_plugin(self):
        self.mock("claude", '''printf 'claude %s\\n' "$*" >> "$CALLS"
[[ "$*" == "plugin list --json" ]] && echo '[{"id":"a@m","scope":"user"},{"id":"p@m","scope":"project"}]'
[[ "$*" == "plugin update a@m --scope user" ]] && exit 1
exit 0''')
        r = self.shell("update_claude_plugins; print_recap")
        calls = Path(self.env["CALLS"]).read_text()
        self.assertIn("claude plugin marketplace update", calls)
        self.assertIn("claude plugin update a@m --scope user", calls)
        self.assertNotIn("p@m", calls)
        self.assertIn("a@m", r.stdout)
        self.assertNotEqual(r.returncode, 0)

    def test_marketplace_failure_skips_updates(self):
        self.mock("claude", '''printf 'claude %s\\n' "$*" >> "$CALLS"
[[ "$*" == "plugin marketplace update" ]] && exit 1; exit 0''')
        self.shell("update_claude_plugins")
        self.assertNotIn("plugin update", Path(self.env["CALLS"]).read_text().replace("marketplace update", ""))


class SudoPrimeTests(FixtureCase):
    """--update/--yes ask for sudo once up front (2026-11-08: prompts timed out mid-run)."""
    def test_update_asks_once_and_warns_on_failure(self):
        self.mock("sudo", 'printf "%s\\n" "sudo $*" >> "$CALLS"; exit 1')
        r = self.shell('ACTION=--update; _sudo_prime; printf "%s\\n" "${WARNINGS[@]}"')
        self.assertEqual(Path(self.env["CALLS"]).read_text(),
                         "sudo -n true\nsudo -v -p     sudo password for %u: \n")
        self.assertIn("enter your password once", r.stdout)
        self.assertIn("no sudo ticket", r.stdout)

    def test_valid_ticket_skips_the_prompt(self):
        self.mock("sudo", 'printf "%s\\n" "sudo $*" >> "$CALLS"; exit 0')
        r = self.shell("ACTION=--update; _sudo_prime")
        self.assertEqual(Path(self.env["CALLS"]).read_text(), "sudo -n true\n")
        self.assertEqual(r.stdout, "")

    def test_other_actions_do_not_prompt(self):
        for action in ("--check", "--actions"):
            self.shell(f"ACTION={action}; _sudo_prime")
        self.assertFalse(Path(self.env["CALLS"]).exists())


class SudoFailureDetailTests(FixtureCase):
    """A sudo prompt nobody answered is named in the recap (2026-11-08)."""
    def test_upgrade_detail_names_sudo_timeout(self):
        log = self.root / "log"
        log.write_text("sudo: timed out reading password\nsudo: a password is required\n")
        r = self.shell(f'_syuu_fail_detail "{log}"')
        self.assertEqual(r.stdout.strip(), "sudo: timed out reading password (password not entered)")

    def test_build_failure_still_wins(self):
        log = self.root / "log"
        log.write_text("sudo: timed out reading password\nerror: packages failed to build: foo-1.0\n")
        r = self.shell(f'_syuu_fail_detail "{log}"')
        self.assertEqual(r.stdout.strip(), "AUR build failed: foo-1.0")

    def test_paccache_warning_names_missing_sudo(self):
        self.mock("sudo", "exit 1")
        self.mock("paccache", "exit 0")
        r = self.shell('clean_caches >/dev/null 2>&1 || true; printf "%s\\n" "${WARNINGS[@]}"')
        self.assertIn("paccache -rk2 failed: no sudo access (password not entered)", r.stdout)


class ConfigFlagTests(FixtureCase):
    """--profile / --pkg / --status / --skip-once against a fixture repo."""

    def setUp(self):
        super().setUp()
        repo = self.home / "Projects/dots"
        (repo / "profiles").mkdir(parents=True)
        (repo / "dotsets/mine/fish").mkdir(parents=True)
        (repo / "packages.toml").write_text('[paru]\ninstall = [\n    "a",  # keep\n]\n')
        (repo / "profiles/desktop.toml").write_text('hostname = "desktop"\ndotset = "mine"\n')
        self.cfg = self.root / "cfg.toml"
        self.env["SYSUP_CONFIG"] = str(self.cfg)
        self.env.pop("SYSUP_PLAN_DIR")
        self.mock("flatpak", "exit 1")

    def test_profile_writes_config(self):
        r = self.cli("--profile", "desktop", "--dotset", "none")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn('profile = "desktop"', self.cfg.read_text())
        self.assertIn('dotset = "none"', self.cfg.read_text())
        self.assertNotEqual(self.cli("--profile", "nope").returncode, 0)

    def test_pkg_targets(self):
        self.assertEqual(self.cli("--pkg", "shared", "newpkg").returncode, 0)
        self.assertIn('"newpkg"', (self.home / "Projects/dots/packages.toml").read_text())
        self.assertIn("# keep", (self.home / "Projects/dots/packages.toml").read_text())
        r = self.cli("--pkg", "ignore", "x", "com.example.App")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        text = self.cfg.read_text()
        self.assertIn('"paru" = ["x"]', text)
        self.assertIn('"flatpak" = ["com.example.App"]', text)
        r = self.cli("--pkg", "profile", "y")  # hostname desktop → profile desktop
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn('"y"', (self.home / "Projects/dots/profiles/desktop.toml").read_text())
        self.assertNotEqual(self.cli("--pkg", "bogus", "x").returncode, 0)

    def test_pkg_profile_without_profile_writes_nothing(self):
        self.env["HOSTNAME"] = "unknown-host"
        before = (self.home / "Projects/dots/profiles/desktop.toml").read_text()
        r = self.cli("--pkg", "profile", "y")
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("sysup --profile", r.stdout + r.stderr)
        self.assertEqual((self.home / "Projects/dots/profiles/desktop.toml").read_text(), before)

    def test_status_and_skip_once(self):
        self.assertEqual(self.cli("--skip-once", "fish").returncode, 0)
        r = self.cli("--status")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("profile: desktop", r.stdout)
        self.assertRegex(r.stdout, r"fish +skipped")
        self.assertNotEqual(self.cli("--skip-once", "audit").returncode, 0)

    def test_actions_stamp_only_ok_one_time_actions(self):
        r = self.shell('_RESULT_NAMES=(action:services action:fish action:audit)\n'
                       '_RESULT_STATES=(ok fail ok)\n_stamp_once')
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        text = self.cfg.read_text()
        self.assertRegex(text, r'"services" = \d{4}-\d\d-\d\d')
        self.assertNotIn("fish", text)
        self.assertNotIn("audit", text)
