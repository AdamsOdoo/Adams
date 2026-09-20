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
