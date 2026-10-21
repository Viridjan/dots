#!/bin/bash
# Prints the current Claude Code model as a statusline tag, e.g. [MODEL: Sonnet 5]
INPUT=$(cat)
NAME=$(printf '%s' "$INPUT" | jq -r '.model.display_name // empty' 2>/dev/null)
[ -z "$NAME" ] && exit 0
printf ' \033[38;5;110m[MODEL: %s]\033[0m' "$NAME"
