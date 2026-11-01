# TODO

- [ ] Review desktop `/etc/fstab` bind-mount entries containing literal `\t`
  separators (observed 2026-10-30). Back up the file and validate corrected
  entries before applying mount changes; this session did not change fstab.

- [ ] Switch `vectorcraft-bin` to Flathub once `ai.storyteller.vectorcraft` is published (pacman > flatpak > AUR; Flatpak adds a sandbox).
- [ ] Once desktop and Surface both run the `*craft-bin` packages (`pacman -Q vectorcraft-bin`), delete the 9 source `*craft` names from `packages.toml` [paru].remove (2026-10-25 swap).
- [ ] Greeter swap on the desktop (Surface done 2026-11-01): `vjupdate --actions install` now replaces `greetd-dms-greeter-git` with `dux-greeter-git` in one transaction (`--ask=4`; a failed build keeps the old greeter). Confirm with `pacman -Q dux-greeter-git`, then `vjupdate --actions greeter`. If the conflict isn't auto-accepted, fall back to `paru -S dux-greeter-git` by hand.
- [ ] Install `alvr-bin` for Pico 4 Ultra VR (desktop). `alvr`/`alvr-git` are on the malware blocklist (June 2026 hijack); `alvr-bin` isn't (maintainer Ari43, last change 2026-02-13). Review the PKGBUILD before building, then add it to `profiles/desktop.toml`. Client APK must match `pacman -Q alvr-bin`.

## Desktop leftovers from the Surface migration (2026-11-01)

- [ ] Desktop micro still highlights `.sh` / `.py` files
- [ ] Delete `~/dots-backup-20260815-213204.bundle` on the desktop

## Ollama model for Surface Pro 9

RX 6700 XT (desktop) uses `qwen3.5` (VRAM-capped in its Modelfile). Surface has no discrete GPU — need to pick
a CPU/iGPU-friendly model (small enough to run on Iris Xe + RAM offload).
Options to evaluate: `qwen3:4b`, `llama3.2:3b`, `gemma3:4b`.
Add `setup_ollama` surface branch once decided.

No Flatpak: `alacritty` (terminal sandboxing issues), `shelly`.
