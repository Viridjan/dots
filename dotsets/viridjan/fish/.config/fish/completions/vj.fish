# vj: no args opens the TUI; `plan DIR` and `unused PLANDIR [DAYS]` are for vjupdate.
complete -c vj -f
complete -c vj -n __fish_use_subcommand -a plan -d 'Write the run plan vjupdate reads'
complete -c vj -n __fish_use_subcommand -a unused -d 'Report unlisted/unused apps'
complete -c vj -n '__fish_seen_subcommand_from plan unused' -F
