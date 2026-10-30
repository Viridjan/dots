"""Textual TUI: one screen — menu with a recap per row, submenus open inline below it."""
import os
import shutil
import socket
import tempfile
from pathlib import Path

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Vertical
from textual.screen import Screen
from textual.widgets import Footer, Header, Input, OptionList, SelectionList
from textual.widgets.option_list import Option

from . import config
from .state import State, detect_installed
from .progress import RunScreen


class Checklist(Vertical):
    """Generic checklist submenu. `apply(ticked_ids)` persists the whole selection."""

    BINDINGS = [Binding("escape", "close", "Close"), Binding("a", "all", "All"),
                Binding("n", "none", "None"), Binding("d", "defaults", "Repo defaults"),
                Binding("slash", "filter", "Filter")]

    def __init__(self, title, items, ticked, apply):
        super().__init__(classes="panel")
        self.border_title = title
        self.items, self.ticked, self.apply = items, set(ticked), apply
        self.mode = "filter"

    def compose(self) -> ComposeResult:
        yield Input(placeholder="filter…", id="flt")
        yield SelectionList(id="sl")

    def on_mount(self):
        self.query_one("#flt").display = False
        self.refill()
        self.query_one("#sl").focus()

    def refill(self, text=""):
        sl = self.query_one("#sl", SelectionList)
        keep = sl.highlighted
        sl.clear_options()
        sl.add_options([(label, i, i in self.ticked) for i, label, _ in self.items if text.lower() in label.lower()])
        if sl.option_count:
            sl.highlighted = min(keep or 0, sl.option_count - 1)

    def current(self):
        sl = self.query_one("#sl", SelectionList)
        return None if sl.highlighted is None else sl.get_option_at_index(sl.highlighted).value

    def commit(self):
        self.apply([i for i, _, _ in self.items if i in self.ticked])
        self.screen.refresh_menu()

    def on_selection_list_selection_toggled(self, ev):
        self.ticked ^= {ev.selection.value}
        self.commit()

    def on_input_changed(self, ev):
        if self.mode == "filter":
            self.refill(ev.value)

    def on_input_submitted(self, ev):
        f = self.query_one("#flt", Input)
        if self.mode != "filter":
            self.submit_text(ev.value)
            self.mode = "filter"
            f.value, f.placeholder, f.display = "", "filter…", False
        self.query_one("#sl").focus()

    def submit_text(self, text):
        pass

    def ask(self, mode, placeholder):
        f = self.query_one("#flt", Input)
        self.mode, f.placeholder, f.value, f.display = mode, placeholder, "", True
        f.focus()

    def action_filter(self):
        self.ask("filter", "filter…")

    def action_all(self):
        self.ticked = {i for i, _, _ in self.items}
        self.refill(); self.commit()

    def action_none(self):
        self.ticked = set()
        self.refill(); self.commit()

    def action_defaults(self):
        self.ticked = {i for i, _, d in self.items if d}
        self.refill(); self.commit()

    def action_close(self):
        self.screen.close_panel()


class PackagesChecklist(Checklist):
    BINDINGS = [Binding("plus", "add", "Add package"), Binding("x", "remove", "Mark remove")]

    def __init__(self, state):
        self.state = state
        items = state.package_items()
        super().__init__("Packages — untick = declined (remembered) · + add · x remove (demoted to dependency, removed if unneeded)",
                         items, [i for i, _, t in items if t], self.apply_all)

    def apply_all(self, ticked):
        ticked = set(ticked)
        for pid, _, _ in self.items:
            src, name = pid.split(":", 1)
            if (name in self.state.cfg["declined"][src]) == (pid in ticked):
                self.state.set_package(pid, pid in ticked)

    def reload(self):
        self.items = self.state.package_items()
        self.ticked = {i for i, _, t in self.items if t}
        self.refill(self.query_one("#flt", Input).value if self.mode == "filter" else "")
        self.screen.refresh_menu()

    def action_add(self):
        self.ask("add", "add package: name (paru) or flatpak:app.id — Enter to add")

    def submit_text(self, text):
        src, _, name = text.strip().rpartition(":")
        self.state.add_package("flatpak" if src == "flatpak" else "paru", name)
        self.reload()

    def action_remove(self):
        if self.current():
            if not self.state.toggle_remove(self.current()):
                self.notify("Flatpak removal is not supported. Untick the app to exclude it from installation.",
                            severity="warning")
            self.reload()


