# TODO

## Ollama model for Surface Pro 9

RX 6700 XT (desktop) uses `qwen3:14b`. Surface has no discrete GPU — need to pick
a CPU/iGPU-friendly model (small enough to run on Iris Xe + RAM offload).
Options to evaluate: `qwen3:4b`, `llama3.2:3b`, `gemma3:4b`.
Add `setup_ollama` surface branch once decided.

No Flatpak: `alacritty` (terminal sandboxing issues), `btop`, `shelly`, `proton-mail-bin`.


