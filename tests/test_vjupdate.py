"""Isolated regressions. VJUPDATE_SCRIPT can point at a pre-fix snapshot."""
import os
import fcntl
from pathlib import Path
import shlex
import subprocess
import tempfile
import unittest


SCRIPT = Path(os.environ.get("VJUPDATE_SCRIPT", Path(__file__).resolve().parents[1]
                             / "scripts/.local/bin/vjupdate")).resolve()


class FixtureCase(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="vjupdate-test-")
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.home = self.root / "home"
        self.home.mkdir()
        self.bin = self.root / "bin"
        self.bin.mkdir()
        # Restricted PATH: system/package commands cannot accidentally run.
        for name in ("bash", "cat", "grep", "sed", "awk", "cut", "tail", "head",
                     "tr", "sort", "tee", "date", "mkdir", "cp", "rm", "dirname",
                     "basename", "mktemp", "python3", "flock", "mv", "ln", "du", "xargs", "echo"):
            (self.bin / name).symlink_to(Path("/usr/bin") / name)
        for name in ("pacman", "paru", "sudo", "systemctl", "stow", "git",
                     "flatpak", "paccache", "curl", "pacman-key", "makepkg"):
            self.mock(name, 'printf "%s\\n" "$0 $*" >> "$CALLS"; exit 97')
        self.env = {**os.environ, "HOME": str(self.home), "PATH": str(self.bin),
                    "HOSTNAME": "desktop", "XDG_STATE_HOME": str(self.home / ".state"),
                    "CALLS": str(self.root / "calls"), "SCRIPT": str(SCRIPT)}
        self.env.pop("BASH_ENV", None)
        self.env.pop("SKIP_PHASES", None)

    def mock(self, name, body):
        f = self.bin / name
        if f.is_symlink():
            f.unlink()
        f.write_text("#!/bin/bash\n" + body + "\n")
        f.chmod(0o755)

    def shell(self, body):
        return subprocess.run(["/usr/bin/bash", "-c", 'source "$SCRIPT"\n' + body],
                              env=self.env, text=True, capture_output=True, timeout=10)

    def cli(self, *args):
        return subprocess.run(["/usr/bin/bash", str(SCRIPT), *args], env=self.env,
                              text=True, capture_output=True, timeout=10)

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
_swap_pkg() { :; }
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
COMMON_STOW_PKGS=(sample)
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
        r = self.cli("--rebuild")
        self.assertNotEqual(r.returncode, 0, r.stdout)
        calls = Path(self.env["CALLS"])
        self.assertFalse(calls.exists() and "BAD_REBUILD" in calls.read_text())

    def test_configure_kernel_action_scans_first(self):
        r = self.shell('''
_bootstrap_multiselect() { _MS_RESULT=$(mktemp); echo 'kernels — install/remove' > "$_MS_RESULT"; }
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
COMMON_STOW_PKGS=(sample)
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

    def test_menu_groups_dotfiles_and_upload_under_dms(self):
        r = self.shell('_multiselect() { printf "%s\\n" "$@"; }\n_bootstrap_multiselect')
        self.assertEqual(r.returncode, 0, r.stderr)
        section = r.stdout.split(':  DMS & Stow', 1)[1].split(':  Shell & tools', 1)[0]
        self.assertIn('dotfiles-export —', section)
        self.assertIn('dotfiles-import —', section)
        self.assertIn('stow-symlinks —', section)
        self.assertLess(section.index('dotfiles-export —'), section.index('dotfiles-import —'))
        self.assertLess(section.index('dotfiles-import —'), section.index('stow-symlinks —'))
        self.assertNotIn('+dotfiles', section)
        self.assertNotIn('dotfiles —', r.stdout)
        self.assertNotIn('dotfiles-upload', r.stdout)

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
        log = state / "vjupdate.log"
        log.write_text("original log")
        with (state / "vjupdate.lock").open("w") as lock:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            r = self.cli("--app-launchers")
            self.assertNotEqual(r.returncode, 0)
            self.assertIn("already running", r.stderr)
            self.assertEqual(log.read_text(), "original log")
            self.assertFalse((state / "vjupdate.log.1").exists())
        r = self.cli("--app-launchers")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertEqual((state / "vjupdate.log.1").read_text(), "original log")

    @unittest.skipUnless(Path("/usr/bin/stow").exists(), "installed Stow unavailable")
    def test_installed_stow_conflict_format(self):
        repo = self.fixture_repo()
        # The real Stow is only allowed to simulate against temporary fixtures.
        r = subprocess.run(["/usr/bin/stow", "-n", "-d", str(repo), "-t",
                            str(self.home), "sample"], env=self.env,
                           text=True, capture_output=True, timeout=10)
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


if __name__ == "__main__":
    unittest.main()
