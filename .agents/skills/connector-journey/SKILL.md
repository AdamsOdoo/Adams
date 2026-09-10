---
name: connector-journey
description: Complete and verify end-to-end connector workflows and their native Odoo experience, including management metrics, recovery, roles and business outcomes.
---

Read root AGENTS.md and handoff. UI redesign is currently parked; do not resume prototypes or production redesign without the user's instruction. Backend journey contracts/tests can advance.

Use docs/v2 product experience (01), UX contract (05), test/release contract (09), scope matrix (15), and current delivery blueprint (16). Map historical scenarios to U1–U14 rather than duplicating campaigns.

Define actor, business question, input, allowed action, held/error state, effect, verified result and safe next step. Read the actual DTO/command; a prototype control does not establish availability. Current read-only launch controls must not become a generic mutation launcher.

Keep native lists/forms/search/action navigation; use Owl for composed views and guided decisions. Prove store context and company switching through native actions. No SPA router or webclient patch to imitate a mockup. Authorization covers records, counters, suggestions, direct RPC and diagnostics.

Management metrics need source, date/timezone, store, currency, exclusions, freshness and an identical drill-down population. Imported order value is not net sales/profit/cash. No fabricated zero or full-store completeness claim when data is unavailable/incomplete. Management reporting remains required while visuals are parked.

Demonstrate the whole path and relevant failure/recovery, with local/Shopify readback. Check keyboard/focus, announcements, empty/loading/stale/partial states, responsive/RTL and contrast on the actual native candidate. Report prototype, component, native tour, live journey and human usability evidence separately; model approval does not replace human UAT.
