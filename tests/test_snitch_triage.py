"""snitch-triage: verdicts per executable path and rule files, with a mocked pacman."""
import json
import os
import sqlite3
import subprocess
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parent.parent / "scripts/.local/lib/sysup/snitch-triage.py"

# pacman mock: ownership/foreign/altered decided by the queried path or package name.
PACMAN = r"""#!/bin/bash
case "$1" in
  -Qoq) case "$3" in
          /usr/lib/systemd/systemd-timesyncd) echo systemd ;;
          /usr/bin/tampered) echo coreutils ;;
          /opt/brave-origin-bin/brave) echo brave-origin-bin ;;
          /usr/bin/python3.14) echo python ;;
          *) exit 1 ;;
        esac ;;
  -Qmq) [[ "$3" == brave-origin-bin ]] ;;
  -Qkk) [[ "$3" == coreutils ]] && echo "warning: coreutils: /usr/bin/tampered (Modification time mismatch)"; true ;;
esac
"""


class SnitchTriageTests(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        (self.tmp / "bin").mkdir()
        (self.tmp / "bin/pacman").write_text(PACMAN)
        (self.tmp / "bin/pacman").chmod(0o755)
        self.rules = self.tmp / "rules"
        self.rules.mkdir()
        self.db = self.tmp / "events.db"
        c = sqlite3.connect(self.db)
        c.execute("create table connections (time, process)")
        procs = ["/usr/lib/systemd/systemd-timesyncd", "/tmp/x/miner", "/usr/bin/tampered",
                 "/usr/bin/dropped", "/opt/brave-origin-bin/brave", "/usr/bin/python3.14",
                 "/home/u/Downloads/tool", "/tmp/.mount_AppXyz/AppRun", "/usr/bin/gone (deleted)",
                 "/home/u/.local/bin/mine"]
        c.executemany("insert into connections values ('t', ?)", [(p,) for p in procs])
        c.commit()
        self.env = dict(os.environ, PATH=f"{self.tmp}/bin:/usr/bin", SNITCH_DB=str(self.db),
                        SNITCH_RULES=str(self.rules), SNITCH_TRIAGE_LOG=str(self.tmp / "log"),
                        SNITCH_HOME="/home/u", SNITCH_ONCE="1")

    def run_(self):
        r = subprocess.run(["python3", "-I", str(SCRIPT)], env=self.env, capture_output=True, text=True, timeout=30)
        self.assertEqual(r.returncode, 0, r.stderr)
        return {json.load(open(f))["operator"]["data"]: json.load(open(f))["action"] for f in self.rules.glob("*.json")}

    def test_verdicts(self):
        rules = self.run_()
        self.assertEqual(rules, {
            "/usr/lib/systemd/systemd-timesyncd": "allow",   # repo package, unaltered
            "/tmp/x/miner": "deny",                          # temp dir
            "/usr/bin/tampered": "deny",                     # pacman -Qkk lists it
            "/usr/bin/dropped": "deny",                      # system dir, no package
            "/home/u/Downloads/tool": "deny",
            "/usr/bin/gone (deleted)": "deny",
        })   # brave (AUR), python (generic), AppImage, ~/.local/bin: left to the pop-up
        log = (self.tmp / "log").read_text()
        self.assertIn("ASK    /opt/brave-origin-bin/brave  (AUR package brave-origin-bin)", log)
        self.assertIn("ASK    /usr/bin/python3.14  (generic tool", log)

    def test_existing_rules_are_respected_and_second_run_writes_nothing(self):
        (self.rules / "mine.json").write_text(json.dumps(
            {"action": "allow", "operator": {"operand": "process.path", "data": "/tmp/x/miner"}}))
        self.run_()
        self.assertFalse(any("miner" in f.name for f in self.rules.glob("triage-*.json")))
        before = sorted(f.name for f in self.rules.iterdir())
        self.run_()
        self.assertEqual(sorted(f.name for f in self.rules.iterdir()), before)

    def test_deny_rules_take_precedence(self):
        self.run_()
        deny = next(json.load(open(f)) for f in self.rules.glob("triage-deny-miner-*.json"))
        self.assertTrue(deny["precedence"])
        self.assertEqual(deny["duration"], "always")


if __name__ == "__main__":
    unittest.main()
