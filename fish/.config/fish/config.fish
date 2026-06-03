source /usr/share/cachyos-fish-config/cachyos-config.fish

# suppress fastfetch greeting
function fish_greeting
    fastfetch --logo none
end

# tide renders async — fish_mode_prompt runs before every prompt render,
# resetting the cursor to blinking block before tide's async repaint fires.
function fish_mode_prompt
    printf '\e[1 q'
end
