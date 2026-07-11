# Screen spec — Matching center (S6/S8)

> **Status: U0 prototype spec. Proposed, not accepted.** Inherits S6/S8 /
> DEC-006 / DEC-012 §6 / Part D §11 and the fixed match-key order (customers:
> binding → email (sole automatic key) → manual; name/phone advisory only) from
> `../../02-product/ui-ux-final-design-spec.md`. Source: `matching-center.html`.
> Customer matching is the exemplar; the same pattern serves products. Copy
> illustrative (MBQ-22).

## Purpose
Turn identity resolution into confirming, not detective work: show the incoming
Shopify record, the candidate Odoo records, the **evidence** (which fields
matched or conflicted), and let the operator decide — with the consequence
visible before they act. **Nothing is guessed.**

## Elements
- **Incoming Shopify record** summary (`.sc-incoming`, key/value).
- **Candidate Odoo records** (`.sc-candidate`) — each with a radio (**at most
  one selected**), a title + reference, **confidence explained in words**
  (never a bare score), and a **field-level evidence table** marking each field
  *Exact match / Similar / Conflicts* (word + icon + color).
- **Explicit decisions:** Link · Create new (where policy permits) · Leave for
  review · Reject suggestion — the last kept apart from the primary.
- **Audit consequence** (`.sc-consequence`) — “what happens after confirmation”
  (binding created, order attached, decision recorded who/when/matched-by) is
  visible **before** the action. No destructive merge tooling exists.

## States rendered
| State | File | Behavior |
| --- | --- | --- |
| Single confident match | `matching-single-1366.png` | One candidate pre-evaluated as a strong (email-exact) match, selected; consequence + four decisions. |
| Ambiguous / multiple | `matching-ambiguous-1366.png` (+ `-768`, `-375`) | Two partial candidates, **none auto-selected**; “Link” disabled until one is chosen; warning family + hand icon; “a person should decide”. |
| No candidate | `matching-none-1366.png` | Neutral band + empty card; email is the only automatic key; name/phone advisory; offers Create new / Leave for review. |
| Loading | `matching-loading-1366.png` | Skeleton incoming + candidate cards + “Searching Odoo contacts by email…”. |
| Technical error | `matching-error-1366.png` | Danger family; **explicitly labelled “a technical error, not an ambiguous match”**; owner = the system; nothing changed, order stays held. |

**Ambiguous vs error is a first-class distinction** (V-4): ambiguity uses the
warning family + hand icon + decision language; technical error uses the danger
family + system owner + “try again”. This is the key design assertion of the
screen.

## Tokens
`--sc-info` for the incoming band, `--sc-warning` for ambiguity, `--sc-danger`
for technical error; evidence verdicts use success/warning/danger text; the
selected candidate gets an `--sc-accent` inset ring; radios use
`--sc-border-strong`.

## Accessibility
Candidates are a `role="radiogroup"` (arrow-key selection, one `aria-checked`);
evidence tables use real `<th>` associations; verdicts are words, not color
alone; the consequence note is associated with the decision buttons. See
`../accessibility/keyboard-and-focus-notes.md` §2.

## Performance (mapped)
PB-13 single-customer matching lookup ≤ 50ms p95 at 100k partners via the
indexed normalized-email path (the Task 011B budget); the UI reads a bounded
candidate set (PB-10), never a full partner scan.

## Proposed vs inherited
- **Inherited:** three distinct states (unmatched/ambiguous/duplicate-risk
  never folded), match-key order, evidence-first, blocking preview, audit.
- **Proposed:** confidence-in-words phrasing; the field-level evidence-table
  layout; the explicit four-decision button set with “Reject suggestion”
  separated; the ambiguous-vs-technical-error visual split.
- **Not invented:** no RPC, no scoring algorithm, no new binding field — the
  evidence table is a presentation of the accepted match keys only.
