---
name: vjupdate-2026-11-own-builds-ufw
description: "2026-11-01..03 vjupdate additions — projects.toml `build` (7000bar), [ufw].allow, AUR conflict swaps via --useask"
metadata:
  node_type: memory
  type: project
  originSessionId: 60db854a-0e54-4caf-9051-0350d88829db
  modified: 2026-11-03T18:46:15.380Z
---

- **Own software:** `projects.toml` `[[repo]]` may carry `build = "<cmd>"` → `project-builds.list` → `update_projects` (install + `--update`): ff-only pull, rebuild when HEAD ≠ `~/.local/state/dots/builds/<name>`, dirty tree skipped. 7000bar (Rust music player, `~/Projects/7000bar`, binary `~/.local/bin/7000bar`, launcher in `scripts/.local/share/applications`) is the first user; `rust` package provides cargo. Put new own-git software there, not in `.install-scripts.list`.
- **Firewall:** `[ufw] allow = [...]` (packages.toml/profiles) → `ufw_allow` at end of the services action; add-only. 2234/tcp for nicotine+ (re-added 2026-11-03).
- **AUR conflict swaps:** `_install_list` passes `--useask --ask=4`; without `--useask` paru refuses AUR conflicts under `--noconfirm`. Swapped greetd-dms-greeter-git → dux-greeter-git this way 2026-11-01. `install_all` returns 0 (recorded failures must not trip ERR trap).
- 7000bar is often edited live by another agent (Codex/Claude) — don't commit its dirty tree; user prefers waiting.

Related: [[vjupdate-2026-10-27-cleanup]], [[feedback-fix-script-systematically]], [[working-with-codex-in-dots]].
