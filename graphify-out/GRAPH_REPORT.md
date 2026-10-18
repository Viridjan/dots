# Graph Report - dots  (2026-10-18)

## Corpus Check
- 40 files · ~34,882 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 362 nodes · 850 edges · 40 communities (24 shown, 16 thin omitted)
- Extraction: 98% EXTRACTED · 2% INFERRED · 0% AMBIGUOUS · INFERRED: 13 edges (avg confidence: 0.76)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `d5908d9e`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- vjupdate Regression Tests
- Caveman Hook Scripts
- vjupdate Helpers & Gates
- System Config Actions
- Interactive Menu Engine
- Bootstrap & Malware Gate
- Package Install Pipeline
- Menu PTY Tests
- Bootstrap Phase Docs
- Stow Repo Policy
- Sync Skill & Windows VM
- Machine Profiles & Policies
- DMS Override Sync
- Statusline Tests
- VSCodium Python REPL
- Audit Checks
- Niri Output Merge Trap
- Surface Sync Script
- Menu Model Tests
- Menu, Lint & Git Hooks
- Package List Files
- Dotfile Deployment
- Claude Keybindings
- Statusline Aggregator
- Upgrade Failure Recap
- Caveman Statusline
- Hooks package.json
- Model Statusline
- Topic Statusline
- Statusline Docs
- Pre-commit Hook
- Keep Launcher
- Open Notebook Launcher
- Windows VM Launcher
- graphify reference: add a URL and watch a folder
- graphify reference: commit hook and native CLAUDE.md integration
- graphify reference: incremental update and cluster-only
- _install_list

## God Nodes (most connected - your core abstractions)
1. `FixtureCase` - 20 edges
2. `ReviewTests` - 18 edges
3. `MenuTerminalTests` - 15 edges
4. `vjupdate bootstrap/maintenance script` - 15 edges
5. `UploadTests` - 14 edges
6. `FollowupReviewTests` - 12 edges
7. `HoldTests` - 11 edges
8. `SafetyChecks` - 9 edges
9. `BuildTimeEstimateTests` - 8 edges
10. `MenuModelTests` - 8 edges

## Surprising Connections (you probably didn't know these)
- `Commit and push to origin main step` --semantically_similar_to--> `Review and upload Git changes action`  [INFERRED] [semantically similar]
  claude/.claude/skills/sync/SKILL.md → README.md
- `Refresh CLAUDE.md via init skill` --references--> `dots repo (GNU Stow dotfiles for CachyOS + niri)`  [INFERRED]
  claude/.claude/skills/sync/SKILL.md → CLAUDE.md
- `Btrfs snapshots (snapper, snap-pac, btrfs-assistant)` --references--> `vjupdate bootstrap/maintenance script`  [EXTRACTED]
  README.md → CLAUDE.md
- `vjupdate --dry-run preview` --references--> `vjupdate bootstrap/maintenance script`  [EXTRACTED]
  README.md → CLAUDE.md
- `Fresh install procedure (hostname, SSH key, clone, vjupdate)` --references--> `vjupdate bootstrap/maintenance script`  [EXTRACTED]
  README.md → CLAUDE.md

## Import Cycles
- None detected.

## Hyperedges (group relationships)
- **VRR flicker / output block first-wins misdiagnosis** — claude_kdl_merge_semantics, claude_display_kdl, claude_dms_outputs_kdl, claude_one_click_trap [EXTRACTED 1.00]
- **DMS override sync flow (regeneration, export/import, colors)** — claude_dms_regeneration, claude_dms_export_import, claude_dms_colors_kdl, claude_dms_binds_kdl, claude_dms_settings_json [EXTRACTED 1.00]
- **/sync end-of-session pipeline** — claude__claude_skills_sync_skill_refresh_claude_md, claude__claude_skills_sync_skill_update_readme, claude__claude_skills_sync_skill_save_memories, claude__claude_skills_sync_skill_commit_push [EXTRACTED 1.00]

## Communities (40 total, 16 thin omitted)

### Community 2 - "vjupdate Helpers & Gates"
Cohesion: 0.10
Nodes (22): AUDIT_ACTIONS, _fix_untrusted_keys(), _held_packages(), _init_pkg_index(), _INSTALLED_PKGS, _mark_done(), _needs_run(), optimize_system() (+14 more)

