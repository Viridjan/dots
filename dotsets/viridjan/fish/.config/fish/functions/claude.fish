# Launch Claude Code directly. The retry launcher's POSIX tmux command fails
# when tmux uses fish as its default shell, closing the session at startup.
function claude --wraps claude --description "Claude Code"
    command claude $argv
end
