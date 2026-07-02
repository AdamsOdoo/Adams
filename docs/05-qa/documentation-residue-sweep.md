# Documentation Residue Sweep

> **Purpose.** A point-in-time sweep for stale documentation residue and
> process bloat, run as a mechanical cleanup/convergence sprint (not a
> research sprint). Investigates Fable's independent-review input, verifies
> each item against the repo before fixing, and records what was fixed, what
> was not found, and what is deferred. No architecture decisions; no MVP scope
> change; DEC-003 body untouched.

## Sprint / date

**Control-Room Reset Sprint 1 — 2026-07-02.** Precondition confirmed: PR #58
(RB-14 Part 2) is merged into `Shopify-connector`; the working branch is based
on that merge tip.

## PR #59 revision (2026-07-02, ChatGPT review — REVISE)

ChatGPT reviewed PR #59 and returned **REVISE**: the sprint stayed in scope but
**missed several current-truth stale residues in allowed files** — the first
pass fixed the two most prominent TQ/MVP statements per file but did not
grep exhaustively for every recurrence. Fixed on the same branch (commit
`docs: fix missed reset residue`), within the revision's own allowed-files
list only:

- **TeqStars/TQ residue in `feature-taxonomy.md`:** the evidence-weighting
  note and the "Capabilities with weak or blocked evidence" section still said
  TQ docs are 403-blocked / all TQ support is claim-only. Corrected to note the
  Sprint C2 (PR #56) rebaseline, with conservative routing language (not new
  per-capability claims) to `competitor-feature-matrix.md` /
  `competitor-deep-dives.md` for the ~40 unrevised per-cell TQ🟨/🔒 symbols in
  the domain tables, which were **not** individually re-verified in this pass.
- **TeqStars/TQ residue in `capability-evidence-map.md`:** the "Competitor
  keys" line and the `C-DOCS-01`/`C-DOCS-02` rows still said TQ = docs
  403/claims-only and "TQ 403 = anti-patterns." Corrected the two `C-DOCS-*`
  rows against already-merged Sprint C2 evidence (`C-DOCS-01` TQ🔒→✅, screenshot-
  rich docs now demonstrated; `C-DOCS-02` TQ🔒→⬜, docs readable but still no
  dated changelog — not blocked, just not-found); all other TQ symbols left
  unrevised with an explicit routing note, per the revision's "do not upgrade
  individual capabilities beyond already-merged evidence" instruction.
- **Single-store/multi-store MVP residue in `feature-taxonomy.md`:** three
  locations (the "Open questions" list, the "MVP-candidate inputs" section
  intro, and the C-MULTI-01 capability entry/permissions note) still called
  single- vs multi-store "not decided" or "open." Corrected: DEC-003 (RB-13)
  accepted single-store/single-company as the MVP product-scope baseline;
  the architecture *mechanism* for future multi-store/multi-company stays
  gated (AR-004/AR-005) — not reworded as an architecture decision.
