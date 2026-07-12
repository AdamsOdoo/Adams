# Screen spec — Odoo-native list & form exemplar

> **Status: U0 prototype spec. Proposed, not accepted.** Demonstrates that
> ordinary connector records (S4 sync center list; job form) stay **Odoo-native**
> — the point PD-7 makes: selective Owl only for the four premium surfaces,
> everything else standard Odoo views. Source: `list-form.html`. Copy
> illustrative (MBQ-22).

## Purpose
Prove that “premium” does **not** require rebuilding standard Odoo list/form
views in Owl. The connector token layer is applied *restrained-ly* on top of
platform-native list/search/filter and form/sheet/notebook patterns.

## What it demonstrates
- **Standard Odoo shell** — top system bar, connector app menu (7 entries),
  breadcrumb, persistent health indicator.
- **List / search / filter** — a search bar with a removable facet (“Needs
  attention”), Filters and Group-by controls, a paginated list with column
  headers, and **row-level exception visibility** (a tinted row + a state
  **word** in the State column, never tint alone).
- **Form sheet & tabs** — statusbar (Draft · Queued · Running · On hold · Done),
  smart buttons (source order / log entries / binding), a reason+fix+owner
  block, and a notebook (Breakdown / Logs / Technical detail / Audit trail).
- **Status text and chips** — every state is a plain word plus a reinforcing
  color; the financial breakdown uses Match / Differs verdicts.
- **Empty state** — the filtered list’s affirmative empty (“Nothing needs
  attention”) names the next useful action.
- **Restrained connector token layer** — the only connector-specific styling is
  the token system (spacing, type, status colors, 8px card radius); no custom
  table or form engine, no foreign SPA chrome.

## States rendered
| State | File |
| --- | --- |
| List — default (needs-attention filter) | `native-list-1366.png` (+ `-768`, `-375`) |
| List — empty (filtered, affirmative) | `native-list-empty-1366.png` |
| Form — job detail (on-hold, financial mismatch) | `native-form-1366.png` |

The five canonical states are covered across the pair: **loading** (standard
Odoo list/form load — not separately screenshotted), **empty**
(`native-list-empty`), **success** (Done rows), **error** (on-hold form + tinted
rows), **manual review** (the “Waiting on a decision” row + reviewer routing).

## Responsive
`native-list-{768,375}.png`: at 375px the list uses Odoo’s **optional-column
hiding** (Source / Reference / Age hidden) so the **primary answer — State +
identifier + reason — stays visible**; no horizontal page scroll (design-system
§10). At ≤ 640px the app bar collapses to the **compact Odoo-native mobile
shell** (☰ Menu + current section + persistent health), so the connection-health
state stays visible and no menu label is clipped (review `4950255482` §4).

## Accessibility
Native list/form keyboard behavior is inherited; the search facet is a removable
token; notebook tabs follow the ARIA APG tabs pattern; statusbar exposes the
current stage; row exceptions carry a state word, not color alone.

## Performance (mapped)
PB-4/PB-5 list load ≤ 1.5s p75 on RD-1; PB-9 the list is a **server-paginated
Odoo-native list**, never client-loaded in full; PB-6 job-log open ≤ 1s.

## Proposed vs inherited
- **Inherited:** everything structural — S4/job form, fixed vocabularies as
  text labels, reason+fix+owner, smart buttons, no-raw-token rule, PD-7’s
  “ordinary records stay Odoo-native”.
- **Proposed:** only the token-layer *look* (spacing/type/status-color polish)
  applied to standard views — this exemplar exists to let ChatGPT accept how
  restrained that token treatment should be (decision 7).
