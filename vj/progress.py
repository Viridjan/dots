"""In-app maintenance output backed by a real controlling terminal."""
import codecs
import errno
import fcntl
import os
import pty
import re
import select
import signal
import struct
import sys
import termios
import tty

from rich.text import Text
from textual.binding import Binding
from textual.screen import Screen
from textual.widgets import Footer, Header, Input, Label, ProgressBar, RichLog


class RunScreen(Screen):
    BINDINGS = [Binding('escape', 'back', 'Back'),
                Binding('ctrl+c', 'interrupt', 'Interrupt', priority=True),
                Binding('ctrl+t', 'terminal', 'Terminal / editor', priority=True)]
    CSS = '''
    RunScreen {padding: 0 1}
    RunScreen Label {height: auto}
    RunScreen ProgressBar {height: 1; margin-bottom: 1}
    #output {height: 1fr; border: round $accent}
    #reply {height: 3}
    '''

    def __init__(self, command, env, results):
        super().__init__()
        self.command, self.env, self.results = command, env, results
        self.returncode = None
        self.output = ''
        self.pid = self.fd = None
        self.decoder = codecs.getincrementaldecoder('utf-8')('replace')
        self.reaped = False
        self.exitcode = None

    def compose(self):
        yield Header()
        yield Label('Overall: completed or skipped phases', id='phase-label')
        yield ProgressBar(total=5, show_eta=False, id='overall')
        yield Label('Starting…', id='status', markup=False)
        yield ProgressBar(total=None, show_eta=False, show_percentage=False, id='activity')
        yield RichLog(id='output', wrap=True, max_lines=3000, markup=False)
        yield Input(placeholder='Reply to prompts here · Ctrl+T opens terminal mode for editors', id='reply')
        yield Footer()

    def on_mount(self):
        self.pid, self.fd = pty.fork()
        if self.pid == 0:
            try:
                os.execvpe(self.command[0], self.command, self.env)
            except OSError as exc:
                os.write(2, f'Cannot start maintenance: {exc}\n'.encode())
                os._exit(127)
        os.set_blocking(self.fd, False)
        self.resize_terminal()
        self.set_interval(0.05, self.poll_child)
        self.query_one('#reply', Input).focus()

    def resize_terminal(self):
        if self.fd is not None:
            fcntl.ioctl(self.fd, termios.TIOCSWINSZ,
                        struct.pack('HHHH', max(10, self.size.height - 12), max(20, self.size.width - 4), 0, 0))

    def on_resize(self):
        self.resize_terminal()

    def add_output(self, data):
        text = self.decoder.decode(data)
        self.output = (self.output + text)[-100000:]
        # Keep partial prompts visible even without a trailing newline.
        for line in text.replace('\r', '\n').splitlines():
            self.query_one('#output', RichLog).write(Text.from_ansi(line))
            plain = re.sub(r'\x1b\[[0-?]*[ -/]*[@-~]', '', line).strip()
            if plain.startswith('==>') or '▶' in plain:
                self.query_one('#status', Label).update(plain)

    def poll_child(self):
        if self.fd is None:
            return
        # Limit each tick so heavy output cannot starve keyboard/UI events.
        eof = False
        for _ in range(16):
            try:
                data = os.read(self.fd, 16384)
            except BlockingIOError:
                break
            except OSError as exc:
                if exc.errno != errno.EIO:
                    raise
                eof = True
                break
            if not data:
                eof = True
                break
            self.add_output(data)
        try:
            rows = self.results.read_text().splitlines()
        except FileNotFoundError:
            rows = []
        phases = {row.split('\t')[0] for row in rows
                  if row.startswith('phase:') and row.endswith(('\tok', '\tskip', '\tfail'))}
        self.query_one('#overall', ProgressBar).update(progress=len(phases))
        if not self.reaped:
            pid, status = os.waitpid(self.pid, os.WNOHANG)
            if pid:
                self.reaped = True
                self.exitcode = os.waitstatus_to_exitcode(status)
        if self.reaped and eof:
            self.returncode = self.exitcode
            os.close(self.fd)
            self.fd = None
            self.query_one('#activity', ProgressBar).update(total=1, progress=1 if self.returncode == 0 else 0)
            self.query_one('#status', Label).update(f'Finished (exit {self.returncode}) · Escape returns to menu')
            self.query_one('#reply', Input).disabled = True
        elif not eof:
            # sudo disables terminal echo: mask its response and never log input.
            self.query_one('#reply', Input).password = not bool(termios.tcgetattr(self.fd)[3] & termios.ECHO)

    def on_unmount(self):
        if self.fd is not None:
            # An externally closed app must not leave an unattended installer.
            try:
                os.killpg(self.pid, signal.SIGHUP)
            except ProcessLookupError:
                pass
            os.close(self.fd)
            self.fd = None
            if not self.reaped:
                os.waitpid(self.pid, os.WNOHANG)

    def on_input_submitted(self, event):
        if self.fd is not None and not self.reaped:
            os.write(self.fd, (event.value + '\n').encode())
            event.input.value = ''

    def action_interrupt(self):
        if self.fd is not None:
            os.write(self.fd, b'\x03')

    def action_back(self):
        if self.fd is None:
            self.dismiss(self.returncode)
        else:
            self.notify('Maintenance is running. Ctrl+C interrupts it.', severity='warning')

    def action_terminal(self):
        """Explicit full-terminal access to the same PTY for Vim/pacdiff."""
        if self.fd is None or not sys.stdin.isatty():
            return
        stdin = sys.stdin.fileno()
        old = termios.tcgetattr(stdin)
        with self.app.suspend():
            try:
                tty.setraw(stdin)
                os.write(1, b'\r\nTerminal mode: Ctrl+] returns to the progress view.\r\n')
                # Redraw interactive programs at the real terminal size.
                fcntl.ioctl(self.fd, termios.TIOCSWINSZ, fcntl.ioctl(stdin, termios.TIOCGWINSZ, b'\0' * 8))
                while True:
                    ready, _, _ = select.select([stdin, self.fd], [], [], 0.2)
                    if stdin in ready:
                        data = os.read(stdin, 4096)
                        if b'\x1d' in data:
                            break
                        os.write(self.fd, data)
                    if self.fd in ready:
                        try:
                            data = os.read(self.fd, 16384)
                        except OSError as exc:
                            if exc.errno == errno.EIO:
                                break
                            raise
                        if not data:
                            break
                        os.write(1, data)
            finally:
                termios.tcsetattr(stdin, termios.TCSADRAIN, old)
        self.resize_terminal()
