# TODO

## Migrate pacman packages to Flatpak

| Package (pacman) | Flatpak ID | List |
|---|---|---|
| `firefox` | `org.mozilla.firefox` | common |
| `thunderbird` | `org.mozilla.thunderbird` | common |
| `vlc` + `vlc-plugins-all` | `org.videolan.VLC` | common |
| `qbittorrent` | `org.qbittorrent.qBittorrent` | common |
| `libreoffice-still` | `org.libreoffice.LibreOffice` | common |
| `zathura` + `zathura-pdf-poppler` + `poppler-glib` | `org.pwmt.zathura` | common |
| `meld` | `org.gnome.meld` | common |
| `pavucontrol` | `org.pulseaudio.pavucontrol` | common |
| `vscodium` | `com.vscodium.codium` | common |
| `telegram-desktop` | `org.telegram.desktop` | common |
| `spotify-launcher` | `com.spotify.Client` | common |
| `dolphin` | `org.kde.dolphin` | common |
| `bitwarden` | `com.bitwarden.desktop` | common |

For each: remove from `.paru-S-common.list`, add to `.flatpak-S.list`, check mimeapps/autostart/niri rules for references.

## Ollama model for Surface Pro 9

RX 6700 XT (desktop) uses `qwen3:14b`. Surface has no discrete GPU — need to pick
a CPU/iGPU-friendly model (small enough to run on Iris Xe + RAM offload).
Options to evaluate: `qwen3:4b`, `llama3.2:3b`, `gemma3:4b`.
Add `setup_ollama` surface branch once decided.

No Flatpak: `alacritty` (terminal sandboxing issues), `btop`, `shelly`, `proton-mail-bin`.