class UnlistedChecklist(Checklist):
    """Installed by hand but in no list. Keys act on ticked rows, else the highlighted one."""
    BINDINGS = [Binding("p", "sort('repo')", "packages.toml"), Binding("f", "sort('profile')", "Profile"),
                Binding("m", "sort('machine')", "This machine"), Binding("x", "sort('demote')", "Demote"),
                Binding("i", "sort('ignore')", "Ignore")]

    def __init__(self, state):
        self.state = state
        super().__init__("Unlisted — p packages.toml · f profile · m this machine · x demote to dependency · i ignore"
                         " · a ticks all", self.rows(), [], lambda ids: None)

    def rows(self):
        return [(f"{src}:{n}", f"{src:8} {n}", False) for src, n in self.state.unlisted()]

    def action_sort(self, how):
        pids = [i for i, _, _ in self.items if i in self.ticked] or ([self.current()] if self.current() else [])
        if not pids:
            return
        try:
            self.app.notify(self.state.sort_unlisted(pids, how))
        except config.ConfigError as e:
            self.app.notify(str(e), severity="error")
        self.items, self.ticked = self.rows(), set()
        self.refill(); self.screen.refresh_menu()


class OnceChecklist(Checklist):
    BINDINGS = [Binding("s", "skip", "Skip forever"), Binding("D", "done", "Already done")]

    def __init__(self, state):
        self.state = state
        super().__init__("One-time setup — ticked = run now · s skip · D already done",
                         state.items("once"), state.ticked("once"), lambda ids: state.set_ticks("once", ids))

    def mark(self, how):
        if self.current():
            self.state.mark_once(self.current(), how)
            self.items = self.state.items("once")
            self.refill(); self.screen.refresh_menu()

    def action_skip(self):
        self.mark("skip")

    def action_done(self):
        self.mark("done")


class SetupPanel(Vertical):
    """Profile + dotfile set, stacked. Auto-opens until a valid choice is saved."""

    BINDINGS = [Binding("escape", "close", "Close"), Binding("tab", "switch", "Switch box"),
                Binding("enter", "done", "Confirm", priority=True)]

    def __init__(self, state, host):
        super().__init__(classes="panel")
        self.state, self.host = state, host
        self.border_title = "Profile / dotfile set — Tab switches box, Enter confirms"

    def compose(self) -> ComposeResult:
        profs = self.state.repo.profiles
        yield OptionList(*[Option(f"{k:10} {v.get('description', '')}", id=k) for k, v in profs.items()],
                         id="prof", classes="pick")
        yield OptionList(*[Option(d, id=d) for d in [*self.state.repo.dotsets, "none"]], id="set", classes="pick")

    def on_mount(self):
        prof, dset = self.query_one("#prof", OptionList), self.query_one("#set", OptionList)
        prof.border_title, dset.border_title = "Profile", "Dotfile set"
        names = list(self.state.repo.profiles)
        cur = self.state.cfg.get("profile")
        pick = cur if cur in names else config.host_profile(self.state.repo, self.host)
        prof.highlighted = names.index(pick) if pick in names else 0
        sets = [*self.state.repo.dotsets, "none"]
        dflt = self.state.cfg.get("dotset") or self.state.repo.profiles.get(names[prof.highlighted] if names else "", {}).get("dotset")
        dset.highlighted = sets.index(dflt) if dflt in sets else len(sets) - 1
        prof.focus()

    def action_switch(self):
        self.screen.focus_next()

    def action_done(self):
        prof, dset = self.query_one("#prof", OptionList), self.query_one("#set", OptionList)
        if prof.highlighted is None or dset.highlighted is None:
            return
        self.state.choose(prof.get_option_at_index(prof.highlighted).id, dset.get_option_at_index(dset.highlighted).id)
        self.screen.close_panel()

    def action_close(self):
        if self.state.ready():  # first run: a profile must be chosen
            self.screen.close_panel()


