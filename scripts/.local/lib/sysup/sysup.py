"""sysup's TOML side: repo lists + per-machine config → run plan, plus the small
config edits sysup's flags make. Stdlib only. Called by bash as
`python3 -B sysup.py <command> ...`; exit 2 = usage or config error (one line on stderr).

Commands:
  plan DIR                            write the run plan sysup reads
  unused PLANDIR [DAYS]               unlisted / unused apps (default 60 days)
  add WHERE SRC NAME [PROFILE]        WHERE: shared profile local remove ignore; SRC: paru flatpak
  choose PROFILE [DOTSET]             set this machine's profile (and dotfile set)
  status                              profile, features, one-time actions, last check
  menu ID...                          menu rows (TSV: id group label state description)
  once-done ID...                     stamp one-time actions done today
  once-skip ID                        mark a one-time action skipped
"""
import copy
import datetime
import json
import os
import re
import shlex
import socket
import subprocess
import sys
import tempfile
import time
import tomllib
from dataclasses import dataclass, field
from pathlib import Path

# scripts/.local/lib/sysup/sysup.py → repo root (resolve() follows the stow link).
DOTS = Path(os.environ["SYSUP_DOTS"]) if os.environ.get("SYSUP_DOTS") else Path(__file__).resolve().parents[4]

DEFAULTS = {
    "profile": None,
    "dotset": None,
    "paru": {"add": [], "remove": []},
    "flatpak": {"add": [], "remove": []},
    "declined": {"paru": [], "flatpak": []},
    "ignored": {"paru": [], "flatpak": []},  # unlisted installs the audit stops reporting
    "once": {},
    "select": {},   # dotfiles / repos: subsets to deploy / clone; missing = all
    "display": {},  # text_scale (applied by the dotfiles deploy)
}

