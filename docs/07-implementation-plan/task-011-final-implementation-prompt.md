# Task 011 — Customer Import / Matching: Final Implementation Prompt

DO NOT USE UNTIL CHATGPT REVIEWS, ACCEPTS, EXPLICITLY OPENS THE TASK 011 GATE, AND ISSUES THIS PROMPT.

> **Status: Proposed final prompt — NOT accepted, NOT issued, NOT
> usable.** Prepared 2026-07-10 by the AR-039 gate-readiness session
> (Proposed for ChatGPT review). This document converts the **accepted**
> MBQ-55 customer-binding naming/schema proposal
> ([`mbq-55-customer-binding-naming-schema-proposal.md`](./mbq-55-customer-binding-naming-schema-proposal.md),
> Accepted, control-room comment `4928377625`, PR #140) and the
> **accepted-as-criteria-only** customer-domain gate criteria
> ([`customer-domain-gate-criteria-proposal.md`](./customer-domain-gate-criteria-proposal.md))
> into a copy-paste-ready `CLAUDE.md` §9 implementation prompt for Task
> 011, carrying the D1–D8 recommendations of
> [`task-011-decision-closure-brief.md`](./task-011-decision-closure-brief.md)
> as **proposed prompt content**. It mirrors the accepted Task 010
> pattern
> ([`task-010-product-import-final-implementation-prompt.md`](./task-010-product-import-final-implementation-prompt.md)).
> **Nothing in this document is binding until ChatGPT accepts it, and
> nothing is executable until ChatGPT additionally (a) performs the
> distinct customer-domain gate-opening act and (b) explicitly issues
> this prompt, verbatim, as its own later chat turn in a new Claude Code
> session.** The customer-domain gate is **closed** today. Task 011 is
> **unauthorized** today.

## How this document will be used

1. **Not yet satisfied** — ChatGPT reviews and accepts this document and
   the companion
   [`task-011-customer-domain-gate-opening-proposal.md`](./task-011-customer-domain-gate-opening-proposal.md)
   (deciding D1–D8 via
   [`task-011-decision-closure-brief.md`](./task-011-decision-closure-brief.md)
   in the same review).
2. **Not yet satisfied** — ChatGPT performs the distinct, explicit
   **customer-domain gate-opening act** named in
   [`customer-domain-gate-criteria-proposal.md`](./customer-domain-gate-criteria-proposal.md)
   §4 — the gate opens for exactly one future Task 011 implementation
   session, effective once condition 3 is also met, and closes again the
   moment that session's PR opens as draft.
3. **Not yet satisfied** — the PR carrying this package has merged into
   `Shopify-connector`.
4. **Not yet satisfied** — before pasting the prompt below, the issuing
   session verifies the base placeholder in §2 is still the actual
   current tip of `Shopify-connector`; if the branch has moved, it
   re-verifies every cited accepted document/decision is unchanged before
   pasting, not assumes it.
5. **Not yet satisfied** — ChatGPT explicitly pastes/issues the exact
   finalized prompt text below into a **new** Claude Code session, as its
   own later chat turn.
6. **Not yet satisfied** — the implementing session stops at its own
   scoped boundary (`CLAUDE.md` §6) — it must not chain into Task
   012/013/014/015, UI, webhook, OAuth, or any other next-feature work.

**Nothing in this document authorizes Claude to begin implementation now
or at any point before all six conditions above are met.**

---

## 1. Session objective

Implement **Task 011: Shopify customer import and matching only** —
Shopify → Odoo, read-only against Shopify, email-only automatic matching.
Create the `shopify_connector_sale` addon containing the accepted
`shopify.connector.customer.binding` model (Shopify Customer ↔ Odoo
`res.partner`), a read-only customer importer/matching service
implementing the exact D1 thresholds, the D2 ambiguous-candidate job/log
evidence payload, the D3 default-address-on-create mapping, the D4
person-only classification, and the D5 inert
`customer_fallback_partner_id` store-settings config field. **No customer
export, no order logic, no Shopify write of any kind.**

## 2. Current base placeholder

Use latest known base: `Shopify-connector` at the merge commit of the PR
carrying this package (its direct parent is
`4a45f3ea1e6e92acd0621fdc6e2a435b29170221`, the PR #143 merge commit —
the tip at drafting time, confirmed via `git rev-parse` and GitHub
`pull_request_read`, 2026-07-10).

**The future implementation session must verify the actual current tip of
`Shopify-connector` before writing any code.** If the branch has advanced
past the expected commit, the implementing session must confirm no
intervening PR touched `addons/shopify_connector_core/**`, the accepted
MBQ-55 customer schema, or the accepted gate criteria in a way that
changes any fact this prompt relies on — and if one did, STOP and report
the discrepancy instead of proceeding on a stale base.

## 3. Allowed files

**Be exact.** The future implementation session may create or modify
only:

- `addons/shopify_connector_sale/__init__.py` (NEW)
- `addons/shopify_connector_sale/__manifest__.py` (NEW — per **D6**:
  `depends: ['shopify_connector_core']` **only**. No
  `shopify_connector_product` dependency (customer binding reads no
  product binding — Task 012 adds it when order lines actually need it);
  no Odoo `sale` app dependency (Task 011 references no `sale.order`
  model — Task 012 adds it); `res.partner` lives in Odoo `base`, already
  a transitive dependency. `installable: True`; `application: False`;
  version `19.0.1.0.0`; no `data` entry other than
  `security/ir.model.access.csv`.)
- `addons/shopify_connector_sale/models/__init__.py` (NEW)
- `addons/shopify_connector_sale/models/shopify_connector_customer_binding.py`
  (NEW) — the `shopify.connector.customer.binding` model, §7.1.
- `addons/shopify_connector_sale/models/shopify_connector_customer_importer.py`
  (NEW) — the importer/matching service (§5, §8, §9): a stateless
  read-only `AbstractModel` (no table, no ACL row) mirroring
  `shopify_connector_product_importer.py`'s pattern, **plus** the three
  narrow extension-seam classes named in §9 (`job_type` `selection_add`;
  the `_domain_flag_for_job_type()` override; the `_get_handlers()`
  override) — this is the **one** allowed file where those seam
  extensions may live.
- `addons/shopify_connector_sale/models/shopify_connector_store_settings.py`
  (NEW) — **only** the `_inherit = 'shopify.connector.store.settings'`
  extension adding the single §7.2 field
  (`customer_fallback_partner_id`). File name added by this prompt,
  following the module-file convention; nothing else may live here.
- `addons/shopify_connector_sale/security/ir.model.access.csv` (NEW) —
  access rows for `shopify.connector.customer.binding` **only**, reusing
  the four **existing** `shopify_connector_core` groups
  (`group_shopify_connector_auditor`/`_operator`/`_reviewer`/`_admin`) —
  **no new group, no `security/*.xml`.** Row naming mirrors the existing
  convention, e.g.
  `access_shopify_connector_customer_binding_operator`. (The importer is
  an `AbstractModel` — no ACL row; the settings extension adds a field to
  an existing model — no new ACL row.)
- `addons/shopify_connector_sale/tests/__init__.py` (NEW)
- `addons/shopify_connector_sale/tests/test_customer_binding.py` (NEW) — §10.
- `addons/shopify_connector_sale/tests/test_customer_import_matching.py`
  (NEW) — §10.
- `addons/shopify_connector_sale/tests/test_customer_duplicate_prevention.py`
  (NEW) — §10.
- `addons/shopify_connector_sale/tests/test_customer_fallback_partner.py`
  (NEW) — §10.
- `docs/01-research/research-handoff.md` — the mandatory handoff update
  only.
- `docs/05-qa/task-011-customer-import-validation-results.md` (NEW) — the
  validation-results record, mirroring
  `task-010-product-import-validation-results.md`'s pattern. Per OP-43's
  lesson: quote build-log summary lines **verbatim**; never synthesize
  per-module test totals.
- `docs/05-qa/architecture-review-log.md` — **only** to append the
  implementation-closure AR row (mirroring AR-036's pattern) — no other
  row may be edited.

**If the implementing session believes any file outside this list is
genuinely needed, it must not add it silently — it must STOP and mark it
as a required ChatGPT decision in its PR description.**

## 4. Forbidden files

Explicitly forbidden, no exceptions unless ChatGPT explicitly authorizes
in a separate act:

- Any file under `addons/shopify_connector_core/**` — zero core edits;
  the three §9 seam registrations happen exclusively inside
  `shopify_connector_customer_importer.py` via classic Odoo inheritance,
  never by editing core files.
- Any file under `addons/shopify_connector_product/**` — read-only
  neighbor; never touched.
- Any order/product/inventory/fulfillment/accounting/refund/payout/
  multi-store file or logic of any kind — including any `sale.order`
  reference.
- Any UI/view/menu/action/wizard/controller file of any kind.
- Any webhook receiver/controller file of any kind.
- Any OAuth/token-acquisition file of any kind.
- Any CI/workflow file, Dockerfile, `requirements*.txt`, or migration
  file.
- Any customer **export**/write-mutation code path — zero Shopify
  mutation construction anywhere in the diff.
- `addons/adams_base/**` — never touched.
- Any file not explicitly named in §3.

## 5. Scope

- Create the `shopify_connector_sale` addon (manifest, init, models,
  security, tests only — §3).
- One concrete binding model,
  `shopify.connector.customer.binding` (§7.1), extending
  `shopify.connector.binding.mixin`.
- The inert `customer_fallback_partner_id` store-settings config field
  (§7.2) — **defined, never consumed** (Posture A).
- A read-only importer/matching service that, given a Shopify Customer
  payload (real via the existing Task 003 API client, or fake/stub in
  tests), matches/creates/binds `res.partner` records per the exact §8
  rules, routes ambiguous/blind cases to `blocked_manual_review` with
  the §8.2 candidate-evidence payload, and applies the §8.3 address and
  §8.4 person-only rules on create.
- One new job type, `customer_import_sync`, registered via the three §9
  extension seams — zero core edits.
- **No Shopify write of any kind** — the importer only ever issues read
  (query) calls through the existing, unmodified Task 003 API client.

## 6. Explicit non-scope

Must exclude, with zero code touching any of the following:

- Customer **export** or any write back to Shopify (no mutation of any
  kind).
- Order import/matching/creation of any kind (Task 012) — including any
  consumption of `customer_fallback_partner_id`, any no-PII order
  routing, and any order-level audit marker (Posture A boundary).
- Product, inventory, or fulfillment logic of any kind.
- Multi-customer enumeration/pagination implementation (§9 boundary —
  the posture is pinned for the future task, not implemented here).
- Address-list (`addressesV2`) import, child-partner address rows,
  address drift-sync on re-import (§8.3 deferrals).
- Company/B2B modeling: `companyContactProfiles`, `is_company = True`,
  company-string mapping (§8.4).
- Marketing-consent fields/logic of any kind.
- Setup wizard or any operator-facing UI/view/menu/action/wizard.
- Webhook receiver/controller of any kind.
- OAuth/token-acquisition code of any kind; no distribution/auth
  assumption of any kind baked into code, tests, or docs (MBQ-05 branch
  B remains open and independent).
- Lite/Full packaging of any kind.
- Live Shopify validation (VAL-B2) — fake/stub client tests only.
- Multi-server/concurrent-worker concurrency validation — this task
  inherits the merged Task 006C claim/dispatch mechanism unmodified and
  does not attempt to close SRR-03/SRR-04/SRR-09.

## 7. Customer binding schema and settings field

Accepted names per
[`mbq-55-customer-binding-naming-schema-proposal.md`](./mbq-55-customer-binding-naming-schema-proposal.md)
§5–§8 (Accepted, comment `4928377625`). **Odoo 19 requirement (Task 010
precedent, confirmed against merged core code):** use
`models.Constraint(...)`, never the deprecated `_sql_constraints` dict.

### 7.1 `shopify.connector.customer.binding`

Class `ShopifyConnectorCustomerBinding` in
`shopify_connector_customer_binding.py`, declaring **both**
`_name = 'shopify.connector.customer.binding'` **and**
`_inherit = 'shopify.connector.binding.mixin'` explicitly (the Task 010
control-room lesson — a new concrete model extending an `AbstractModel`
contract states both attributes).

- **Inherited from the mixin** (confirmed field set): `store_id`
  (Many2one → `shopify.connector.store`, required, index,
  `ondelete='restrict'`), `shopify_gid` (Char, required, index, readonly
  — holds the Shopify **Customer** GID), `status` (Selection
  `active`/`stale`/`manually_overridden`/`review`, required, index,
  default `active`), `match_key` (Selection — only
  `existing_binding`/`email`/`manual` are ever populated by this model;
  `sku_reference`/`barcode` are product-domain vocabulary, inherited
  unchanged, never set), `matched_by_uid`, `matched_at`, `override_uid`,
  `override_at`, `override_previous_candidate`.
- **`status = 'review'` semantics (accepted):** lifecycle review of an
  **already-real** binding only — never a placeholder for an unresolved
  candidate selection. An ambiguous match never creates a row of this
  model (§8.1 rule 6).
- **New required relational field:** `partner_id` (Many2one →
  `res.partner`, required, index, `ondelete='restrict'`).
- **Imported snapshot fields (readonly, audit/advisory only — never a
  second source of truth for matching):** `shopify_display_name`
  (`fields.Char`), `shopify_email_snapshot` (`fields.Char`),
  `shopify_phone_snapshot` (`fields.Char` — advisory-hint display only,
  never matched on), `shopify_last_imported_at` (`fields.Datetime`).
  Matching always reads the live incoming payload against
  `res.partner.email` via `partner_id` — never against snapshots.
- **Constraints (`models.Constraint`):** `UNIQUE(store_id, shopify_gid)`;
  `UNIQUE(store_id, partner_id)`.
- **Explicitly out of scope (accepted §7.1.E):** order/order-line
  references; write/export-tracking fields; product/inventory/fulfillment
  references; marketing-consent fields; any `is_company` classification
  field; any address field on the binding model.

### 7.2 Settings extension (in `shopify_connector_store_settings.py`)

Per **D5**: a single field on a `_inherit =
'shopify.connector.store.settings'` extension class —

- `customer_fallback_partner_id = fields.Many2one('res.partner',
  ondelete='restrict')` — **no default, no auto-creation of any partner
  record, no constraint requiring it, no compute/onchange, ordinary
  write path.**
- **Posture A boundary (accepted, restated verbatim as binding prompt
  content):** Task 011 defines this field as inert supporting substrate
  only — **zero order-resolution behavior, zero consumption of the field
  within Task 011's own import/matching flow, zero coupling to order
  import.** When and how an order routes to this partner, and the
  order-level audit marker, are entirely Task 012's own future,
  separately-authorized scope. No Task 011 code path may read this field
  (§10's outcome-equivalence test proves it).

## 8. Matching, duplicate prevention, address, and classification rules (fixed as in-task decisions carried from D1–D4)

These convert the accepted blueprint policy (DEC-006; DEC-014 points E/H;
MBQ-59 two-tier gate; the accepted ambiguous-match posture) into exact
MVP rules **for Task 011's narrow scope only** — they do not reopen or
weaken any accepted decision, and do not resolve MBQ-59 project-wide.

### 8.1 Match sequence and thresholds (D1)

1. **Existing binding** for `(store_id, shopify_gid)` → bind/refresh;
   `match_key = 'existing_binding'`.
2. **Email normalization:** `normalized_incoming =
   odoo.tools.email_normalize(payload defaultEmailAddress.emailAddress)`;
   missing/empty/unnormalizable → rule 5. Candidate comparison happens on
   normalized forms on both sides
   (`email_normalize(partner.email) == normalized_incoming`); a
   case-insensitive pre-filter search (`'=ilike'`) is permitted for
   efficiency but the normalized comparison decides.
3. **Exactly one active candidate** (`active = True` partners only) whose
   normalized email matches, and that partner has no existing
   customer binding in this store for a different `shopify_gid` → bind;
   `match_key = 'email'`. If the single candidate is already bound to a
   different Customer GID in this store → **no row**;
   `blocked_manual_review` / `'binding_conflict'`.
4. **Zero active candidates AND zero archived matches (rule 7's check
   runs first), non-empty normalized email → confident no-match:** the
   one create-eligible case on the automated path (gated by the
   eligibility tier already implemented at start time — §9's
   `sale_domain_enabled` mapping): create the `res.partner` (per §8.3/
   §8.4) and its binding row; `match_key = 'email'`. **Create is never
   reached while any archived-partner match exists** — rule 7 routes
   that case to manual review before this rule can apply.
5. **Missing/empty/unnormalizable email → never an automated create:**
   no partner, no binding row; `blocked_manual_review` /
   `'duplicate_risk'`. Phone and name are **never** fallback automatic
   keys (DEC-014 point E; RA-006).
6. **More than one active candidate → ambiguous:** **no binding row**
   (`partner_id` is required — a row would force an automatic guess,
   forbidden by DEC-006/RA-006): `blocked_manual_review` /
   `'ambiguous_match'`, candidate evidence per §8.2. A binding row is
   created only once an operator confirms exactly one candidate —
   `match_key = 'manual'`, `matched_by_uid`/`matched_at` populated.
7. **Archived-partner rule:** archived partners are never automatic
   candidates. If zero active candidates exist but ≥1 **archived**
   partner's normalized email matches (checked via one explicit
   `with_context(active_test=False)` search run only after the active
   count is zero): no create, no bind, no un-archive —
   `blocked_manual_review` / `'duplicate_risk'`, archived candidate(s)
   in the §8.2 payload with `"active": false`.
8. **No bypass:** no feature flag, setting, or configuration combination
   may bypass any rule above.

### 8.2 Ambiguous/duplicate-risk candidate evidence (D2)

- Carried as JSON in the **existing**
  `shopify.connector.job.log.technical_detail` field of the
  `blocked_manual_review` transition row, written through the existing,
  unmodified `_transition_blocked_manual_review(...)` call — **no new
  field, no core edit**.
- Exact payload shape (no other keys):

  ```json
  {
    "kind": "customer_ambiguous_match_candidates",
    "shopify_customer_gid": "<gid>",
    "incoming_email_normalized": "<normalized email>",
    "candidate_count": <true total>,
    "candidates": [
      {"partner_id": <int>, "display_name": "<str>",
       "email": "<str>", "active": <bool>}
    ]
  }
  ```

  Capped at the first 20 candidates by `partner_id` ascending;
  `candidate_count` carries the true total. The same shape (with
  `manual_review_subreason = 'duplicate_risk'`) carries archived-match
  evidence.
- **PII posture:** minimum disambiguation set only (id, display name,
  email, active) — no phone, no address, no order data; lives only in
  the ACL-restricted job-log model; never emitted to server logs,
  exceptions, or any Shopify-bound call. `message` stays human-readable
  prose, never JSON.

### 8.3 Address handling (D3)

- Read **`defaultAddress` only** (§9 field list); `addressesV2` never
  queried.
- Address fields are written **only when rule 8.1(4) creates a new
  partner**: `street ← address1`, `street2 ← address2`, `city ← city`,
  `zip ← zip`, `country_id ←` `res.country` by `countryCodeV2` code
  lookup (never create), `state_id ←` `res.country.state` by
  `provinceCode` within the matched country (never create).
  Unresolvable country/state → leave the field empty + informational
  job-log line; address resolution failures never fail the import and
  never invent records.
- **Never** write any address field on an existing matched partner; no
  child `res.partner` rows of any `type`.
- Recorded consequence (not code): with no typed child contacts, Odoo's
  `sale.order` will later resolve invoice/shipping to the bound partner
  itself via `address_get` fallback — the Shopify Order's own
  shipping/billing addresses are Task 012's scope.

### 8.4 Company/person classification (D4)

- Every created partner is a **person**: `is_company` is never set
  (default `False` stands); no code path may classify a customer as a
  company.
- `defaultAddress.company` is not queried, not mapped, not stored.
- `companyContactProfiles` is not queried, not stored. B2B stays
  non-MVP.

## 9. Job/sync-engine usage (D7)

**Register exactly one customer job type via the three already-proven
extension seams — no new cron mechanism, zero core edits.** All three
declared inside `shopify_connector_customer_importer.py` only, via
classic Odoo inheritance:

1. **Register the job type:** extend `shopify.connector.job`
   (`_inherit`) with `selection_add` on `job_type` adding
   `customer_import_sync` (one job imports/matches/binds one Shopify
   Customer, read-only).
2. **Gate it on sale-domain enablement:** override
   `_domain_flag_for_job_type()` to return `'sale_domain_enabled'` for
   `customer_import_sync` and `super()._domain_flag_for_job_type(...)`
   for every other job type — never removing an existing mapping. The
   flag **already exists** on `shopify.connector.store.settings`
   (`fields.Boolean(default=False)`, confirmed by direct read
   2026-07-10) — no core field is added. The core `write()` gate and
   `_start_running()` routing that consult this mapping are unmodified.
3. **Register the handler:** override `_get_handlers()` on
   `shopify.connector.job.dispatch` — `super()` plus
   `'customer_import_sync': self._handle_customer_import_sync`.

- The existing generic cron drain loop already claims/dispatches any
  registered job type — no new cron XML, no core wiring.
- `shopify_target_gid` carries the Shopify Customer GID. `res_model`/
  `res_id`, when populated after a successful bind, target the
  **binding row** (`shopify.connector.customer.binding`) — fixed here,
  mirroring Task 010's own recorded in-task choice (validation results
  §C.1) rather than re-deriving it.
- **Single-customer GraphQL query (the only query this task runs),
  executed through the existing Task 003 client at the store's pinned
  `api_version`:** `customer(id: $gid)` selecting exactly
  `id`, `firstName`, `lastName`, `displayName`,
  `defaultEmailAddress { emailAddress }`,
  `defaultPhoneNumber { phoneNumber }`,
  `defaultAddress { address1 address2 city zip provinceCode countryCodeV2 }`,
  `updatedAt` — nothing else. The deprecated `email`/`phone`/`addresses`
  fields must not appear anywhere in the diff (deprecations re-verified
  2026-07-10: "Use `defaultEmailAddress.emailAddress` instead" / "Use
  `defaultPhoneNumber.phoneNumber` instead").
- **Multi-customer enumeration is out of this job type's scope**
  (mirrors Task 010 §9). For the future enumeration task the posture is
  pinned, not implemented: `customers(first: 100, after: $cursor,
  sortKey: UPDATED_AT, query: "updated_at:>=<checkpoint>")`; page size
  100 (max 250); durable checkpoint = last fully processed customer's
  `updatedAt`, domain-owned, never a stored GraphQL cursor as sole
  resume state (Q10/Q11), never a new core/job field. If a genuinely
  needed enumeration primitive cannot fit this constraint, STOP and mark
  it a required ChatGPT decision.
- Throttling/THROTTLED-body/cost handling is the existing client's
  concern — the importer adds no throttle handling, no retry loop of its
  own.

## 10. Tests required (D8)

Exact test files (§3) and required cases:

**`test_customer_binding.py`:**
- Model requires `store_id`, `shopify_gid`, `partner_id`.
- `UNIQUE(store_id, shopify_gid)` enforced.
- `UNIQUE(store_id, partner_id)` enforced.
- `status` defaults to `active`.
- Access matrix across the four existing groups (auditor read-only;
  operator read/create; reviewer read/write for manual-review
  resolution; admin full) — inside this file, per the established
  convention.

**`test_customer_import_matching.py`:**
- Existing-binding match takes priority over email.
- Exactly-one-active-email match binds with `match_key = 'email'`.
- Case-folding/normalization: an incoming `Foo@BAR.com` matches a
  partner stored as `foo@bar.com`.
- Single candidate already bound to a different Customer GID in-store →
  `blocked_manual_review` / `'binding_conflict'`, no new row.
- Ambiguous (two active candidates, same normalized email) → **no**
  binding row; `blocked_manual_review` / `'ambiguous_match'`; the §8.2
  JSON payload parses, has the exact `kind`, lists every candidate
  `partner_id`, correct `candidate_count`, no extra keys; `message` is
  human-readable non-JSON. Include the >20-candidates cap case.
- Create path maps §8.3 address fields; unresolvable `countryCodeV2`
  leaves `country_id` empty without failing; no child partner created.
- Created partner is a person (`is_company = False`,
  `company_type = 'person'`) even when the payload's
  `defaultAddress.company` is non-empty; the company string is mapped
  nowhere.
- Null `defaultEmailAddress` and null `defaultAddress` payloads are
  tolerated per §8.1(5)/§8.3.
- **Sale-domain gating (exact, mirrors Task 010):** a
  `customer_import_sync` job cannot transition to `running` with a
  settings row where `sale_domain_enabled = False`; cannot with **no**
  settings row; can when the store is connected and
  `sale_domain_enabled = True`; the `_domain_flag_for_job_type()`
  override preserves every pre-existing mapping via `super()` (all
  `core_*` types → `None`; regression proof that
  `core_dispatch_selftest` still dispatches successfully with
  `shopify_connector_sale` installed).
- Zero-mutation proof: the fake/stub client double records read/query
  calls only; a source-level assertion that no mutation is constructed
  anywhere in the module.
- The importer requests only the §9 field list (assertable against the
  double's recorded query strings).

**`test_customer_duplicate_prevention.py`:**
- Re-importing the same Customer GID binds to the existing row — never a
  duplicate partner, never a duplicate binding.
- Missing/empty email on the automated path → no create;
  `blocked_manual_review` / `'duplicate_risk'`.
- Archived-only email match → no create, no bind, no un-archive;
  `'duplicate_risk'` with `"active": false` candidate detail (§8.1(7)).
- No settings flag/config combination bypasses any §8.1 rule
  (no-bypass test).
- Direct-create collisions prove the two uniqueness constraints as the
  backstop.
- The import produces **zero** order/product/inventory/fulfillment side
  effects (no such model touched anywhere in the diff).

**`test_customer_fallback_partner.py`:**
- `customer_fallback_partner_id` exists on
  `shopify.connector.store.settings`, type `Many2one('res.partner')`,
  unset by default.
- No partner record is auto-created anywhere by module install,
  settings creation, or import runs.
- **Posture A behavioral proof:** identical payload streams produce
  byte-identical matching outcomes whether the field is unset or set;
  no importer code path reads the field.

## 11. Static checks

- Python import/syntax validity (`py_compile` or equivalent) for every
  new file if no Odoo runtime is available at coding time.
- Odoo test command (`--test-enable`, scoped to
  `shopify_connector_sale`) if a runtime is available.
- If no runtime exists at coding time, document this honestly in the PR
  — inventing a non-Odoo test harness is not acceptable.

## 12. Runtime checks if available

- Install `shopify_connector_sale` alongside `shopify_connector_core`
  and `shopify_connector_product` on a live Odoo 19/PostgreSQL instance.
- Run the four test files; all must pass `0 failed, 0 error(s)`.
- **Mandatory before merge (SRR-06 standing practice): a live Odoo.sh
  branch-database run of the full suite**, evidence recorded in
  `docs/05-qa/task-011-customer-import-validation-results.md` — quoting
  the build log's own summary lines verbatim (OP-43 lesson; never
  synthesize totals).
- Confirm no view/menu/action/controller/webhook/OAuth artifact exists
  in the installed module; confirm zero Shopify mutation construction
  (source-level).
- If no runtime is reachable in the coding session, state this honestly
  in the PR and validation record — the PR stays draft until the live
  run is green.

## 13. Rollback notes

Single-PR revert. No other module depends on `shopify_connector_sale`
(Task 012 does not exist; DEC-008's DAG gives `sale` no dependents), so a
revert affects nothing else. Reverting drops the customer-binding model
and the settings extension field; any already-created `res.partner`
records remain as ordinary, simply un-bound, Odoo data — no destructive
cleanup of business data is required or performed. The
`customer_import_sync` job type and handler registration are removed with
the module; job rows of the removed type persist only as audit history.

## 14. Stop condition

The future implementation session must:

- Open the resulting PR as **draft**. **Stop.**
- **Not** mark it ready for review; **not** merge it.
- Report: exact files changed (vs §3, via `git diff --stat`); which
  tests were written and what they ran against (fake/stub only vs live
  runtime); any narrow in-task decision made; validation status
  (static-only vs runtime-confirmed) — honestly.
- The customer-domain gate **closes** the moment the PR opens as draft
  (accepted §4 rule) — no further customer-domain work may start
  regardless of the PR's outcome.

---

## Draft prompt text (not issued)

```text
You are Claude Code implementing ONE scoped task for the Odoo 19 Shopify
Connector. Implementation is AUTHORISED by ChatGPT for THIS task only —
before writing any code, confirm the Task 011 gate-opening act
(docs/07-implementation-plan/task-011-customer-domain-gate-opening-proposal.md
and docs/07-implementation-plan/customer-domain-gate-criteria-proposal.md)
exists, is merged, and carries ChatGPT's explicit acceptance AND explicit
gate-opening act. Verify Shopify-connector's current tip against the base
named in this prompt document's §2 — if it has moved, re-verify every
cited accepted fact before proceeding; STOP on any discrepancy.

Read first: CLAUDE.md; docs/01-research/research-handoff.md (current
entry); docs/06-prompts/claude-learning-rules.md; this exact prompt
document in full
(docs/07-implementation-plan/task-011-final-implementation-prompt.md);
docs/07-implementation-plan/task-011-decision-closure-brief.md;
docs/07-implementation-plan/mbq-55-customer-binding-naming-schema-proposal.md;
docs/07-implementation-plan/customer-domain-gate-criteria-proposal.md;
docs/07-implementation-plan/task-011-customer-domain-gate-opening-proposal.md;
docs/04-decisions/DEC-006-binding-dedup-identity-strategy.md;
docs/04-decisions/DEC-008-module-boundary-strategy.md;
docs/04-decisions/DEC-009-error-retry-idempotency-strategy.md;
docs/04-decisions/DEC-013-master-blueprint-core-substrate.md;
docs/04-decisions/DEC-014-master-blueprint-product-customer-sale.md;
docs/05-qa/rejected-approaches-log.md;
docs/05-qa/architecture-review-log.md;
docs/05-qa/technical-debt-register.md (confirm TD-002 is still Open and
NOT touched by this task); docs/05-qa/pr-review-checklist.md (A-C);
docs/00-source-materials/shopify-customer-odoo19-partner-task-011-captures.md.

Objective: see §1.
Allowed files (exact): see §3. Forbidden files (exact): see §4.
Scope: see §5. Explicit non-scope: see §6.
Binding schema + settings field: see §7 (declare _name AND _inherit;
models.Constraint only; customer_fallback_partner_id is inert config —
Posture A, zero consumption).
Matching/dedup/address/classification rules: see §8 (fixed in-task
decisions consistent with DEC-006/DEC-014/MBQ-59 — do not re-derive or
weaken; ambiguous matches NEVER create a binding row; candidate evidence
goes in the job log technical_detail JSON per §8.2).
Job/sync-engine usage: see §9 (customer_import_sync via selection_add;
_domain_flag_for_job_type() override mapping customer_import_sync ->
sale_domain_enabled, preserving super() for every other job_type;
_get_handlers() override — all three inside
shopify_connector_customer_importer.py only, zero core edits; the exact
customer(id:) query field list in §9, non-deprecated fields only).
Tests required (exact): see §10.
Static checks: see §11. Runtime checks: see §12 (live Odoo.sh run
mandatory before merge). Rollback notes: see §13.

Definition of done: all §10 tests written and pass (or, absent a
runtime, statically validated and honestly reported per §11, with the
live run still mandatory before merge); zero Shopify mutation anywhere
in the diff (source-level proof); lint/format clean;
docs/05-qa/pr-review-checklist.md section C satisfied; any genuine
shortcut logged in docs/05-qa/technical-debt-register.md; only §3 files
changed (git diff review); the mandatory research-handoff update
included; docs/05-qa/task-011-customer-import-validation-results.md
created, honestly stating what was and was not run, quoting any build
log verbatim.

Explicit hard constraints (restate in the PR body before finishing):
- No live Shopify API call of any kind in tests; no Shopify mutation of
  any kind anywhere in the diff.
- No order/product/inventory/fulfillment logic of any kind; no
  sale.order reference; no consumption of customer_fallback_partner_id.
- No UI, view, menu, action, wizard, webhook, or OAuth file of any kind;
  no distribution/auth assumption baked into code, tests, or docs.
- No edit to any shopify_connector_core or shopify_connector_product
  file; the three §9 seam registrations live inside
  shopify_connector_customer_importer.py only, via classic inheritance.
- No name/phone matching anywhere — email is the sole automatic key;
  archived partners are never automatic candidates.
- VAL-B2, MBQ-05 (both branches), MBQ-55's order portion, TD-002,
  Lite/Full packaging, and the multi-server concurrency proofs
  (SRR-03/04/09) remain exactly as open as before this task — none is
  touched, resolved, or narrowed.
- No claim that the Task 006C claim/dispatch mechanism is proven safe
  under real concurrent-worker/multi-server execution.

Stop condition: see §14 — open the PR as DRAFT, stop, report, do not
merge, do not start any further domain task.

End: run the learning review, update the handoff (Learning feedback loop
section + next prompt), confirm the quality gate per
docs/05-qa/quality-feedback-loop.md, commit/push to the designated
branch, open the PR as DRAFT, then STOP. Do not start Task 012/013/014,
Task 015, any UI work, or any other next-feature work in this session.
```

---

## What this document does not do

- Does not execute the prompt above; does not write any implementation
  code.
- Does not authorize the future Task 011 coding session to start now or
  before all six "How this document will be used" conditions are met.
- Does not open the customer-domain gate — that is a distinct, future,
  explicit ChatGPT act on the companion gate-opening proposal.
- Does not claim ChatGPT has accepted this document or issued this
  prompt — both remain future, separate acts.
- Does not resolve VAL-B2, MBQ-05 (either branch), MBQ-55's order
  portion, TD-002, MBQ-56, MBQ-27, MBQ-32, Lite/Full packaging, or
  SRR-03/04/09 — every one remains exactly as open as its own cited
  source states, except where §8/§9 fix a narrow, named in-task decision
  consistent with already-accepted architecture.

## Evidence / references

- [`task-011-decision-closure-brief.md`](./task-011-decision-closure-brief.md)
  (D1–D8, with full official-source citations) — Accessible, this
  repository, 2026-07-10.
- [`mbq-55-customer-binding-naming-schema-proposal.md`](./mbq-55-customer-binding-naming-schema-proposal.md),
  [`customer-domain-gate-criteria-proposal.md`](./customer-domain-gate-criteria-proposal.md)
  — both Accepted (comment `4928377625`) — Accessible, 2026-07-10.
- [`task-010-product-import-final-implementation-prompt.md`](./task-010-product-import-final-implementation-prompt.md)
  — accepted structural precedent — Accessible, 2026-07-10.
- Merged core code read directly (read-only) 2026-07-10:
  `shopify_connector_job.py`, `shopify_connector_job_log.py`,
  `shopify_connector_job_dispatch.py`,
  `shopify_connector_store_settings.py`,
  `shopify_connector_binding_mixin.py`,
  `shopify_connector_security.xml`.
- Official sources (fetched/re-verified 2026-07-10; excerpts:
  [`../00-source-materials/shopify-customer-odoo19-partner-task-011-captures.md`](../00-source-materials/shopify-customer-odoo19-partner-task-011-captures.md)):
  Shopify `Customer`, `CustomerEmailAddress`, `CustomerPhoneNumber`,
  `MailingAddress`, `customers` query, `CustomerSortKeys`,
  pagination/limits/search-syntax/versioning/access-scopes/PCD pages;
  Odoo 19 `res_partner.py`, `sale/models/sale_order.py`,
  `mail_thread_blacklist.py`.
- GitHub PR #143 (`AdamsOdoo/Adams`) — merged 2026-07-10T05:35:06Z, base
  `Shopify-connector` (via `pull_request_read`, 2026-07-10).
