"""Turn repo lists + local config into concrete package lists, estimates and a run plan."""
import shlex
from pathlib import Path

from .config import DOTS, Repo

GUESS = {"paru": 3, "flatpak": 10}  # seconds per package when there is no history
COLOURS = ((10, "#5fd75f"), (60, "#ffd75f"), (float("inf"), "#ff8700"))


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
    # Repo removes are conflict swaps (pacman -Rdd); local `x` marks are demoted
    # to dependencies, so anything still required stays (pacman -D --asdeps).
    out["paru_remove"] = _uniq(pk.get("paru", {}).get("remove", []))
    out["paru_demote"] = _uniq(cfg["paru"]["remove"])
    out["ignore"] = _uniq(cfg["ignored"]["paru"] + cfg["ignored"]["flatpak"])
    out["paru_hold"] = list(pk.get("paru", {}).get("hold", []))
    out["paru_skip"] = list(skip)
    # Lists with no local overrides: repo + profile, deduped.
    for key, (src, field) in {"systemd_enable": ("systemd", "enable"), "systemd_user": ("systemd", "user"),
                              "npm_install": ("npm", "install"), "uv_install": ("uv", "install")}.items():
        out[key] = _uniq(pk.get(src, {}).get(field, []) + prof.get(src, {}).get(field, []))
    return out


def features(repo: Repo, cfg: dict) -> list:
    return list(repo.profiles.get(cfg.get("profile"), {}).get("features", []))


def load_times(dots: Path = DOTS) -> dict:
    f = dots / "build-times.tsv"
    times = {}
    if f.exists():
        for line in f.read_text().splitlines():
            k, _, v = line.partition("\t")
            if v.strip().isdigit():
                times[k] = int(v)
    return times


def estimate(src: str, name: str, times: dict) -> tuple:
    """(seconds, guessed). AUR build history wins, then the per-package average."""
    if src == "paru" and f"aur:{name}" in times:
        return times[f"aur:{name}"], False
    if f"@{'pacman' if src == 'paru' else 'flatpak'}-per-pkg" in times:
        return times[f"@{'pacman' if src == 'paru' else 'flatpak'}-per-pkg"], False
    return GUESS[src], True


def fmt(sec: int) -> str:
    return "< 10 s" if sec < 10 else "< 1 min" if sec < 60 else f"~{round(sec / 60)} min"


def fmt_c(sec: int, guessed: bool = False, pad: int = 0) -> str:
    """Textual markup: green < 10 s, yellow < 1 min, orange otherwise; `?` = guessed."""
    colour = next(c for limit, c in COLOURS if sec < limit)
    return f"[{colour}]{(fmt(sec) + (' ?' if guessed else '')).ljust(pad)}[/{colour}]"


def write_plan(repo: Repo, cfg: dict, outdir: Path, stow_selected=None, repos_selected=None) -> None:
    """Files vjupdate reads instead of the old .list files, plus a sourceable `env`."""
    outdir = Path(outdir)
    outdir.mkdir(parents=True, exist_ok=True)
    r = resolve(repo, cfg)
    dotset = cfg.get("dotset")
    stow = repo.stow_pkgs(dotset)
    if stow_selected is not None:
        stow = [p for p in stow if p in stow_selected]
    projects = [p for p in repo.projects if repos_selected is None or p["name"] in repos_selected]
    files = {
        "paru-install.list": r["paru_install"], "paru-remove.list": r["paru_remove"],
        "paru-hold.list": r["paru_hold"], "paru-skip.list": r["paru_skip"],
        "paru-demote.list": r["paru_demote"], "ignore.list": r["ignore"],
        "systemd-enable.list": r["systemd_enable"], "systemd-user.list": r["systemd_user"],
        "npm-install.list": r["npm_install"], "uv-install.list": r["uv_install"],
        "flatpak-install.list": r["flatpak_install"],
        "projects.list": [p["url"] for p in projects], "stow.list": stow,
    }
    for name, items in files.items():
        (outdir / name).write_text("".join(f"{i}\n" for i in items))
    set_dir = "" if dotset in (None, "none") else str(repo.root / "dotsets" / dotset)
    env = {"VJ_PROFILE": cfg.get("profile") or "", "VJ_DOTSET": dotset or "none",
           "VJ_DOTSET_DIR": set_dir, "VJ_FEATURES": " ".join(features(repo, cfg))}
    (outdir / "env").write_text("".join(f"{k}={shlex.quote(v)}\n" for k, v in env.items()))