# Menu groups, in display order.
GROUPS = ["packages", "health", "dotfiles", "launchers", "system", "apps", "accounts"]
# Every ID in sysup's MENU_ORDER: (group, label, description) for the menu and --status.
ACTIONS = {
    "sources": ("packages", "Refresh package sources", "Prepare paru, keys, mirrors, Flathub and projects; recent work is skipped."),
    "install": ("packages", "Upgrade and install packages", "Upgrade packages, install configured lists, then clean package caches."),
    "services": ("system", "Enable system services", "Enable configured system/user services and ufw rules; may ask for sudo."),
    "snapper": ("system", "Configure filesystem snapshots", "Create the root Snapper configuration if absent."),
    "automount": ("system", "Configure disk automounting", "Choose partitions and confirm /etc/fstab changes; a backup is kept."),
    "optimize": ("system", "Apply system tuning", "Tune CPU/GPU performance, system services and the mirror timer."),
    "keyboard": ("system", "Configure keyboard layout", "Set the X11/XWayland keyboard to US international."),
    "kernels": ("packages", "Manage kernels", "Interactively install or remove kernels; the running kernel is protected."),
    "greeter": ("system", "Configure login screen", "Install and synchronize the DMS greeter configuration."),
    "keyring-pam": ("system", "Configure login keyring", "Add gnome-keyring integration to the greetd PAM configuration."),
    "nvidia-niri": ("system", "Apply niri NVIDIA VRAM fix", "Install the GLVidHeapReuseRatio=0 NVIDIA application profile for niri."),
    "install-scripts": ("apps", "Run custom installers", "Execute commands in .install-scripts.list; installers may download and run code."),
    "fish": ("apps", "Configure fish and tide", "Install tide and apply the configured shell theme."),
    "dms-plugins": ("apps", "Install DMS plugins", "Install plugins from the repository plugin list."),
    "dms-export": ("dotfiles", "Save live DMS settings to repository", "Copy live DMS overrides except colors into the repo. Changes repository files."),
    "claude": ("apps", "Install Claude Code plugins", "Install Claude Code plugins, skills and MCP setup."),
    "caveman-code": ("apps", "Install caveman-code", "Install the npm command and refresh its local links."),
    "ollama": ("apps", "Download Ollama model", "Pull qwen3.5 and rebuild the Modelfile models (ollama-model feature)."),
    "vms": ("apps", "Prepare Windows virtual machine", "Create VM storage directories and download the Windows container image."),
    "steam-launchers": ("launchers", "Refresh Steam game launchers", "Create game launchers, remove entries for uninstalled Steam games, keep Big Picture off."),
    "app-launchers": ("launchers", "Maintain application launchers", "Remove stale app launchers; report apps without local launcher copies."),
    "lostfiles": ("health", "Report files owned by no package", "Run pacreport --unowned-files (about a minute, report only)."),
    "dotfiles-export": ("dotfiles", "Review and upload Git changes", "Review, stage, commit and push repo changes; each step asks for confirmation."),
    "stow-symlinks": ("dotfiles", "Refresh configuration links", "Refresh Stow/niri links. Conflicts stay unless --adopt was passed."),
    "dms-import": ("dotfiles", "Apply repository DMS settings", "Overwrite the live DMS overrides, including colors. No Git pull."),
    "audit": ("health", "Check system health", "Inspect packages, firmware, malware and database integrity."),
    "orphan-removal": ("packages", "Remove orphan packages", "Remove unused dependencies. Also runs the system health check."),
    "rebuild": ("packages", "Rebuild affected packages", "Reinstall packages flagged by rebuild-detector; holds excluded. Runs the health check."),
    "python-rebuild": ("packages", "Rebuild outdated Python packages", "Rebuild packages built for an old Python; holds excluded. Runs the health check."),
    "pacnew-merge": ("health", "Merge pending configuration files", "Review .pacnew files interactively with pacdiff. Runs the health check."),
    "git-identity": ("accounts", "Set Git name and email", "Set git user.name/email if unset."),
    "ssh-key": ("accounts", "Create SSH key and add it to GitHub", "ssh-keygen if missing, then gh ssh-key add if GitHub lacks it."),
    "fingerprint": ("accounts", "Enroll fingerprint", "Enroll a fingerprint with fprintd (needs the device)."),
    "bitwarden": ("accounts", "Log in to Bitwarden", "Open Bitwarden if no account is logged in."),
    "yubikey-pin": ("accounts", "Set YubiKey FIDO PIN", "Set the YubiKey FIDO2 PIN (needs the key)."),
    "surface-secureboot": ("accounts", "Enroll linux-surface Secure Boot key", "Install linux-surface-secureboot-mok when Secure Boot is on."),
}
# One-time setup actions, stamped in [once].
ONCE = ["services", "snapper", "automount", "optimize", "keyboard", "greeter", "keyring-pam",
        "nvidia-niri", "install-scripts", "fish", "claude", "caveman-code", "dms-plugins", "ollama",
        "vms", "git-identity", "ssh-key", "fingerprint", "bitwarden", "yubikey-pin", "surface-secureboot"]
# Offered only when the profile has this feature.
ONCE_FEATURE = {"nvidia-niri": "nvidia", "ollama": "ollama-model", "vms": "windows-vm", "surface-secureboot": "linux-surface"}


class ConfigError(Exception):
    """A TOML file cannot be parsed or an argument is invalid; message says what to do."""


# ─── Repo + local config ─────────────────────────────────

def _toml(path: Path) -> dict:
    if not path.exists():
        return {}
    try:
        return tomllib.loads(path.read_text())
    except tomllib.TOMLDecodeError as e:
        raise ConfigError(f"{path} is not valid TOML ({e}) — fix or delete it") from None


@dataclass
class Repo:
    root: Path
    packages: dict = field(default_factory=dict)
    profiles: dict = field(default_factory=dict)
    projects: list = field(default_factory=list)
    dotsets: list = field(default_factory=list)

    def stow_pkgs(self, dotset):
        """Stow packages in a set; profile-named dirs hold machine files, not packages."""
        d = self.root / "dotsets" / str(dotset)
        if dotset in (None, "none") or not d.is_dir():
            return []
        return sorted(p.name for p in d.iterdir() if p.is_dir() and p.name not in self.profiles)


