---
name: niri-gaming
description: niri fullscreen keybinds, game window-rule app-id gotcha, and the include-merge semantics that made display config silently inert
metadata:
  node_type: memory
  type: project
  originSessionId: 7c8969fe-be25-4259-b949-842f5d0e3b44
  modified: 2026-10-23T15:57:46.033Z
---

niri has no exclusive fullscreen — all fullscreen is compositor-controlled (windowed). For true exclusive + mode-set, use gamescope per-game (README documents resolutions).

**Keybinds (don't confuse):**
- `Mod+F` → `maximize-column` — fills width, KEEPS gaps/borders/bar, still tiled.
- `Mod+Shift+F` → `fullscreen-window` — whole screen, no gaps/borders/bar. What games want. Works on ANY window.

**Auto-fullscreen rule gotcha** (now inline in `config.kdl`, not `cfg/rules.kdl` — that file was deleted 2026-08-24):
- `match app-id="^steam_app_"` only matches XWayland games (WM_CLASS = steam_app_NNNN).
- Native Wayland games set their OWN app-id = game name (e.g. "Slay the Spire 2"), so the rule SKIPS them → they open tiled, not fullscreen, not on media workspace.
- Fix per game: find app-id via `niri msg windows`, add `match app-id="^<name>$"` (open-on-workspace media + open-fullscreen true).
- Rules apply on OPEN — a running game won't retro-fullscreen; relaunch or Mod+Shift+F.
- **`open-fullscreen true` alone is not enough** (added 2026-09-04): Unity games launched in *windowed* mode set min size == max size, and niri floats any window with that hint — a floating window ignores the fullscreen rule. The `^steam_app_` rule now also carries `open-floating false` to force it tiled first.

**Gamescope-wrapped games can't be matched by ANY rule** (2026-10-22, MTGA): gamescope opens a throwaway window (app-id `gamescope`), closes it, then opens the real one with app-id None and title set only after map. Title rules miss too. Fix = `gamescope-media %command%` launch option (scripts/, pushed 63934ca): sizes gamescope from focused output, moves its windows by PID to `media` with `--focus false`. Diagnose placement with `niri msg event-stream` captured across a relaunch, not `niri msg windows` (shows final title only).
- MTGA without gamescope doesn't stay fullscreen even after setting its Unity prefs (`Screenmanager Fullscreen mode`=1, width 3440 in pfx `user.reg`; backup `user.reg.bak-20261022163409`) — user chose gamescope then, but reversed it 2026-10-30: gamescope removed, launch options now `niri msg action focus-workspace media; %command%` (in Steam `userdata/159835476/config/localconfig.vdf`; backup `.bak-mtga`). If fullscreen breaks again, that's the known cause. Edit localconfig.vdf only with Steam fully exited — it rewrites the file on exit.
- User wants games to open on media WITHOUT stealing focus.

## Include-merge semantics — the trap that cost days (settled 2026-08-25)

**Merge behaviour differs by node kind. This is the single most important thing here.**

| Node kind | Example | Duplicate across includes | Duplicate in ONE file |
|---|---|---|---|
| Keyed | `output "DP-1"` | **FIRST wins**, silently | allowed |
| Singleton | `layout`, `input` | fields merge, **LATER wins** on conflict | **hard parse error** |

Both proven empirically, not read from docs: injected `output "DP-1" { position x=0 y=777 }` *before* the `cfg/display.kdl` include (y=0) → `niri msg outputs` showed `0, 777`. And a temp include with `layout { gaps 40 }` *after* `dms/layout.kdl` (gaps 4) → tile height 1432→1360.

**Consequence:** `dms/outputs.kdl` was included before `cfg/display.kdl`, so **every display edit was inert for days**. Three separate "fixes" appeared to work but were actually my transient `niri msg output` CLI overrides. Fixed by deleting `dms/outputs.kdl` and its include; `cfg/display.kdl` is now the sole output source. Verified across a real reboot 2026-08-25: 165Hz, VRR disabled, flicker gone.

**Root cause of the flicker was VRR, never the refresh rate.** 165Hz is the monitor's genuine native mode. Chasing 144Hz was a detour.

## Debugging traps that hid all of the above

- `niri msg action load-config-file` does **not** force a modeset on a connected output. An *ignored* `mode` looks identical to an *unapplied* one. **Probe with `position`, not `mode`** — position applies live.
- `niri msg output ...` overrides are transient but **survive a config reload** (until the file's output config actually changes). Easy to mistake a stale CLI override for a working config.
- A KDL parse error aborts the reload silently, leaving the last-good config running — a broken test looks like "nothing changed". **Always check `niri validate -c ~/.config/niri/config.kdl` exit code explicitly.**
- Duplicate keybinds anywhere in the tree cause the same silent reload failure.

## ⚠ DMS's one-click regression button

With the include removed, `dms config resolve-include niri outputs.kdl` reports `included:false`, so DMS **Settings → Display** shows a *"First Time Setup"* box with a **Setup** button. It calls `fixOutputsInclude()`, which re-adds `include "dms/outputs.kdl"` and regenerates a real output block → first-wins makes `cfg/display.kdl` inert again, restoring the flicker **in one click**. Never press it. Only ever fires from that button, never automatically.

## What DMS actually regenerates (measured via dms.service restart)

- **Every start:** `layout.kdl`, `alttab.kdl`, `wpblur.kdl` (journal logs "Generated … config at …"), plus `outputs.kdl` as a **0-byte stub** (harmless — the old VRR block does not return).
- **On settings change only:** `colors.kdl`, `outputs.kdl` content.
- **Never:** `binds.kdl`, `cursor.kdl`, `windowrules.kdl` — genuinely hand-editable.

Regeneration is deterministic from `DankMaterialShell/settings.json` (files returned byte-identical after restart). The old blanket claim that DMS rewrites everything "within seconds of every session start" was wrong in both directions.

See [[project-state]], [[dms-export-clobbers-overrides]], [[feedback-verification-rigor]].

**No auto-maximize (2026-10-31):** user asked to stop the first window on a workspace opening maximized → oniri dropped (config spawn removed, in `[paru].remove`). Don't re-add oniri or a lone-window-maximize rule.
