# sysup completions. Flags mirror `sysup --help`; --actions IDs are read
# from the script's MENU_ORDER at completion time, so they never go stale.
function __sysup_action_ids
    set -l script (command -s sysup); or return
    string replace -rf '^\s*MENU_ORDER=\((.*)\)\s*$' '$1' <(realpath $script) | string split ' '
end
# Comma-separated list: keep what is typed up to the last comma, offer the rest.
function __sysup_actions_arg
    set -l tok (commandline -ct | string replace -r '^--actions=' '')
    set -l done (string match -r '^.*,' -- $tok)
    for id in (__sysup_action_ids)
        printf '%s%s\n' "$done" $id
    end
end

complete -c sysup -f
complete -c sysup -s y -l yes -d 'Full bootstrap, no prompts'
complete -c sysup -l actions -x -a '(__sysup_actions_arg)' -d 'Run these action IDs'
complete -c sysup -s u -l update -d 'Update packages + clean caches'
complete -c sysup -s c -l check -d 'Audit only'
complete -c sysup -l profile -x -a '(path basename -E .toml ~/Projects/dots/profiles/*.toml)' -d 'Set this machine profile'
complete -c sysup -l dotset -x -a '(path basename ~/Projects/dots/dotsets/*) none' -d 'Dotfile set (with --profile)'
complete -c sysup -l pkg -x -a 'shared profile local remove ignore' -d 'Put packages in a list'
complete -c sysup -l status -d 'Profile, one-time actions, backups'
complete -c sysup -l skip-once -x -a '(__sysup_action_ids)' -d 'Mark one-time action skipped'
complete -c sysup -l restore -x -a '1 2' -d 'Restore dotset from backup'
complete -c sysup -l adopt -d 'Adopt conflicting files (backed up)'
complete -c sysup -l clean -d 'Also wipe paru/yay caches'
complete -c sysup -s h -l help -d 'Show help'
complete -c sysup -s a -l help-actions -d 'List action IDs'