def load_repo(dots: Path = DOTS) -> Repo:
    profiles = {p.stem: _toml(p) for p in sorted((dots / "profiles").glob("*.toml"))}
    sets = dots / "dotsets"
    return Repo(
        root=dots,
        packages=_toml(dots / "packages.toml"),
        profiles=profiles,
        projects=_toml(dots / "projects.toml").get("repo", []),
        dotsets=sorted(p.name for p in sets.iterdir() if p.is_dir()) if sets.is_dir() else [],
    )


def config_path() -> Path:
    if os.environ.get("SYSUP_CONFIG"):
        return Path(os.environ["SYSUP_CONFIG"])
    base = os.environ.get("XDG_CONFIG_HOME") or Path.home() / ".config"
    return Path(base) / "sysup/config.toml"


def load_local(path: Path | None = None) -> dict:
    """Full-shape config: file values over defaults, so callers never KeyError."""
    cfg = copy.deepcopy(DEFAULTS)
    for k, v in _toml(path or config_path()).items():
        if isinstance(cfg.get(k), dict) and isinstance(v, dict):
            cfg[k].update(v)
        else:
            cfg[k] = v
    return cfg


def _val(v) -> str:
    if isinstance(v, bool):
        return "true" if v else "false"
    if isinstance(v, (int, float, datetime.date)):
        return v.isoformat() if isinstance(v, datetime.date) else str(v)
    if isinstance(v, list):
        return "[" + ", ".join(_val(x) for x in v) + "]"
    return json.dumps(str(v), ensure_ascii=False)  # JSON strings are valid TOML basic strings


def dumps(d: dict) -> str:
    """Minimal TOML writer: top-level scalars, then one level of tables. None is omitted."""
    out = [f"{k} = {_val(v)}" for k, v in d.items() if v is not None and not isinstance(v, dict)]
    for k, v in d.items():
        if isinstance(v, dict):
            out += ["", f"[{k}]"] + [f"{json.dumps(sk)} = {_val(sv)}" for sk, sv in v.items() if sv is not None]
    return "\n".join(out) + "\n"


def save_local(cfg: dict, path: Path | None = None) -> None:
    path = path or config_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=path.parent, prefix=".config.", suffix=".tmp")
    try:
        with os.fdopen(fd, "w") as f:
            f.write(dumps(cfg))
        os.replace(tmp, path)
    except BaseException:
        Path(tmp).unlink(missing_ok=True)
        raise


def migrate_config() -> str:
    """Move the pre-sysup config (~/.config/vjupdate/config.toml) once.
    vj's [last] ticks become [select]; other [last] keys are dropped."""
    new = config_path()
    if os.environ.get("SYSUP_CONFIG") or new.exists():
        return ""
    old = new.parent.parent / "vjupdate/config.toml"
    if not old.exists():
        return ""
    raw = _toml(old)
    last = raw.pop("last", {})
    sel = {k: last[k] for k in ("dotfiles", "repos") if k in last}
    if sel:
        raw["select"] = sel
    cfg = copy.deepcopy(DEFAULTS)
    for k, v in raw.items():
        if isinstance(cfg.get(k), dict) and isinstance(v, dict):
            cfg[k].update(v)
        else:
            cfg[k] = v
    save_local(cfg, new)
    old.unlink()
    return f"moved {old} → {new}"


