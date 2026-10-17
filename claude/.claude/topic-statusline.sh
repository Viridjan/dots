#!/bin/bash
# Prints the session topic and working directory as statusline tags, e.g.
# [TOPIC: Vjupdate log] [DIR: ~/Projects/dots]
# Topic = the newest custom-title (/rename) or ai-title entry in the transcript.
INPUT=$(cat)
TRANSCRIPT=$(printf '%s' "$INPUT" | jq -r '.transcript_path // empty' 2>/dev/null)
DIR=$(printf '%s' "$INPUT" | jq -r '.workspace.current_dir // .cwd // empty' 2>/dev/null)

if [[ -f "$TRANSCRIPT" ]]; then
    # ponytail: tac + first match scans from the end; transcripts stay a few MB.
    TOPIC=$(tac "$TRANSCRIPT" | grep -m1 -E '"type":"(custom|ai)-title"' \
        | jq -r '.customTitle // .aiTitle // empty' 2>/dev/null)
    [[ -n "$TOPIC" ]] && printf ' \033[38;5;180m[TOPIC: %s]\033[0m' "$TOPIC"
fi
[[ -n "$DIR" ]] && printf ' \033[38;5;146m[DIR: %s]\033[0m' "${DIR/#$HOME/\~}"
exit 0
