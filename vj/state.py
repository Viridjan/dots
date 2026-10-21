"""Everything the TUI shows and changes, without Textual. Every change is saved at once."""
import datetime
import subprocess
from pathlib import Path

from . import config, resolve

# Same IDs as vjupdate's menu (_menu_catalog). (id, label, ticked by default)
MAINT = [
    ("sources", "Refresh package sources", True),
    ("install", "Upgrade and install packages", True),
    ("audit", "Check system health", True),
    ("orphan-removal", "Remove orphan packages", True),
    ("rebuild", "Rebuild affected packages", True),
    ("python-rebuild", "Rebuild outdated Python packages", True),
    ("pacnew-merge", "Merge pending configuration files", False),
    ("stow-symlinks", "Refresh configuration links", True),
    ("steam-launchers", "Refresh Steam game launchers", True),
    ("app-launchers", "Maintain application launchers", True),
    ("kernels", "Manage kernels", False),
    ("manual-steps", "Show post-install checklist", False),
]
ONCE = [
    ("services", "Enable system services"),
    ("snapper", "Configure filesystem snapshots"),
    ("automount", "Configure disk automounting"),
    ("optimize", "Apply system tuning"),
    ("keyboard", "Configure keyboard layout"),
    ("greeter", "Configure login screen"),
    ("keyring-pam", "Configure login keyring"),
    ("install-scripts", "Run custom installers"),
    ("fish", "Configure fish and tide"),
    ("claude", "Install Claude Code plugins"),
    ("caveman-code", "Install caveman-code"),
    ("dms-plugins", "Install DMS plugins"),
    ("ollama", "Download Ollama model"),
    ("vms", "Prepare Windows virtual machine"),
]
DMS = [
    ("dms-import", "Apply repository DMS settings"),
    ("dms-export", "Save live DMS settings to repository"),
    ("dotfiles-export", "Review and upload Git changes"),
]


def detect_installed() -> set:
    """pacman + flatpak app IDs; a missing tool just contributes nothing."""
    found = set()
    for cmd in (["pacman", "-Qq"], ["flatpak", "list", "--app", "--columns=application"]):
        try:
            found |= set(subprocess.run(cmd, capture_output=True, text=True, timeout=30).stdout.split())
        except (OSError, subprocess.SubprocessError):
            pass
    return found


def plural(n, word):
    return f"{n} {word}{'' if n == 1 else 's'}"


