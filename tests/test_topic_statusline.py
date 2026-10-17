"""Isolated checks for the topic/directory statusline segment."""
import json
import os
from pathlib import Path
import re
import subprocess
import tempfile
import unittest

SCRIPT = Path(__file__).resolve().parents[1] / "claude/.claude/topic-statusline.sh"


class TopicStatuslineTests(unittest.TestCase):
    def render(self, records, directory=None, compact=False):
        with tempfile.TemporaryDirectory(prefix="topic-statusline-test-") as tmp:
            home = Path(tmp) / "home"
            transcript = Path(tmp) / "transcript.jsonl"
            transcript.write_text("".join(
                (row if isinstance(row, str) else json.dumps(
                    row, separators=(",", ":") if compact else None)) + "\n"
                for row in records))
            payload = {"transcript_path": str(transcript),
                       "cwd": str(home) + (directory or "")}
            result = subprocess.run(["bash", str(SCRIPT)], input=json.dumps(payload),
                                    text=True, capture_output=True,
                                    env={**os.environ, "HOME": str(home)}, timeout=5)
            self.assertEqual(result.returncode, 0, result.stderr)
            return re.sub(r"\x1b\[[0-9;]*m", "", result.stdout)

    def test_manual_title_wins_even_when_auto_is_newer(self):
        output = self.render([{"type": "custom-title", "customTitle": "Manual"},
                              {"type": "ai-title", "aiTitle": "Automatic"}], compact=True)
        self.assertIn("[TOPIC: Manual]", output)

    def test_latest_manual_title_and_json_whitespace(self):
        output = self.render([{"type": "custom-title", "customTitle": "Old"},
                              {"type": "custom-title", "customTitle": "New"}])
        self.assertIn("[TOPIC: New]", output)

    def test_auto_fallback_and_invalid_records(self):
        output = self.render([{"type": "ai-title", "aiTitle": "Old"},
                              "{incomplete", [], None,
                              {"type": "custom-title", "customTitle": ""},
                              {"type": "custom-title", "customTitle": 123},
                              {"type": "ai-title", "aiTitle": "New"}])
        self.assertIn("[TOPIC: New]", output)

    def test_directory_boundaries(self):
        self.assertIn("[DIR: ~]", self.render([]))
        self.assertIn("[DIR: ~/Projects/dots]", self.render([], "/Projects/dots"))
        output = self.render([], "-other/project")
        self.assertIn("/home-other/project]", output)
        self.assertNotIn("[DIR: ~", output)
        self.assertNotIn("[TOPIC:", output)


if __name__ == "__main__":
    unittest.main()
