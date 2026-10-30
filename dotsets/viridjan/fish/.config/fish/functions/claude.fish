# claude-auto-retry: runs claude inside tmux with a monitor that waits out
# usage limits / API overload and continues. Its installer skips fish, so this
# is the function it prints. Falls back to plain claude if the npm package is gone.
function claude --wraps claude --description "Claude Code via claude-auto-retry"
    set -l launcher ~/.local/lib/node_modules/claude-auto-retry/src/launcher.js
    if not test -f $launcher; or not command -q tmux
        command claude $argv
        return
    end
    set -lx CLAUDE_AUTO_RETRY_ACTIVE 1
    node $launcher $argv
end
