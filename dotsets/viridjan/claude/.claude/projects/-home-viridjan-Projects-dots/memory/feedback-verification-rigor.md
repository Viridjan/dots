---
name: feedback-verification-rigor
description: User pushes back on completeness claims; list-of-fixes is not evidence the code is clean
metadata: 
  node_type: memory
  type: feedback
  originSessionId: 74ac168d-fad3-4549-8662-ad28e7e617d5
  modified: 2026-08-15T17:38:17.527Z
---

Do not say "all fixed" when what is true is "all the items on my list are fixed." The
user challenged this directly ("all fixed you said?") after I claimed 11 vjupdate bugs
were resolved and a follow-up pass immediately found 5 more — three of them inside code
I had just edited.

**Why:** a list I assembled by reading is evidence about my attention, not about the
code. Presenting it as completeness sets up a claim the next pass falsifies, which
costs trust much faster than saying "here is what I checked and what I didn't."

**How to apply:**
- Audit by **bug class**, not by inspection. Grep for the class across the whole file
  (unguarded `$(...)`, `(( ))` under `set -e`, unguarded `cd`), so the sweep terminates
  on evidence instead of on attention running out.
- Reach for a linter before hand-auditing. Three passes of eyeballing found what
  `shellcheck` reports in one run.
- Always state what was **not** exercised. After fixing vjupdate, only `--check` and
  `--help` had actually been run; saying so plainly was received well.
- Verify with a run, not an assertion — simulate the failure branch if the real one
  can't be triggered, and label it as simulated.

See [[dots-shell-conventions]] for the specific bug class this came from.