def add_to_list(path: Path, section: str, name: str) -> None:
    """Append name to `[section] install` in a hand-written TOML file, keeping its
    comments. Writes only if the result parses and contains the name."""
    text = path.read_text() if path.exists() else ""
    head = re.search(rf"^\[{re.escape(section)}\][ \t]*$", text, re.M)
    item = json.dumps(name)
    if not head:
        new = text.rstrip("\n") + f"\n\n[{section}]\ninstall = [\n    {item},\n]\n"
    else:
        nxt = re.compile(r"^\[", re.M).search(text, head.end())
        end = nxt.start() if nxt else len(text)
        key = re.compile(r"^install[ \t]*=[ \t]*\[", re.M).search(text, head.end(), end)
        if not key:
            new = text[:head.end()] + f"\ninstall = [{item}]" + text[head.end():]
        elif (rest := text[key.end():].split("\n", 1)[0].strip()) == "" or rest.startswith("#"):
            close = re.compile(r"^\][ \t]*$", re.M).search(text, key.end())  # multi-line array
            if not close:
                raise ConfigError(f"{path}: cannot find the end of [{section}] install")
            new = text[:close.start()] + f"    {item},\n" + text[close.start():]
        else:
            new = text[:key.end()] + f"{item}, " + text[key.end():]
    try:
        ok = name in tomllib.loads(new).get(section, {}).get("install", [])
    except tomllib.TOMLDecodeError:
        ok = False
    if not ok:
        raise ConfigError(f"{path}: could not add {name} to [{section}] install — edit it by hand")
    path.write_text(new)


def valid_choice(cfg: dict, repo: Repo) -> bool:
    return cfg.get("profile") in repo.profiles and (cfg.get("dotset") == "none" or cfg.get("dotset") in repo.dotsets)


def host_profile(repo: Repo, host: str):
    """First profile whose `hostname` is a substring of host."""
    for name, prof in repo.profiles.items():
        if prof.get("hostname") and prof["hostname"] in host:
            return name
    return None


# ─── Resolution + run plan ───────────────────────────────

def _uniq(items):
    return list(dict.fromkeys(items))


def resolve(repo: Repo, cfg: dict) -> dict:
    """install = repo + profile + local add − local remove − declined − skip."""
    prof = repo.profiles.get(cfg.get("profile"), {})
    pk = repo.packages
    skip = pk.get("paru", {}).get("skip", [])
    out = {}
    for src in ("paru", "flatpak"):
        drop = set(cfg[src]["remove"]) | set(cfg["declined"][src]) | (set(skip) if src == "paru" else set())
        wanted = pk.get(src, {}).get("install", []) + prof.get(src, {}).get("install", []) + cfg[src]["add"]
        out[f"{src}_install"] = [p for p in _uniq(wanted) if p not in drop]
    # Repo removes are conflict swaps (pacman -Rdd); local removes are demoted
    # to dependencies, so anything still required stays (pacman -D --asdeps).
    out["paru_remove"] = _uniq(pk.get("paru", {}).get("remove", []))
    out["paru_demote"] = _uniq(cfg["paru"]["remove"])
    out["flatpak_remove"] = _uniq(pk.get("flatpak", {}).get("remove", []))
    out["ignore"] = _uniq(cfg["ignored"]["paru"] + cfg["ignored"]["flatpak"])
    out["paru_hold"] = list(pk.get("paru", {}).get("hold", []))
    out["paru_pin"] = list(pk.get("paru", {}).get("pin", []))
    out["paru_skip"] = list(skip)
    # Lists with no local overrides: repo + profile, deduped.
    for key, (src, fld) in {"systemd_enable": ("systemd", "enable"), "systemd_user": ("systemd", "user"),
                            "npm_install": ("npm", "install"), "uv_install": ("uv", "install"),
                            "ufw_allow": ("ufw", "allow")}.items():
        out[key] = _uniq(pk.get(src, {}).get(fld, []) + prof.get(src, {}).get(fld, []))
    return out


def features(repo: Repo, cfg: dict) -> list:
    return list(repo.profiles.get(cfg.get("profile"), {}).get("features", []))