- **Odoo Online residue in `setup-ux-principles.md`:** two locations (a
  Principle-1 evidence note and an "Open questions" item) still called Odoo
  Online custom-module/queue compatibility open. Corrected: RB-14 Part 2
  (PR #58) already established Odoo Online is incompatible with custom
  modules as an `[Official fact]` — that substrate question is resolved;
  what remains open (AR-003) is narrowed to Odoo.sh/on-prem `odoo.conf`/queue
  feasibility.
- **`rejected-approaches-log.md` contradiction:** RA-001 was added correctly
  in the prior commit, but the historical Sprint A–C and Sprint G notes still
  read as if no approach had ever been rejected / no entry would be added.
  Added superseded markers (history preserved, not deleted) pointing to
  RA-001, and marked the Sprint G note's "TeqStars rebaseline is pending"
  clause superseded (Sprint C2 completed it the same day).
- **`docs/03-architecture/README.md` phantom-file reference:** the "Current
  status" line was corrected in the first pass, but the "What belongs here"
  line still named `architecture-preparation.md` as if it existed. Corrected
  to describe what belongs in the folder generically and point to the actual
  RB-14 files, with a note that the originally planned filename was never
  created.

**No architecture decisions made. No implementation authorized. DEC-003 body
untouched. MVP scope unchanged.** Logged as an addendum to DP-007 in
`defect-pattern-log.md` (same category/root cause as the first pass, not a new
occurrence — caught and fixed within the same review cycle).

## What was checked

All files in the "Required pre-session read" list of the sprint prompt, plus a
repo-wide grep sweep for: `Proposed`/`pending ChatGPT`, `No MVP scope`/`not
finalized`, `403`/`blocked`/`claim-only`/`claims only`, `TeqStars`/`TQ`,
`Sprint C2`/`2026-07-01`, `not started`, `empty`/`phantom`, and the DEC-003
Option C / rejected-approaches consistency. Each Fable-flagged item (1–11 in
the sprint prompt) was individually verified against current file content
before any edit — Fable's list was treated as investigation targets, not fact.

## Confirmed stale residue (fixed)

1. **`docs/04-decisions/README.md`** — said "Empty except the template."
   DEC-003 exists. Fixed to acknowledge DEC-003 and flag the
   `DEC-003` vs `ADR-NNNN-<slug>.md` naming/numbering inconsistency (see
   *Deferred / flagged* below) rather than inventing missing entries.
2. **`docs/03-architecture/README.md`** — said "Empty. Opens with backlog item
   RB-14... pre-decision framing only." RB-14 Part 1 + Part 2 framing/
   decision-candidate docs already exist. Fixed to list them and restate
   AR-002/003/005 as framed-and-narrowed-but-**not decided**.
3. **`docs/05-qa/pr-review-checklist.md`** — checkbox read "No premature
   architecture / no MVP finalization," which now contradicts the accepted
   DEC-003 baseline. Reworded to still block premature architecture decisions
   and unauthorized MVP scope changes, without forbidding the (already
   accepted) MVP finalization itself.
4. **`docs/02-product/mvp-scope.md`** (line ~1481) — the MVP-critical
   reliability capabilities section still read "Proposed MVP inclusion —
   pending ChatGPT acceptance," contradicting the file's own top-of-file
   "Accepted MVP baseline" status. Fixed to "accepted MVP inclusions
   (DEC-003)"; architecture-dependent mechanism still correctly gated to RB-14.
5. **`docs/02-product/feature-taxonomy.md`** (closing note) — "MVP scope
   (RB-13)... remain gated pending ChatGPT review." Fixed: MVP scope is
   accepted (DEC-003); architecture + module boundaries remain gated.
6. **`docs/02-product/product-vision.md`** and **`docs/02-product/setup-ux-principles.md`**
   (Status sections) — both authored in Product Sprint E (before DEC-003
   existed) and still asserted "No MVP scope is finalized." Both were product
   Sprint E documents.  Fixed with a dated correction noting DEC-003 postdates
   this document's authoring and the document itself was not rewritten against
   it — read as directional strategy/principles, not a scope statement (per
   the preservation guardrail: minimal correction, not a rewrite).
7. **`docs/02-product/setup-ux-principles.md`** (evidence-weighting note) —
   "Teqstars (TQ) docs are 403-blocked → UX unverifiable," contradicted by the
   Sprint C2 rebaseline (TQ Accessible, 31 pages, ~98 screenshots). Fixed with
   a superseded-note pointing to `ux-ui-benchmark.md`.
8. **`docs/00-source-materials/screenshots/teqstars/README.md`** — still
   stated the docs host was 403-blocked and screenshots were caption-only/low
   confidence. Sprint C2 (PR #56) read 31 pages with ~98 real screenshots.
   Fixed by adding a "Current status (Sprint C2)" section above the original
   note, which is retained as history, not deleted.
9. **`docs/00-source-materials/source-access-notes.md`** — the R2 (Teqstars)
   entry and the 2026-06-30 access-summary table still read "Blocked (HTTP 403
   Forbidden)" / "Ready for deep dive: No," with no acknowledgment that Sprint
   C2 unblocked it. `resource-inventory.md` already carried the Sprint C2
   correction; this file did not. Fixed by adding an "R2 status correction —
   Sprint C2" subsection (mirroring `resource-inventory.md`'s structure) and a
   one-line pointer above the dated summary table. The dated Sprint B table
   and R2 narrative are retained as history, not rewritten.
10. **`docs/01-research/research-backlog.md`** — nearly every backlog item
    (RB-01.1 through RB-14.1) was still marked `Not started` or
    `Blocked (access)` despite the corresponding output file existing and
    being complete (competitor deep dives, matrix, UX benchmark, official
    notes, common patterns, best-in-class, gaps, avoid-list, product vision,
    feature taxonomy, MVP scope/DEC-003, RB-14 Part 1+2 framing). Fixed each
    item's `Status` field to `Done` with a pointer to its actual output file,
    while leaving the original `Objective`/`Acceptance criteria` text intact
    (it accurately describes what was originally scoped). RB-02.6 (Google Doc,
    R5) correctly remains `Blocked` — this is a genuine, still-open external
    dependency, not stale residue. RB-13.1's title/acceptance-criteria
    ("not finalized — pending ChatGPT review") is kept as the historical
    scoping description, with a status note that MVP scope is now accepted
    (DEC-003) and superseded that criterion. RB-14.1's `Output file` field
    named `architecture-preparation.md`, which was never created — flagged as
    a filename drift (see *Deferred / flagged*) and the actual output files
    listed instead.
11. **`docs/05-qa/rejected-approaches-log.md`** — DEC-003 explicitly rejects
    "Option C — Thin import-only pilot" as an MVP-scope option, but no
    corresponding row existed in this log (every prior sprint note explained
    *why* no row was needed, but none of those notes covered DEC-003's own
    Option C rejection). Added row RA-001, linked to DEC-003.

## Not found / no change needed

- **`docs/01-research/resource-inventory.md`** — Fable flagged possible
  TeqStars residue; verified **already correctly rebaselined** (has its own
  "Sprint C2 access change" section with an updated 2026-07-01 access
  summary). No change needed.
- **`docs/00-source-materials/competitor-source-notes.md`** — verified R2 is
  already restructured into "Sprint C historical" + "Sprint C2 accessible"
  subsections with verbatim quotes, per the Sprint C2 handoff description. No
  change needed.
- **`docs/01-research/competitor-feature-matrix.md`** — verified the TQ column
  is already rebaselined (Sprint C2 header note + per-cell evidence). No
  change needed.
- **`docs/02-product/capability-evidence-map.md`** — checked for "No MVP scope
  is finalized"-style language; none found. No change needed.
- **`docs/02-product/non-mvp-and-later-phases.md`**, **`docs/02-product/user-stories.md`**
  — checked for stale MVP-not-finalized language; none found. No change
  needed.
- **`docs/01-research/gaps-opportunities.md`** — Fable flagged this file
  (item 2). Its line "MVP scope and architecture are NOT finalized **here**"
  is a scoped disclaimer about this document's own authority (it is a
  recommendations file, not a scope decision), not a claim that MVP scope is
  globally undecided elsewhere — still accurate after DEC-003. No change
  needed.
