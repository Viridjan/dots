#!/bin/bash
# Prints the session topic and working directory as statusline tags.
# The latest nonempty manual title wins over any automatic title.
INPUT=$(cat)
TRANSCRIPT=$(printf '%s' "$INPUT" | jq -r '.transcript_path // empty' 2>/dev/null)
DIR=$(printf '%s' "$INPUT" | jq -r '.workspace.current_dir // .cwd // empty' 2>/dev/null)

if [[ -f "$TRANSCRIPT" ]]; then
    # Parse JSONL independently of whitespace, retaining only two title strings.
    # Ignore incomplete/malformed lines while a transcript is being appended.
    TOPIC=$(jq -nRr '
        reduce inputs as $line ({manual: null, auto: null};
            (try ($line | fromjson) catch null) as $entry |
            if ($entry | type) != "object" then .
            elif $entry.type == "custom-title" and
                ($entry.customTitle | type) == "string" and $entry.customTitle != ""
            then .manual = $entry.customTitle
            elif $entry.type == "ai-title" and
                ($entry.aiTitle | type) == "string" and $entry.aiTitle != ""
            then .auto = $entry.aiTitle
            else . end
        ) | .manual // .auto // empty
    ' "$TRANSCRIPT" 2>/dev/null)
    # Titles derive from conversation content: never pass escape sequences
    # (e.g. OSC 52 clipboard writes) through to the terminal.
    TOPIC=$(printf '%s' "$TOPIC" | tr -d '[:cntrl:]')
    [[ -n "$TOPIC" ]] && printf ' \033[38;5;180m[TOPIC: %s]\033[0m' "$TOPIC"
fi
DIR=$(printf '%s' "$DIR" | tr -d '[:cntrl:]')
case "$DIR" in
    "$HOME") DIR='~' ;;
    "$HOME"/*) DIR="~${DIR#"$HOME"}" ;;
esac
[[ -n "$DIR" ]] && printf ' \033[38;5;146m[DIR: %s]\033[0m' "$DIR"
exit 0
