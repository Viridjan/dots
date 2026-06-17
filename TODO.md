# TODO

## Ollama model for Surface Pro 9

RX 6700 XT (desktop) uses `qwen3:14b`. Surface has no discrete GPU — need to pick
a CPU/iGPU-friendly model (small enough to run on Iris Xe + RAM offload).
Options to evaluate: `qwen3:4b`, `llama3.2:3b`, `gemma3:4b`.
Add `setup_ollama` surface branch once decided.

No Flatpak: `alacritty` (terminal sandboxing issues), `btop`, `shelly`, `proton-mail-bin`.

## caveman-code install

`@juliusbrussee/caveman-code` npm package — install globally and add symlink to scripts stow package:

```bash
npm install -g @juliusbrussee/caveman-code
# then add symlink to scripts/.local/bin/ pointing to the installed cli.js
```

Find install path with: `npm root -g`