### Community 3 - "System Config Actions"
Cohesion: 0.22
Nodes (30): automount_disks(), check_app_launchers(), check_foreign_orphans(), clone_projects(), _confirm(), dms_export(), dms_import(), _enable() (+22 more)

### Community 4 - "Interactive Menu Engine"
Cohesion: 0.11
Nodes (19): _bootstrap_multiselect(), _cleanup(), _menu_add(), _menu_catalog(), _menu_choice_line(), _menu_clear(), _menu_defaults(), _menu_draw() (+11 more)

### Community 5 - "Bootstrap & Malware Gate"
Cohesion: 0.23
Nodes (17): vjupdate script, bootstrap(), check_aur_malware(), _check_packages_against_malware(), detect_machine(), die(), _die_infected(), _enable_audit_action() (+9 more)

### Community 6 - "Package Install Pipeline"
Cohesion: 0.20
Nodes (14): check_pacman_db(), clean_caches(), _do_install(), _estimate_aur_builds(), flatpak_update(), install_all(), _install_list(), phase_install() (+6 more)

### Community 8 - "Bootstrap Phase Docs"
Cohesion: 0.18
Nodes (12): vjupdate bootstrap phases (sources/install/dotfiles/configure/audit), Cache cleanup keeps AUR sources (--clean-aggressive opt-in), claude package requires stow --adopt, manage_kernels running-kernel protection via pacman -Qoq, Phase stamps in ~/.local/state/dots, projects.list (auto-cloned repos), vjupdate flock single-instance lock, Stow conflicts not adopted by default; --adopt backs up first (+4 more)

### Community 9 - "Stow Repo Policy"
Cohesion: 0.22
Nodes (9): .gitignore policy (secrets + continuously regenerated; churn rate not size), git filter-repo history purge procedure, scripts package stowed --no-folding (~/.local/bin unfolded), npm global prefix ~/.local, surface-sync.sh temporary one-shot catch-up, vjupdate --app-launchers cleanup, MTG Arena Tool AppImage, vjupdate --steam-launchers (+1 more)

### Community 10 - "Sync Skill & Windows VM"
Cohesion: 0.40
Nodes (6): Update README.md step, Windows 11 VM (dockur/windows, start-windows), Manual post-install steps (dms setup, fprintd, ykman, Bitwarden), Ports 8006 noVNC + 3389 RDP, ~/Shared:/shared volume + ./storage, windows service (dockurr/windows, Win11, 16G RAM, 8 cores, 128G disk)

### Community 11 - "Machine Profiles & Policies"
Cohesion: 0.20
Nodes (10): Brave managed policy LoopbackNetworkAllowedForUrls (Discord to Vesktop arRPC), Resolved 2026-08-24 cfg/ drift cleanup, Launch Claude Code from ~/Projects (memory scope), Machine-specific niri cfg files (display/input/autostart-machine/surface-layout), Machine profiles desktop/surface (hostname-detected, mutually exclusive), ollama ROCm systemd drop-in, Root-target stow packages (ollama, brave; stow -t /), _stow_niri_cfg machine-pkg symlink loop (+2 more)

### Community 12 - "DMS Override Sync"
Cohesion: 0.33
Nodes (7): DankMaterialShell (DMS), dms/binds.kdl (sole live keybind source), vjupdate --dms-export / --dms-import (DMS_MANUAL vs DMS_AUTO), dms ipc call (call subcommand required), DMS regeneration table (layout/alttab/wpblur every start), DankMaterialShell/settings.json, Duplicate keybind silent reload failure

### Community 14 - "VSCodium Python REPL"
Cohesion: 0.25
Nodes (3): get_last_command(), PS1, REPLHooks

### Community 15 - "Audit Checks"
Cohesion: 0.39
Nodes (8): check(), check_firmware(), check_flatpak_orphans(), check_held_updates(), check_pacnew(), check_python_rebuilds(), check_rebuilds(), phase_audit()

### Community 16 - "Niri Output Merge Trap"
Cohesion: 0.32
Nodes (8): cfg/display.kdl (sole output source, VRR off), dms/colors.kdl (repo copy authoritative, DMS_AUTO), dms/outputs.kdl (deliberately not included), niri include merge semantics (keyed FIRST wins, singleton LATER wins), niri config.kdl include tree, DMS Display 'First Time Setup' one-click trap, Gamescope launch options (desktop 3440x1440@165, Surface 2880x1920@60), System optimisations (vjupdate --optimize)

