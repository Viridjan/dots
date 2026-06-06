---
name: sync
description: Use when ending a dots session — refreshes CLAUDE.md, saves session memories, commits all changes, and pushes to remote. Trigger: /sync
trigger: /sync
---

# /sync — End-of-session sync for the dots repo

Wraps up a dots working session in five steps.

## Steps

### 1. Refresh CLAUDE.md
Invoke the `init` skill to regenerate project documentation from the current repo state.

### 2. Update README.md
Review session changes and update `~/Projects/dots/README.md` if anything is now outdated or missing. The README is human-facing — covers fresh install, manual steps, stow operations, packages, gaming, and system optimisations. Update only what changed:
- New packages or tools added → update the relevant section
- New manual steps → add to "Manual steps (after the script)" 
- New VM or setup → document under the appropriate section
- Removed packages/tools → remove stale entries

Skip if no user-visible changes were made this session.

### 4. Save memories
Review the current conversation. Save anything worth keeping across sessions:
- User preferences or feedback given this session
- Project state changes (new packages, new rules, new workflows)
- Anything that would change how you'd approach dots next time

Use the memory types: `user`, `feedback`, `project`, `reference`. Skip ephemeral task details.

### 5. Commit
Stage all modified tracked files in `~/Projects/dots/`. Generate a commit message summarizing what changed this session. Use conventional commits format. Co-author line required.

```bash
cd ~/Projects/dots
git add -u
# also stage any new files the user added
git status  # confirm what's staged
git commit -m "$(cat <<'EOF'
<summary of session changes>

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>
EOF
)"
```

### 6. Push
```bash
git push origin main
```

## Notes
- If nothing changed (`git status` clean), skip commit/push and say so
- If `init` finds nothing new to document, skip it silently
- Confirm push succeeded before reporting done
