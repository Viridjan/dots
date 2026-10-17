"""Menu model and real terminal interaction, with all system work disabled."""
import errno
import fcntl
import os
from pathlib import Path
import pty
import select
import signal
import struct
import tempfile
import termios
import time
import unittest

from tests.test_vjupdate import FixtureCase, SCRIPT


class MenuModelTests(FixtureCase):
    def menu(self, body):
        return self.shell('''
_menu_catalog
declare -A MENU_SELECTED=() MENU_OPEN=()
_menu_defaults
''' + body)

    def test_defaults_and_dependencies(self):
        r = self.menu('''
printf '%s\\n' "${!MENU_SELECTED[@]}" | sort
_menu_set audit false
for id in audit orphan-removal rebuild python-rebuild pacnew-merge; do
    echo "$id:${MENU_SELECTED[$id]}"
done
_menu_set rebuild true
echo "AUDIT:${MENU_SELECTED[audit]}"
_menu_clear
_menu_set pacnew-merge true
echo "PACNEW:${MENU_SELECTED[audit]}"
''')
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn('audit:false', r.stdout)
        self.assertIn('rebuild:false', r.stdout)
        self.assertIn('AUDIT:true', r.stdout)
        self.assertIn('PACNEW:true', r.stdout)

    def test_group_selection_is_scoped_and_defaults_restore(self):
        r = self.menu('''
_menu_clear
_menu_group_select ai
echo "AI:${MENU_SELECTED[ollama]}:${MENU_SELECTED[vms]}"
echo "GIT:${MENU_SELECTED[dotfiles-export]}"
_menu_group_select ai
echo "CLEARED:${MENU_SELECTED[ollama]}"
_menu_defaults
echo "LINKS:${MENU_SELECTED[stow-symlinks]}"
echo "GIT:${MENU_SELECTED[dotfiles-export]}"
''')
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn('AI:true:true', r.stdout)
        self.assertIn('CLEARED:false', r.stdout)
        self.assertIn('LINKS:true', r.stdout)
        self.assertNotIn('GIT:true', r.stdout)

    def test_filter_finds_collapsed_items_and_no_matches_is_safe(self):
        r = self.menu('''
for group in "${MENU_GROUP_IDS[@]}"; do MENU_OPEN[$group]=false; done
MENU_QUERY='repository DMS'
_menu_rows
for row in "${MENU_ROWS[@]}"; do
    [[ "$row" == g:* ]] || echo "MATCH:${MENU_IDS[$row]}"
done
MENU_QUERY='nothing-matches-this'
_menu_rows
echo "ROWS:${#MENU_ROWS[@]}"
''')
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn('MATCH:dms-import', r.stdout)
        self.assertIn('ROWS:0', r.stdout)

    def test_stable_ids_reach_bootstrap_without_unselected_actions(self):
        r = self.shell('''
_bootstrap_multiselect() {
    _MS_RESULT=$(mktemp)
    printf '%s\\n' stow-symlinks > "$_MS_RESULT"
}
_ensure_dots_repo() { :; }
_check_packages_against_malware() { echo BAD_GATE; }
check_aur_malware() { echo BAD_GATE; }
deploy_dotfiles() { echo LINKS_DEPLOYED; }
dms_import() { echo BAD_IMPORT; }
bootstrap
''')
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn('LINKS_DEPLOYED', r.stdout)
        self.assertNotIn('BAD_GATE', r.stdout)
        self.assertNotIn('BAD_IMPORT', r.stdout)

    def test_plan_has_execution_order_and_uses_ids(self):
        r = self.menu('''
_menu_clear
for id in dms-import stow-symlinks dotfiles-export dms-export; do _menu_set "$id" true; done
_menu_plan
printf '%s\\n' "${MENU_PLAN[@]}"
# Changing labels must not change selection IDs.
MENU_LABELS[0]='A different title'
_selected_action sources $'sources\\ninstall'
''')
        self.assertEqual(r.returncode, 0, r.stderr)
        lines = r.stdout.splitlines()
        self.assertEqual(lines, ['Save live DMS settings to repository',
                                'Review and upload Git changes',
                                'Refresh configuration links',
                                'Apply repository DMS settings'])


class MenuTerminalTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix='vjupdate-menu-pty-')
        self.addCleanup(self.tmp.cleanup)
        self.output = bytearray()
        self.pid, self.fd = pty.fork()
        if self.pid == 0:
            os.environ.update(TERM='xterm-256color', HOME=self.tmp.name)
            # Only enter the selection UI, never bootstrap or any real action.
            body = '''source "$1"
_tui_start() { :; }
_tui_end() { :; }
MACHINE=desktop
_bootstrap_multiselect
rc=0; [[ "$_MS_STATUS" == ok ]] || rc=1
printf '\\nMENU_DONE:%s\\n' "$rc"
if ((rc == 0)); then cat "$_MS_RESULT"; fi
'''
            os.execv('/usr/bin/bash', ['bash', '-c', body, 'menu-test', str(SCRIPT)])
        self.addCleanup(self.close_child)
        self.resize(24, 80)
        self.await_text('Enter Review')

    def close_child(self):
        try:
            os.kill(self.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        try:
            os.waitpid(self.pid, 0)
        except ChildProcessError:
            pass
        os.close(self.fd)

    def resize(self, rows, cols):
        fcntl.ioctl(self.fd, termios.TIOCSWINSZ, struct.pack('HHHH', rows, cols, 0, 0))
        os.kill(self.pid, signal.SIGWINCH)

    def await_text(self, text, start=0):
        deadline = time.monotonic() + 5
        needle = text.encode()
        while needle not in self.output[start:]:
            remaining = deadline - time.monotonic()
            self.assertGreater(remaining, 0, self.output.decode(errors='replace'))
            ready, _, _ = select.select([self.fd], [], [], min(remaining, 0.2))
            if ready:
                try:
                    data = os.read(self.fd, 65536)
                except OSError as error:
                    if error.errno == errno.EIO:
                        data = b''
                    else:
                        raise
                self.assertTrue(data, self.output.decode(errors='replace'))
                self.output.extend(data)
        return self.output.decode(errors='replace')

    def send(self, keys):
        start = len(self.output)
        os.write(self.fd, keys)
        return start

    def finish(self, status):
        output = self.await_text(f'MENU_DONE:{status}')
        self.assertIn('\x1b[?1049l', output)
        self.assertIn('\x1b[?25h', output)
        return output

    def test_default_review_back_and_run(self):
        start = self.send(b'\r')
        self.await_text('REVIEW', start)
        start = self.send(b'b')
        self.await_text('Enter Review', start)
        start = self.send(b'\r')
        self.await_text('REVIEW', start)
        self.send(b'\r')
        output = self.finish(0)
        # Wait for the result file to finish printing before checking its IDs.
        output = self.await_text('\r\npython-rebuild\r\n')
        result = output.split('MENU_DONE:0', 1)[1]
        self.assertIn('stow-symlinks', result)
        self.assertIn('sources', result)
        self.assertNotIn('dotfiles-export', result)
        self.assertNotIn('dms-import', result)

    def test_search_select_and_escape_cancel(self):
        self.send(b'c')
        start = self.send(b'/Apply repository DMS')
        self.await_text('Apply repository DMS settings', start)
        self.send(b'\rj ')
        start = self.send(b'\r')
        self.await_text('REVIEW', start)
        self.send(b'\r')
        self.finish(0)
        output = self.await_text('\r\ndms-import\r\n')
        self.assertEqual(output.split('MENU_DONE:0', 1)[1].strip(), 'dms-import')

    def test_resize_and_navigation_cancel(self):
        start = len(self.output)
        self.resize(10, 30)
        self.await_text('Resize terminal', start)
        self.send(b'\r')  # must not execute at this size
        start = len(self.output)
        self.resize(18, 55)
        self.await_text('Enter Review', start)
        self.send(b'\x1b[6~\x1b[F\x1b[5~\x1b[H\x1b[C\x1b[D')
        self.send(b'\x1b')
        self.finish(1)

    def test_interrupt_restores_terminal(self):
        os.kill(self.pid, signal.SIGINT)
        self.await_text('\x1b[?1049l')
        self.assertTrue(termios.tcgetattr(self.fd)[3] & termios.ECHO)
        self.assertTrue(termios.tcgetattr(self.fd)[3] & termios.ICANON)

    def test_termination_restores_terminal(self):
        os.kill(self.pid, signal.SIGTERM)
        self.await_text('\x1b[?1049l')
        self.assertTrue(termios.tcgetattr(self.fd)[3] & termios.ECHO)
        self.assertTrue(termios.tcgetattr(self.fd)[3] & termios.ICANON)

    def test_idle_menu_does_not_repaint_and_navigation_updates_only_changed_rows(self):
        # The initial frame is one write; wait across two input polling intervals.
        deadline = time.monotonic() + 2.2
        extra = bytearray()
        while time.monotonic() < deadline:
            ready, _, _ = select.select([self.fd], [], [], 0.1)
            if ready:
                extra.extend(os.read(self.fd, 65536))
        self.assertEqual(extra, b'')
        start = self.send(b'j')
        self.await_text('Prepare paru', start)
        delta = bytes(self.output[start:])
        self.assertNotIn(b'\x1b[2J', delta)
        self.assertNotIn(b'Upgrade and install packages', delta)
        self.assertNotIn(b'Enter Review', delta)
        self.send(b'q')
        self.finish(1)

    def test_standalone_escape_cancels_cleanly(self):
        self.send(b'\x1b')
        self.finish(1)


if __name__ == '__main__':
    unittest.main()
