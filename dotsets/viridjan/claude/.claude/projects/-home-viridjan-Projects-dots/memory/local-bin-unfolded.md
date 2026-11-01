---
name: local-bin-unfolded
description: ~/.local/bin unfolded from the repo 2026-09-25; Surface must run the migration BEFORE git pull
metadata:
  node_type: memory
  type: project
  originSessionId: 56a37e3a-1df0-4b5b-9e28-6c130ab2771b
  modified: 2026-09-27T10:03:44.017Z
---

2026-09-25: `scripts` is now stowed `--no-folding` (commit 680e17d). `~/.local/bin` is a real dir; only the tracked scripts link into the repo (vjupdate, start-windows, start-open-notebook, start-keep as of 2026-10-13; adding one means updating the KEEP lists in CLAUDE.md and surface-sync.sh). Installer outputs (uv, codex, graphify, unsloth, AppImages…) live outside git.

**Why:** the folded link made every installer write into the repo (tracked absolute symlinks, growing .gitignore list of binaries).

**How to apply:** Desktop is migrated. **Surface is NOT yet**: the one-shot `surface-sync.sh` (repo root, commit after 128192f) does everything — run via `git fetch && git show origin/main:surface-sync.sh > /tmp/s.sh && bash /tmp/s.sh`; log in `~/.local/state/dots/surface-sync-*.log`. Once the Surface reports done: `git rm surface-sync.sh`, clear this note and the PENDING note in [[dots-history-purge]]. Manual fallback: the migration snippet in CLAUDE.md ("Before 2026-09-25 ~/.local/bin was a folded link…") BEFORE `git pull` there, or the pull removes the tracked installer links from PATH. Never re-add `scripts` to a plain `stow --restow` list. Related: [[dots-history-purge]] (Surface also still owes a hard-reset).
