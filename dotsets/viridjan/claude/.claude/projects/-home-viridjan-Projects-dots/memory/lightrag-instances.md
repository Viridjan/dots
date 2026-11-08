---
name: lightrag-instances
description: LightRAG = one server per doc set (lightrag@summit :9621, lightrag@dots :9622), capped qwen3.5, EMBEDDING_TIMEOUT=600
metadata:
  type: project
---
2026-11-08: LightRAG 1.5.7 can't switch workspace per request, so template unit `lightrag@.service` (WorkingDirectory `~/.local/share/lightrag/%i`). summit :9621 (videogame docs, `~/Projects/videogame/tools/lightrag_update.py`), dots :9622 (`rag/lightrag_update.py`, 42 docs). Both use capped `qwen3.5`; uncapped `qwen3.5-full` dropped (user still has to `ollama rm` it, TODO.md).

**Why:** with the capped model Ollama queues embedding calls behind slow LLM calls; default 60 s worker timeout failed 39/42 docs.
**How to apply:** `.env` needs `EMBEDDING_TIMEOUT=600`; failed docs → `POST /documents/reprocess_failed`. Related: [[ollama-limits]].
