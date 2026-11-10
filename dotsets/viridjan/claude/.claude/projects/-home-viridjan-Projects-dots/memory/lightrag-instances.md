---
name: lightrag-instances
description: LightRAG = one server per doc set (lightrag@summit :9621, lightrag@dots :9622), indexed by `lightrag-index <project>`; capped qwen3.5, EMBEDDING_TIMEOUT=600
metadata:
  type: project
---
2026-11-08: LightRAG 1.5.7 can't switch workspace per request, so template unit `lightrag@.service` (WorkingDirectory `~/.local/share/lightrag/%i`). summit :9621 (Bethe Knight docs, `~/Projects/bethe-knight`, renamed from videogame 2026-11-08), dots :9622. Both use capped `qwen3.5`.

2026-11-10: one generic indexer `lightrag-index <project-dir>` (scripts/.local/bin; replaced rag/lightrag_update.py and the game's copy). Set + sources from the project's `.lightrag.json`; it starts/stops the unit itself. Unit sets `TIKTOKEN_CACHE_DIR=~/.cache/tiktoken` (default /tmp cache was wiped each boot → download before DNS → start-limit-hit).

**Why:** with the capped model Ollama queues embedding calls behind slow LLM calls; default 60 s worker timeout failed 39/42 docs.
**How to apply:** `.env` needs `EMBEDDING_TIMEOUT=600`; failed docs are retried by the next `lightrag-index` run. Related: [[ollama-limits]].
