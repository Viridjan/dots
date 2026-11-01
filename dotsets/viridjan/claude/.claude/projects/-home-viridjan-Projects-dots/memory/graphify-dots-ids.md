---
name: graphify-dots-ids
description: graphify on dots — AST node IDs drop dots without doubling underscores (claude_claude_...), subagent chunks guess claude__claude_; remap before merge
metadata:
  type: reference
---

graphify AST IDs for paths under `.claude/` are `dotsets_viridjan_claude_claude_skills_...` (single underscore). Semantic subagents following the spec produce `claude__claude_` → dangling edges. Check chunk external refs against AST ids and remap before merging.
`.graphifyignore` excludes pixel-art-studio `docs/` + `pixel-art/` (80 sprite images = 80 LLM calls), VSCodium History/CachedConfigurations, `scripts/.local/share/icons/`. Run `/graphify` as incremental update (graph.json tracked).
