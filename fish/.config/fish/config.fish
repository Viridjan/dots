source /usr/share/cachyos-fish-config/cachyos-config.fish

# suppress fastfetch greeting
function fish_greeting
    # Pre-warm tide: first fish_prompt call spawns the async background job.
    # Running it here (discarding output) lets the job complete while fastfetch
    # displays, so $prompt_var is already populated when the real prompt renders.
    fish_prompt > /dev/null 2>&1
    fastfetch --logo none
end
