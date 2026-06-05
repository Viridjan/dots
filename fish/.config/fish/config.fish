source /usr/share/cachyos-fish-config/cachyos-config.fish

# ROCm: RX 6700 XT (Navi 22/gfx1031) not in official support list — override needed
set -x HSA_OVERRIDE_GFX_VERSION 10.3.0

# suppress fastfetch greeting
function fish_greeting
    # Pre-warm tide: first fish_prompt call spawns the async background job.
    # Running it here (discarding output) lets the job complete while fastfetch
    # displays, so $prompt_var is already populated when the real prompt renders.
    fish_prompt > /dev/null 2>&1
    fastfetch --logo none
end
