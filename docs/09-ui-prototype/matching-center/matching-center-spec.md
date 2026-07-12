# Screen spec — Matching center (S6/S8)

> **Status: U0 prototype spec. Proposed, not accepted.** Inherits S6/S8 /
> DEC-006 / DEC-012 §6 / Part D §11 and the fixed match-key order (customers:
> binding → email (sole automatic key) → manual; name/phone advisory only) from
> `../../02-product/ui-ux-final-design-spec.md`. Source: `matching-center.html`.
> Customer matching is the exemplar; the same pattern serves products. Copy
> illustrative (MBQ-22).

## Purpose
Show identity resolution honestly: the connector **resolves the automatic
outcomes itself** (merged Task 011) and asks a person to decide **only** when
the outcome is genuinely ambiguous. Every screen shows the incoming Shopify
record, the **evidence** (which fields are the binding key vs advisory), and the
**audit consequence** — for automatic outcomes as *what already happened*, for
manual review as *what will happen once you choose*. **Nothing is guessed.**

## Automatic outcomes vs human decisions (merged Task 011 — authoritative)
The accepted customer matcher is **binding → exact normalized email → manual
review**; name/phone are advisory only. That policy makes two outcomes
**automatic** (no operator decision) and reserves manual review for real
ambiguity:

| Situation | Outcome | Screen |
| --- | --- | --- |
| Exactly **one active** contact with the exact normalized email | **Bind automatically** | Single exact match (success/audit) |
| **Valid** normalized email, **zero active and zero archived** exact-email contacts | **Create the contact automatically** | No candidate (success/audit) |
| **Multiple** exact-email contacts | **Manual review** | Ambiguous |
| Archived-only / duplicate risk · missing/empty/unnormalizable email · binding conflict | **Manual review** | (policy — represented by the ambiguous exemplar) |

The prototype does **not** weaken or redesign this policy; it renders it.

## Elements
- **Incoming Shopify record** summary (`.sc-incoming`, key/value).
- **Automatic-outcome card** (`.sc-candidate.is-linked`) — for the two automatic
  results: a success badge + a “Linked” / “Created” chip, the bound/created Odoo
  record, and its evidence or summary shown as a **completed outcome**. There is
  **no radio and no selection** — the connector already acted.
- **Candidate Odoo records** (`.sc-candidate`, manual review only) — each with a
  radio (**at most one selected**), a title + reference, **confidence explained
  in words** (never a bare score), and a **field-level evidence table**. The
  evidence marks encode the **binding policy exactly**: the normalized **Email is
  the binding key** (“Matched — binding key”); every other row is **advisory
  only** (“Same” / “Differs — advisory”) — shown to help the human choose,
  **never used to discover a candidate**. There is no “Similar”/fuzzy verdict
  (review `4950255482` §2).
- **Decisions appear only when a decision exists.** The automatic outcomes offer
  **navigation only** (Open contact · View audit trail · Back). Manual review
  offers Link (disabled until one candidate is chosen) · Create new · Leave for
  review.
- **Audit consequence** (`.sc-consequence`) — for automatic outcomes, *what
  happened* (binding/contact created, order attached, recorded who/when/matched-by
  or created-because); for manual review, *what happens once you choose*. Shown
  before/with the outcome. No destructive merge tooling exists.

## States rendered
| State | File | Behavior |
| --- | --- | --- |
| Single exact match — **bound automatically** | `matching-single-1366.png` | Exactly one **active** Odoo contact has the exact normalized email, so the connector **binds automatically** (merged Task 011). **Success band + green outcome chips** (“Linked automatically” · “Done by the connector” · “No decision needed”); an `is-linked` outcome card (no radio) with a “Linked” chip and the binding-key evidence; audit note (binding created, order #1043 attached, *matched automatically by normalized email*, master data not overwritten). Actions are **navigation only**: Open Odoo contact · View audit trail · Back. **No Link / Create / Leave / Reject.** |
| No candidate — **contact created automatically** | `matching-none-1366.png` | A **valid** normalized email with **zero active and zero archived** exact-email contacts, so the connector **creates the contact automatically** (merged Task 011). **Success band + green outcome chips**; an `is-linked` card (no radio) with a “Created” chip and the new-contact summary (ref P-4102); audit note (contact + binding created, order attached, *created because no active or archived contact used this email*, no existing record changed). Actions are **navigation only**: Open new contact · View audit trail · Back. **No Create-new / Leave-for-review decision.** |
| Ambiguous / multiple — **manual review** | `matching-ambiguous-1366.png` (+ `-768`, `-375`) | **Both candidates share the exact same normalized incoming email** `j.okafor@example.com` (the binding key returned both); **none auto-selected**; “Link” disabled until one is chosen; **danger family + hand icon**, a “Waiting on a decision” status + reviewer owner, and “not a system failure”. Ambiguity comes only from **advisory** fields (name form, contact type, company, order history) — never fuzzy discovery. This is the representative `blocked_manual_review` case. |
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
In **manual review**, candidates are a `role="radiogroup"` (arrow-key selection,
one `aria-checked`) and “Link” is `aria-disabled` until one is chosen. The
**automatic outcomes have no radiogroup** — they are a completed result, so the
outcome chip carries the state in words and the buttons are plain navigation.
Evidence tables use real `<th>` associations; verdicts are words, not color
alone; the consequence note is associated with the outcome. See
`../accessibility/keyboard-and-focus-notes.md` §2.

## Performance (mapped)
PB-13 single-customer matching lookup ≤ 50ms p95 at 100k partners via the
indexed normalized-email path (the Task 011B budget); the UI reads a bounded
candidate set (PB-10), never a full partner scan.

## Proposed vs inherited
- **Inherited:** the **binding → exact normalized email → manual review** key
  order (email is the *sole* automatic key; name/phone/company advisory only);
  **the automatic outcomes themselves** — one active exact-email match binds
  automatically, and a valid email with no active/archived match creates the
  contact automatically (merged Task 011); manual review reserved for ambiguity /
  archived-only duplicate risk / missing-email / binding conflict; evidence-first;
  audit; `blocked_manual_review → danger`.
- **Proposed:** confidence-in-words phrasing; the field-level evidence-table
  layout with the binding-key/advisory mark vocabulary; the **success/audit
  presentation of the two automatic outcomes** (`is-linked` outcome card,
  green outcome chips, navigation-only actions); the hand-icon/reviewer-owner
  distinction of ambiguity from technical error within the shared danger family.
- **Not invented / corrected:** no RPC, no scoring algorithm, no fuzzy/partial
  matching, no new binding field. Two corrections applied on control-room review:
  (a) the prior ambiguous example (a `jane.okafor@…` candidate justified by
  “same domain + similar name”) **could never be returned by the exact-email
  lookup** and was replaced by two contacts sharing the exact normalized email
  (review `4950255482` §2); (b) the single-match and no-candidate screens, which
  previously asked the operator to press **“Link to this contact”** / **“Create
  new contact”**, are now the **automatic** success/audit outcomes the merged
  Task 011 backend actually produces — those decision sets are removed (review
  `4950432754` §1).
