#!/usr/bin/env bash
# Statusline aggregator: feeds the same stdin JSON to every segment script and
# concatenates their output.
#
# Why this exists: the plugin cache dirs carry version hashes
# (caveman/25d22f864ad6, ponytail/4.7.0), so any settings.json that hardcodes
# those paths goes stale on the next plugin update. Globbing them here means
# settings.json stays a static committed file and vjupdate needs no statusline
# generation code at all. Adding a segment = one line below.
#
# Each script gets its own copy of stdin — piping them in sequence would let the
# first one consume the input and starve the rest.

INPUT=$(cat)

# Newest match wins, so a lingering old plugin version is ignored.
_newest() {
    local best="" f
    for f in "$@"; do
        [[ -f "$f" ]] || continue
        [[ -z "$best" || "$f" -nt "$best" ]] && best="$f"
    done
    printf '%s' "$best"
}

for _seg in \
    "$(_newest "$HOME"/.claude/plugins/cache/caveman/*/*/src/hooks/caveman-statusline.sh)" \
    "$(_newest "$HOME"/.claude/plugins/cache/ponytail/*/*/hooks/ponytail-statusline.sh)" \
    "$HOME/.claude/model-statusline.sh"
do
    [[ -n "$_seg" && -f "$_seg" ]] || continue
    printf '%s' "$INPUT" | bash "$_seg"
done