class State:
    def __init__(self, repo, cfg_path: Path, installed=None):
        self.repo, self.cfg_path = repo, cfg_path
        self.cfg = config.load_local(cfg_path)
        self.installed = detect_installed() if installed is None else installed
        self.times = resolve.load_times(repo.root)
        self.ticks = {"once": [], "dms": []}  # per-run only, never remembered

    # ── persistence ──
    def save(self):
        config.save_local(self.cfg, self.cfg_path)

    def ready(self):
        return config.valid_choice(self.cfg, self.repo)

    def choose(self, profile, dotset):
        self.cfg.update(profile=profile, dotset=dotset)
        self.save()

    # ── generic checklists ──
    def items(self, key):
        """(id, label, default) for a non-package checklist."""
        if key == "maint":
            return MAINT
        if key == "once":
            return [(i, f"{label:<34}[dim]{self.once_status(i)}[/dim]", False) for i, label in ONCE]
        if key == "dms":
            return [(i, label, False) for i, label in DMS]
        if key == "repos":
            return [(p["name"], p["name"], True) for p in self.repo.projects]
        if key == "dotfiles":
            return [(p, p, True) for p in self.repo.stow_pkgs(self.cfg.get("dotset"))]
        raise KeyError(key)

    def ticked(self, key):
        if key in self.ticks:
            return list(self.ticks[key])
        if key in self.cfg["last"]:
            return list(self.cfg["last"][key])
        return [i for i, _, d in self.items(key) if d]

    def set_ticks(self, key, ids):
        if key in self.ticks:
            self.ticks[key] = list(ids)
        else:
            self.cfg["last"][key] = list(ids)
            self.save()

    # ── packages ──
    def _offered(self):
        """Resolved lists as if nothing were declined, so declined stay visible to re-tick."""
        empty = {"add": [], "remove": []}
        cfg = {**self.cfg, "declined": {"paru": [], "flatpak": []},
               "paru": {**empty, "add": self.cfg["paru"]["add"]}, "flatpak": {**empty, "add": self.cfg["flatpak"]["add"]}}
        r = resolve.resolve(self.repo, cfg)
        return [("paru", n) for n in r["paru_install"]] + [("flatpak", n) for n in r["flatpak_install"]]

    def package_items(self):
        out = []
        for src, name in self._offered():
            sec, guessed = resolve.estimate(src, name, self.times)
            removing = name in self.cfg[src]["remove"]
            state = "[#ff8700]remove[/]   " if removing else f"{'installed' if name in self.installed else 'new':9}"
            out.append((f"{src}:{name}", f"{resolve.fmt_c(sec, guessed, pad=9)}  {state}  {name}",
                        not removing and name not in self.cfg["declined"][src]))
        return out

    def set_package(self, pid, ticked):
        src, name = pid.split(":", 1)
        declined = [n for n in self.cfg["declined"][src] if n != name]
        if not ticked:
            declined.append(name)
        self.cfg["declined"][src] = declined
        self.save()

    def add_package(self, src, name):
        name = name.strip()
        if name and name not in self.cfg[src]["add"]:
            self.cfg[src]["add"].append(name)
            self.cfg[src]["remove"] = [n for n in self.cfg[src]["remove"] if n != name]
            self.save()

    def toggle_remove(self, pid):
        src, name = pid.split(":", 1)
        rm = self.cfg[src]["remove"]
        self.cfg[src]["remove"] = [n for n in rm if n != name] if name in rm else rm + [name]
        self.save()

    def to_install(self):
        r = resolve.resolve(self.repo, self.cfg)
        return {src: [n for n in r[f"{src}_install"] if n not in self.installed] for src in ("paru", "flatpak")}

    def install_seconds(self):
        return sum(resolve.estimate(src, n, self.times)[0] for src, ns in self.to_install().items() for n in ns)

    def removals(self):
        repo_rm = [n for n in self.repo.packages.get("paru", {}).get("remove", []) if n in self.installed]
        return list(dict.fromkeys(repo_rm + self.cfg["paru"]["remove"] + self.cfg["flatpak"]["remove"]))

    # ── one-time tasks ──
    def once_status(self, i):
        v = self.cfg["once"].get(i)
        return "never run" if v is None else "skipped" if v == "skip" else f"done {v}"

    def mark_once(self, i, how, today=None):
        self.cfg["once"][i] = "skip" if how == "skip" else (today or datetime.date.today())
        self.save()

    def apply_results(self, path: Path, today=None):
        once = {i for i, _ in ONCE}
        if not Path(path).exists():
            return
        for line in Path(path).read_text().splitlines():
            name, _, result = line.partition("\t")
            i = name.removeprefix("action:")
            if name.startswith("action:") and result == "ok" and i in once:
                self.cfg["once"][i] = today or datetime.date.today()
        self.save()

    # ── run ──
    def run_ids(self):
        return self.ticked("maint") + self.ticked("once") + self.ticked("dms")

    def write_plan(self, outdir):
        resolve.write_plan(self.repo, self.cfg, Path(outdir),
                           stow_selected=self.ticked("dotfiles"), repos_selected=self.ticked("repos"))

    # ── one-line summaries next to each menu entry ──
    def recap(self, key):
        if key == "maint":
            n = len(self.ticked("maint"))
            return f"run {n} of {len(MAINT)} actions" if n else "[dim]nothing[/dim]"
        if key == "packages":
            new = sum(len(v) for v in self.to_install().values())
            parts = [f"install {plural(new, 'package')} {resolve.fmt_c(self.install_seconds())}" if new
                     else "all installed"]
            if self.removals():
                parts.append(f"remove {len(self.removals())}")
            declined = sum(len(v) for v in self.cfg["declined"].values())
            if declined:
                parts.append(f"{declined} declined")
            return " · ".join(parts)
        if key == "repos":
            return f"clone missing · {len(self.ticked('repos'))} of {plural(len(self.repo.projects), 'repo')}"
        if key == "dotfiles":
            if self.cfg.get("dotset") in (None, "none"):
                return "[dim]not managed[/dim]"
            total = len(self.items("dotfiles"))
            return f"link {len(self.ticked('dotfiles'))} of {total} from {self.cfg['dotset']}"
        if key == "once":
            never = sum(1 for i, _ in ONCE if i not in self.cfg["once"])
            n = len(self.ticked("once"))
            return (f"run {n} · " if n else "") + (f"[#ffd75f]{never} never run[/]" if never else "all done")
        if key == "dms":
            n = len(self.ticked("dms"))
            return f"run {n}" if n else "[dim]nothing[/dim]"
        if key == "settings":
            return f"{self.cfg.get('profile') or '[#ffd75f]not set[/]'} · {self.cfg.get('dotset') or '—'}"
        if key == "run":
            return f"press r · install time {resolve.fmt_c(self.install_seconds())} [dim](upgrades/actions extra)[/dim]"
        return ""
