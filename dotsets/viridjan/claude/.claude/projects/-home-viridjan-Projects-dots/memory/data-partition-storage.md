---
name: data-partition-storage
description: "Desktop root disk (586G) vs /mnt/data (3.1T); big media and downloads go to /mnt/data, not ~"
metadata:
  node_type: memory
  type: project
  originSessionId: c23e2fd4-82a1-4d1c-9515-27a0b5ccdda1
  modified: 2026-11-19T15:42:22.510Z
---

Desktop root (`/dev/nvme0n1p2`, 586G btrfs, `@` + `@home`; snapper only on `/`) fills up; `/mnt/data` (3.1T) is the place for bulk files. 2026-11-19 cleanup: 448G → ~337G used: Breaking Bad S01/S02 (212G) moved `~/Downloads` → `/mnt/data/Videos/`, uv cache, `~/.unsloth`, Lutris data, Trash, paccache -rk1. qBittorrent now defaults to `/mnt/data/Downloads` (sysup feature `data-partition`).

**Why:** the user asked to free main-disk space; `/mnt/download` was asked for but would have lived on root, so `/mnt/data/Downloads` was chosen instead.

**How to apply:** for disk-space questions, check `du -xh --max-depth=1 ~` first (Downloads, `~/.var/app/com.usebottles.bottles` 36G still on root). Freed space that doesn't show in `df` = a deleted file still held open (qBittorrent seeding) — check `/proc/*/fd` for `(deleted)`. Moving `~/.var/app/com.usebottles.bottles` to /mnt/data is the next candidate.
