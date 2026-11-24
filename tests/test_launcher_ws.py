"""launcher-ws watch: the launched app's window goes back to the workspace Mod+Space was pressed on."""
import json
import os
import subprocess
import tempfile
import time
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parent.parent / "scripts/.local/bin/launcher-ws"


class LauncherWsTests(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        bin_ = self.tmp / "bin"
        bin_.mkdir()
        self.calls = self.tmp / "calls"
        # Focused workspace 3; remembered workspace 4 has idx 4.
        (self.tmp / "ws.json").write_text(json.dumps([
            {"id": 3, "idx": 3, "is_focused": True}, {"id": 4, "idx": 4, "is_focused": False}]))
        niri = bin_ / "niri"
        niri.write_text(f"""#!/bin/sh
case "$*" in
  "msg --json event-stream") cat "{self.tmp}/events" ;;
  "msg --json workspaces") cat "{self.tmp}/ws.json" ;;
  *) echo "niri $*" >> "{self.calls}" ;;
esac
""")
        niri.chmod(0o755)
        for tool in ("bash", "jq", "date", "rm", "cat"):
            os.symlink(subprocess.check_output(["which", tool], text=True).strip(), bin_ / tool)
        self.env = {"PATH": str(bin_), "XDG_RUNTIME_DIR": str(self.tmp)}

    def run_watch(self, windows, age=0):
        (self.tmp / "launcher-ws").write_text(f"4 {int(time.time()) - age}\n")
        (self.tmp / "events").write_text("".join(
            json.dumps({"WindowOpenedOrChanged": {"window": w}}) + "\n" for w in windows))
        r = subprocess.run(["bash", str(SCRIPT), "watch"], env=self.env, capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stderr)
        return self.calls.read_text() if self.calls.exists() else ""

    def test_moves_only_first_window_back(self):
        calls = self.run_watch([{"id": 7, "workspace_id": 3, "app_id": "x"},
                                {"id": 7, "workspace_id": 3, "app_id": "x"},
                                {"id": 8, "workspace_id": 3, "app_id": "y"}])
        self.assertEqual(calls, "niri msg action move-window-to-workspace --window-id 7 --focus false 4\n")

    def test_rule_placed_stale_and_launcher_windows_stay(self):
        self.assertEqual(self.run_watch([{"id": 9, "workspace_id": 1, "app_id": "spotify"}]), "")
        self.assertEqual(self.run_watch([{"id": 10, "workspace_id": 3, "app_id": "x"}], age=120), "")
        self.assertEqual(self.run_watch([{"id": 11, "workspace_id": 3, "app_id": "com.danklinux.dms"}]), "")
        self.assertTrue((self.tmp / "launcher-ws").exists())   # DMS window did not consume the record


if __name__ == "__main__":
    unittest.main()
