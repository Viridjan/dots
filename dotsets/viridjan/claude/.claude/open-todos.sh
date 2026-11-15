#!/usr/bin/env bash
# SessionStart/CwdChanged hook: show the open "- [ ]" items of the project's TODO.md.
# In ~/Projects itself: one count line per project with open items.
# Prints once per project per session (CwdChanged inside the same repo stays quiet).
set -u
in=$(cat)
event=$(jq -r '.hook_event_name // "SessionStart"' <<<"$in")
sid=$(jq -r '.session_id // "x"' <<<"$in")
dir=$(jq -r '.new_cwd // .cwd // empty' <<<"$in")
dir=${dir:-$PWD}
projects="$HOME/Projects"

root=$(git -C "$dir" rev-parse --show-toplevel 2>/dev/null) || root=$dir

state="${XDG_RUNTIME_DIR:-/tmp}/claude-open-todos-$sid"
[ "$(cat "$state" 2>/dev/null)" = "$root" ] && exit 0
printf '%s' "$root" >"$state"

open_items() { grep -E '^[[:space:]]*[-*] \[ \]' "$1" 2>/dev/null | sed -E 's/^[[:space:]]*[-*] \[ \] //' | cut -c1-140; }

msg=
if [ "$root" = "$projects" ]; then
  for f in "$projects"/*/TODO.md; do
    n=$(open_items "$f" | wc -l)
    [ "$n" -gt 0 ] && msg+="  $(basename "$(dirname "$f")"): $n open"$'\n'
  done
  [ -n "$msg" ] && msg="Open TODOs in ~/Projects:"$'\n'"$msg"
elif [ -f "$root/TODO.md" ]; then
  items=$(open_items "$root/TODO.md")
  [ -n "$items" ] && msg="Open TODOs in $(basename "$root") ($(wc -l <<<"$items")):"$'\n'"$(sed 's/^/  - /' <<<"$items")"
fi
[ -z "$msg" ] && exit 0

jq -n --arg m "$msg" --arg e "$event" '{systemMessage: $m,
  hookSpecificOutput: {hookEventName: $e,
    additionalContext: ("Tell the user these open TODO items at the start of your first reply:\n" + $m)}}'
