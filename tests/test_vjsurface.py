"""vjsurface: every step idempotent, nothing aborts the run (mocked system)."""
import os
import subprocess
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
SCRIPT = REPO / "scripts/.local/bin/vjsurface"


class VjsurfaceTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory(prefix="vjsurface-test-")
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name)
        self.home = self.root / "home"
        self.bin = self.root / "bin"
        self.dots = self.root / "dots"
        for d in (self.home, self.bin, self.dots / "scripts/.local/bin", self.dots / "dotsets/me"):
            d.mkdir(parents=True)
        # The script finds the repo from its own location.
        (self.dots / "scripts/.local/bin/vjsurface").symlink_to(SCRIPT)
        for name in ("bash", "cat", "grep", "sed", "sort", "comm", "tr", "tee", "date", "mkdir", "cp",
                     "mv", "rm", "find", "realpath", "dirname", "stow", "perl", "echo", "readlink", "ln", "flock"):
            (self.bin / name).symlink_to(Path("/usr/bin") / name)
        self.calls = self.root / "calls"
        self.mock("sudo", '[ "$1" = -n ] || [ "$1" = -v ] && exit 0\necho "sudo $*" >> "$CALLS"; "$@"')
        self.mock("pgrep", "exit 1")
        self.mock("pacman", "exit 0")
        self.mock("grub-mkconfig", 'echo "grub-mkconfig $*" >> "$CALLS"')
        self.mock("uname", "echo 7.2.11-arch1-1-surface")
        self.mock("systemctl", "echo 'iptsd@dev-hidraw3.service loaded active running iptsd'")
        self.boot = self.root / "boot"
        self.boot.mkdir()
        (self.boot / "vmlinuz-linux-surface").write_text("k")
        self.grub = self.root / "grub"
        self.grub.write_text("GRUB_DEFAULT=0\nGRUB_TOP_LEVEL='/boot/vmlinuz-linux-cachyos'\n")
        self.grub_cfg = self.root / "grub.cfg"
        self.grub_cfg.write_text("menuentry linux-cachyos\n")
        self.conf = self.root / "pacman.conf"
        self.conf.write_text("[options]\n[cachyos]\n[core]\n[linux-surface]\n")
        cfg = self.home / ".config/vjupdate/config.toml"
        cfg.parent.mkdir(parents=True)
        cfg.write_text('profile = "surface"\ndotset = "me"\n')
        self.env = {"HOME": str(self.home), "PATH": str(self.bin), "CALLS": str(self.calls),
                    "VJS_GRUB_FILE": str(self.grub), "VJS_GRUB_CFG": str(self.grub_cfg),
                    "VJS_BOOT": str(self.boot), "VJS_DMI": str(self.root / "dmi"),
                    "VJS_PACMAN_FILES": str(self.conf), "VJS_DOTS": str(self.dots)}

    def mock(self, name, body):
        f = self.bin / name
        if f.exists() or f.is_symlink():
            f.unlink()
        f.write_text("#!/bin/bash\n" + body + "\n")
        f.chmod(0o755)

    def run_it(self):
        r = subprocess.run(["/usr/bin/bash", str(self.dots / "scripts/.local/bin/vjsurface")], env=self.env,
                           text=True, capture_output=True, timeout=20, stdin=subprocess.DEVNULL)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        return r.stdout

    def calls_text(self):
        return self.calls.read_text() if self.calls.exists() else ""

    def test_not_a_surface_does_nothing(self):
        (self.home / ".config/vjupdate/config.toml").write_text('profile = "desktop"\n')
        out = self.run_it()
        self.assertIn("Not a Surface", out)
        self.assertEqual(self.calls_text(), "")

    def test_waits_for_running_vjupdate(self):
        lock = self.home / ".local/state/dots/vjupdate.lock"
        lock.parent.mkdir(parents=True)
        lock.touch()
        import fcntl
        with open(lock) as f:
            fcntl.flock(f, fcntl.LOCK_EX)
            self.assertIn("vjupdate is running", self.run_it())
            fcntl.flock(f, fcntl.LOCK_UN)
        self.assertNotIn("vjupdate is running", self.run_it())

    def test_grub_set_once_then_idempotent(self):
        out = self.run_it()
        self.assertIn(f"GRUB_TOP_LEVEL='{self.boot}/vmlinuz-linux-surface'", self.grub.read_text())
        self.assertIn("grub-mkconfig -o", self.calls_text())
        self.assertIn("all good", out)
        # Second run: line present, grub.cfg lists the kernel → nothing changes.
        self.grub_cfg.write_text("menuentry vmlinuz-linux-surface\n")
        self.calls.unlink()
        out = self.run_it()
        self.assertIn("already linux-surface", out)
        self.assertNotIn("grub-mkconfig", self.calls_text())

    def test_pacman_conf_restored_from_bak(self):
        good = self.conf.read_text()
        (self.root / "pacman.conf.bak").write_text(good)
        self.conf.write_text("[options]\n[core]\n")
        out = self.run_it()
        self.assertEqual(self.conf.read_text(), good)
        self.assertIn("had lost [cachyos] [linux-surface]", out)

    def test_failing_steps_warn_and_run_continues(self):
        self.mock("grub-mkconfig", "exit 1")
        self.mock("uname", "echo 7.3.1-1-cachyos")
        self.mock("pacman", '[ "$1" = -Q ] && exit 1\nexit 1')
        out = self.run_it()
        self.assertIn("could not install linux-surface", out)
        self.assertIn("grub-mkconfig failed", out)
        self.assertIn("reboot into linux-surface", out)
        self.assertIn("dotfile links", out)  # last step still ran
        self.assertIn("thing(s) to look at", out)

    def test_refold_keeps_untracked_files(self):
        pkg = self.dots / "dotsets/me/app/.config/app"
        pkg.mkdir(parents=True)
        (pkg / "conf").write_text("tracked")
        live = self.home / ".config/app"
        live.mkdir(parents=True)
        (live / "conf").symlink_to(pkg / "conf")  # stow's file-by-file link
        (live / "extra").write_text("untracked")
        out = self.run_it()
        self.assertIn("refolded 'app'", out)
        self.assertTrue(live.is_symlink())
        self.assertEqual((pkg / "extra").read_text(), "untracked")
        self.assertIn("every package is a folded link", self.run_it())

    def test_refold_skips_clashing_real_file(self):
        pkg = self.dots / "dotsets/me/app/.config/app"
        pkg.mkdir(parents=True)
        (pkg / "conf").write_text("tracked")
        live = self.home / ".config/app"
        live.mkdir(parents=True)
        (live / "conf").write_text("local edit")
        out = self.run_it()
        self.assertIn("merge by hand", out)
        self.assertEqual((live / "conf").read_text(), "local edit")
        self.assertFalse(live.is_symlink())


if __name__ == "__main__":
    unittest.main()
