# UX v2 visual fidelity — blocking acceptance gate

The supplied `Odoo_Executive_Dashboard_UX_v2.html` and Finance/Sales/Mobile PNGs
are the design authority. Their hashes are recorded in `requirements/input-manifest.json`.
The contract supersedes fictional data/calculations, not the visual hierarchy.

The initial generic card grid did not implement the supplied design closely enough.
The user raised this on 20 September 2026. Correction is in progress, preserving
native Odoo data integration and existing branch work.

## Required comparison

| Area | Reference requirement | Acceptance evidence still required |
|---|---|---|
| Workspace | White desktop sidebar, six departments, plum active navigation, compact owner header | Current-candidate desktop screenshot comparison |
| Profitability | Four primary cards, margin context, chart left/performance context right | Correct hierarchy at 1440/1920; authorized native data and missing-data states |
| Liquidity/working capital | Dark cash card, separate cash/forecast/aging/bank detail | Native sources stay distinct; no fabricated outlook or totals |
| Sales | Commercial cards, orders/quotes and rankings, fulfillment/customer panels | Current-candidate Sales screenshot comparison; full design still under review |
| Supporting departments | Separate CRM/Inventory/Procurement/HR panels, compact by default | Navigation, expansion, returned report scope and permissions |
| Mobile | Compact header/filter bar, horizontal tabs, two-column cards, one column below 370px | 320/390 actual browser screenshots and visual inspection |
| Arabic | Mirrored layout, complete localization, readable mixed-script references | Same comparison in RTL, including opened details/tables |
| Interaction | Source definitions, report navigation, chart table alternative, keyboard focus | Functional runner checks plus manual visual/interaction review |

The native Odoo global toolbar remains provided by Odoo. Prototype-only sample
badges, fictional user/company identity, scenario controls, unapproved targets and
unsupported branch policies must not be rendered as real application facts.
Any further necessary visual departure must be explicit and reviewed, not silently
substituted by a generic design. Passing a reflow assertion alone does not close
this gate.

## Liquidity and working-capital correction

Source 397557b positions the native Cash Flow Statement bridge beside the
bank/cash account directory under three liquidity cards. The bridge reads the
native opening_balance/net_increase/closing_balance rows directly, without
recalculating their values. Bank rows retain native balance, account currency,
archive status, pagination and scoped native GL routes. A ready approved cash
mapping loads the directory automatically; unavailable access never becomes zero.

Receivable/payable cards expose the existing native due-date buckets as signed
values and magnitude bars. The full native aging action is explicit; individual
buckets are not advertised as scoped drilldowns. Daily cash-plan/minimum cash
remain visibly unconfigured until their distinct business definition is approved.
Native browser fixtures now configure cash and both aging reports to exercise the
actual layout and automatic directory loading in EN/AR, instead of only revenue.
Build 38347354 passed 53 native tests with zero failures/errors. Twelve source-matched
EN/AR captures are retained in the private evidence linked in implementation-status.md.
The 1024px liquidity screens were inspected in both languages. Full visual parity
and the remaining Sales/mobile/department interactions are not yet accepted.
