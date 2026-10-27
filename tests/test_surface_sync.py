"""Exercise checkout replacement in an isolated repository, without system setup."""
import os
from pathlib import Path
import subprocess
import tempfile
import unittest


class SurfaceSyncTests(unittest.TestCase):
    def test_launcher_edits_survive_checkout_reset_in_stash(self):
        script = (Path(__file__).resolve().parents[1] / "surface-sync.sh").read_text()
        block = script.split('step "Updating checkout to origin/main"', 1)[1].split('# ── 5.', 1)[0]
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            env = {**os.environ, "GIT_CONFIG_GLOBAL": os.devnull,
                   "GIT_CONFIG_NOSYSTEM": "1"}

            def git(*args):
                return subprocess.run(["git", *args], cwd=root, env=env,
                                      check=True, capture_output=True, text=True).stdout

            git("init", "-q")
            git("config", "user.name", "Test")
            git("config", "user.email", "test@example.invalid")
            launcher = root / "scripts/.local/bin/vjupdate"
            launcher.parent.mkdir(parents=True)
            launcher.write_text("original\n")
            git("add", ".")
            git("commit", "-qm", "initial")
            git("update-ref", "refs/remotes/origin/main", "HEAD")
            launcher.write_text("local launcher edit\n")
            result = subprocess.run(["bash", "-euc",
                'NEED_RESET=true; BACKUP_BRANCH=""; TS=test; ok() { :; };\n' + block],
                cwd=root, env=env, capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertTrue(git("stash", "list").strip(), "launcher edits were discarded without a stash")
            self.assertEqual(git("show", "stash@{0}:scripts/.local/bin/vjupdate"), "local launcher edit\n")
            self.assertEqual(launcher.read_text(), "original\n")
