# Graph Report - .  (2026-10-27)

## Corpus Check
- 75 files · ~82,254 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 952 nodes · 2059 edges · 70 communities (46 shown, 24 thin omitted)
- Extraction: 96% EXTRACTED · 4% INFERRED · 0% AMBIGUOUS · INFERRED: 73 edges (avg confidence: 0.71)
- Token cost: 168,453 input · 0 output

## Community Hubs (Navigation)
- vj Config Loading
- Dots Docs & CI
- vjupdate Test Suites
- Audit Checks
- vjupdate Core Helpers
- vj State Model
- Adoption & Review Tests
- Pixel Drawing Primitives
- Sprite Export & Inspection
- vj TUI Screens
- Sprite Layers & Transforms
- vj Checklist Widget
- Bootstrap & Malware Gate
- Followup Fix Tests
- Palette Cleanup Pipeline
- Upgrade Recap Tests
- Pixel Grid Recovery
- Package Install Pipeline
- Pixel Art Failure Modes
- Anime Cast Example
- vj State Tests
- Hold & Priority Tests
- Dotfile Deployment
- Menu PTY Tests
- Knight Animation Example
- LPC Sheet Builder
- DMS & Configure Phase
- pixelstudio Core Helpers
- vj Launcher & Test Fixtures
- System Tuning & Mirrors
- vj App Shell
- Frame & Cel Operations
- Plan Resolution Tests
- Malware & Automount Tests
- Animation Studies
- Build Time Estimate Tests
- Once & Unlisted Checklists
- Pixel Art Studio Skill
- Palettes & Hybrid Pipeline
- Iron Man Sprite Example
- VSCodium Python REPL
- Topic Statusline Tests
- vj Config Tests
- Run Plan Tests
- Pixelstudio Tests
- Plan Command Tests
- Unlisted Package Tests
- vj Package Modules
- Character Proportions
- pixelpipe CLI
- Surface Sync Script
- vj UI Tests
- Dotset Tests
- Export & LPC Reference
- Capybara Example
- --actions Tests
- Knight Walkcycle Example
- Tactical Oracle Example
- Claude Keybindings
- Slime Example
- Statusline Aggregator
- Windows VM Compose
- Model Statusline
- Topic Statusline
- Pre-commit Hook
- gamescope-media Launcher
- Keep Launcher
- Open Notebook Launcher
- Windows VM Launcher

## God Nodes (most connected - your core abstractions)
1. `Sprite` - 76 edges
2. `FixtureCase` - 36 edges
3. `State` - 34 edges
4. `Checklist` - 24 edges
5. `pixel-art-studio SKILL.md` - 22 edges
6. `ReviewTests` - 18 edges
7. `hex2rgba()` - 16 edges
8. `StateTests` - 16 edges
9. `MenuTerminalTests` - 15 edges
10. `UploadTests` - 14 edges

## Surprising Connections (you probably didn't know these)
- `pre-commit hook (secret scan + shellcheck)` --semantically_similar_to--> `CI shellcheck -S error step`  [INFERRED] [semantically similar]
  CLAUDE.md → .github/workflows/test.yml
- `vj terminal UI section` --references--> `vj (Textual TUI)`  [INFERRED]
  README.md → CLAUDE.md
- `AUR build-time estimate section` --conceptually_related_to--> `build-times.tsv`  [AMBIGUOUS]
  README.md → CLAUDE.md
- `Mocked unittest suite (restricted PATH)` --references--> `CI unittest discover step`  [INFERRED]
  CLAUDE.md → .github/workflows/test.yml
- `surface-sync.sh manual-confirm checklist` --references--> `Dotfile sets (dotsets/<name>/)`  [INFERRED]
  TODO.md → CLAUDE.md

## Import Cycles
- None detected.

