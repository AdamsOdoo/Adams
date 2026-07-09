# Task 010 — Product Import / Variant Binding: Final Implementation Prompt

DO NOT USE THIS PROMPT UNTIL CHATGPT ACCEPTS THE TASK 010 GATE-OPENING PROPOSAL AND EXPLICITLY ISSUES THIS PROMPT IN CHAT.

> **Status: Accepted final prompt / Not issued.** Accepted by ChatGPT via
> PR #137 control-room review, GitHub comment ID `4926437491`. This
> document converts the accepted MBQ-55 product-template/product-variant
> naming/schema proposal
> ([`mbq-55-product-binding-naming-schema-proposal.md`](./mbq-55-product-binding-naming-schema-proposal.md),
> Accepted by ChatGPT, control-room comment ID `4924917266`, PR #136) and
> the accepted product-domain gate criteria
> ([`product-domain-gate-criteria-proposal.md`](./product-domain-gate-criteria-proposal.md),
> Accepted as criteria only, same PR #136) into a copy-paste-ready
> `CLAUDE.md` §9 implementation prompt for Task 010, per
> [`task-010-product-import-proposed.md`](./task-010-product-import-proposed.md).
> **This document's content is now accepted, fixing it as binding — it is
> still NOT issued.** Acceptance authorizes the product-domain
> implementation gate to open for exactly one future Task 010
> implementation session (see the companion
> [`task-010-product-import-gate-opening-proposal.md`](./task-010-product-import-gate-opening-proposal.md)
> §1/§9), effective once PR #137 merges into `Shopify-connector` — it does
> **not**, by itself, authorize Claude to write any Task 010 code now, and
> it does **not** issue this prompt. **Claude must not use this prompt
> until ChatGPT explicitly pastes/issues it, verbatim, into a new Claude
> Code session, as its own later chat turn, after PR #137 merges** — the
> top warning above is unweakened by this acceptance. This mirrors the
> draft-then-finalize precedent already used for Task 004
> ([`task-004-final-implementation-prompt.md`](./task-004-final-implementation-prompt.md))
> and Task 006C
> ([`task-006c-sync-engine-skeleton-final-prompt.md`](./task-006c-sync-engine-skeleton-final-prompt.md)).

> **Revision note (2026-07-09, PR #137 control-room review, GitHub comment
> ID `4925370944`) — REVISE before merge, addressed in this revision.**
> Five precision gaps were identified and are fixed in this revision: (1)
> §3's manifest `depends` now includes Odoo's own `product` module
> explicitly, and the "two security files" wording is corrected to "one"
> (only `ir.model.access.csv` is allowed); (2) §7.2's imported snapshot
> fields now name exact Odoo field types (`fields.Text`/`fields.Float`)
> instead of "Char or Text"/"Monetary or Float", and explicitly forbid a
> `Monetary`/currency field; (3) §7.1/§7.2 now state each concrete binding
> model's `_name` explicitly, not implied through `_inherit` alone; (4) §9
> now requires a third seam extension — a `_domain_flag_for_job_type()`
> override mapping `product_import_sync` to the already-existing
> `product_domain_enabled` flag on `shopify.connector.store.settings`
> (confirmed directly this revision), so the new job type is gated by the
> same product-domain-enablement mechanism the core `write()` gate already
> implements, instead of silently bypassing it; (5) §10 now requires tests
> proving that gating (false / missing-settings / true cases) and
> `core_dispatch_selftest` preservation. This revision does not change any
> other section's substance, does not open any gate, and does not
> authorize any code.

> **Acceptance note (2026-07-09, PR #137 control-room review, GitHub
> comment ID `4926437491`) — Content accepted.** ChatGPT confirmed all
> five precision fixes above and accepted this document's content,
> **fixing it as binding**. This acceptance does **not** issue the prompt
> and does **not** itself authorize any Task 010 code — see the companion
> gate-opening proposal's own §1/§9 for the exact authorization boundary
> (gate opens for exactly one future Task 010 session once PR #137
> merges; the prompt is issued only by a later, separate ChatGPT chat
> turn). This note updates only this document's Status; §1–§14 and the
> draft prompt text below are otherwise unchanged by this acceptance.

## How this document will be used

1. ✅ **Satisfied** — ChatGPT reviewed and accepted
   [`task-010-product-import-gate-opening-proposal.md`](./task-010-product-import-gate-opening-proposal.md)
   (PR #137 control-room review, comment ID `4926437491`).
2. ✅ **Satisfied** — ChatGPT performed the distinct, explicit
   product-domain gate-opening act named in that proposal and in
   [`product-domain-gate-criteria-proposal.md`](./product-domain-gate-criteria-proposal.md)
   §4, via that same acceptance — the gate opens for exactly one future
   Task 010 implementation session, effective once condition 3 below is
   also met.
3. **Not yet satisfied** — PR #137 (carrying this acceptance) has not yet
   merged into `Shopify-connector`.
4. **Not yet satisfied** — before pasting the prompt below, the issuing
   session verifies the base-commit placeholder in the prompt text is
   still the actual current tip of `Shopify-connector` (see "Current base
   placeholder" below) — if `Shopify-connector` has moved since this
   document was drafted, the issuing session must re-verify every cited
   accepted document/decision is still unchanged before pasting, not
   assume it.
5. **Not yet satisfied** — ChatGPT explicitly pastes the exact finalized
   prompt text below into a **new** Claude Code session, as its own chat
   turn.
6. **Not yet satisfied** — the implementing session stops at its own
   scoped boundary (`CLAUDE.md` §6) — it must not chain into Task
   011/012/013/014, Task 015, any UI work, or any other next-feature
   work.

**Nothing in this document authorizes Claude to begin implementation now or
at any point before all six conditions above are met.**

---

## 1. Session objective

Implement **Product Task 010: Shopify product import and variant binding
only** — Shopify → Odoo, read-only against Shopify. Establish the
product/variant identity foundation (two concrete binding models) that
later domains (customer, order, inventory, fulfillment) resolve *through*,
per the already-accepted
[`mbq-55-product-binding-naming-schema-proposal.md`](./mbq-55-product-binding-naming-schema-proposal.md)
naming/schema and
[`task-010-product-import-proposed.md`](./task-010-product-import-proposed.md)
scope. **No product export, update, or write back to Shopify of any kind.**

## 2. Current base placeholder

Use latest known base: `Shopify-connector` at commit
`c171d8f9b404f0b9bc066ee6fbef811086f5d0fc` (PR #136 merge commit, confirmed
via `git rev-parse`/`pull_request_read` this session, 2026-07-09).

**The future implementation session must verify this is still the actual
tip of `Shopify-connector` before writing any code.** If `Shopify-connector`
has advanced past this commit, the implementing session must:

- Confirm no PR merged since this commit has touched
  `addons/shopify_connector_core/**`, the accepted MBQ-55 schema, or the
  accepted product-domain gate criteria in a way that would change any
  fact this prompt relies on.
- If it has, STOP and report the discrepancy instead of silently
  proceeding on a stale base.

## 3. Allowed files

**Be exact.** The future implementation session may create or modify only:

- `addons/shopify_connector_product/__init__.py` (NEW)
- `addons/shopify_connector_product/__manifest__.py` (NEW — `depends:
  ['shopify_connector_core', 'product']`, per DEC-008's one-directional
  dependency DAG plus an explicit Odoo `product` dependency — confirmed
  directly this session that `shopify_connector_core` itself depends only
  on `base`, and this task's two binding models link to `product.template`
  and `product.product`, so `shopify_connector_product` must declare
  `product` as its own explicit dependency rather than relying on it
  transitively; `installable: True`; `application: False`; no `data` entry
  other than the one security file below, `security/ir.model.access.csv`)
- `addons/shopify_connector_product/models/__init__.py` (NEW)
- `addons/shopify_connector_product/models/shopify_connector_product_template_binding.py`
  (NEW) — the `shopify.connector.product.template.binding` model, §7.1
  below.
- `addons/shopify_connector_product/models/shopify_connector_product_variant_binding.py`
  (NEW) — the `shopify.connector.product.variant.binding` model, §7.2
  below.
- `addons/shopify_connector_product/models/shopify_connector_product_importer.py`
  (NEW) — the importer/matching service (§5, §9): a stateless
  `AbstractModel` (no table, no new ACL row) mirroring
  `shopify_connector_readiness_check.py`'s and
  `shopify_connector_job_dispatch.py`'s own `AbstractModel` pattern
  (confirmed directly this session), **plus** the three narrow
  extension-seam classes named in §9 (`_inherit =
  'shopify.connector.job'` for the `job_type` `selection_add`; a second
  `_inherit = 'shopify.connector.job'` extension, or the same class, for
  the `_domain_flag_for_job_type()` override mapping `product_import_sync`
  to `product_domain_enabled`; and `_inherit =
  'shopify.connector.job.dispatch'` for the `_get_handlers()` override) —
  this is the **one** allowed file where those three seam extensions may
  live; do not add a separate file for them.
- `addons/shopify_connector_product/security/ir.model.access.csv` (NEW) —
  access rows for the two concrete binding models only, reusing the four
  **existing** `shopify_connector_core` groups
  (`group_shopify_connector_auditor`/`_operator`/`_reviewer`/`_admin`,
  confirmed present this session in
  `shopify_connector_security.xml`/`ir.model.access.csv`) — **no new
  group.** Row naming mirrors the existing core convention exactly, e.g.
  `access_shopify_connector_product_template_binding_operator`. No
  `security/*.xml` file — no new group, category, or privilege is needed.
- `addons/shopify_connector_product/tests/__init__.py` (NEW)
- `addons/shopify_connector_product/tests/test_product_template_binding.py`
  (NEW) — §10.
- `addons/shopify_connector_product/tests/test_product_variant_binding.py`
  (NEW) — §10.
- `addons/shopify_connector_product/tests/test_product_import_matching.py`
  (NEW) — §10.
- `addons/shopify_connector_product/tests/test_product_duplicate_prevention.py`
  (NEW) — §10.
- `docs/01-research/research-handoff.md` — the mandatory handoff update
  only.
- `docs/05-qa/task-010-product-import-validation-results.md` (NEW) — the
  validation-results record, mirroring
  `task-006c-sync-engine-skeleton-validation-results.md`'s pattern.
- `docs/05-qa/architecture-review-log.md` — **only** to append the
  implementation-closure AR row (mirroring AR-032's Task-006C-closure
  pattern) — no other row may be edited.

**If the implementing session believes any file outside this list is
genuinely needed (e.g. a core extension-seam file, per §9), it must not add
it silently — it must STOP and mark it as a required ChatGPT decision in
its PR description, per this prompt's own §9 boundary below.**

## 4. Forbidden files

Explicitly forbidden, no exceptions unless ChatGPT explicitly authorizes in
a separate act:

- Any file under `addons/shopify_connector_core/**` **except** the three
  narrow, already-proven extension-seam edits named in §9 below (a
  `selection_add` on `shopify.connector.job`'s `job_type` field; a
  `_domain_flag_for_job_type()` override on `shopify.connector.job`
  mapping `product_import_sync` to `product_domain_enabled`; and a
  `_get_handlers()` override on `shopify.connector.job.dispatch`) — no
  core file may be touched at all; all three edits happen exclusively
  inside the already-listed `shopify_connector_product_importer.py` (§3,
  §9), using classic Odoo inheritance, never by editing
  `shopify_connector_core`'s own files directly.
- Any file under `shopify_connector_sale`, `shopify_connector_customer`,
  `shopify_connector_inventory`, `shopify_connector_fulfillment`, or any
  other domain module, including creation of any such module.
- Any order/customer/inventory/fulfillment/accounting/refund/payout/
  multi-store file or logic of any kind.
- Any UI/view/menu/action/wizard/controller file of any kind.
- Any webhook receiver/controller file of any kind.
- Any OAuth/token-acquisition file of any kind.
- Any CI/workflow file, Dockerfile, `requirements*.txt`, or migration file.
- Any product/variant **export, update, or write-mutation** code path,
  including any construction of `productSet`, `productVariantsBulkUpdate`,
  `productVariantsBulkCreate`, or any other Shopify mutation — Task 010 is
  **import-only**; zero mutation calls anywhere in the diff.
- `addons/adams_base/**` — never touched.
- Any file not explicitly named in §3 above.

## 5. Scope

- Create the `shopify_connector_product` addon (manifest, init, models,
  security, tests only — see §3).
- Two concrete binding models, both extending
  `shopify.connector.binding.mixin` (confirmed `AbstractModel`, no table
  of its own, this session):
  - `shopify.connector.product.template.binding` — binds Shopify `Product`
    to Odoo `product.template`.
  - `shopify.connector.product.variant.binding` — binds Shopify
    `ProductVariant` to Odoo `product.product`, with a **required**
    `product_template_binding_id` (Many2one →
    `shopify.connector.product.template.binding`) — the variant binding
    never stands in for, and is never replaced by, the template binding
    (DEC-006 §A.7).
- A read-only importer/matching service
  (`shopify_connector_product_importer.py`) that, given a Shopify
  product+variant payload (real via the existing Task 003 API client, or
  fake/stub in tests), maps/creates/binds `product.template` and
  `product.product` records using the match-key priority: **existing
  binding → SKU/internal reference (`default_code`) → barcode → manual
  review** (DEC-006; DEC-003; RA-006 — name is advisory only, never
  automatic).
- **No blind create.** Every automated import creation is gated by the
  MBQ-59 two-tier gate (eligibility, then match-quality) per DEC-014 point
  H, using the exact conservative MVP thresholds fixed in §8 below.
- Duplicate-risk / ambiguous-match conditions route to
  `blocked_manual_review` with the matching `manual_review_subreason`
  (`ambiguous_match`, `binding_conflict`, or `duplicate_risk`, per the
  already-accepted, fixed six-value vocabulary confirmed this session in
  `shopify_connector_job.py`) — never a silent skip, never a silent
  create.
- **No Shopify write of any kind.** The importer only ever issues read
  (query) calls through the existing, already-gated Task 003 API client —
  it never constructs a mutation.

## 6. Explicit non-scope

Must exclude, with zero code touching any of the following:

- Product/variant **export, update**, or any write back to Shopify.
- `productSet`.
- `productVariantsBulkUpdate`.
- `productVariantsBulkCreate`.
- Any other Shopify mutation call of any kind.
- Image/media sync beyond the accepted read-only snapshot fields (§7.1.D,
  §7.2.D) — no multi-image, alt-text, ordering, or per-image GID modeling.
- Inventory quantity of any kind.
- Fulfillment of any kind.
- Customer or order data/logic of any kind.
- Setup wizard or any operator-facing UI/view/menu/action/wizard.
- Webhook receiver/controller of any kind.
- OAuth/token-acquisition code of any kind.
- Lite/Full packaging of any kind.
- Live Shopify validation (VAL-B2) — tests use a fake/stub client only;
  this task does not attempt or claim a live Shopify call.
- Multi-server/concurrent-worker concurrency validation — this task
  inherits the existing, already-merged Task 006C claim/dispatch mechanism
  unmodified and unproven-live; it does not add to or attempt to close
  SRR-03/SRR-04/SRR-09.

## 7. Product binding schema

Accepted per
[`mbq-55-product-binding-naming-schema-proposal.md`](./mbq-55-product-binding-naming-schema-proposal.md)
§5–§8 (Accepted by ChatGPT, PR #136). **Odoo 19 requirement, confirmed
directly this session** (`shopify_connector_job.py`,
`shopify_connector_binding_mixin.py` read this session; the accepted
proposal additionally cites `shopify_connector_store.py`/
`shopify_connector_location.py`): use `models.Constraint(...)`, **never**
the deprecated `_sql_constraints` dict.

### 7.1 `shopify.connector.product.template.binding`

Class `ShopifyConnectorProductTemplateBinding`, declaring **both**
`_name = 'shopify.connector.product.template.binding'` **and**
`_inherit = 'shopify.connector.binding.mixin'` explicitly (fixed on
control-room review, comment ID `4925370944` — do not leave `_name`
implied through `_inherit` alone; this is a **new concrete model**
extending an `AbstractModel` contract, not a re-opening of an existing
model, so both attributes must be stated).

- **Inherited from the mixin** (confirmed field set, read directly this
  session): `store_id` (Many2one → `shopify.connector.store`, required,
  index, `ondelete='restrict'`), `shopify_gid` (Char, required, index,
  readonly — holds the Shopify **Product** GID), `status` (Selection
  `active`/`stale`/`manually_overridden`/`review`, required, index,
  default `active`), `match_key` (Selection — only
  `existing_binding`/`sku_reference`/`barcode`/`manual` apply at template
  level; `email` is never populated), `matched_by_uid`, `matched_at`,
  `override_uid`, `override_at`, `override_previous_candidate`.
- **New required relational field:** `product_template_id` (Many2one →
  `product.template`, required, index, `ondelete='restrict'`).
- **Imported snapshot fields (readonly, informational only — never a
  second source of truth for matching):** `shopify_title` (Char),
  `shopify_status` (Selection `active`/`archived`/`draft`/`unlisted`),
  `shopify_primary_image_url` (Char), `shopify_last_imported_at`
  (Datetime).
- **Constraints (`models.Constraint`):** `UNIQUE(store_id, shopify_gid)`;
  `UNIQUE(store_id, product_template_id)`.
- **Explicitly out of scope:** any price field (variant-level only, see
  §7.2), any inventory-quantity field, any fulfillment field, any
  customer/order reference, any write/export-tracking field. **Explicitly
  deferred:** richer media modeling; any Odoo `active`/archive side effect
  driven by `shopify_status` (Task 010 is import-only — no write side
  effect of any kind).

### 7.2 `shopify.connector.product.variant.binding`

Class `ShopifyConnectorProductVariantBinding`, declaring **both**
`_name = 'shopify.connector.product.variant.binding'` **and**
`_inherit = 'shopify.connector.binding.mixin'` explicitly (same fix,
same reason, as §7.1).

- **Inherited from the mixin:** identical set to §7.1 — here `shopify_gid`
  holds the Shopify **ProductVariant** GID, independent of, and never
  substituted for, the parent Product's GID (DEC-006 §A.7).
- **New required relational fields:** `product_variant_id` (Many2one →
  `product.product`, required, index, `ondelete='restrict'`);
  `product_template_binding_id` (Many2one →
  `shopify.connector.product.template.binding`, **required**, index,
  `ondelete='restrict'`).
- **Imported snapshot fields (readonly, exact types — fixed on
  control-room review, comment ID `4925370944`):** `shopify_option_values`
  (`fields.Text`), `shopify_price_snapshot` (`fields.Float` — read-only
  snapshot, no write-back, no `price_source_of_truth` enforcement — that
  belongs to future Task 015; **not** `Monetary` — no currency field is
  authorized by this prompt, see below), `shopify_compare_at_price_snapshot`
  (`fields.Float`, same posture), `shopify_last_imported_at` (`fields.Datetime`),
  `shopify_primary_image_url` (`fields.Char`). **Do not add a
  `currency_id`/`Monetary` field of any kind** — a `Monetary` field
  requires a companion currency field, and no currency field is
  authorized by this prompt; using `fields.Float` avoids inventing one
  silently.
- **SKU/barcode are deliberately not duplicated as new fields.** Matching
  reads the incoming Shopify SKU/barcode and compares against
  `product.product.default_code`/`product.product.barcode` directly
  (reached via `product_variant_id`) — no shadow copy.
- **Constraints (`models.Constraint`):** `UNIQUE(store_id, shopify_gid)`;
  `UNIQUE(store_id, product_variant_id)`. `product_template_binding_id` is
  indexed, **not** unique (many variants legitimately share one template
  binding).
- **Explicitly out of scope:** inventory-quantity, fulfillment,
  customer/order reference, write/export-tracking fields. **Explicitly
  deferred:** richer media modeling; variant-level publish/draft status
  (not applicable — `status` is a Product-level Shopify field, not
  ProductVariant-level).

## 8. Dedup thresholds / duplicate prevention (fixed as an in-task decision)

Per DEC-014 point H (accepted, blueprint-policy level) and
`mbq-55-product-binding-naming-schema-proposal.md` §9, the MBQ-59
eligibility-check/match-confidence residual is fixed here, for Task 010
only, as follows — **this does not reopen or contradict DEC-014; it
converts DEC-014's already-accepted two-tier gate into exact MVP
thresholds:**

- **Existing binding found** (`(store_id, shopify_gid)` already bound) →
  bind to the existing Odoo record; `match_key = 'existing_binding'`.
- **No existing binding. Exactly one of SKU (`default_code`) or barcode
  yields exactly one candidate** `product.product`/`product.template` in
  the same store scope → **confident match**, bind; `match_key =
  'sku_reference'` or `'barcode'` per whichever matched (SKU checked
  before barcode, per the accepted priority).
- **No existing binding, no SKU/barcode candidate found at all, but the
  incoming Shopify record carries a non-empty SKU or barcode value** →
  **confident no-match** — for the **automated** path (webhook/scheduled/
  reconciliation), this is the one case DEC-014 point H's "confident
  no-match creation candidate" explicitly allows to proceed to create,
  gated by the eligibility tier (setup complete; domain enabled) already
  implemented at enqueue/execution time. For the **interactive/batch**
  path, this still requires the existing blocking preview before the
  operator confirms (DEC-006; DEC-003) — never a silent create either way.
- **More than one SKU/barcode candidate** (ambiguous) → `status =
  'review'`, `manual_review_subreason = 'ambiguous_match'`,
  `blocked_manual_review` on the job — **never** an automated create.
- **SKU and barcode are both empty/absent on the incoming record** (a
  blind create — no identifier was actually checked) → `status =
  'review'`, `manual_review_subreason = 'duplicate_risk'`,
  `blocked_manual_review` on the job for the automated path — **never**
  an automated create. Manual/interactive import may still proceed only
  through the existing blocking-preview path with the operator explicitly
  confirming a matchless create.
- **No feature flag, setting, or configuration combination may bypass any
  condition above** — Part A §I.5's no-bypass rule (confirmed via DEC-013)
  applies to this gate by construction, restated here, not weakened.
- This fixes MBQ-59's residual **for Task 010's own narrow scope only** —
  it does not resolve MBQ-59 project-wide, and does not bind any later
  domain task's own dedup-threshold decision.

## 9. Job/sync-engine usage

**Strict recommendation: register exactly one product job type via three
already-proven extension seams — do not build any new cron mechanism.**
Revised on control-room review (comment ID `4925370944`) to add the
required product-domain enablement gating seam (the third bullet below),
which the original draft omitted.

All three seam extensions below are declared **inside the already-listed
`addons/shopify_connector_product/models/shopify_connector_product_importer.py`**
(§3), via classic Odoo inheritance only, never in a file outside §3's
exact allowed-files list, and never by editing `shopify_connector_job.py`
or `shopify_connector_job_dispatch.py` themselves:

1. **Register the job type.** Extend `shopify.connector.job` (`_inherit =
   'shopify.connector.job'`) to add **one** new `job_type` Selection
   value, `product_import_sync` (one job imports/binds one Shopify
   Product plus all of its variants together, read-only), via
   `selection_add` on the existing `job_type` field.
2. **Gate it on product-domain enablement.** Extend `shopify.connector.job`
   (same `_inherit`) to override `_domain_flag_for_job_type()`: return
   `'product_domain_enabled'` when `job_type == 'product_import_sync'`,
   and `super()._domain_flag_for_job_type(job_type)` for every other
   `job_type` — never remove or silently override an already-mapped
   `job_type`, matching the method's own docstring instruction, confirmed
   directly this session by reading `shopify_connector_job.py`. This is
   **not optional** — without it, `product_import_sync` jobs would start
   with no product-domain enablement check at all, silently bypassing the
   gate every other future domain job type is expected to use. The
   mapped flag, `product_domain_enabled`, is confirmed directly this
   session to already exist as `fields.Boolean(default=False)` on
   `shopify.connector.store.settings`
   (`shopify_connector_store_settings.py`) — no core field is added by
   this task. The core gate that consults this mapping already exists
   and is unmodified by this task: `shopify.connector.job.write()`, on
   any transition to `state == 'running'`, calls
   `_domain_flag_for_job_type(job_type)`; if it returns a flag name, the
   job is blocked unless a `shopify.connector.store.settings` row exists
   for that store **and** that row's flag field is true (confirmed
   directly this session by reading `shopify_connector_job.py`'s
   `write()` method) — a blocked start is routed by
   `shopify_connector_job_dispatch.py`'s existing `_start_running()` to
   `failed_retryable`/`odoo_validation_configuration`, unmodified by this
   task.
3. **Register the handler.** Extend `shopify.connector.job.dispatch`
   (`_inherit = 'shopify.connector.job.dispatch'`) to override
   `_get_handlers()`: call `super()._get_handlers()` and add
   `'product_import_sync': self._handle_product_import_sync` to the
   returned mapping — mirrors the accepted, already-demonstrated
   extension seam (`core_dispatch_selftest`'s own registration is the
   working precedent), confirmed directly this session by reading
   `shopify_connector_job_dispatch.py`.

- The existing, already-merged, generic `ir.cron`-driven drain loop
  (`shopify_connector_cron_drain.xml`, core-owned) already claims and
  dispatches **any** registered `job_type` — Task 010 does **not** need
  new cron XML, a new drain mechanism, or any other core wiring. This is
  the "do not over-integrate with cron" boundary: the seam is sufficient
  as-is.
- `shopify_target_gid` on the job carries the Shopify Product GID (known
  before any Odoo record exists). Exact `res_model`/`res_id` targeting
  (the binding model itself, vs. the underlying `product.template`) is
  **left open, as `mbq-55-product-binding-naming-schema-proposal.md` §8
  already flagged** — the implementing session fixes this as its own
  narrow, named in-task decision (do not invent a third option; pick one
  of the two already-named candidates and document the choice in the PR).
- **Multi-product enumeration/pagination is out of this job type's
  scope.** Which Shopify products to enqueue, and how a paused enumeration
  pass resumes, is a **separate, narrower open point** — checkpoint/cursor
  state must be **domain-owned** (e.g. tracked on a
  `shopify_connector_product`-owned record or within job/log evidence),
  **never** a new field added to `shopify.connector.job` or any other
  `shopify_connector_core` file. Task 010's own tests may exercise the
  importer/matching logic and the single-product job type against a
  bounded, fake/stub payload without implementing multi-page enumeration.
  If a genuinely safe, conservative enumeration approach cannot be
  designed within this constraint, the implementing session must STOP and
  mark it as a required ChatGPT decision rather than editing
  `shopify_connector_core` to add a cursor primitive silently.

## 10. Tests required

Exact test files (per §3) and their required test cases:

**`test_product_template_binding.py`:**
- Model requires `store_id` and `shopify_gid`.
- `UNIQUE(store_id, shopify_gid)` enforced.
- `UNIQUE(store_id, product_template_id)` enforced.
- `status` defaults to `active`.
- Access matrix across the four existing groups (auditor read-only;
  operator read/create; reviewer read/write for manual-review resolution;
  admin full) — mirrors `test_credential_access.py`'s pattern (confirmed
  this codebase has no separate dedicated ACL test file; access is tested
  inside each model's own test file).

**`test_product_variant_binding.py`:**
- Model requires `store_id`, `shopify_gid`, and `product_template_binding_id`.
- `UNIQUE(store_id, shopify_gid)` enforced.
- `UNIQUE(store_id, product_variant_id)` enforced.
- `product_template_binding_id` is required and never stands in for a
  missing variant binding — importing a variant always creates/links its
  own variant-binding row.
- Access matrix across the four existing groups.

**`test_product_import_matching.py`:**
- Existing-binding match takes priority over SKU/barcode.
- SKU (`default_code`) match when no existing binding, per §8.
- Barcode match when no SKU match, per §8.
- Ambiguous match (more than one SKU/barcode candidate) routes to
  `status='review'` / `manual_review_subreason='ambiguous_match'` /
  `blocked_manual_review` — never creates.
- Import creates and binds both a `product.template` and its
  `product.product` variants from a fake/stub payload, populating
  `product_template_binding_id` correctly.
- Template GID and variant GID are never conflated (two independent
  bindings, two independent `shopify_gid` values, from one payload).
- The importer constructs **zero** Shopify mutation calls — a
  source-level test asserting the fake/stub API client double never
  receives anything but read/query calls.
- **Product-domain gating (added on control-room review, comment ID
  `4925370944`) — required, exact:**
  - A `product_import_sync` job **cannot** transition to `running` when
    a `shopify.connector.store.settings` row exists for its store with
    `product_domain_enabled = False` — asserts the existing
    `ValidationError`/`failed_retryable`/`odoo_validation_configuration`
    routing already implemented in `shopify_connector_job.py`'s
    `write()` and `shopify_connector_job_dispatch.py`'s
    `_start_running()`, both unmodified by this task.
  - A `product_import_sync` job **cannot** transition to `running` when
    **no** `shopify.connector.store.settings` row exists at all for its
    store (same routing as above — `not settings` is falsy exactly like
    `not settings[flag_name]`).
  - A `product_import_sync` job **can** transition to `running` when the
    store is `connected` **and** its settings row has
    `product_domain_enabled = True`.
  - The `_domain_flag_for_job_type()` override preserves every
    pre-existing core `job_type`'s behavior (`core_readiness_check`,
    `core_manual_maintenance`, `core_test_connection`,
    `core_dispatch_selftest` each still map to `None`, via `super()`) —
    a regression test proving `core_dispatch_selftest` still dispatches
    successfully with `shopify_connector_product` installed, unchanged
    from its `shopify_connector_core`-only behavior.

**`test_product_duplicate_prevention.py`:**
- No automated create without a confident match or confident no-match, per
  §8's exact thresholds.
- A blind create attempt (no SKU, no barcode) on the automated path routes
  to `blocked_manual_review` / `manual_review_subreason='duplicate_risk'`
  — never creates.
- No feature flag/setting bypasses any condition in §8 (source-level
  test).
- Re-importing the same Shopify Product/ProductVariant GID a second time
  binds to the existing binding row — never creates a duplicate.
- The import job produces **zero** customer/order/inventory/fulfillment
  side effects (no such model is touched, read, or written anywhere in
  the diff).

## 11. Static checks

- Python import/syntax validity (`py_compile` or equivalent) for every new
  file, if no Odoo runtime is available at coding time.
- Odoo test command (`--test-enable --test-tags` scoped to
  `shopify_connector_product`) if a runtime is available.
- If no runtime exists at coding time, the implementing session must
  document this honestly in the PR — inventing a non-Odoo test harness is
  not acceptable (per the Task 001A precedent, restated in
  `task-010-product-import-proposed.md` §"Tests required").

## 12. Runtime checks if available

- Install `shopify_connector_product` alongside `shopify_connector_core`
  on a live Odoo 19/PostgreSQL instance.
- Run the four test files above; all must pass with `0 failed, 0
  error(s)`.
- Confirm no view/menu/action/controller/webhook/OAuth artifact exists
  anywhere in the installed module.
- Confirm no Shopify mutation call is ever constructed (source-level
  confirmation, restated as a runtime-install sanity check, not a live
  Shopify call).
- If no runtime is reachable, state this honestly in the PR and in
  `docs/05-qa/task-010-product-import-validation-results.md` — do not
  claim runtime validation that did not happen.

## 13. Rollback notes

Single-PR revert. Per the accepted domain-boundary DAG (DEC-008), only
`sale` and `inventory` depend on `product`, and neither is authorized to
start before Task 010, so no dependent domain logic is affected by a
revert. Reverting drops the two binding models (`product_template_binding_id`
foreign key removed with them); any already-imported `product.template`/
`product.product` Odoo records remain as ordinary, simply un-bound, Odoo
data — no destructive cleanup of business data is required or performed.
The new `job_type` value and its handler registration are removed with the
module; no job rows of the removed type persist meaning beyond their own
audit history (`ondelete='restrict'` on the job log, unchanged).

## 14. Stop condition

The future implementation session must:

- Open the resulting PR as **draft**.
- **Stop.**
- **Not** mark it ready for review.
- **Not** merge it.
- Report: exact files changed (confirmed against §3 via `git diff
  --stat`), which tests were written and whether they were run (and
  against what — fake/stub only, or a live runtime), any residual risk or
  open in-task decision made (per §9's `res_model`/`res_id` targeting
  choice and any enumeration-approach decision), and validation status
  (static-only vs. runtime-confirmed).

---

## Draft prompt text (not issued)

```text
You are Claude Code implementing ONE scoped task for the Odoo 19 Shopify
Connector. Implementation is AUTHORISED by ChatGPT for THIS task only —
confirm the Task 010 gate-opening act
(docs/07-implementation-plan/task-010-product-import-gate-opening-proposal.md
and docs/07-implementation-plan/product-domain-gate-criteria-proposal.md)
exists, is merged, and carries ChatGPT's explicit acceptance, before
writing any code. Verify Shopify-connector's current tip against the base
commit named in this document's "Current base placeholder" section — if it
has moved, re-verify every cited accepted fact before proceeding.

Read first: CLAUDE.md; docs/01-research/research-handoff.md (current
entry); docs/06-prompts/claude-learning-rules.md; this exact prompt
document in full; docs/07-implementation-plan/mbq-55-product-binding-naming-schema-proposal.md;
docs/07-implementation-plan/product-domain-gate-criteria-proposal.md;
docs/07-implementation-plan/task-010-product-import-gate-opening-proposal.md;
docs/07-implementation-plan/task-010-product-import-proposed.md;
docs/04-decisions/DEC-006-binding-dedup-identity-strategy.md;
docs/04-decisions/DEC-008-module-boundary-strategy.md;
docs/04-decisions/DEC-009-error-retry-idempotency-strategy.md;
docs/04-decisions/DEC-013-master-blueprint-core-substrate.md;
docs/04-decisions/DEC-014-master-blueprint-product-customer-sale.md;
docs/05-qa/rejected-approaches-log.md; docs/05-qa/architecture-review-log.md;
docs/05-qa/technical-debt-register.md (confirm TD-002 is still Open and is
NOT touched by this task); docs/05-qa/pr-review-checklist.md (A-C).

Objective: see §1.
Allowed files (exact): see §3. Forbidden files (exact): see §4.
Scope: see §5. Explicit non-scope: see §6.
Product binding schema: see §7. Dedup thresholds: see §8 (fixed, an
in-task decision consistent with DEC-014 point H — do not re-derive or
weaken).
Job/sync-engine usage: see §9 (product_import_sync job type via
selection_add; product-domain gating via a _domain_flag_for_job_type()
override mapping product_import_sync -> product_domain_enabled, preserving
super() for every other job_type; handler via _get_handlers() override —
all three declared inside shopify_connector_product_importer.py only,
zero edits to shopify_connector_core).
Tests required (exact): see §10.
Static checks: see §11. Runtime checks if available: see §12.
Rollback notes: see §13.

Definition of done: all tests in §10 written and pass (or, absent a
runtime, statically validated and honestly reported per §11); zero
Shopify mutation call anywhere in the diff (source-level proof); lint/
format clean; docs/05-qa/pr-review-checklist.md section C satisfied; any
genuine shortcut logged in docs/05-qa/technical-debt-register.md; only the
files in §3 changed (confirmed by git diff review); the mandatory
docs/01-research/research-handoff.md update included; a new
docs/05-qa/task-010-product-import-validation-results.md created,
honestly stating what was and was not run.

Explicit hard constraints (restate in the PR body before finishing):
- No live Shopify API call of any kind in tests; no Shopify mutation call
  of any kind anywhere in the diff.
- No customer/order/inventory/fulfillment logic of any kind.
- No UI, view, menu, action, wizard, webhook, or OAuth file of any kind.
- No edit to any shopify_connector_core file except the three seam-based
  registrations named in §9 (job_type selection_add,
  _domain_flag_for_job_type() override, _get_handlers() override), all
  declared inside shopify_connector_product_importer.py only, via classic
  Odoo inheritance.
- VAL-B2, MBQ-05, TD-002, the fulfillment API model, Lite/Full packaging,
  and the multi-server concurrency proof requirement remain exactly as
  open as before this task — none is touched, resolved, or narrowed.
- No claim that the existing Task 006C claim/dispatch mechanism is proven
  safe under real concurrent-worker or multi-server execution — this task
  inherits it unmodified and does not attempt to close SRR-03/SRR-04/SRR-09.

Stop condition: see §14 — open the PR as DRAFT, stop, report, do not merge,
do not start any further domain task.

End: run the learning review, update the handoff (Learning feedback loop
section + next prompt), confirm the quality gate per
docs/05-qa/quality-feedback-loop.md, commit/push to the designated branch,
open the PR as DRAFT, then STOP. Do not start Task 011/012/013/014, Task
015, any UI work, or any other next-feature work in this session.
```

---

## What this document does not do

- Does not execute the prompt above.
- Does not write any implementation code.
- Does not authorize the future Task 010 coding session to start now or at
  any point before the conditions in "How this document will be used"
  above are all met.
- Does not itself open the Task 010/product-domain implementation gate —
  that act is performed by the companion
  [`task-010-product-import-gate-opening-proposal.md`](./task-010-product-import-gate-opening-proposal.md)'s
  own acceptance (PR #137 control-room review, comment ID `4926437491`),
  not by this document. See that document's §1/§9 for the exact,
  current gate status: open for exactly one future Task 010
  implementation session, effective once PR #137 merges into
  `Shopify-connector` — not a standing authorization for any other
  product-domain task.
- Does not claim ChatGPT has issued this prompt. Issuance is a distinct,
  later, separate chat turn by ChatGPT in a new Claude Code session.
- Does not resolve VAL-B2, MBQ-05, TD-002, the fulfillment API model,
  Lite/Full packaging, checkpoint/resume ownership beyond §9's narrow
  single-job-type scope, or the multi-server concurrency proof
  requirement — every one remains exactly as open as its own cited source
  states, except where §8/§9 above explicitly fix a narrow, named,
  in-task decision consistent with already-accepted architecture.

---

## Evidence / references

- [`mbq-55-product-binding-naming-schema-proposal.md`](./mbq-55-product-binding-naming-schema-proposal.md),
  [`product-domain-gate-criteria-proposal.md`](./product-domain-gate-criteria-proposal.md) —
  both Accepted by ChatGPT, PR #136, comment ID `4924917266` — access:
  Accessible, this repository, observed 2026-07-09.
- [`task-010-product-import-proposed.md`](./task-010-product-import-proposed.md),
  [`master-implementation-readiness-checkpoint.md`](./master-implementation-readiness-checkpoint.md),
  [`mvp-domain-implementation-sequence.md`](./mvp-domain-implementation-sequence.md) —
  access: Accessible, this repository, observed 2026-07-09.
- [`DEC-006`](../04-decisions/DEC-006-binding-dedup-identity-strategy.md),
  [`DEC-008`](../04-decisions/DEC-008-module-boundary-strategy.md),
  [`DEC-009`](../04-decisions/DEC-009-error-retry-idempotency-strategy.md),
  [`DEC-013`](../04-decisions/DEC-013-master-blueprint-core-substrate.md),
  [`DEC-014`](../04-decisions/DEC-014-master-blueprint-product-customer-sale.md) —
  all read directly in full this session — access: Accessible, this
  repository, observed 2026-07-09.
- `addons/shopify_connector_core/models/shopify_connector_job.py`,
  `shopify_connector_job_dispatch.py`, `shopify_connector_binding_mixin.py`,
  `__manifest__.py`, `security/ir.model.access.csv`,
  `security/shopify_connector_security.xml` — read directly (not
  modified) this session to confirm the `job_type`/`_get_handlers()`
  extension seams, the `models.Constraint` convention, the four existing
  groups, and the generic cron-drain mechanism — access: Accessible, this
  repository, observed 2026-07-09.
- [`docs/05-qa/sync-engine-open-questions.md`](../05-qa/sync-engine-open-questions.md)
  (Q7, Q37, Q39), [`sync-engine-risk-register.md`](../05-qa/sync-engine-risk-register.md)
  (SRR-03/04/09), [`technical-debt-register.md`](../05-qa/technical-debt-register.md)
  (TD-002) — read directly this session — access: Accessible, this
  repository, observed 2026-07-09.
- [`DEC-025`](../04-decisions/DEC-025-task-006-sync-engine-gate.md) — read
  directly this session, confirms the generic drain mechanism and the
  unresolved concurrency-proof items — access: Accessible, this
  repository, observed 2026-07-09.
- [`task-004-final-implementation-prompt.md`](./task-004-final-implementation-prompt.md),
  [`task-006c-sync-engine-skeleton-final-prompt.md`](./task-006c-sync-engine-skeleton-final-prompt.md) —
  structural pattern this document mirrors — access: Accessible, this
  repository, observed 2026-07-09.
- **Revision evidence (2026-07-09, PR #137 control-room review, comment ID
  `4925370944`):** `addons/shopify_connector_core/models/shopify_connector_store_settings.py`
  — read directly this revision, confirms `product_domain_enabled =
  fields.Boolean(default=False)` already exists on
  `shopify.connector.store.settings`, unmodified by this task.
  `addons/shopify_connector_core/models/shopify_connector_job.py` — re-read
  directly this revision, confirms `write()`'s `state -> 'running'` gate
  already calls `_domain_flag_for_job_type(job_type)` and, when it returns
  a flag name, blocks the start unless a matching, truthy
  `shopify.connector.store.settings` row exists for the store — access:
  Accessible, this repository, observed 2026-07-09.
- **Acceptance evidence (2026-07-09, PR #137 control-room review, comment
  ID `4926437491`):** ChatGPT confirmed all five precision fixes above and
  accepted this document's content — access: Accessible, 2026-07-09.
