# TODO

- [ ] Switch `vectorcraft-bin` to Flathub once `ai.storyteller.vectorcraft` is published (pacman > flatpak > AUR; Flatpak adds a sandbox).
- [ ] Once desktop and Surface both run the `*craft-bin` packages (`pacman -Q vectorcraft-bin`), delete the 9 source `*craft` names from `packages.toml` [paru].remove (2026-10-25 swap).
- [ ] Greeter swap on the desktop (Surface done 2026-11-01): `sysup --actions install` now replaces `greetd-dms-greeter-git` with `dux-greeter-git` in one transaction (`--ask=4`; a failed build keeps the old greeter). Confirm with `pacman -Q dux-greeter-git`, then `sysup --actions greeter`. If the conflict isn't auto-accepted, fall back to `paru -S dux-greeter-git` by hand.
- [ ] Desktop: `sysup --actions install` builds `alvr-bin` (in `profiles/desktop.toml`, PKGBUILD reviewed 2026-11-01). Then install the matching ALVR client APK on the Pico 4 Ultra.


## sysup rename (2026-11-08) — Surface and Plancia, once each

After `git pull` the old `vjupdate` and `vj` links in `~/.local/bin` point at
deleted files. Run by full path once:

```bash
~/Projects/dots/scripts/.local/bin/sysup --actions stow-symlinks,services
```

- [ ] Surface: run the command above. It links `sysup`, prunes the dead links,
      moves `~/.config/vjupdate/config.toml` to `~/.config/sysup/config.toml`, and the
      services action swaps `vjupdate-check.timer` for `sysup-check.timer`.
      Confirm: `sysup --status` shows profile `surface` and the old one-time dates;
      `systemctl --user list-timers | grep sysup-check`.
- [ ] Plancia: same command and checks (profile `plancia`).
- [ ] Both: `pacman -Q python-textual` — no longer listed; remove with
      `sudo pacman -Rns python-textual` if nothing else needs it.

## Ollama model for Surface Pro 9

RX 6700 XT (desktop) uses `qwen3.5` (VRAM-capped in its Modelfile). Surface has no discrete GPU — need to pick
a CPU/iGPU-friendly model (small enough to run on Iris Xe + RAM offload).
Options to evaluate: `qwen3:4b`, `llama3.2:3b`, `gemma3:4b`.
Add `setup_ollama` surface branch once decided.

No Flatpak: `alacritty` (terminal sandboxing issues), `shelly`.
