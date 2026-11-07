# RAG tools for agent coding (Claude Code + Codex)

Status: planned 2026-11-07, not integrated. Chosen for the Summit game project (`~/Projects/videogame`) but
useful for any repo. Everything runs locally through Ollama: no cloud API keys.

| Tool | What it does | Package | Runs as |
|---|---|---|---|
| graphify | Knowledge graph of code + docs (GraphRAG), `/graphify` skill | `graphifyy` (`[uv]`, already listed) | CLI + skill |
| Claude Context | Code search by meaning (hybrid keyword + vector) | `@zilliz/claude-context-mcp` (npm) | MCP server (stdio) |
| Milvus | Vector database Claude Context stores its index in | `milvusdb/milvus:v3.0.5` (Docker) | container, 127.0.0.1:19530 |
| Godot MCP | Agent runs the Godot project, reads errors, inspects scenes | `@coding-solo/godot-mcp` (npm) | MCP server (stdio) |
| LightRAG | Graph + vector RAG over design docs, incremental updates | `lightrag-hku[api]` (uv) | HTTP server, 127.0.0.1:9621 |
| nomic-embed-text | Embedding model shared by Claude Context and LightRAG (768 dim) | Ollama model | ollama |

## How to add them to dots (follow the existing patterns)

1. **Feature flag.** New feature `rag-stack` in `profiles/desktop.toml` `features` (the desktop has the RX 6700 XT
   and `ollama-model`); every step below is skipped without it, like `windows-vm` / `ollama-model`.
2. **`packages.toml`:**
   - `[npm].install`: `"@zilliz/claude-context-mcp"`, `"@coding-solo/godot-mcp"` (comment: MCP servers,
     registered by the setup step below). Check their binary names with `npm view <pkg> bin` and register the
     installed binaries (`~/.local/bin/...`) instead of `npx -y` (no download on every start).
   - `[uv].install`: `"lightrag-hku[api]"`.
3. **Ollama model.** In `setup_ollama` (`scripts/.local/bin/vjupdate`) add `nomic-embed-text` to `models`
   (only with the `rag-stack` feature).
4. **Milvus.** New non-stow folder `rag/` beside `windows/`: `rag/docker-compose.yml` with the official standalone
   settings (`ETCD_USE_EMBED=true`, `ETCD_DATA_DIR=/var/lib/milvus/etcd`,
   `ETCD_CONFIG_PATH=/milvus/configs/embedEtcd.yaml`, `COMMON_STORAGETYPE=local`, `DEPLOY_MODE=STANDALONE`,
   `security_opt: seccomp:unconfined`, command `milvus run standalone`), ports bound to `127.0.0.1` only
   (19530, 9091), `restart: unless-stopped`, volume under `/mnt/data/` like the Windows VM storage, plus
   `embedEtcd.yaml` / `user.yaml` (from upstream `scripts/standalone_embed.sh`). First start needs the volume
   chowned to the image's `milvus` user (upstream does it with a one-shot root container). A `setup_rag` action
   runs `docker compose up -d` (Docker is already enabled in `[systemd].enable`).
5. **LightRAG service.** User unit `lightrag.service` in the `systemd-user` dotset: `ExecStart=lightrag-server`,
   `WorkingDirectory=%h/.local/share/lightrag/summit` (its `.env` holds the settings below); add `"lightrag"` to the
   desktop profile's `[systemd].user`. Example `.env` (already on the desktop at
   `~/.local/share/lightrag/summit/.env`):
   ```
   HOST=127.0.0.1
   PORT=9621
   WORKING_DIR=/home/viridjan/.local/share/lightrag/summit/rag_storage
   INPUT_DIR=/home/viridjan/.local/share/lightrag/summit/inputs
   LLM_BINDING=ollama
   LLM_BINDING_HOST=http://127.0.0.1:11434
   LLM_MODEL=qwen3.5:latest
   OLLAMA_LLM_NUM_CTX=32768
   MAX_ASYNC_LLM=2
   EMBEDDING_BINDING=ollama
   EMBEDDING_BINDING_HOST=http://127.0.0.1:11434
   EMBEDDING_MODEL=nomic-embed-text
   EMBEDDING_DIM=768
   OLLAMA_EMBEDDING_NUM_CTX=8192
   ```
   Keep `HOST=127.0.0.1` (the server binds every interface otherwise and has no auth by default).
6. **MCP registration** (untracked `~/.claude.json` / `~/.codex/config.toml`, like `_setup_rea`): a
   `_setup_rag_mcp` called from `setup_claude` after `_setup_rea`, idempotent with `claude mcp get <name>`:
   ```
   claude mcp add -s user godot -e GODOT_PATH=/usr/bin/godot -- <godot-mcp binary>
   claude mcp add -s user claude-context -e EMBEDDING_PROVIDER=Ollama -e EMBEDDING_MODEL=nomic-embed-text \
     -e MILVUS_ADDRESS=127.0.0.1:19530 -e CUSTOM_EXTENSIONS=.gd,.tscn -- <claude-context-mcp binary>
   ```
   and the same two servers for Codex when installed (`codex mcp add …`, or `[mcp_servers.<name>]` blocks in
   `~/.codex/config.toml` with `env = { ... }` and `startup_timeout_ms = 20000` for claude-context).
7. **Docs.** README "Manual steps": first index per repo (Claude Context: ask the agent to `index_codebase` the repo;
   LightRAG: upload docs at `http://127.0.0.1:9621` or drop files in `inputs/` and scan). CLAUDE.md package table:
   the new `[npm]`/`[uv]` entries and the `rag-stack` feature.

## Checks
- `claude mcp list` shows `godot` and `claude-context` connected; `codex mcp list` likewise.
- `docker ps` shows `milvus` healthy; `curl -s 127.0.0.1:9091/healthz` → `OK`.
- `systemctl --user is-active lightrag` → `active`; `curl -s 127.0.0.1:9621/health`.
- `ollama list` includes `nomic-embed-text`.
- Ports 19530 / 9091 / 9621 are not reachable from the LAN (`ss -tlnp` shows `127.0.0.1`).
