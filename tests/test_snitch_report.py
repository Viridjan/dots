"""snitch-report: summary and --follow over a temp OpenSnitch events database."""
import os
import sqlite3
import subprocess
import tempfile
import unittest
from datetime import datetime, timedelta
from pathlib import Path

SCRIPT = Path(__file__).resolve().parent.parent / "scripts/.local/bin/snitch-report"
COLS = "time, action, protocol, dst_ip, dst_host, dst_port, uid, process, process_args"


class SnitchReportTests(unittest.TestCase):
    def setUp(self):
        self.db = Path(tempfile.mkdtemp()) / "events.db"
        c = sqlite3.connect(self.db)
        c.execute(f"create table connections ({COLS})")
        now = datetime.now()
        rows = [(now - timedelta(days=3), "allow", "tcp", "1.1.1.1", "old.example", "443", "1000", "/usr/bin/brave", "brave"),
                (now - timedelta(hours=1), "allow", "tcp", "1.1.1.1", "old.example", "443", "1000", "/usr/bin/brave", "brave"),
                (now - timedelta(minutes=5), "deny", "udp", "9.9.9.9", "", "53", "0", "/usr/bin/evil", "evil --x")]
        c.executemany(f"insert into connections ({COLS}) values (?,?,?,?,?,?,?,?,?)",
                      [(str(r[0]),) + r[1:] for r in rows])
        c.commit()
        self.env = dict(os.environ, SNITCH_DB=str(self.db))

    def run_(self, *args, **env):
        r = subprocess.run(["python3", "-B", str(SCRIPT), *args], env={**self.env, **env},
                           capture_output=True, text=True, timeout=20)
        self.assertEqual(r.returncode, 0, r.stderr)
        return r.stdout

    def test_summary_flags_new_denied_root(self):
        out = self.run_("6")
        self.assertIn("2 connections, 2 programs", out)
        self.assertIn("/usr/bin/evil  (1, first", out)
        self.assertIn("[DENY NEW ROOT]", out)
        self.assertIn("9.9.9.9:53/udp", out)
        brave = next(l for l in out.splitlines() if l.startswith("/usr/bin/brave"))
        self.assertNotIn("NEW", brave)   # seen before the window
        self.assertLess(out.index("/usr/bin/evil"), out.index("/usr/bin/brave"))   # new first

    def test_follow_prints_only_unseen_pairs(self):
        p = subprocess.Popen(["python3", "-B", str(SCRIPT), "--follow"], env={**self.env, "SNITCH_POLL": "0.1"},
                             stdout=subprocess.PIPE, text=True)
        try:
            self.assertIn("following", p.stdout.readline())
            c = sqlite3.connect(self.db)
            t = str(datetime.now() + timedelta(seconds=1))
            c.executemany(f"insert into connections ({COLS}) values (?,?,?,?,?,?,?,?,?)", [
                (t, "allow", "tcp", "1.1.1.1", "old.example", "443", "1000", "/usr/bin/brave", "brave"),
                (t, "allow", "tcp", "2.2.2.2", "new.example", "443", "1000", "/usr/bin/brave", "brave --x"),
                (t, "allow", "tcp", "3.3.3.3", "", "80", "1000", "/usr/bin/curl", "curl")])
            c.commit()
            lines = [p.stdout.readline() for _ in range(4)]
        finally:
            p.kill()
        out = "".join(lines)
        self.assertIn("/usr/bin/brave → new.example:443/tcp\n", out)   # known program, new host: no tag
        self.assertIn("/usr/bin/curl → 3.3.3.3:80/tcp  [NEW]", out)
        self.assertNotIn("old.example", out)   # pair seen before


if __name__ == "__main__":
    unittest.main()