- **`docs/02-product/product-research-handoff.md`** — checked in full (not
  Fable-flagged by name, but on the allowed list). Its top-of-file Governance
  block already correctly states "From Sprint G the MVP *product scope* is
  accepted (RB-13, DEC-003)" and the TeqStars Sprint C2 rebaseline. The
  "not finalized" hits found by grep are inside its own dated, historical
  Sprint F/E/D sections (predating DEC-003) — preserved, not rewritten, per
  the preservation guardrail. No change needed.
- **`docs/01-research/shopify-official-api-notes.md`**, **`docs/01-research/odoo-official-architecture-notes.md`**
  — the only "not finalized"/"gated" language found refers to **architecture**
  (still accurately gated) or is already marked "Superseded by RB-14 Part 2."
  No change needed.
- **`docs/03-architecture/architecture-decision-framing.md`**,
  **`ar-002-distribution-api-framing.md`**, **`ar-003-sync-orchestration-framing.md`**,
  **`ar-005-binding-dedup-framing.md`**, **`rb14-decision-candidate-brief.md`**
  — grepped for the same stale patterns; all current statements are accurate
  (AR-002/003/005 genuinely still "Not decided"). No change needed.
- **`docs/05-qa/architecture-review-log.md`**, **`docs/05-qa/defect-pattern-log.md`**
  (existing rows), **`docs/05-qa/technical-debt-register.md`** — reviewed; AR
  rows are genuinely still "Not decided / Evidence pending" (not residue); no
  incorrect current-truth statements found in existing content (this sprint
  adds new rows/notes to these logs — see *Files changed*).
