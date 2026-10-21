source /usr/share/cachyos-fish-config/cachyos-config.fish

# CachyOS's fish_greeting runs plain `fastfetch`, which shows the CachyOS
# logo. Override the logo to Arch while keeping every other CachyOS default
# (info modules, layout, etc.) — a fastfetch config.jsonc file is NOT safe
# here: once ANY config.jsonc exists, an absent "modules" key means an EMPTY
# module list, not "use built-in defaults" (silently dropped all info lines
# on 2026-08-25). A CLI flag has no such trap.
function fish_greeting
    fastfetch --logo arch
end