## Hyperedges (group relationships)
- **vj → run plan → vjupdate flow** — claude_packages_toml, claude_profiles, claude_local_config, claude_run_plan, claude_vj_tui, claude_vjupdate [EXTRACTED 1.00]
- **niri output config pitfalls** — claude_niri_merge_semantics, claude_dms_one_click_trap, claude_dms_export_import, claude_duplicate_keybind_trap [INFERRED 0.75]
- **vjupdate safety checks** — claude_aur_update_review, claude_staged_niri_validation, claude_protected_packages, claude_single_instance_lock, claude_stow_no_adopt_default [INFERRED 0.85]
- **Brief→build→look→fix→deliver creation loop** — dotsets_viridjan_claude__claude_skills_pixel_art_studio_skill_see_critique_fix_loop, dotsets_viridjan_claude__claude_skills_pixel_art_studio_skill_build_script, dotsets_viridjan_claude__claude_skills_pixel_art_studio_references_validations, dotsets_viridjan_claude__claude_skills_pixel_art_studio_references_sharp_edges, dotsets_viridjan_claude__claude_skills_pixel_art_studio_references_patterns [EXTRACTED 1.00]
- **Learned style study cards** — dotsets_viridjan_claude__claude_skills_pixel_art_studio_references_learned_index, dotsets_viridjan_claude__claude_skills_pixel_art_studio_references_learned_template, dotsets_viridjan_claude__claude_skills_pixel_art_studio_references_learned_001_chibi_jrpg_cast, dotsets_viridjan_claude__claude_skills_pixel_art_studio_references_learned_002_dynamic_attack_canvas, dotsets_viridjan_claude__claude_skills_pixel_art_studio_references_learned_003_dramatic_chibi_swordsman, dotsets_viridjan_claude__claude_skills_pixel_art_studio_references_learned_004_tactical_chibi_layered_cloth, dotsets_viridjan_claude__claude_skills_pixel_art_studio_references_learned_005_tall_tactical_job_sprites [EXTRACTED 1.00]
- **Hybrid cleanup pipeline steps** — dotsets_viridjan_claude__claude_skills_pixel_art_studio_skill_hybrid_pipeline, dotsets_viridjan_claude__claude_skills_pixel_art_studio_references_cleanup_grid_recovery, dotsets_viridjan_claude__claude_skills_pixel_art_studio_references_cleanup_harden_alpha, dotsets_viridjan_claude__claude_skills_pixel_art_studio_references_cleanup_palette_lock [EXTRACTED 1.00]

## Communities (70 total, 24 thin omitted)

### Community 0 - "vj Config Loading"
Cohesion: 0.06
Nodes (54): Exception, add_to_list(), config_path(), ConfigError, dumps(), host_profile(), load_local(), load_repo() (+46 more)

### Community 1 - "Dots Docs & CI"
Cohesion: 0.05
Nodes (55): test.yml CI workflow, CI shellcheck -S error step, CI unittest discover step, --actions menu IDs, AUR update review (_review_aur_updates), Bootstrap phases sources→install→dotfiles→configure→audit, build-times.tsv, DMS export/import (DMS_MANUAL vs DMS_AUTO) (+47 more)

### Community 2 - "vjupdate Test Suites"
Cohesion: 0.07
Nodes (18): Exercise checkout replacement in an isolated repository, without system setup., SurfaceSyncTests, AuditTests, AurReviewTests, ExtrasCase, LinkTests, NiriValidateTests, PackageRemovalTests (+10 more)

### Community 3 - "Audit Checks"
Cohesion: 0.17
Nodes (37): check(), check_dms_owner(), check_firmware(), check_flatpak_orphans(), check_foreign_orphans(), check_held_updates(), check_logins(), check_modified_configs() (+29 more)

### Community 4 - "vjupdate Core Helpers"
Cohesion: 0.09
Nodes (27): AUDIT_ACTIONS, _bootstrap_multiselect(), _cleanup(), _held_packages(), _init_pkg_index(), _INSTALLED_PKGS, _menu_add(), _menu_catalog() (+19 more)

### Community 5 - "vj State Model"
Cohesion: 0.13
Nodes (7): plural(), Path, Resolved lists as if nothing were declined, so declined stay visible to re-tick., [(src, name)] explicitly installed but in no list and not ignored., how: repo (packages.toml), profile (profiles/<p>.toml), machine (local add),, (id, label, default) for a non-package checklist., State

### Community 7 - "Pixel Drawing Primitives"
Cohesion: 0.13
Nodes (8): Bresenham line — one pixel per step, no doubles., Pixel-perfect midpoint circle (odd diameter 2r+1). Use this, not ellipse(),, PIL-backed ellipse — fine for blobs >= ~12px; for small circles use circle()., Flood fill from (x,y). Leaks through diagonal gaps only if truly connected 4-way, Ordered dither over a rect: each px becomes c2 where mix > threshold, else c1., Banded gradient with dithered transitions across a rect. colors = dark->light li, Deterministic speckle (stone/grain). Same seed -> same result every render., Outline the current cel's silhouette. outside = new px on transparent neighbors

### Community 8 - "Sprite Export & Inspection"
Cohesion: 0.16
Nodes (9): hex2rgba(), _mkdirs(), Magnified crop for detailed inspection. Box is inclusive pixel coords., Silhouette test image: if the subject doesn't read here, redesign the shape., Animated GIF. bg=None keeps binary transparency; give a bg color for social post, PNG sheet + Aseprite-compatible JSON (frames, durations, frameTags)., Side-by-side contact sheet: requires the sprite to carry a ._orig snapshot, #RGB' / '#RRGGBB' / '#RRGGBBAA' / (r,g,b[,a]) / None(=transparent) -> rgba tuple (+1 more)