### Community 17 - "Surface Sync Script"
Cohesion: 0.52
Nodes (6): ask(), die(), ok(), surface-sync.sh script, step(), warn()

### Community 19 - "Menu, Lint & Git Hooks"
Cohesion: 0.29
Nodes (7): Commit and push to origin main step, AUDIT_ACTIONS table / _enable_audit_action, vjupdate interactive menu (collapsible groups, search, review), .githooks/pre-commit shellcheck guard, Shell lint gotchas (# shellcheck directive, set -e var=$(cmd), warn() recap), AUR build-time estimate (aur-build-times.tsv), Review and upload Git changes action

### Community 20 - "Package List Files"
Cohesion: 0.50
Nodes (5): Package install priority pacman > flatpak > paru, Flat package list files (.paru-S-*, .paru-R, .paru-skip, .paru-hold, .flatpak-S, ...), .paru-hold.list held packages, No-Flatpak exceptions (alacritty, btop, shelly, proton-mail), Switch vectorcraft to Flathub

### Community 21 - "Dotfile Deployment"
Cohesion: 0.17
Nodes (6): FixtureCase, A failed paru -Syuu must name the cause in the end-of-run recap., The mirrors-step database sync must recover from an untrusted repo key., ReviewFollowupTests, SyyRecoveryTests, UpgradeFailureReportingTests

### Community 22 - "Claude Keybindings"
Cohesion: 0.50
Nodes (3): bindings, $docs, $schema

### Community 24 - "Upgrade Failure Recap"
Cohesion: 0.67
Nodes (3): print_recap exit status recap, _REPO_KEYS third-party repo key map, _syuu / _syuu_fail_detail (SYUU_FAIL_DETAIL)

### Community 25 - "Caveman Statusline"
Cohesion: 0.18
Nodes (3): Menu model and real terminal interaction, with all system work disabled., Isolated regressions. VJUPDATE_SCRIPT can point at a pre-fix snapshot., SafetyChecks

### Community 38 - "graphify reference: incremental update and cluster-only"
Cohesion: 0.47
Nodes (6): _adopt_backup(), deploy_dotfiles(), _deploy_pkg(), _mutate(), phase_dotfiles(), _stow_niri_cfg()

### Community 39 - "_install_list"
Cohesion: 0.40
Nodes (5): Refresh CLAUDE.md via init skill, Save session memories step, /sync end-of-session skill, dots repo (GNU Stow dotfiles for CachyOS + niri), GNU Stow symlink deployment (-t ~)

## Knowledge Gaps
- **26 isolated node(s):** `$schema`, `$docs`, `bindings`, `model-statusline.sh script`, `statusline.sh script` (+21 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **16 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `FixtureCase` connect `Dotfile Deployment` to `vjupdate Regression Tests`, `Caveman Hook Scripts`, `graphify reference: add a URL and watch a folder`, `graphify reference: commit hook and native CLAUDE.md integration`, `Menu PTY Tests`, `Menu Model Tests`, `Caveman Statusline`, `Hooks package.json`?**
  _High betweenness centrality (0.042) - this node is a cross-community bridge._
- **Why does `vjupdate bootstrap/maintenance script` connect `Bootstrap Phase Docs` to `_install_list`, `Machine Profiles & Policies`, `DMS Override Sync`, `Menu, Lint & Git Hooks`, `Package List Files`?**
  _High betweenness centrality (0.023) - this node is a cross-community bridge._
- **Why does `MenuTerminalTests` connect `Menu PTY Tests` to `Caveman Statusline`, `Dotfile Deployment`?**
  _High betweenness centrality (0.021) - this node is a cross-community bridge._
- **What connects `$schema`, `$docs`, `bindings` to the rest of the system?**
  _26 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `vjupdate Helpers & Gates` be split into smaller, more focused modules?**
  _Cohesion score 0.09885057471264368 - nodes in this community are weakly interconnected._
- **Should `Interactive Menu Engine` be split into smaller, more focused modules?**
  _Cohesion score 0.1111111111111111 - nodes in this community are weakly interconnected._