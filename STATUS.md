# STATUS.md — Current State

Updated 2026-06-13 — Goal 3 Phase B implemented locally; awaiting Claude review.

## What changed
- Goal 3 Phase B menu IA restructure implemented locally in `shopify_menu.xml`.
- One live Shopify root retained; Store Overview and Manager Dashboard both kept because B-T0a found distinct actions.
- Hollow `shopify_connector_pro_dashboard` tombstone-cleaned; AUD-030 and AUD-031 resolved.
- Generate Demo Data menu gated to `base.group_no_one`; wizard logic untouched.
- AUD-032 promoter `action_dummy` stat-button defect logged and deferred to Goal 8.

## Verified locally
- Local static checks ran: Python compile, XML parse, menu/action reference integrity, preserved domain/group regression, forbidden-grep.
- No sync/controller/API/wizard/model logic, promoter view, money path, manifest, migration, hook, or README change was made.

## Pending / Next
- Claude review required.
- Odoo.sh fresh install, upgrade, and full three-profile relay required before acceptance/merge.
- Goal 4 and Goal 5 are reserved only; neither was implemented.