### Community 9 - "vj TUI Screens"
Cohesion: 0.13
Nodes (7): ComposeResult, Screen, Vertical, Home, Path, Profile + dotfile set, stacked. Auto-opens until a valid choice is saved., SetupPanel

### Community 10 - "Sprite Layers & Transforms"
Cohesion: 0.11
Nodes (7): Frames x layers of RGBA cels. Frames and coordinates are what you expect:     fr, Create (if missing) and select a layer. New layers go on top, or above `above`., Copy one half onto the other, flipped (symmetric characters). Odd width keeps, Move the current cel. wrap=True scrolls (seamless-tile inspection!)., Stamp an external PNG onto the current cel (alpha-respecting)., frames: None=current | 'all' | list of 1-based indices., Sprite

### Community 11 - "vj Checklist Widget"
Cohesion: 0.18
Nodes (3): Checklist, PackagesChecklist, Generic checklist submenu. `apply(ticked_ids)` persists the whole selection.

### Community 12 - "Bootstrap & Malware Gate"
Cohesion: 0.22
Nodes (19): vjupdate script, bootstrap(), check_app_launchers(), check_aur_malware(), _check_packages_against_malware(), detect_machine(), die(), _die_infected() (+11 more)

### Community 14 - "Palette Cleanup Pipeline"
Cohesion: 0.14
Nodes (9): _pal_image(), P-mode palette image, cyclically padded to 256 so no stray black entries attract, Remap every pixel to the given palette (retro conversion). Keeps layers/alpha., Flatten and reduce to n colors chosen adaptively from the art itself., Snap semi-transparent pixels. threshold: alpha<threshold -> 0, else 255 (kills A, Remove isolated pixel clusters: connected components (4-way) of opaque pixels, Merge colors within `tol` (max channel distance) into their most-used         re, Detect opaque edge pixels that are color-contaminated by a former background (+1 more)

### Community 15 - "Upgrade Recap Tests"
Cohesion: 0.15
Nodes (5): A failed paru -Syuu must name the cause in the end-of-run recap., The mirrors-step database sync must recover from an untrusted repo key., ReviewFollowupTests, SyyRecoveryTests, UpgradeFailureReportingTests

### Community 16 - "Pixel Grid Recovery"
Cohesion: 0.23
Nodes (14): block_downscale(), detect_scale(), estimate_scale(), Import art and recover true pixels.          scale: 'auto' (detect; falls back t, Largest integer s such that the image is exact s x s pixel blocks., Median run-length of similar colors — for sloppy/resampled upscales where     de, Dominant-color block sampling at scale s: each output pixel is the modal color, rgba2hex() (+6 more)

### Community 17 - "Package Install Pipeline"
Cohesion: 0.18
Nodes (16): _check_disk_space(), _demote_packages(), _do_install(), _estimate_aur_builds(), _import_aur_keys(), install_all(), _install_list(), _is_protected() (+8 more)

### Community 18 - "Pixel Art Failure Modes"
Cohesion: 0.15
Nodes (15): harden_alpha / despeckle / dedupe_colors / dehalo, Study 001: chibi JRPG cast, Sharp Edges failure modes, AA halos, Editing exports instead of build script, Orphan pixels, Pillow shading (balloon sprite), Techniques reference (+7 more)

### Community 19 - "Anime Cast Example"
Cohesion: 0.15
Nodes (7): catmage(), frog(), mushroom(), ramp(), Rotate hue h toward target by up to `amount` degrees (all in degrees)., Shading ramp (dark -> light) with proper hue shifting.      Shadows rotate towar, _toward()

### Community 21 - "Hold & Priority Tests"
Cohesion: 0.26
Nodes (3): BuildPriorityTests, HoldTests, Package builds must not outrank games: lowest CPU and idle I/O priority.

### Community 22 - "Dotfile Deployment"
Cohesion: 0.22
Nodes (14): _adopt_backup(), clean_caches(), deploy_dotfiles(), _deploy_pkg(), _deploy_root_pkg(), flatpak_update(), install_user_tools(), _mutate() (+6 more)

### Community 24 - "Knight Animation Example"
Cohesion: 0.23
Nodes (11): compose(), frame_to_gif(), main(), outline(), parts: list of (layer, (dx, dy))., Flood-fill the baked navy background to transparency from the edges only,     so, 1px dark outline so the sprite reads on light backgrounds., plume: red pixels in the top third; legs: bottom band; body: everything else. (+3 more)

### Community 25 - "LPC Sheet Builder"
Cohesion: 0.22
Nodes (6): LPCSheet, Render one action row as an animated GIF preview., Absolute sheet row for an action+direction., Yield every (action, direction, frame) cell in sheet order., Paste one frame into its cell: canvas centered on x, feet on the baseline., row_of()

### Community 26 - "DMS & Configure Phase"
Cohesion: 0.15
Nodes (13): _act(), _confirm(), dms_export(), dms_import(), _dms_repo(), export_dotfiles(), manage_kernels(), phase_configure() (+5 more)

### Community 27 - "pixelstudio Core Helpers"
Cohesion: 0.18
Nodes (7): _dist2(), mix(), nearest(), Blend two colors, returns hex., Integer-upscale an existing PNG (nearest neighbor)., _rgb_to_hsv(), upscale_png()

### Community 28 - "vj Launcher & Test Fixtures"
Cohesion: 0.23
Nodes (7): vj script, fixture_repo(), Path, Tests for the vj Python package (config, resolution, plan, UI). No system change, Minimal repo: two profiles, one dotset with two stow packages + profile dirs., Tmp, UnusedTests

### Community 29 - "System Tuning & Mirrors"
Cohesion: 0.18
Nodes (12): automount_disks(), _fix_untrusted_keys(), _has_feature(), _mark_done(), _needs_run(), optimize_system(), print_manual_steps(), refresh_mirrors() (+4 more)

### Community 30 - "vj App Shell"
Cohesion: 0.18
Nodes (3): App, Hand the terminal to vjupdate so sudo/pacman prompts work as usual., VjApp

### Community 31 - "Frame & Cel Operations"
Cohesion: 0.20
Nodes (5): _Frame, Append a frame (or insert after frame index `after`). Copies current frame's cel, Copy one layer's cel to other frames (static background pattern).         link=T, RGBA tuple at (x,y) — None if transparent. composite=True reads merged layers., Swap a color. frames: None=current | 'all' | list. layers: None=current | 'all'

### Community 34 - "Animation Studies"
Cohesion: 0.20
Nodes (10): Animation reference, Oversized attack frames / stable pivot, Part-per-layer puppeting, 4-frame walk construction, Study 002: dynamic attack canvas, Study 003: dramatic chibi swordsman, Jewel-tone clusters + black-plum outline, Study 004: tactical chibi layered cloth (+2 more)

### Community 36 - "Once & Unlisted Checklists"
Cohesion: 0.29
Nodes (3): OnceChecklist, Installed by hand but in no list. Keys act on ticked rows, else the highlighted, UnlistedChecklist

### Community 37 - "Pixel Art Studio Skill"
Cohesion: 0.36
Nodes (9): Pixel Art Studio README, Draw from scratch mode, Learned Styles Index, Validations critique checklist, pixel-art-studio SKILL.md, Knowledge routing table, Learning from user-provided art, Learning persistence rule (+1 more)

### Community 38 - "Palettes & Hybrid Pipeline"
Cohesion: 0.22
Nodes (9): Cleanup / hybrid pipeline reference, True grid recovery (from_png block-sampling), Palette lock (clean palette=/max_colors=), Palettes reference, Hard color budget, Palette swaps (enemy variants), Palette presets (Game Boy, PICO-8, Sweetie16, C64, Endesga32), Palette bloat (+1 more)

### Community 39 - "Iron Man Sprite Example"
Cohesion: 0.31
Nodes (7): armor_segment(), beam(), build(), iron_man(), Connected repulsor beam clusters with a bright core and tapered endpoint., A filled armored limb segment; never use a 1px line for anatomy., Tall tactical 3/4 armored hero: ~4.4 heads high, stable foot pivot.

### Community 40 - "VSCodium Python REPL"
Cohesion: 0.25
Nodes (3): get_last_command(), PS1, REPLHooks

### Community 44 - "Pixelstudio Tests"
Cohesion: 0.29
Nodes (6): Remove a baked-in light-gray checkerboard background (common in AI-gen exports)., strip_checker(), test_dedupe_merges_into_most_used_and_never_into_merged_colour(), test_frame_indices_checked_and_tags_follow(), test_quantize_ignores_transparent_background(), test_strip_checker_keeps_light_pixels_inside_art()

### Community 47 - "vj Package Modules"
Cohesion: 0.32
Nodes (4): detect_installed(), Everything the TUI shows and changes, without Textual. Every change is saved at, pacman + flatpak app IDs; a missing tool just contributes nothing., Textual TUI: one screen — menu with a recap per row, submenus open inline below

### Community 48 - "Character Proportions"
Cohesion: 0.29
Nodes (7): Chibi head ≈ 45-50% height rule, Study 005: tall tactical job sprites, 4-5 heads tall heroic field sprites, Patterns reference, Character proportions (chibi/heroic/tall-tactical), Silhouette-first build order, Tiles & tilesets

### Community 49 - "pixelpipe CLI"
Cohesion: 0.48
Nodes (6): main(), _next_idx(), _parse_steps(), Write a study card + save the cleaned palette, reusing study.analyze., run(), _run_study()

### Community 50 - "Surface Sync Script"
Cohesion: 0.52
Nodes (6): ask(), die(), ok(), surface-sync.sh script, step(), warn()

### Community 53 - "Export & LPC Reference"
Cohesion: 0.33
Nodes (6): Export reference, Integer-only nearest-neighbor scaling, Spritesheet + engine JSON, LPC universal sheet reference, Margin canvas to avoid weapon clipping, LPC universal sheet (64x64 grid)

### Community 54 - "Capybara Example"
Cohesion: 0.60
Nodes (5): build_dir(), draw_down(), draw_side(), faces RIGHT; left = mirror, sprout()

### Community 56 - "Knight Walkcycle Example"
Cohesion: 0.70
Nodes (4): bbox(), main(), outline(), strip_bg()

### Community 57 - "Tactical Oracle Example"
Cohesion: 0.60
Nodes (3): build(), oracle(), staff()

### Community 58 - "Claude Keybindings"
Cohesion: 0.50
Nodes (3): bindings, $docs, $schema

### Community 61 - "Windows VM Compose"
Cohesion: 0.67
Nodes (3): Ports 8006 noVNC + 3389 RDP, ~/Shared:/shared volume + ./storage, windows service (dockurr/windows, Win11, 16G RAM, 8 cores, 128G disk)

## Ambiguous Edges - Review These
- `build-times.tsv` → `AUR build-time estimate section`  [AMBIGUOUS]
  README.md · relation: conceptually_related_to

## Knowledge Gaps
- **35 isolated node(s):** `Ports 8006 noVNC + 3389 RDP`, `~/Shared:/shared volume + ./storage`, `$schema`, `$docs`, `bindings` (+30 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **24 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **What is the exact relationship between `build-times.tsv` and `AUR build-time estimate section`?**
  _Edge tagged AMBIGUOUS (relation: conceptually_related_to) - confidence is low._
- **Why does `Sprite` connect `Sprite Layers & Transforms` to `Iron Man Sprite Example`, `Sprite Export & Inspection`, `Pixel Drawing Primitives`, `Pixelstudio Tests`, `Palette Cleanup Pipeline`, `Pixel Grid Recovery`, `pixelpipe CLI`, `Capybara Example`, `Tactical Oracle Example`, `pixelstudio Core Helpers`, `Frame & Cel Operations`?**
  _High betweenness centrality (0.038) - this node is a cross-community bridge._
- **Why does `pixel-art-studio SKILL.md` connect `Pixel Art Studio Skill` to `Animation Studies`, `Palettes & Hybrid Pipeline`, `Character Proportions`, `pixelpipe CLI`, `Pixel Art Failure Modes`, `Pixel Grid Recovery`, `Export & LPC Reference`, `LPC Sheet Builder`, `pixelstudio Core Helpers`?**
  _High betweenness centrality (0.026) - this node is a cross-community bridge._
- **Why does `FixtureCase` connect `vjupdate Test Suites` to `Malware & Automount Tests`, `Build Time Estimate Tests`, `Adoption & Review Tests`, `Run Plan Tests`, `Followup Fix Tests`, `Upgrade Recap Tests`, `Dotset Tests`, `Hold & Priority Tests`, `Menu PTY Tests`, `--actions Tests`?**
  _High betweenness centrality (0.024) - this node is a cross-community bridge._
- **Are the 3 inferred relationships involving `Sprite` (e.g. with `build_dir()` and `build()`) actually correct?**
  _`Sprite` has 3 INFERRED edges - model-reasoned connections that need verification._
- **Are the 12 inferred relationships involving `FixtureCase` (e.g. with `AuditTests` and `AurReviewTests`) actually correct?**
  _`FixtureCase` has 12 INFERRED edges - model-reasoned connections that need verification._
- **What connects `Ports 8006 noVNC + 3389 RDP`, `~/Shared:/shared volume + ./storage`, `$schema` to the rest of the system?**
  _35 weakly-connected nodes found - possible documentation gaps or missing edges._