# TODO

- [ ] Switch `vectorcraft-bin` to Flathub once `ai.storyteller.vectorcraft` is published (pacman > flatpak > AUR; Flatpak adds a sandbox), then remove it from `.paru-hold.list`.

## Run `surface-sync.sh` on the Surface — confirm manually

One-time catch-up for the Surface clone (unfolds `~/.local/bin`, resets to
origin/main incl. the 2026-08-15 history rewrite, re-stows, validates niri).
Run it from a copy outside the repo:

```bash
cd ~/Projects/dots && git fetch origin && git show origin/main:surface-sync.sh > /tmp/surface-sync.sh && bash /tmp/surface-sync.sh
```

Confirm each box by hand:

- [ ] Script ended with **Done.** (log: `~/.local/state/dots/surface-sync-*.log`)
- [ ] `~/.local/bin` is a real directory; `codex`, `uv`, `graphify`, … still run
- [ ] `git log -1` matches the desktop's HEAD
- [ ] niri reloaded, windows look normal
- [ ] Backup branch `pre-sync-backup-*` / stash `surface-sync *` (if created) checked, then dropped
- [ ] Desktop micro still highlights `.sh` / `.py` files
- [ ] Then: `git rm surface-sync.sh`, delete this section, clear the pending notes in Claude memory,
      delete `~/dots-backup-20260815-213204.bundle` on the desktop

## Ollama model for Surface Pro 9

RX 6700 XT (desktop) uses `qwen3:14b`. Surface has no discrete GPU — need to pick
a CPU/iGPU-friendly model (small enough to run on Iris Xe + RAM offload).
Options to evaluate: `qwen3:4b`, `llama3.2:3b`, `gemma3:4b`.
Add `setup_ollama` surface branch once decided.

No Flatpak: `alacritty` (terminal sandboxing issues), `btop`, `shelly`, `proton-mail-bin`.
