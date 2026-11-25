---
name: feedback-memory-links
description: memory dir is stow-linked per file; write new memories in the repo path, never sed -i a linked file
metadata:
  type: feedback
---

`~/.claude/projects/-home-viridjan-Projects-dots/memory/*.md` are per-file stow links into `dotsets/viridjan/claude/.claude/projects/.../memory/`. A new file written at the live path is a real file outside git; `sed -i` on a link replaces it with a real file (happened 2026-11-26 with MEMORY.md).
**Why:** breaks sync to Surface/Plancia and causes `stow conflict in 'claude'`.
**How to apply:** create/edit memory files at the repo path, then `cd dotsets/viridjan && stow --restow -t ~ claude`; append with `>>` or Edit, not `sed -i`. Related: [[dots-shell-conventions]].
