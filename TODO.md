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

No Flatpak: `alacritty` (terminal sandboxing issues), `btop`, `shelly`, `proton-mail-bin`.

## Desktop shortcuts + webapps

- Windows VM: done (http://localhost:8006) — pending script + .desktop file
- Open Notebook: find URL once cloned, then create script + .desktop file (same pattern as Windows)

