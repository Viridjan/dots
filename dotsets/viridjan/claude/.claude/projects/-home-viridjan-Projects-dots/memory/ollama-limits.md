---
name: ollama-limits
description: Desktop ollama runs qwen3.5 only (DeepSeek removed 2026-10-30); ~40% cap; ollama 0.40 ignores GPU_OVERHEAD/MAX_LOADED_MODELS; user rejects OOM-kill caps
metadata:
  type: feedback
---

Ollama on the desktop runs only `qwen3.5`. DeepSeek (`deepseek-r1:7b`, `deepseek-cave`, the `@deepseek-ai/dsh` harness + `~/.dsh`) was set up and then removed on 2026-10-30 at user request — don't re-add it.

Limits: `limits.conf` drop-in (CPUQuota=640%, MemoryHigh=40%, OLLAMA_KEEP_ALIVE=1m). qwen3.5 has a VRAM cap: `num_gpu 26` in `scripts/.local/share/ollama/qwen3.5.Modelfile` (30/70 CPU/GPU, ~19 tok/s vs 53 stock). Same day: user rolled back cap+caveman prompt as "really slow", then asked to reapply the caps only — so keep the cap, no SYSTEM prompt; if speed complaints return, ask which they want rather than flipping.

**Why:** user wanted ollama limited to 40% of CPU/GPU/RAM, and rejected `MemoryMax` because it kills the process when exceeded. ollama 0.40 silently ignored OLLAMA_GPU_OVERHEAD and OLLAMA_MAX_LOADED_MODELS: two models loaded, VRAM 11.7/12 GB, qwen warm-up hung.

**How to apply:** prefer soft limits (MemoryHigh, throttling) over hard kill limits. Per-model `num_gpu` works (check `ollama ps` CPU/GPU split); it trades speed for VRAM. GPU compute can't be capped. With OLLAMA_NUM_PARALLEL=1 a request queues behind an open chat and looks hung. Related: [[claude-auto-retry]].
