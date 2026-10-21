"""`python3 -m vj` opens the TUI; `python3 -m vj plan DIR` writes a run plan for vjupdate."""
import os
import socket
import sys
from pathlib import Path

from . import config, resolve


def repo_root() -> Path:
    return Path(os.environ["VJ_DOTS"]) if os.environ.get("VJ_DOTS") else config.DOTS


def plan(outdir: str) -> int:
    repo = config.load_repo(repo_root())
    cfg = config.load_local()
    if not config.valid_choice(cfg, repo):
        host = os.environ.get("HOSTNAME") or socket.gethostname()
        name = config.host_profile(repo, host)
        if not name:
            print(f"no profile for host '{host}' — run 'vj' to choose one", file=sys.stderr)
            return 2
        cfg["profile"] = name
        cfg["dotset"] = repo.profiles[name].get("dotset", "none")
        if cfg["dotset"] not in repo.dotsets:
            cfg["dotset"] = "none"
    resolve.write_plan(repo, cfg, Path(outdir),
                       stow_selected=cfg["last"].get("dotfiles"), repos_selected=cfg["last"].get("repos"))
    return 0


def main(argv) -> int:
    if argv[:1] == ["plan"] and len(argv) == 2:
        return plan(argv[1])
    if argv:
        print("usage: vj            open the TUI\n       vj plan DIR   write a run plan for vjupdate", file=sys.stderr)
        return 2
    from .ui import run  # Textual is only needed for the TUI
    return run(repo_root())


if __name__ == "__main__":
    try:
        sys.exit(main(sys.argv[1:]))
    except config.ConfigError as e:
        print(f"vj: {e}", file=sys.stderr)
        sys.exit(2)