- **`docs/06-prompts/claude-session-prompts.md`** — no MVP/TeqStars-status
  contradiction found (it is a reusable prompt-preamble reference, not a
  status document). Its "Quick index" table row for RB-14.1 still names the
  originally planned `architecture-preparation.md` output file, which is the
  same filename drift already flagged via `research-backlog.md`; not edited
  separately to avoid duplicate/scattered corrections.
- **`README.md`** (root) — describes the project as being in a research &
  governance phase with no code written; still accurate (architecture and
  implementation remain gated). No change needed.

## Deferred residue (out of this sprint's allowed-files list)

Per the sprint's allowed-files list, the following files were **not** edited
even though they matched the Fable grep patterns, because they are outside
this sprint's allowed-files list. They were spot-checked and, based on the
Sprint C2 handoff's own files-changed list, already appear to have been
rebaselined in PR #56 — but a full verification was out of scope here:

- `docs/01-research/ux-ui-benchmark.md`
- `docs/01-research/common-patterns.md`
- `docs/01-research/best-in-class-observations.md`
- `docs/01-research/avoid-list.md`
- `docs/01-research/competitor-deep-dives.md`
- `docs/00-source-materials/competitor-screenshot-inventory.md`

If a future sprint authorizes editing these files and finds residue, log it
there; do not fix it under this sprint's allowed-files list.

## Flagged, not fixed (per explicit sprint instruction)

- **`DEC-003-mvp-scope.md` is read-only this sprint.** Two stale references
  were found and are **flagged for a future dated post-decision note only**
  (not added here):
  1. The revision note (top of file) says a "full TeqStars evidence rebaseline
     is pending a later research sprint" — that rebaseline is now **done**
     (Research Sprint C2, PR #56, 2026-07-01, same day as DEC-003 but later in
     sequence).
  2. The "Evidence weighting" note in *Sources and evidence* still lists
     Teqstars (TQ) among "caption/guide/claim-only vendors (SH/WK/EC/TQ)" —
     TQ's evidence strength materially improved in Sprint C2 (now mostly
     `✅ demonstrated`, per `competitor-feature-matrix.md`).
  **Recommendation:** a short, separately dated "Post-decision evidence note
  (2026-07-02 or later)" appended to DEC-003 by a session ChatGPT authorizes
  for that purpose — not a body edit, and not performed in this sprint.
- **`docs/04-decisions/README.md` naming/numbering inconsistency** — the
  folder's own instructions say decisions are named `ADR-NNNN-<slug>.md`, but
  the only decision present is `DEC-003-mvp-scope.md` (a different prefix, and
  no `DEC-001`/`DEC-002` exist). This sprint does **not** invent missing
  entries or rename `DEC-003`; the inconsistency is recorded here and in the
  README for ChatGPT to resolve (e.g. by deciding whether future decisions use
  `DEC-NNN` or `ADR-NNNN`, and whether `DEC-003` is renumbered or grandfathered).

## Files changed

See the PR diff. Summary: `docs/04-decisions/README.md`,
`docs/03-architecture/README.md`, `docs/05-qa/pr-review-checklist.md`,
`docs/02-product/mvp-scope.md`, `docs/02-product/feature-taxonomy.md`,
`docs/02-product/product-vision.md`, `docs/02-product/setup-ux-principles.md`,
`docs/00-source-materials/screenshots/teqstars/README.md`,
`docs/00-source-materials/source-access-notes.md`,
`docs/01-research/research-backlog.md`,
`docs/05-qa/rejected-approaches-log.md`,
`docs/05-qa/documentation-residue-sweep.md` (this file),
`docs/05-qa/quality-feedback-loop.md`, `CLAUDE.md`,
`docs/06-prompts/session-handoff-template.md`,
`docs/01-research/research-handoff.md`,
`docs/05-qa/architecture-review-log.md`, `docs/05-qa/defect-pattern-log.md`.

## No architecture decisions made

Confirmed: no AR-002/003/005 (or any AR row) status changed; all remain "Not
decided / Evidence pending." No REST/GraphQL, queue, binding, data-model,
module, or distribution choice was made.

## No implementation authorized

Confirmed: no code, no Odoo module, no `*.py`/`*.xml`/`*.csv`/manifest files,
no CI/Docker files were created or touched. The no-code gate (`CLAUDE.md` §5)
remains in force.
