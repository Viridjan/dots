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
  "msg --json windows") cat "{self.tmp}/windows.json" ;;
  "msg --json focused-window") cat "{self.tmp}/focused.json" 2>/dev/null || echo null ;;
  *) echo "niri $*" >> "{self.calls}" ;;
esac
""")
        niri.chmod(0o755)
        # Process tree: 100 alacritty (window 1 on workspace 4) > 101 fish > 102 claude > 103 app;
        # 200 is an app nobody's agent started.
        self.proc = self.tmp / "proc"
        for pid, comm, ppid in ((100, "alacritty", 1), (101, "fish", 100), (102, "claude", 101),
                                (103, "app", 102), (200, "app", 1)):
            (self.proc / str(pid)).mkdir(parents=True)
            (self.proc / str(pid) / "comm").write_text(comm + "\n")
            (self.proc / str(pid) / "status").write_text(f"Name:\t{comm}\nPPid:\t{ppid}\n")
        (self.tmp / "windows.json").write_text(json.dumps([{"id": 1, "pid": 100, "workspace_id": 4}]))
        for tool in ("bash", "jq", "date", "rm", "cat", "awk"):
            os.symlink(subprocess.check_output(["which", tool], text=True).strip(), bin_ / tool)
        self.env = {"PATH": str(bin_), "XDG_RUNTIME_DIR": str(self.tmp), "LAUNCHER_WS_PROC": str(self.proc)}

    def run_watch(self, windows, age=0, record=True):
        rec = self.tmp / "launcher-ws"
        rec.unlink(missing_ok=True)
        if record:
            rec.write_text(f"4 {int(time.time()) - age}\n")
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


    def test_agent_window_goes_to_agent_terminal_workspace(self):
        # Even rule-placed (workspace 1) and with no launcher record; record stays for the launcher's app.
        move = "niri msg action move-window-to-workspace --window-id {} --focus false 4\n"
        self.assertEqual(self.run_watch([{"id": 5, "workspace_id": 1, "app_id": "spotify", "pid": 103}],
                                        record=False), move.format(5))
        self.calls.unlink()
        self.assertEqual(self.run_watch([{"id": 6, "workspace_id": 4, "app_id": "x", "pid": 103}]), "")
        self.assertTrue((self.tmp / "launcher-ws").exists())
        self.assertEqual(self.run_watch([{"id": 7, "workspace_id": 1, "app_id": "x", "pid": 200}],
                                        record=False), "")


    def test_terminal_or_browser_you_opened_gets_focus(self):
        # Launched on workspace 4 and you are still there (focused workspace = 4).
        (self.tmp / "ws.json").write_text(json.dumps([{"id": 4, "idx": 4, "is_focused": True}]))
        self.assertEqual(self.run_watch([{"id": 50, "workspace_id": 4, "app_id": "Alacritty", "pid": 200}]),
                         "niri msg action focus-window --id 50\n")
        self.calls.unlink()
        self.assertEqual(self.run_watch([{"id": 51, "workspace_id": 4, "app_id": "spotify", "pid": 200}]), "")
        # No launcher/shortcut record (a script opened it): old rule, no focus.
        self.assertEqual(self.run_watch([{"id": 52, "workspace_id": 4, "app_id": "brave-origin", "pid": 200}],
                                        record=False), "")

    def test_new_window_from_focused_same_app_gets_focus(self):
        # Ctrl+N in Brave: focus stays on the old Brave window (open-focused false).
        (self.tmp / "focused.json").write_text(json.dumps({"id": 12, "app_id": "brave-origin"}))
        w = lambda i, **k: {"id": i, "workspace_id": 3, "app_id": "brave-origin", "pid": 200, **k}
        self.assertEqual(self.run_watch([w(60)], record=False), "niri msg action focus-window --id 60\n")
        self.calls.unlink()
        self.assertEqual(self.run_watch([w(61, is_floating=True)], record=False), "")   # PiP
        (self.tmp / "focused.json").write_text(json.dumps({"id": 23, "app_id": "Alacritty"}))
        self.assertEqual(self.run_watch([w(62)], record=False), "")   # Brave opened while in a terminal

    def test_run_records_only_when_it_will_spawn(self):
        (self.tmp / "windows.json").write_text(json.dumps([{"id": 1, "app_id": "brave-origin", "workspace_id": 4}]))
        rec = self.tmp / "launcher-ws"
        run = lambda *a: subprocess.run(["bash", str(SCRIPT), "run", *a], env=self.env, check=True)
        os.symlink(subprocess.check_output(["which", "true"], text=True).strip(), self.tmp / "bin/true")
        run("--app-id", "^brave-origin$", "true")
        self.assertFalse(rec.exists())   # already open: nirius only focuses it
        run("--app-id", "^Alacritty$", "true")
        self.assertEqual(rec.read_text().split()[0], "3")
        rec.unlink()
        run("true")
        self.assertTrue(rec.exists())


if __name__ == "__main__":
    unittest.main()
