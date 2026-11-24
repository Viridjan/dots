---
name: go-pinned-extra
description: "go was pinned to extra/ 2026-11-13..24 (cachyos-v3 1.27.4-2 v4 binary); pin removed, -3 works; test recipe for v4 breakage"
metadata:
  node_type: memory
  type: project
  originSessionId: 7a61ea6d-ff7c-4a56-8b25-402004496d61
  modified: 2026-11-14T09:44:54.620Z
---

2026-11-13: cachyos-v3 `go 2:1.27.4-2` shipped `/usr/bin/go` built for x86-64-v4; on the desktop (no AVX-512, v3 max) every `go` call dies with "This program can only be run on AMD64 processors with v4 microarchitecture support." → dux-player build failed. Fix: `[paru].pin = ["extra/go"]` in packages.toml (new sysup feature: held from -Syuu, then `pacman -S --needed extra/go`).

**Why:** a CachyOS packaging bug, not ours; Arch's generic build works.
**How to apply:** when a later cachyos-v3 go works (`pacman -Si cachyos-v3/go` newer than 1.27.4-2, test on a v3 CPU), remove the pin. Same pattern for any future "v4 binary in v3 repo" breakage. Related: [[dots-package-preferences]].

**Resolved 2026-11-24:** cachyos-v3 `go 2:1.27.4-3` runs on the desktop (user ran it from a temp extract: `go version go1.27.4`). Pin removed; `[paru].pin` is empty. Test recipe without installing (bash, not fish): `d=$(mktemp -d) && curl -fsSL "$(pacman -Sp cachyos-v3/go | tail -1)" | tar -C "$d" --zstd -x && GOROOT=$d/usr/lib/go "$d/usr/lib/go/bin/go" version; rm -rf "$d"` — the auto-mode classifier blocks Claude from running downloaded binaries, so give it to the user.
