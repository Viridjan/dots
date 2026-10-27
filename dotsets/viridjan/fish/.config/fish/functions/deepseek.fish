# ponytail: no terminal UI ships yet (profiles: web acp headless sdk) — switch to `dsh tui` if one lands
function deepseek --wraps dsh --description "DeepSeek Harness (web UI on 127.0.0.1:3080)"
    dsh web $argv
end
