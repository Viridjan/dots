---
name: feedback-gitignore-policy
description: "dots .gitignore policy — ignore secrets only, track everything else"
metadata: 
  node_type: memory
  type: feedback
  originSessionId: 54d9a0e6-cd7e-4488-9b0f-42690c84cece
  modified: 2026-08-15T22:01:27.110Z
---

User wants the dots repo .gitignore to ignore **sensitive data** (access tokens, passwords, credentials, session auth, crash dumps that can leak memory) **plus artifacts that regenerate continuously**. Everything else — machine-specific state, generated logs, themes, app settings, VM-storage symlinks — should be TRACKED so a fresh clone carries maximum config/state.

**Why:** maximize info available on clone; minimize re-setup. Only hard requirement: never push a credential.

**Refined 2026-08-15 — the second test is churn rate, not size.** A payload written once is fine to track however big; anything an app rewrites every launch grows history forever. Same session, both calls made explicitly by the user: `vesktop/ExtensionCache/` (3MB React DevTools, written once) → **track**; VSCodium's Chromium caches (`Cache`, `CachedData`, `GPUCache`, `Code Cache`, `Dawn*`, `CachedProfilesData`, `CachedExtensionVSIXs`, comparable size but rewritten each launch) → **ignore**. The latter had reached 41.5MB of 60MB of history (68%) and dirtied 24 files on every commit. See [[dots-history-purge]].

**How to apply:**
- Before adding a gitignore entry, ask "is this a secret?" If not, default to tracking it.
- Currently ignored (secrets): claude .credentials.json, cave auth.json + sessions/, vesktop sessionData/ (Discord token), VSCodium Cookies/Local Storage/Session Storage/Trust Tokens, fish_history, Crashpad/ dirs. (matrix/gomuks package removed entirely — see [[project-state]].)
- Exceptions kept ignored despite not being secrets: vesktop Singleton* (single-instance lock — stale copy breaks launch), vesktop state.json (window-bounds, churns every session, no clone value), scripts/.local/bin/{uv,uvx,claude-science} (large vendored binaries with their own installer/updater — 60-150MB+ each, permanent repo bloat with no clone value).
- New rule of thumb (2026-07-28): a non-secret file can still be excluded if it's a large (tens of MB+) binary that's reproducible via its own installer/package manager — same "no clone value, permanent bloat" logic as the churn-only exceptions above. Ask before committing; git history growth from binaries isn't easily reversible.
- GOTCHA: .gitignore does NOT support inline `# comments` after a path — put comments on their own line.
- Audited 2026-06-21: full scan (token prefixes syt_/xox/gh*_/sk-/AIza/ya29/JWT, PEM keys, SQLite .vscdb via strings, git history) found no secrets in any tracked file.

See [[project-state]].
