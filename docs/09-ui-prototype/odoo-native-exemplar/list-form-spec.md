# Screen spec — Odoo-native list & form exemplar

> **Status: Accepted U0 visual baseline** (control-room comment `4951204357`,
> 2026-07-12; merged via **PR #152** into `Shopify-connector` at merge commit
> `65e915aada32930a19a14c94d23dc9bd5e6fb517`). History preserved — gate
> `4948902516` → reviews `4950255482`, `4950432754` → acceptance `4951204357`.
> **Implementation remains separately gated** — UI-U1/U2/U3 stay CLOSED and this
> spec authorizes no code. Demonstrates that
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
rows), **manual review** (the Customers “Waiting on a decision” and Products
“Needs review” rows + reviewer routing).

### Row status → color family (token-map aligned)
Every attention row in this list is either a **held/manual-review** state in the
**danger** family or a **retry** state in the **info** family — there is **no
non-blocking `warning` row** in this snapshot. Specifically:

| Row | State word | Family | Why |
| --- | --- | --- | --- |
| Orders | On hold | **danger** | Financial mismatch — held for the operator |
| Products | Needs review | **danger** | `blocked_manual_review` — a product waiting on a reviewer’s match decision |
| Customers | Waiting on a decision | **danger** | `blocked_manual_review` — two contacts share the email; a reviewer must choose |
| Inventory | Waiting to retry | info | `retry_waiting` — rate-limited, the system will retry |
| Fulfillment / Products | Done | success | Completed |

The two `blocked_manual_review` rows follow the accepted map
(`blocked_manual_review → danger`, review `4950432754` §2); they are told apart
from a **technical failure** by their **plain-language state + reason** (a
reviewer decision, not a system fault) and reviewer routing — **not** by
reverting to `warning`. The `warning` family is reserved for genuinely
**non-blocking advisories** (e.g. “overdue but retrying”); none appears here, so
none is mislabelled as manual review. The raw token `blocked_manual_review` is
**never shown** — the State column shows plain words only.

## Responsive
`native-list-{768,375}.png`: at 375px the list uses Odoo’s **optional-column
hiding** (Source / Reference / Age hidden) so the **primary answer — State +
identifier + reason — stays visible**; no horizontal page scroll (design-system
§10). At **≤ 900px** the app bar collapses to the **compact Odoo-native mobile
shell** (☰ Menu + current section + persistent health), so the connection-health
state stays visible and no menu label is clipped (review `4950255482` §4;
breakpoint corrected to the actual ≤ 900px contract per review `4950432754` §3).

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
