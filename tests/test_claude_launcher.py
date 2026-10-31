"""The fish entry point must launch Claude without the tmux retry wrapper."""
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


class ClaudeLauncherTests(unittest.TestCase):
    def test_launches_binary_with_arguments_even_when_retry_package_exists(self):
        fish = shutil.which("fish")
        if not fish:
            self.skipTest("fish required")
        with tempfile.TemporaryDirectory(prefix="dots-claude-") as tmp:
            home = Path(tmp)
            launcher = home / ".local/lib/node_modules/claude-auto-retry/src/launcher.js"
            launcher.parent.mkdir(parents=True)
            launcher.write_text("throw new Error('retry wrapper must not run');")
            bin_dir = home / "bin"
            bin_dir.mkdir()
            for name, body in {
                "claude": 'printf "arg:<%s>\\n" "$@"; exit 7',
                "node": "echo BROKEN_RETRY_WRAPPER; exit 42",
                "tmux": "exit 42",
            }.items():
                path = bin_dir / name
                path.write_text("#!/bin/sh\n" + body + "\n")
                path.chmod(0o755)
            result = subprocess.run(
                [fish, "--no-config", "-c", 'source "$argv[1]"; claude --resume "a b"',
                 str(ROOT / "dotsets/viridjan/fish/.config/fish/functions/claude.fish")],
                env={**os.environ, "HOME": str(home), "PATH": str(bin_dir)},
                text=True, capture_output=True,
            )
            self.assertEqual(result.returncode, 7, result.stdout + result.stderr)
            self.assertEqual(result.stdout, "arg:<--resume>\narg:<a b>\n")
