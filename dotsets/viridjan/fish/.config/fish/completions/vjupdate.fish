# vjupdate completions. Flags mirror `vjupdate --help`; --actions IDs are read
# from the script's MENU_ORDER at completion time, so they never go stale.
function __vjupdate_action_ids
    set -l script (command -s vjupdate); or return
    string replace -rf '^\s*MENU_ORDER=\((.*)\)\s*$' '$1' <(realpath $script) | string split ' '
end
# Comma-separated list: keep what is typed up to the last comma, offer the rest.
function __vjupdate_actions_arg
    set -l tok (commandline -ct | string replace -r '^--actions=' '')
    set -l done (string match -r '^.*,' -- $tok)
    for id in (__vjupdate_action_ids)
        printf '%s%s\n' "$done" $id
    end
end

complete -c vjupdate -f
complete -c vjupdate -s i -l interactive -d 'Open vj (default)'
complete -c vjupdate -s y -l yes -d 'Full bootstrap, no prompts'
complete -c vjupdate -l actions -x -a '(__vjupdate_actions_arg)' -d 'Run these action IDs'
complete -c vjupdate -s u -l update -d 'Update packages + clean caches'
complete -c vjupdate -s c -l check -d 'Audit only'
complete -c vjupdate -l kernels -d 'Install/remove kernels'
complete -c vjupdate -l automount -d 'Add internal partitions to fstab'
complete -c vjupdate -l optimize -d 'Apply CachyOS tuning'
complete -c vjupdate -l keyring-pam -d 'gnome-keyring in greetd PAM'
complete -c vjupdate -l dms-export -d 'Live DMS overrides → repo'
complete -c vjupdate -l dms-import -d 'Repo DMS overrides → live'
complete -c vjupdate -l steam-launchers -d 'Steam game launchers'
complete -c vjupdate -l app-launchers -d 'Prune stale app launchers'
complete -c vjupdate -l pacnew -d 'Merge .pacnew files'
complete -c vjupdate -l rebuild -d 'Rebuild flagged packages'
complete -c vjupdate -l lostfiles -d 'List files no package owns'
complete -c vjupdate -s n -l dry-run -d 'Preview, change nothing'
complete -c vjupdate -l adopt -d 'Adopt conflicting files (backed up)'
complete -c vjupdate -l clean-aggressive -d 'Also wipe paru/yay caches'
complete -c vjupdate -s h -l help -d 'Show help'
