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
  (never a bare score), and a **field-level evidence table**. The evidence
  marks encode the **binding policy exactly**: the normalized **Email is the
  binding key** (“Matched — binding key”); every other row is **advisory only**
  (“Same” / “Differs — advisory”) — shown to help the human choose, **never used
  to discover a candidate**. There is no “Similar”/fuzzy verdict (review
  `4950255482` §2).
- **Explicit decisions:** Link · Create new (where policy permits) · Leave for
  review · Reject suggestion — the last kept apart from the primary.
- **Audit consequence** (`.sc-consequence`) — “what happens after confirmation”
  (binding created, order attached, decision recorded who/when/matched-by) is
  visible **before** the action. No destructive merge tooling exists.

## States rendered
| State | File | Behavior |
| --- | --- | --- |
| Single confident match | `matching-single-1366.png` | One candidate found by the **exact normalized email** (the only automatic key), pre-selected; just one Odoo contact uses this email, so no ambiguity; consequence + four decisions. |
| Ambiguous / multiple | `matching-ambiguous-1366.png` (+ `-768`, `-375`) | **Both candidates share the exact same normalized incoming email** `j.okafor@example.com` (the binding key returned both); **none auto-selected**; “Link” disabled until one is chosen; **danger family + hand icon**, a “Waiting on a decision” status + reviewer owner, and “not a system failure”. Ambiguity comes only from **advisory** fields (name form, contact type, company, order history) — never fuzzy discovery. |
| No candidate | `matching-none-1366.png` | Neutral band + empty card; email is the only automatic key; name/phone advisory; offers Create new / Leave for review. |
| Loading | `matching-loading-1366.png` | Skeleton incoming + candidate cards + “Searching Odoo contacts by email…”. |
| Technical error | `matching-error-1366.png` | Danger family; **explicitly labelled “a technical error, not an ambiguous match”**; owner = the system; nothing changed, order stays held. |

**Ambiguous (`blocked_manual_review`) vs technical error (`failed`) is a
first-class distinction** (V-4), and — per the accepted token map — **both are
the danger family**. They are told apart **without color**: ambiguity uses the
**hand** icon + a **reviewer** owner + “waiting on a decision / not a system
failure”; technical error uses the **triangle** icon + the **system** owner +
“try again”. This is the key design assertion of the screen.

## Tokens
`--sc-info` for the incoming band; **`--sc-danger` for the ambiguous
(`blocked_manual_review`) band and for the technical-error band** (distinguished
by icon/owner/copy, not color); evidence verdicts use success text for the
binding-key/“Same” rows and neutral (`--sc-text-secondary`) for advisory
“Differs” rows; the selected candidate gets an `--sc-accent` inset ring; radios
use `--sc-border-strong`.

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
  never folded); the **binding → exact normalized email → manual review** key
  order (email is the *sole* automatic key; name/phone/company advisory only);
  evidence-first; blocking preview; audit; `blocked_manual_review → danger`.
- **Proposed:** confidence-in-words phrasing; the field-level evidence-table
  layout with the binding-key/advisory mark vocabulary; the explicit
  four-decision button set with “Reject suggestion” separated; the
  hand-icon/reviewer-owner distinction of ambiguity from technical error within
  the shared danger family.
- **Not invented / corrected:** no RPC, no scoring algorithm, no fuzzy/partial
  matching, no new binding field. The prior ambiguous example (a
  `jane.okafor@…` candidate justified by “same domain + similar name”) **could
  never be returned by the exact-email lookup** and is removed — both candidates
  now share the exact normalized incoming email (review `4950255482` §2).
