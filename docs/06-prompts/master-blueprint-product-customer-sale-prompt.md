# Archived Sprint Prompt — Master Blueprint Sprint B: Product, Customer, and Sale/Order Domain Blueprint

> Archived verbatim per the sprint's own instruction ("Archive this
> prompt"). Executed 2026-07-03 on branch
> `claude/master-blueprint-sprint-b-7zrvji` (harness-assigned; the
> prompt's preferred name was
> `architecture/master-blueprint-product-customer-sale` — discrepancy
> recorded in `../01-research/research-handoff.md`).

---

```
You are Sonnet 5 working in repository:

AdamsOdoo/Adams

You are the GitHub execution worker.
ChatGPT is the strategic control room and final decision-maker.

Sprint:
Master Blueprint Sprint B — Product, Customer, and Sale/Order Domain Blueprint

This is documentation-only.
Do not write code.
Do not create Odoo modules.
Do not create Python, XML, CSV, security, manifest, test, or workflow files.
Do not start implementation.
Do not merge.

Current required base:
Latest `Shopify-connector` after PR #71 merge.

Expected PR #71 merge commit:
283a38f26ef90fca2a53c18ff6faf4775da4a2ee

Before editing, confirm:

1. `Shopify-connector` contains PR #71 merge commit:
   283a38f26ef90fca2a53c18ff6faf4775da4a2ee
2. PR #71 is merged into `Shopify-connector`.
3. DEC-003 through DEC-013 are all Accepted by ChatGPT.
4. AR-002 through AR-010 are all Accepted.
5. Master Blueprint Part A is accepted.
6. Master Blueprint Part B is not started.
7. MBQ-23 through MBQ-31 exist and are routed to Sprint B.
8. MBQ-53 remains open and still blocks operator-facing screen implementation.
9. Implementation is still blocked.

If any check fails, stop and report the exact blocker.

Create a new branch from latest `Shopify-connector`.

Preferred branch name:
architecture/master-blueprint-product-customer-sale

If the harness assigns a different `claude/...` branch, use it and record the discrepancy in the handoff.

Objective:
Create Master Blueprint Sprint B covering the Phase 1 product, customer, and sale/order domain blueprints.

This sprint must convert accepted DEC-003, DEC-006, DEC-007, DEC-012, and the accepted core substrate DEC-013 into implementation-ready domain blueprint documentation, without writing code.

The output must be detailed enough for later implementation planning, but must not become implementation.

Scope:

A. Product domain blueprint

Cover:

1. Product import from Shopify to Odoo.
2. Product export from Odoo to Shopify.
3. Product update flow after first binding.
4. Variant handling and option handling.
5. SKU/internal reference and barcode matching.
6. Product template vs product variant identity.
7. Product binding responsibility.
8. Duplicate-prevention preview.
9. Draft-first export safety.
10. Destructive-write preview / guard.
11. Source-of-truth choices:
    - product attributes / variant structure
    - product title/name
    - SKU/barcode
    - price / compare-at price
    - image/media basics
12. Product media/image basic handling, without advanced media strategy.
13. Product price / compare-at-price handling, without Shopify Markets pricing.
14. Product publish/draft/status safety.
15. Product preview/review states, but not full UI wireframes.
16. Product job types that later implementation planning will need.
17. Product logs, errors, retry, and manual-review touchpoints through DEC-013 core substrate.
18. Product-specific open questions, especially MBQ-23, MBQ-24, MBQ-25.

Respect:

- Controlled import/export/update is accepted MVP scope.
- No autonomous bidirectional catalog conflict ownership.
- No name-only matching.
- No blind create.
- No destructive write without preview.
- No Shopify Markets, metafields, SEO, taxonomy, subscriptions, gift cards, POS, or B2B in Phase 1.
- No exact GraphQL mutation finalization unless official-doc evidence is verified and cited.
- If mutation behaviour is unverified, keep it as MBQ, do not assert.

B. Customer domain blueprint

Cover:

1. Customer import from Shopify to Odoo.
2. Customer matching priority:
   existing binding → email/customer key → manual review.
3. No customer export in Phase 1 unless explicitly re-decided later.
4. No name-only automatic matching.
5. Handling missing email / no-PII Shopify customer data.
6. Default customer fallback posture as an open/decision item if not resolved.
7. Customer binding responsibility and relation to `sale` module.
8. Duplicate-prevention preview for customers.
9. Customer privacy and protected-data minimization.
10. Customer-specific logs/errors/manual-review states through DEC-013 core substrate.
11. Customer-specific job types that later implementation planning will need.
12. Customer-specific open questions, especially MBQ-29 and MBQ-31.

Respect:

- Do not invent PII.
- Do not create unsafe partner duplicates.
- Do not export customers in Phase 1.
- Do not decide exact Odoo partner field mapping unless already evidenced.
- Keep exact model/field names for implementation planning.

C. Sale/order domain blueprint

Cover:

1. Shopify order import into Odoo sale orders.
2. Shopify order binding responsibility.
3. Order identity and duplicate prevention.
4. Order line mapping from Shopify line items to Odoo sale order lines.
5. Product binding prerequisite / fallback handling for unmatched products.
6. Customer binding/import prerequisite / fallback handling for unmatched customers.
7. Financial-evidence capture from Shopify order data.
8. Total-check guard / reconciliation posture.
9. Tax/shipping/discount/payment evidence handling as evidence, not accounting automation.
10. Gateway → Odoo journal mapping as classification/routing input only, not accounting automation.
11. No invoice/payment posting automation in Phase 1 unless later DEC explicitly changes it.
12. Handling order edits/cancellations/refunds as deferred unless needed for safe import posture.
13. Manual review triggers:
    - unmatched product
    - unmatched customer
    - duplicate order risk
    - total mismatch
    - unsupported data shape
    - missing mapping
14. Order-import operator touchpoints:
    - decide whether the core error center is enough
    - or whether a dedicated order-import review flow is needed
    - resolve or re-route MBQ-26
15. Order-specific job types that later implementation planning will need.
16. Order-specific logs/errors/retry/manual-review states through DEC-013 core substrate.
17. Order-specific open questions, especially MBQ-26, MBQ-27, MBQ-28, MBQ-30.

Respect:

- Order import must be conservative and auditable.
- Total-check guard is mandatory and permanent.
- Do not invent Odoo accounting automation.
- Do not decide exact tax engine implementation unless verified.
- Do not write invoices/payments/payouts/refunds into scope.
- Do not start accounting, refund, payout, or inventory/fulfillment blueprinting.

D. Cross-domain sequencing

Define safe dependency and flow sequencing:

1. Product binding availability before order import line creation.
2. Customer binding/import before order customer assignment.
3. Order import preview or validation before create.
4. Manual review if product/customer/mapping is missing.
5. Reconciliation backstop through accepted core substrate.
6. How product/customer/order domain jobs use the core job/log/error/binding substrate.
7. Which actions are manual, scheduled, webhook-driven, or reconciliation-driven.

E. Product/customer/sale domain open-question handling

Update the central open-questions register carefully.

Existing Sprint B rows:

- MBQ-23 — variant-write mutation strategy
- MBQ-24 — productSet delete-on-omit and media behaviour
- MBQ-25 — Shopify draft/publish mechanism
- MBQ-26 — order-import operator touchpoints
- MBQ-27 — Shopify-computed tax representation in Odoo sale order
- MBQ-28 — Domain 9 draft-artifact guard
- MBQ-29 — default-customer fallback for no-PII Shopify plans
- MBQ-30 — gateway → Odoo journal mapping surface
- MBQ-31 — final customer match-key set

Rules:

- Resolve a row only if this sprint actually decides it with accepted DEC-backed reasoning or cited official evidence.
- If official Shopify/Odoo docs are needed and not checked, do not resolve the row.
- You may mark a row partially resolved if the blueprint direction is now clear but exact implementation detail remains open.
- Do not delete any MBQ row.
- Add new MBQ rows if the sprint discovers necessary unresolved items.
- Keep MBQ-53 open; this sprint may describe operator touchpoints but must not create screen-level wireframes or final UI design.

Required outputs / file changes:

1. Create:
docs/03-architecture/master-blueprint-product-customer-sale.md

Content structure required:

- Status:
  Proposed for ChatGPT review
  Documentation only
  No implementation authorization

- Scope and non-goals
- Relation to accepted decisions DEC-003/006/007/012/013
- Product domain blueprint
- Customer domain blueprint
- Sale/order domain blueprint
- Cross-domain sequencing
- Job/log/error/retry usage through core
- Binding/dedup usage through core
- Manual review and operator touchpoints
- Source-of-truth decisions and open questions
- Error classes / retry classes mapping at blueprint level
- Open questions resolved / partially resolved / carried forward
- What this does not decide
- Implementation remains blocked
- Next recommended sprint after ChatGPT review:
  Master Blueprint Sprint C — Inventory and Fulfillment Domain Blueprint

2. Update:
docs/03-architecture/master-blueprint.md

Required meaning:

- Part B now links to `master-blueprint-product-customer-sale.md`.
- Part B status becomes Proposed for ChatGPT review.
- Part A remains Accepted via DEC-013.
- Parts C/D/E remain Not started.
- Implementation remains blocked.
- UI/UX Screen Design Blueprint still required before operator-facing screen implementation.
- Do not change accepted DEC-013 substance.

3. Update:
docs/03-architecture/master-blueprint-open-questions.md

Required meaning:

- Update MBQ-23 through MBQ-31 only where justified by this sprint.
- Add new MBQ rows if needed, using the next available number after MBQ-54.
- Do not delete rows.
- Do not mark MBQ-04, MBQ-08, MBQ-53, or MBQ-54 resolved.
- Maintain the register status accepted-through-DEC-013.
- Add a short note that Sprint B has proposed updates for product/customer/order rows, pending DEC-014 acceptance.

4. Create:
docs/04-decisions/DEC-014-master-blueprint-product-customer-sale.md

Required meaning:

- Status:
  Proposed for ChatGPT review
- Date:
  2026-07-03
- Proposes accepting Master Blueprint Sprint B.
- Records accepted context:
  DEC-003 through DEC-013 accepted.
  AR-002 through AR-010 accepted.
  PR #71 merged into `Shopify-connector`, merge commit:
  283a38f26ef90fca2a53c18ff6faf4775da4a2ee
- Does not authorize implementation.
- Does not start Sprint C.
- Does not start UI/UX Screen Design Blueprint.
- Does not start implementation.
- Summarize proposed product/customer/sale-order blueprint decisions.
- List open questions carried forward.
- Make clear which MBQ rows are proposed as resolved, partially resolved, or still open.
- Next recommended sprint:
  Master Blueprint Sprint C — Inventory and Fulfillment Domain Blueprint, after ChatGPT/Fable review and any required revision/acceptance process.

5. Update:
docs/04-decisions/README.md

Required meaning:

- Add DEC-014 as proposed / not yet accepted.
- Do not move it to accepted.
- Do not change DEC-003 through DEC-013 statuses.

6. Update:
docs/05-qa/architecture-review-log.md

Required meaning:

- Add AR-011:
  Master Blueprint Product, Customer, and Sale/Order Domain Blueprint
- Status:
  Proposed for ChatGPT review
- Related DEC:
  DEC-014
- No implementation authorization.
- AR-002 through AR-010 remain accepted and untouched.

7. Update:
docs/01-research/research-handoff.md

Add compact handoff entry at the top.

Required meaning:

- PR #71 merged into `Shopify-connector`.
- Merge commit:
  283a38f26ef90fca2a53c18ff6faf4775da4a2ee
- DEC-013 / AR-010 accepted.
- Sprint B started as documentation-only.
- Created proposed DEC-014 and proposed AR-011.
- Created product/customer/sale-order Master Blueprint document.
- Updated open questions register for Sprint B rows.
- No code files changed.
- No implementation authorized.
- Sprint C not started.
- UI/UX Screen Design Blueprint not started.
- Next:
  ChatGPT/Fable review of DEC-014 / AR-011.

Also append a compact Sprint checkpoint log note at the bottom.

8. Create:
docs/06-prompts/master-blueprint-product-customer-sale-prompt.md

Archive this prompt.

Allowed files only:

- docs/03-architecture/master-blueprint-product-customer-sale.md
- docs/03-architecture/master-blueprint.md
- docs/03-architecture/master-blueprint-open-questions.md
- docs/04-decisions/DEC-014-master-blueprint-product-customer-sale.md
- docs/04-decisions/README.md
- docs/05-qa/architecture-review-log.md
- docs/01-research/research-handoff.md
- docs/06-prompts/master-blueprint-product-customer-sale-prompt.md

Do not modify anything else.

Forbidden:

- Do not modify DEC-003 through DEC-013.
- Do not modify Master Blueprint Part A except through the index file listed above.
- Do not create Sprint C files.
- Do not create UI/UX Screen Design Blueprint files.
- Do not create implementation plan files.
- Do not modify code files.
- Do not create Odoo module files.
- Do not create Python files.
- Do not create XML files.
- Do not create CSV/security files.
- Do not create manifests.
- Do not create tests.
- Do not merge.

Evidence and citation rules:

- Use existing accepted DEC/AR/MBQ documents as the main source.
- Do not invent Shopify or Odoo API behaviour.
- For Shopify mutation behaviour, draft/publish mechanism, media behaviour, tax data shape, or Odoo sale-order/tax mechanics:
  - Use official Shopify/Odoo documentation only if you verify it.
  - Cite the official source in the relevant document.
  - If not verified, leave the item as an open MBQ.
- Do not rely on competitor docs for technical platform behaviour.
- Do not perform broad research. Only targeted official-doc checks if needed for Sprint B decisions.

Validation before PR:

Confirm:

1. Branch is based on latest `Shopify-connector` containing PR #71 merge commit:
   283a38f26ef90fca2a53c18ff6faf4775da4a2ee
2. DEC-003 through DEC-013 remain accepted and were not edited.
3. AR-002 through AR-010 remain accepted.
4. DEC-014 exists and is Proposed for ChatGPT review.
5. AR-011 exists and is Proposed for ChatGPT review.
6. `master-blueprint-product-customer-sale.md` exists.
7. `master-blueprint.md` links Part B and marks it Proposed for ChatGPT review.
8. Parts C/D/E remain Not started.
9. MBQ-23 through MBQ-31 are handled clearly:
   resolved / partially resolved / carried forward / unchanged.
10. MBQ-04 remains open.
11. MBQ-08 remains open.
12. MBQ-53 remains open.
13. MBQ-54 remains open.
14. No code files changed.
15. No product/customer/sale/inventory/fulfillment implementation started.
16. Sprint C not started.
17. UI/UX Screen Design Blueprint not started.
18. Implementation remains blocked.
19. Handoff updated.
20. Prompt archived.

Commit:

Use one commit:
docs: propose master blueprint product customer sale

Open one draft PR into:
Shopify-connector

PR title:
Propose Master Blueprint product customer sale

PR body:

Purpose:
Create Master Blueprint Sprint B for Product, Customer, and Sale/Order domain blueprinting after DEC-013 acceptance.

Outputs:
- Product/customer/sale-order Master Blueprint document
- Proposed DEC-014
- Proposed AR-011
- Master Blueprint index updated
- Open questions register updated for MBQ-23 through MBQ-31
- Handoff updated
- Prompt archived

Explicit non-goals:
- No connector code
- No Odoo model/view/security implementation
- No implementation authorization
- No DEC-003 through DEC-013 edit
- No Sprint C
- No UI/UX Screen Design Blueprint
- No product/customer/sale/inventory/fulfillment implementation
- No merge

Quality checks:
- PR targets Shopify-connector
- PR based on latest Shopify-connector
- PR #71 merge confirmed first
- DEC-014 status is Proposed for ChatGPT review
- AR-011 proposed only, not accepted
- DEC-003 through DEC-013 not edited
- No code files changed
- Implementation remains blocked
- Sprint C not started
- UI/UX Screen Design Blueprint not started
- Handoff updated
- Prompt archived

Final response only:

Master Blueprint Sprint B completed.

Branch:
<actual branch>

Draft PR:
<PR URL>

PR target:
Shopify-connector

Commit:
<hash> docs: propose master blueprint product customer sale

Files changed:
- <list>

DEC-014 status:
Proposed for ChatGPT review

AR-011 accepted:
No

AR-011 status:
Proposed for ChatGPT review

Master Blueprint Part B created:
Yes

MBQ-23 through MBQ-31 handled:
Yes

MBQ-04 remains open:
Yes

MBQ-08 remains open:
Yes

MBQ-53 remains open:
Yes

MBQ-54 remains open:
Yes

DEC-003/004/005/006/007/008/009/010/011/012/013 edited:
No

Code files changed:
No

Implementation authorized:
No

Sprint C started:
No

UI/UX Screen Design Blueprint started:
No

Main modified:
No

Plain dev modified:
No

Stopped as instructed:
Yes
```