class Home(Screen):
    BINDINGS = [Binding("q", "app.quit", "Quit"), Binding("r", "run", "Run")]
    CSS = """
    #menu {height: auto; border: round $accent; border-title-style: bold}
    #menu:blur {border: round $panel-lighten-2; border-title-color: $text}
    #sub {height: 1fr}
    .panel {height: 1fr; border: round $accent; border-title-style: bold; padding: 0 1}
    .panel SelectionList {height: 1fr; border: none}
    .pick {height: auto; margin-bottom: 1; border: round $panel-lighten-2;
           border-title-color: $text; border-title-style: bold}
    .pick:focus {border: round $accent; border-title-color: $accent}
    """
    MENU = [("maint", "Maintenance actions"), ("packages", "Packages"), ("unlisted", "Unlisted packages"),
            ("repos", "Git repositories"),
            ("dotfiles", "Dotfiles"), ("once", "One-time setup"), ("dms", "DMS & Git"),
            ("settings", "Profile / dotfile set"), ("run", "▶ Run")]
    TITLES = {"maint": "Maintenance actions", "repos": "Git repositories to clone (missing ones only)",
              "dotfiles": "Dotfiles to link from the chosen set", "dms": "DMS & Git — off by default"}

    def __init__(self, state, host):
        super().__init__()
        self.state, self.host = state, host

    def compose(self) -> ComposeResult:
        yield Header()
        yield OptionList(*[Option(self.menu_row(n), id=k) for n, (k, _) in enumerate(self.MENU)], id="menu")
        yield Vertical(id="sub")
        yield Footer()

    def menu_row(self, n):
        key, label = self.MENU[n]
        return f"{label:<24}[dim]│[/dim] {self.state.recap(key)}"

    def on_mount(self):
        m = self.query_one("#menu", OptionList)
        m.border_title = "Menu  ·  what will happen"
        m.highlighted = 0
        m.focus()
        if not self.state.ready():
            self.open_panel(SetupPanel(self.state, self.host))

    def refresh_menu(self):
        m = self.query_one("#menu", OptionList)
        for n in range(len(self.MENU)):
            m.replace_option_prompt_at_index(n, self.menu_row(n))

    def open_panel(self, panel):
        sub = self.query_one("#sub")
        sub.remove_children()
        sub.mount(panel)

    def close_panel(self):
        self.query_one("#sub").remove_children()
        self.refresh_menu()
        self.query_one("#menu").focus()

    def on_option_list_option_selected(self, ev):
        if ev.option_list.id != "menu":
            return
        key, st = ev.option.id, self.state
        if key == "run":
            self.action_run()
        elif key == "settings" or not st.ready():
            self.open_panel(SetupPanel(st, self.host))
        elif key == "packages":
            self.open_panel(PackagesChecklist(st))
        elif key == "once":
            self.open_panel(OnceChecklist(st))
        elif key == "unlisted":
            self.open_panel(UnlistedChecklist(st))
        else:
            self.open_panel(Checklist(self.TITLES[key], st.items(key), st.ticked(key),
                                      lambda ids, k=key: st.set_ticks(k, ids)))

    def action_run(self):
        self.app.run_selected()


class VjApp(App):
    TITLE = "vj"
    SUB_TITLE = "dots maintenance"

    def __init__(self, repo, cfg_path, installed=None, runner=None, host=None):
        super().__init__()
        self.state = State(repo, cfg_path, installed=installed)
        self.detect = installed is None
        self.host = host or os.environ.get("HOSTNAME") or socket.gethostname()
        self.runner = runner

    def on_mount(self):
        self.push_screen(Home(self.state, self.host))

    def action_quit(self):
        if isinstance(self.screen, RunScreen) and self.screen.fd is not None:
            self.notify("Maintenance is running. Ctrl+C interrupts it.", severity="warning")
            return
        super().action_quit()

    def run_selected(self):
        st = self.state
        if not st.ready():
            self.notify("Choose a profile and dotfile set first.", severity="warning")
            return
        ids = st.run_ids()
        if not ids:
            self.notify("Nothing selected to run.", severity="warning")
            return
        plan = Path(tempfile.mkdtemp(prefix="vj-plan-", dir=os.environ.get("XDG_RUNTIME_DIR")))
        try:
            st.write_plan(plan)
            env = {**os.environ, "VJ_PLAN_DIR": str(plan), "VJ_RESULT_FILE": str(plan / "result.tsv")}
            if self.runner is None:
                cmd = [str(st.repo.root / "scripts/.local/bin/vjupdate"), "--actions", ",".join(ids)]
                self.push_screen(RunScreen(cmd, env, plan / "result.tsv"),
                                 lambda rc: self.finish_run(plan, rc))
                return
            rc = self.runner(ids, env)
        except BaseException:
            shutil.rmtree(plan, ignore_errors=True)
            raise
        self.finish_run(plan, rc)

    def finish_run(self, plan, rc):
        st = self.state
        try:
            st.apply_results(plan / "result.tsv")
        finally:
            shutil.rmtree(plan, ignore_errors=True)
        st.ticks = {"once": [], "dms": []}
        if self.detect:
            st.installed = detect_installed()  # packages changed during the run
        self.screen.refresh_menu()
        self.notify(f"vjupdate exited {rc}", severity="information" if rc == 0 else "error")


def run(dots: Path) -> int:
    VjApp(config.load_repo(dots), config.config_path()).run()
    return 0
