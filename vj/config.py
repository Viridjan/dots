"""Repo data (packages, profiles, projects, dotsets) and the per-machine local config."""
import copy
import datetime
import json
import os
import tempfile
import tomllib
from dataclasses import dataclass, field
from pathlib import Path

DOTS = Path(__file__).resolve().parents[1]

DEFAULTS = {
    "profile": None,
    "dotset": None,
    "paru": {"add": [], "remove": []},
    "flatpak": {"add": [], "remove": []},
    "declined": {"paru": [], "flatpak": []},
    "once": {},
    "last": {},
}


def _toml(path: Path) -> dict:
    return tomllib.loads(path.read_text()) if path.exists() else {}


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
    if os.environ.get("VJ_CONFIG"):
        return Path(os.environ["VJ_CONFIG"])
    base = os.environ.get("XDG_CONFIG_HOME") or Path.home() / ".config"
    return Path(base) / "vjupdate/config.toml"


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
    if isinstance(v, (int, datetime.date)):
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


def valid_choice(cfg: dict, repo: Repo) -> bool:
    return cfg.get("profile") in repo.profiles and (cfg.get("dotset") == "none" or cfg.get("dotset") in repo.dotsets)
