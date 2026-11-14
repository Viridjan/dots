"""Dotset backups: rotation, capture, restore — against a real temp git repo."""
import subprocess
import unittest
from pathlib import Path

from test_sysup import FixtureCase


class BackupTests(FixtureCase):
    def setUp(self):
        super().setUp()
        (self.bin / "git").unlink()
        (self.bin / "git").symlink_to("/usr/bin/git")
        self.env.update(GIT_AUTHOR_NAME="t", GIT_AUTHOR_EMAIL="t@x", GIT_COMMITTER_NAME="t",
                        GIT_COMMITTER_EMAIL="t@x", GIT_CONFIG_GLOBAL="/dev/null", GIT_CONFIG_NOSYSTEM="1")
        self.repo = self.home / "Projects/dots"
        self.set = self.repo / "dotsets/mine"
        (self.set / "niri/.config/niri/dms").mkdir(parents=True)
        (self.set / "a").write_text("v1\n")
        (self.set / "niri/.config/niri/dms/binds.kdl").write_text("repo binds\n")
        (self.repo / "other").write_text("o1\n")
        (self.repo / ".gitignore").write_text("secret\n")
        self.git("init", "-q", "-b", "main")
        self.git("add", "-A")
        self.git("commit", "-qm", "init")
        self.env["SYSUP_DOTSET_DIR"] = str(self.set)

    def git(self, *args):
        return subprocess.run(["git", "-C", str(self.repo), *args], env=self.env, text=True,
                              capture_output=True, check=True).stdout.strip()

    def backup(self, mode="work"):
        r = self.shell(f"_backup_dotset {mode}")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        return r

    def at(self, n, path="dotsets/mine/a"):
        return self.git("show", f"backup/mine/{n}:{path}")

    def tags(self):
        return self.git("tag", "-l", "backup/*").split()

    def test_rotation_keeps_two_newest(self):
        self.backup()
        self.assertEqual(self.tags(), ["backup/mine/1"])
        (self.set / "a").write_text("v2\n")
        self.backup()
        self.assertEqual((self.at(1), self.at(2)), ("v2", "v1"))
        (self.set / "a").write_text("v3\n")
        self.backup()
        self.assertEqual((self.at(1), self.at(2)), ("v3", "v2"))
        self.assertEqual(len(self.tags()), 2)

    def test_unchanged_set_does_not_rotate(self):
        self.backup()
        (self.set / "a").write_text("v2\n")
        self.backup()
        before = self.git("rev-parse", "backup/mine/1", "backup/mine/2")
        self.backup()
        (self.repo / "other").write_text("changed outside the set\n")
        self.backup()
        self.assertEqual(self.git("rev-parse", "backup/mine/1", "backup/mine/2"), before)

    def test_snapshot_leaves_branch_index_and_tree_alone(self):
        (self.set / "a").write_text("uncommitted\n")
        (self.set / "secret").write_text("token\n")
        head, status = self.git("rev-parse", "HEAD"), self.git("status", "--porcelain")
        self.backup()
        self.assertEqual(self.at(1), "uncommitted")
        self.assertNotIn("secret", self.git("ls-tree", "-r", "--name-only", "backup/mine/1"))
        self.assertEqual(self.git("rev-parse", "HEAD"), head)
        self.assertEqual(self.git("status", "--porcelain"), status)
        self.assertEqual(self.git("diff", "--cached", "--name-only"), "")

    def test_live_dms_files_are_captured(self):
        live = self.home / ".config/niri/dms"
        live.mkdir(parents=True)
        (live / "binds.kdl").write_text("live binds\n")
        self.backup("live-dms")
        self.assertEqual(self.at(1, "dotsets/mine/niri/.config/niri/dms/binds.kdl"), "live binds")
        self.assertEqual((self.set / "niri/.config/niri/dms/binds.kdl").read_text(), "repo binds\n")

    def test_head_mode_saves_last_commit_not_working_tree(self):
        (self.set / "a").write_text("about to be committed\n")
        self.backup("head")
        self.assertEqual(self.at(1), "v1")

    def test_restore_round_trip_and_undo(self):
        self.backup()                        # 1 = v1
        (self.set / "a").write_text("v2\n")
        self.backup()                        # 1 = v2, 2 = v1
        (self.set / "a").write_text("broken\n")
        r = subprocess.run(["/usr/bin/bash", "-c", 'source "$SCRIPT"\nrestore_dotset 2'], env=self.env,
                           text=True, capture_output=True, timeout=10, input="y\n")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertEqual((self.set / "a").read_text(), "v1\n")
        self.assertEqual(self.at(1), "broken")  # the replaced state, so the restore can be undone
        self.assertEqual(self.git("rev-parse", "HEAD"), self.git("rev-parse", "main"))

    def test_restore_declined_changes_nothing(self):
        self.backup()
        (self.set / "a").write_text("keep me\n")
        subprocess.run(["/usr/bin/bash", "-c", 'source "$SCRIPT"\nrestore_dotset 1'], env=self.env,
                       text=True, capture_output=True, timeout=10, input="n\n")
        self.assertEqual((self.set / "a").read_text(), "keep me\n")
        self.assertEqual(self.tags(), ["backup/mine/1"])

    def test_restore_without_backup_dies(self):
        r = self.shell("restore_dotset 2")
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("no backup/mine/2 yet", r.stdout + r.stderr)

    def test_no_dotset_does_nothing(self):
        self.env["SYSUP_DOTSET_DIR"] = ""
        self.shell("_backup_dotset work")
        self.assertEqual(self.tags(), [])


if __name__ == "__main__":
    unittest.main()
