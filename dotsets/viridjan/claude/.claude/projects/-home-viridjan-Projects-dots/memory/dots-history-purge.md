---
name: dots-history-purge
description: 2026-08-15 git history rewrite shrank dots 104MB→19MB; surface machine must hard-reset
metadata: 
  node_type: memory
  type: project
  originSessionId: 74ac168d-fad3-4549-8662-ad28e7e617d5
  modified: 2026-08-15T22:01:38.238Z
---

On 2026-08-15 the dots repo history was rewritten to purge VSCodium's Chromium
caches. `.git` went **104MB → 19MB**; all 286 commits preserved, every SHA changed.
HEAD `7a630fa` → `9a31b66`, force-pushed to origin/main.

**PENDING ACTION — the surface machine's clone is broken.** Every SHA changed, so it
cannot fast-forward. On that machine, after stashing anything uncommitted:

```bash
cd ~/Projects/dots && git fetch origin && git reset --hard origin/main
```

Remove this note once the surface has been reset.

**Backup:** `~/dots-backup-20260815-213204.bundle` (60MB, all refs, pre-purge) on the
desktop. Restore via `git clone dots-backup-*.bundle`. Safe to delete once the surface
is reset and nothing is missed.

**Method, if it's ever needed again:** two steps. `git rm -r --cached <paths>` plus
gitignore entries stops future growth (that alone took 104→61MB with
`git gc --prune=now`). Then `git filter-repo --force --path <each> --invert-paths`
purges history (61→19MB). Gotchas hit:
- filter-repo prompts "treat this run as a continuation?" when `.git/filter-repo/already_ran`
  exists from a previous run — needs `printf 'Y\n' |` in a non-interactive shell.
- It **removes the origin remote** afterward as a safety measure; re-add it and
  re-set upstream with `git branch --set-upstream-to=origin/main main`.
- Take a `git bundle create <file> --all` backup before starting, and verify the purge
  (commit count, real config files resolvable at HEAD) *before* force-pushing.

Related: [[feedback-gitignore-policy]] for the churn-rate rule this came from,
[[project-state]].
