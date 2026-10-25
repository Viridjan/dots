"""`python3 -m vj unused PLANDIR [DAYS]`: report installed apps that are not in
the package lists, and apps with no recorded use in DAYS days.

Usage comes from DankMaterialShell, which already records it:
  appusage.json  last launch per desktop ID (DMS launcher only)
  wellbeing/db   focused seconds per window app_id per day (all windows)
Report only; removes nothing.
"""
import json
import re
import subprocess
import time
from pathlib import Path

STATE = Path.home() / ".local/state/DankMaterialShell"
DAY = re.compile(rb'\{"date":"(\d{4}-\d{2}-\d{2})","active":\d+,"apps":(\{[^{}]*\})\}')


def _run(*cmd) -> list:
    return subprocess.run(cmd, capture_output=True, text=True, check=True).stdout.split()


def last_seen(state: Path = STATE) -> tuple:
    """({lowercased id: unix seconds}, first tracked day or None)."""
    seen = {}

    def put(key, t):
        k = key.lower()
        seen[k] = max(seen.get(k, 0), t)

    try:
        rank = json.loads((state / "appusage.json").read_text()).get("appUsageRanking", {})
    except (OSError, ValueError):
        rank = {}
    for key, v in rank.items():
        put(key, v.get("lastUsed", 0) / 1000)
    first = None
    try:
        # ponytail: regex over the BoltDB file instead of a bolt reader; values
        # are plain JSON. Breaks if DMS changes the record shape → empty result.
        raw = (state / "wellbeing/db").read_bytes()
    except OSError:
        raw = b""
    for date, apps in DAY.findall(raw):
        day = time.mktime(time.strptime(date.decode(), "%Y-%m-%d")) + 86399
        first = min(first or date.decode(), date.decode())
        for app in json.loads(apps):
            put(app, day)
    return seen, first


def desktop_keys(path: Path) -> set | None:
    """Names a window or launcher entry may use for this app. None if hidden;
    empty for terminal apps (they never get their own window)."""
    keys = {path.stem, path.stem.rsplit(".", 1)[-1]}  # org.gnome.Nautilus → Nautilus
    for line in path.read_text(errors="replace").splitlines():
        if line.startswith("[") and line != "[Desktop Entry]":
            break
        k, _, v = line.partition("=")
        v = v.strip()
        if (k == "NoDisplay" and v.lower() == "true") or (k == "Hidden" and v.lower() == "true"):
            return None
        if k == "Terminal" and v.lower() == "true":
            return set()
        if k == "StartupWMClass":
            keys.add(v)
        if k == "Exec" and v.split() and Path(v.split()[0]).name != "flatpak":
            keys.add(Path(v.split()[0]).name)
    return {k.lower() for k in keys}


def apps() -> dict:
    """{package or flatpak ID: keys} for everything with a visible launcher."""
    out = {}
    for line in subprocess.run(["pacman", "-Ql", *_run("pacman", "-Qeq")],
                               capture_output=True, text=True, check=True).stdout.splitlines():
        pkg, _, f = line.partition(" ")
        p = Path(f)
        if p.parent == Path("/usr/share/applications") and p.suffix == ".desktop":
            keys = desktop_keys(p)
            if keys is not None:
                out.setdefault(pkg, set()).update(keys | ({pkg} if keys else set()))
    try:
        fl = _run("flatpak", "list", "--app", "--columns=application")
    except (OSError, subprocess.CalledProcessError):
        fl = []
    for app in fl:
        keys = {app.lower(), app.rsplit(".", 1)[-1].lower()}
        for root in ("/var/lib/flatpak", str(Path.home() / ".local/share/flatpak")):
            d = Path(root, "exports/share/applications", app + ".desktop")
            if d.exists():
                keys |= desktop_keys(d) or set()
        out[app] = keys
    return out


def report(plan: Path, days: int, now: float | None = None, installed=None, seen=None) -> list:
    """Lines to print; empty when nothing to report."""
    installed = apps() if installed is None else installed
    seen, first = last_seen() if seen is None else seen
    now = time.time() if now is None else now
    listed = set()
    for name in ("paru-install.list", "paru-skip.list", "flatpak-install.list"):
        try:
            listed |= set((plan / name).read_text().split())
        except OSError:
            pass
    lines = []
    unlisted = sorted(a for a in installed if a not in listed)
    if unlisted:
        lines.append("Installed but in no package list: " + " ".join(unlisted))
    cutoff = now - days * 86400
    if not first or time.mktime(time.strptime(first, "%Y-%m-%d")) > cutoff:
        # Launcher data alone misses keybind/autostart launches: wait for a full window.
        ready = time.strftime("%Y-%m-%d", time.localtime(
            (time.mktime(time.strptime(first, "%Y-%m-%d")) if first else now) + days * 86400))
        lines.append(f"Unused-app check starts {ready} (needs {days} days of DMS window tracking)")
        return lines
    idle = []
    for app, keys in sorted(installed.items()):
        if not keys:
            continue  # terminal app: not trackable
        t = max(seen.get(k, 0) for k in keys)
        if t < cutoff:
            idle.append(f"{app} ({time.strftime('%Y-%m-%d', time.localtime(t)) if t else 'never'})")
    if idle:
        lines.append(f"Not used in {days} days (last seen): " + ", ".join(idle))
    return lines
