# TODO

- [ ] Switch `vectorcraft-bin` to Flathub once `ai.storyteller.vectorcraft` is published (pacman > flatpak > AUR; Flatpak adds a sandbox).
- [ ] Once desktop and Surface both run the `*craft-bin` packages (`pacman -Q vectorcraft-bin`), delete the 9 source `*craft` names from `packages.toml` [paru].remove (2026-10-25 swap).
- [ ] Install `alvr-bin` for Pico 4 Ultra VR (desktop). `alvr`/`alvr-git` are on the malware blocklist (June 2026 hijack); `alvr-bin` isn't (maintainer Ari43, last change 2026-02-13). Review the PKGBUILD before building, then add it to `profiles/desktop.toml`. Client APK must match `pacman -Q alvr-bin`.

## Run `surface-sync.sh` on the Surface — confirm manually

One-time catch-up for the Surface clone (unfolds `~/.local/bin`, resets to
origin/main incl. the 2026-08-15 history rewrite, relinks dotfiles from the
2026-10-21 `dotsets/viridjan/` layout, writes `~/.config/vjupdate/config.toml`
with `profile = "surface"`, validates niri). It asks for sudo for `/etc/brave`
and the ollama drop-in.
Run it from a copy outside the repo:

```bash
cd ~/Projects/dots && git fetch origin && git show origin/main:surface-sync.sh > /tmp/surface-sync.sh && bash /tmp/surface-sync.sh
```

Confirm each box by hand:

- [ ] Script ended with **Done.** (log: `~/.local/state/dots/surface-sync-*.log`)
- [ ] `~/.local/bin` is a real directory; `codex`, `uv`, `graphify`, … still run
- [ ] `git log -1` matches the desktop's HEAD
- [ ] niri reloaded, windows look normal
- [ ] `vj` opens, menu shows `surface · viridjan`; `readlink ~/.config/alacritty/alacritty.toml` points into `dotsets/viridjan`
- [ ] Optional: `sudo pacman -S python-textual` if `vj` says Textual is missing
- [ ] Backup branch `pre-sync-backup-*` / stash `surface-sync *` (if created) checked, then dropped
- [ ] Desktop micro still highlights `.sh` / `.py` files
- [ ] Then: `git rm surface-sync.sh`, delete this section, clear the pending notes in Claude memory,
      delete `~/dots-backup-20260815-213204.bundle` on the desktop

## Ollama model for Surface Pro 9

RX 6700 XT (desktop) uses `deepseek-r1:7b` (capped by `ollama` limits.conf). Surface has no discrete GPU — need to pick
a CPU/iGPU-friendly model (small enough to run on Iris Xe + RAM offload).
Options to evaluate: `qwen3:4b`, `llama3.2:3b`, `gemma3:4b`.
Add `setup_ollama` surface branch once decided.

No Flatpak: `alacritty` (terminal sandboxing issues), `btop`, `shelly`.