def write_plan(repo: Repo, cfg: dict, outdir: Path, stow_selected=None, repos_selected=None) -> None:
    """The list files sysup reads, plus a sourceable `env`."""
    outdir = Path(outdir)
    outdir.mkdir(parents=True, exist_ok=True)
    r = resolve(repo, cfg)
    dotset = cfg.get("dotset")
    stow = repo.stow_pkgs(dotset)
    if stow_selected is not None:
        stow = [p for p in stow if p in stow_selected]
    projects = [p for p in repo.projects if repos_selected is None or p["name"] in repos_selected]
    # Audit membership ignores [declined]: a declined package is still known.
    prof = repo.profiles.get(cfg.get("profile"), {})
    known = _uniq([p for src in ("paru", "flatpak")
                   for p in (repo.packages.get(src, {}).get("install", [])
                             + prof.get(src, {}).get("install", []) + cfg[src]["add"])])
    files = {
        "known-packages.list": known,
        "paru-install.list": r["paru_install"], "paru-remove.list": r["paru_remove"],
        "paru-hold.list": r["paru_hold"], "paru-pin.list": r["paru_pin"], "paru-skip.list": r["paru_skip"],
        "paru-demote.list": r["paru_demote"], "ignore.list": r["ignore"],
        "systemd-enable.list": r["systemd_enable"], "systemd-user.list": r["systemd_user"],
        "npm-install.list": r["npm_install"], "uv-install.list": r["uv_install"],
        "ufw-allow.list": r["ufw_allow"],
        "flatpak-install.list": r["flatpak_install"], "flatpak-remove.list": r["flatpak_remove"],
        "projects.list": [p["url"] for p in projects], "stow.list": stow,
        "project-builds.list": [f'{p["name"]}\t{p["build"]}' for p in projects if p.get("build")],
    }
    for name, items in files.items():
        (outdir / name).write_text("".join(f"{i}\n" for i in items))
    set_dir = "" if dotset in (None, "none") else str(repo.root / "dotsets" / dotset)
    env = {"SYSUP_PROFILE": cfg.get("profile") or "", "SYSUP_DOTSET": dotset or "none",
           "SYSUP_DOTSET_DIR": set_dir, "SYSUP_FEATURES": " ".join(features(repo, cfg)),
           "SYSUP_TEXT_SCALE": str(cfg["display"].get("text_scale", ""))}
    (outdir / "env").write_text("".join(f"{k}={shlex.quote(v)}\n" for k, v in env.items()))


def effective(repo: Repo) -> dict:
    """Local config with profile/dotset filled from the hostname when unset or stale."""
    cfg = load_local()
    if not valid_choice(cfg, repo):
        host = os.environ.get("HOSTNAME") or socket.gethostname()
        name = host_profile(repo, host)
        if not name:
            raise ConfigError(f"no profile for host '{host}' — run 'sysup --profile NAME' "
                              f"({', '.join(repo.profiles)})")
        cfg["profile"] = name
        cfg["dotset"] = repo.profiles[name].get("dotset", "none")
        if cfg["dotset"] not in repo.dotsets:
            cfg["dotset"] = "none"
    return cfg


# ─── Unlisted / unused apps (report only) ────────────────
# Usage comes from DankMaterialShell, which already records it:
#   appusage.json  last launch per desktop ID (DMS launcher only)
#   wellbeing/db   focused seconds per window app_id per day (all windows)

STATE = Path.home() / ".local/state/DankMaterialShell"
DAY = re.compile(rb'\{"date":"(\d{4}-\d{2}-\d{2})","active":\d+,"apps":(\{[^{}]*\})\}')


def _run(*cmd) -> list:
    return subprocess.run(cmd, capture_output=True, text=True, check=True).stdout.split()


def detect_explicit() -> dict:
    """{name: source} for explicitly installed pacman packages and flatpak apps."""
    found = {}
    for src, cmd in (("paru", ["pacman", "-Qeq"]), ("flatpak", ["flatpak", "list", "--app", "--columns=application"])):
        try:
            found |= dict.fromkeys(subprocess.run(cmd, capture_output=True, text=True, timeout=30).stdout.split(), src)
        except (OSError, subprocess.SubprocessError):
            pass
    return found


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
    for date, apps_json in DAY.findall(raw):
        day = time.mktime(time.strptime(date.decode(), "%Y-%m-%d")) + 86399
        first = min(first or date.decode(), date.decode())
        for app in json.loads(apps_json):
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


