"""Real pseudo-terminal runs: prompts, phase reporting, and UI responsiveness."""
import asyncio
import os
from pathlib import Path
import sys
import tempfile
import unittest

from textual.app import App


class ProgressTests(unittest.TestCase):
    def test_password_prompt_masks_response_and_keeps_secret_out_of_output(self):
        from vj.progress import RunScreen

        async def go():
            with tempfile.TemporaryDirectory() as tmp:
                code = ('import termios; a=termios.tcgetattr(0); '
                        'a[3] &= ~termios.ECHO; termios.tcsetattr(0,termios.TCSANOW,a); '
                        'input("Password: "); print("accepted",flush=True)')
                screen = RunScreen([sys.executable, '-c', code], os.environ.copy(), Path(tmp)/'results')
                async with App().run_test() as pilot:
                    pilot.app.push_screen(screen)
                    for _ in range(100):
                        await pilot.pause(0.02)
                        if 'Password:' in screen.output:
                            break
                    field = screen.query_one('#reply')
                    self.assertTrue(field.password)
                    field.value = 'test-secret'
                    await pilot.press('enter')
                    for _ in range(100):
                        await pilot.pause(0.02)
                        if screen.returncode is not None:
                            break
                    self.assertEqual(screen.returncode, 0)
                    self.assertIn('accepted', screen.output)
                    self.assertNotIn('test-secret', screen.output)
        asyncio.run(go())

    def test_run_stays_in_app_and_accepts_prompt(self):
        from vj.progress import RunScreen

        async def go():
            with tempfile.TemporaryDirectory() as tmp:
                results = Path(tmp) / 'result.tsv'
                code = ('import os; from pathlib import Path; '
                        'print("TTY", os.isatty(0), flush=True); '
                        'answer=input("Continue? "); '
                        f'Path({str(results)!r}).write_text("phase:install\\tok\\n"); '
                        'print("ANSWER="+answer, flush=True)')
                screen = RunScreen([sys.executable, '-c', code], os.environ.copy(), results)
                app = App()
                async with app.run_test() as pilot:
                    app.push_screen(screen)
                    for _ in range(100):
                        await pilot.pause(0.02)
                        if 'Continue?' in screen.output:
                            break
                    self.assertIn('TTY True', screen.output)
                    self.assertIsNone(screen.returncode)
                    field = screen.query_one('#reply')
                    field.value = 'yes'
                    field.focus()
                    await pilot.press('enter')
                    for _ in range(100):
                        await pilot.pause(0.02)
                        if screen.returncode is not None:
                            break
                    self.assertEqual(screen.returncode, 0)
                    self.assertIn('ANSWER=yes', screen.output)
                    self.assertEqual(screen.query_one('#overall').progress, 1)
                    self.assertIs(app.screen, screen)
        asyncio.run(go())

    def test_failed_child_reports_failure_without_completing_progress(self):
        from vj.progress import RunScreen

        async def go():
            with tempfile.TemporaryDirectory() as tmp:
                screen = RunScreen([sys.executable, '-c', 'raise SystemExit(7)'],
                                   os.environ.copy(), Path(tmp) / 'results')
                app = App()
                async with app.run_test() as pilot:
                    app.push_screen(screen)
                    for _ in range(100):
                        await pilot.pause(0.02)
                        if screen.returncode is not None:
                            break
                    self.assertEqual(screen.returncode, 7)
                    self.assertEqual(screen.query_one('#overall').progress, 0)
                    self.assertIn('exit 7', str(screen.query_one('#status').render()))
        asyncio.run(go())
