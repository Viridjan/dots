source /usr/share/cachyos-fish-config/cachyos-config.fish

# suppress fastfetch greeting
function fish_greeting
    fastfetch --logo none
    printf '\e[1 q'  # reset to blinking block cursor (matches alacritty config)
end