def report(plan: Path, days: int, now: float | None = None, installed=None, seen=None, explicit=None) -> list:
    """Lines to print; empty when nothing to report. `explicit`: every explicitly
    installed package/flatpak (unlisted check); `installed`: apps with a launcher."""
    installed = apps() if installed is None else installed
    explicit = set(detect_explicit()) if explicit is None else explicit
    seen, first = last_seen() if seen is None else seen
    now = time.time() if now is None else now
    listed = set()
    for name in ("known-packages.list", "paru-install.list", "paru-skip.list", "paru-remove.list", "paru-demote.list",
                 "flatpak-install.list", "flatpak-remove.list", "ignore.list"):
        try:
            listed |= set((plan / name).read_text().split())
        except OSError:
            pass
    lines = []
    unlisted = sorted(a for a in explicit if a not in listed)
    if unlisted:
        lines.append(f"{len(unlisted)} installed but in no package list: " + " ".join(unlisted))
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


# ─── Status ──────────────────────────────────────────────

def last_check(path=None, now=None) -> str:
    """One line summarising the last `sysup --check` (last-check.tsv), or ""."""
    path = Path(path or Path(os.environ.get("XDG_STATE_HOME") or Path.home() / ".local/state") / "dots/last-check.tsv")
    try:
        lines, mtime = path.read_text().splitlines(), path.stat().st_mtime
    except OSError:
        return ""
    rows = dict(line.split("\t", 1) for line in lines if "\t" in line)
    failed = [n for n, st in rows.items() if st == "fail"]
    warns = int(rows.get("@warnings", "0") or 0)
    days = int(((now or time.time()) - mtime) // 86400)
    age = "today" if days <= 0 else f"{days}d ago"
    if failed:
        return f"check {age}: {len(failed)} failed ({', '.join(failed[:3])})"
    if warns:
        return f"check {age}: {warns} warning{'' if warns == 1 else 's'}"
    return f"check {age}: ok"


def once_tasks(repo: Repo, cfg: dict) -> list:
    have = set(features(repo, cfg))
    return [(i, ACTIONS[i][1]) for i in ONCE if ONCE_FEATURE.get(i) in (None, *have)]


def once_state(cfg: dict, i: str) -> str:
    v = cfg["once"].get(i)
    return "never run" if v is None else "skipped" if v == "skip" else f"done {v}"


def menu_rows(repo: Repo, cfg: dict, ids) -> list:
    """TSV rows id, group, label, state, description for the sysup menu, by GROUPS then MENU_ORDER."""
    unknown = [i for i in ids if i not in ACTIONS]
    if unknown:
        raise ConfigError(f"no menu entry for: {' '.join(unknown)}")
    have = set(features(repo, cfg))
    return ["\t".join((i, *ACTIONS[i][:2], once_state(cfg, i) if i in ONCE else "", ACTIONS[i][2]))
            for i in sorted(ids, key=lambda i: GROUPS.index(ACTIONS[i][0]))
            if ONCE_FEATURE.get(i) in (None, *have)]


def actions_table(ids) -> list:
    """Help text: action IDs by group, one per row with its label (needs no config)."""
    width = max(len(i) for i in ids)
    out = []
    for g in GROUPS:
        rows = [f"    {i.ljust(width)}  {ACTIONS[i][1]}" for i in ids if ACTIONS.get(i, ("",))[0] == g]
        out += [f"  {g}:", *rows] if rows else []
    return out + [f"    {i}" for i in ids if i not in ACTIONS]


def status_lines(repo: Repo, cfg: dict) -> list:
    out = [f"profile: {cfg['profile']}   dotset: {cfg['dotset']}",
           f"features: {' '.join(features(repo, cfg)) or '-'}", "", "one-time actions (sysup --actions ID):"]
    width = max(len(i) for i in ONCE)
    for i, label in once_tasks(repo, cfg):
        state = once_state(cfg, i)
        out.append(f"  {i.ljust(width)}  {state.ljust(16)} {label}")
    chk = last_check()
    if chk:
        out += ["", chk]
    return out


# ─── CLI ─────────────────────────────────────────────────

def _once_ids(ids) -> list:
    known = set(ONCE)
    return [i for i in ids if i in known]


def cmd_add(where: str, src: str, name: str, profile: str = "") -> None:
    if src not in ("paru", "flatpak"):
        raise ConfigError(f"source must be paru or flatpak, not '{src}'")
    if where in ("shared", "profile"):
        if where == "profile" and not profile:
            raise ConfigError("no profile chosen — run: sysup --profile NAME")
        path = DOTS / "packages.toml" if where == "shared" else DOTS / "profiles" / f"{profile}.toml"
        if not path.exists():
            raise ConfigError(f"{path} does not exist")
        add_to_list(path, src, name)
        return
    if where == "remove" and src == "flatpak":
        raise ConfigError("local remove (demote) is for pacman packages only")
    cfg = load_local()
    target = {"local": cfg[src]["add"], "remove": cfg[src]["remove"],
              "ignore": cfg["ignored"][src]}.get(where)
    if target is None:
        raise ConfigError(f"unknown target '{where}' (shared profile local remove ignore)")
    if name not in target:
        target.append(name)
        save_local(cfg)


def main(argv) -> int:
    cmd, args = (argv[0], argv[1:]) if argv else ("", [])
    if cmd in ("plan", "choose", "status", "menu", "add", "once-done", "once-skip"):
        msg = migrate_config()
        if msg:
            print(msg, file=sys.stderr)
    if cmd == "plan" and len(args) == 1:
        repo = load_repo()
        cfg = effective(repo)
        write_plan(repo, cfg, Path(args[0]),
                   stow_selected=cfg["select"].get("dotfiles"), repos_selected=cfg["select"].get("repos"))
        return 0
    if cmd == "unused" and len(args) in (1, 2) and (len(args) == 1 or args[1].isdigit()):
        print("\n".join(report(Path(args[0]), int(args[1]) if len(args) == 2 else 60)))
        return 0
    if cmd == "add" and len(args) in (3, 4):
        cmd_add(*args)
        return 0
    if cmd == "choose" and len(args) in (1, 2):
        repo = load_repo()
        if args[0] not in repo.profiles:
            raise ConfigError(f"unknown profile '{args[0]}' — choose one of: {', '.join(repo.profiles)}")
        dotset = args[1] if len(args) == 2 else repo.profiles[args[0]].get("dotset", "none")
        if dotset != "none" and dotset not in repo.dotsets:
            raise ConfigError(f"unknown dotfile set '{dotset}' — choose one of: none, {', '.join(repo.dotsets)}")
        cfg = load_local()
        cfg["profile"], cfg["dotset"] = args[0], dotset
        save_local(cfg)
        print(f"profile: {args[0]}   dotset: {dotset}")
        return 0
    if cmd == "status" and not args:
        repo = load_repo()
        print("\n".join(status_lines(repo, effective(repo))))
        return 0
    if cmd == "actions" and args:
        print("\n".join(actions_table(args)))
        return 0
    if cmd == "menu" and args:
        repo = load_repo()
        print("\n".join(menu_rows(repo, effective(repo), args)))
        return 0
    if cmd in ("once-done", "once-skip") and args:
        ids = _once_ids(args)
        if cmd == "once-skip" and len(ids) != len(args):
            raise ConfigError(f"not a one-time action: {' '.join(set(args) - set(ids))}")
        if ids:
            cfg = load_local()
            for i in ids:
                cfg["once"][i] = "skip" if cmd == "once-skip" else datetime.date.today()
            save_local(cfg)
        return 0
    print(__doc__.split("Commands:")[1].rstrip(), file=sys.stderr)
    return 2


if __name__ == "__main__":
    try:
        sys.exit(main(sys.argv[1:]))
    except ConfigError as e:
        print(f"sysup: {e}", file=sys.stderr)
        sys.exit(2)
