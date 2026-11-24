---
name: vj-logo
description: fastfetch Vj logo (fish vj-logo.txt) — how it is built and what the user rejected
metadata:
  type: feedback
---

`dotsets/viridjan/fish/.config/fish/vj-logo.txt` (first line starts `$1` = fastfetch colour 1, cyan): V = `fastfetch --logo arch --structure none --pipe true` flipped vertically, j joined to the V's right arm on row 5.

**Why:** user rejected a hand-redrawn V ("disfigured") and a nearest-neighbour downscale (bent the top concave notch). Accepted (2026-11-24, 9cadfa3): exact flip, made smaller only by dropping near-duplicate rows (flipped rows 10 and 14), top rows untouched.

**How to apply:** flip map `/`↔`\`, `` ` ``→`.`, `.`→`'` (upright top dot, not the slanted backtick — user asked to check `.='`). Resize by removing/duplicating rows, never by redrawing or resampling. Edit the txt directly; the generator script was scratchpad-only.
