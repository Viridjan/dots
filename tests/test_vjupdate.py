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


class SafetyChecks(FixtureCase):
    # Preservation checks, not regressions claimed to fail pre-fix.
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
