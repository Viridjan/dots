---
name: ollama-limits
description: Desktop ollama runs qwen3.5 only (DeepSeek removed 2026-10-30); caps 8 threads / 60% RAM / 60% GPU compute / 5 GB VRAM; ollama 0.40 ignores GPU_OVERHEAD/MAX_LOADED_MODELS; user rejects OOM-kill caps
metadata:
  type: feedback
---

Ollama on the desktop runs only `qwen3.5`. DeepSeek (`deepseek-r1:7b`, `deepseek-cave`, the `@deepseek-ai/dsh` harness + `~/.dsh`) was set up and then removed on 2026-10-30 at user request — don't re-add it.

Limits (current): `limits.conf` drop-in (CPUQuota=800% = 8 threads, MemoryHigh=60%, HSA_CU_MASK=0:0-23 = 60% GPU compute (unverified), OLLAMA_KEEP_ALIVE=1m). qwen3.5 VRAM cap: `num_gpu 24` in `scripts/.local/share/ollama/qwen3.5.Modelfile` (≤5 GB, ~14 tok/s vs 55 stock). 2026-11-08: LightRAG (both sets) switched from an uncapped local `qwen3.5-full` (num_gpu 99) to the capped `qwen3.5` at user request — every model must respect the cap; check `ollama ps` for stray uncapped models. Same day: user rolled back cap+caveman prompt as "really slow", then asked to reapply the caps only — so keep the cap, no SYSTEM prompt; if speed complaints return, ask which they want rather than flipping.

**Why:** user wants ollama limited (first 40%, later the caps above), and rejected `MemoryMax` because it kills the process when exceeded. ollama 0.40 silently ignored OLLAMA_GPU_OVERHEAD and OLLAMA_MAX_LOADED_MODELS: two models loaded, VRAM 11.7/12 GB, qwen warm-up hung.

**How to apply:** prefer soft limits (MemoryHigh, throttling) over hard kill limits. Per-model `num_gpu` works (check `ollama ps` CPU/GPU split); it trades speed for VRAM. GPU compute is capped only via HSA_CU_MASK (unverified). With OLLAMA_NUM_PARALLEL=1 a request queues behind an open chat and looks hung. Related: [[claude-auto-retry]].

Surface: no Ollama at all (user decision 2026-11-10). Never propose a Surface model; desktop only.
