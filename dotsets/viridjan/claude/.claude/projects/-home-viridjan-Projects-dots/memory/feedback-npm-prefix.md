---
name: feedback-npm-prefix
description: npm global prefix must be ~/.local to avoid sudo requirement
metadata: 
  node_type: memory
  type: feedback
  originSessionId: 6f526ee9-e2af-4c62-a0cf-1fb32cfc6529
---

npm global prefix must be `~/.local`, not the default `/usr`.

**Why:** Default `/usr` prefix requires root for `npm install -g`. vjupdate runs npm install without sudo, so it silently fails. Setting prefix to `~/.local` puts binaries in `~/.local/bin/` which is user-writable and already in PATH.

**How to apply:** Before running any `npm install -g`, verify `npm config get prefix` returns `/home/viridjan/.local`. If not, run `npm config set prefix ~/.local` first.
