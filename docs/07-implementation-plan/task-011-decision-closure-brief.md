# Task 011 — Decision Closure Brief (D1–D8)

> **Status: Recommended for ChatGPT acceptance — NOT accepted, NOT a
> decision.** Docs-only. Prepared 2026-07-10 by the AR-039 gate-readiness
> session, closing — at recommendation level only — the eight decisions
> D1–D8 that [`next-gate-readiness-roadmap.md`](./next-gate-readiness-roadmap.md)
> §4 requires before Task 011's final implementation prompt can be issued.
> Every recommendation below becomes binding **only** when ChatGPT accepts
> the final prompt that carries it
> ([`task-011-final-implementation-prompt.md`](./task-011-final-implementation-prompt.md))
> — none is a decision today. **This document does not open the
> customer-domain gate, does not authorize Task 011 or any code, and does
> not weaken any accepted DEC/AR/RA/MBQ record.**
>
> Evidence layers used, per claim: (a) already-accepted repo records
> (cited inline); (b) merged core code, read directly this session
> (read-only); (c) official Shopify/Odoo sources — every platform fact was
> **re-verified against current official sources on 2026-07-10** (the
> prior audit's 2026-07-09 fetches were not assumed), with excerpts
> captured in
> [`../00-source-materials/shopify-customer-odoo19-partner-task-011-captures.md`](../00-source-materials/shopify-customer-odoo19-partner-task-011-captures.md)
> per `CLAUDE.md` §7.4 (OP-44).

> **Acceptance note (2026-07-10, PR #144 control-room review, comment ID
> `4932704451` — supersedes the "NOT accepted" wording above, which is
> preserved as the accurate drafting-time record).** ChatGPT accepted
> this package with two required fixes, both applied in this same PR:
> D1's candidate-discovery rule is now explicitly recall-safe (see D1
> rule 2 — `'=ilike'` forbidden; recall-preserving discovery mandatory
> for both active and archived-inclusive searches; new test expectations
> in D8), and the merge-safety status patch is applied. **D1–D8 are
> thereby fixed as binding content of the accepted final prompt — which
> remains NOT issued.** This acceptance does not open the customer-domain
> gate (closed), does not authorize Task 011–015, and does not decide
> MBQ-05 branch B.

## 0. How to read this brief

Each section states: the decision question (from
`next-gate-readiness-roadmap.md` §4), the accepted constraints it must not
violate, the official-source facts it rests on, the **exact recommended
outcome** (in final-prompt-ready terms), the alternatives considered, and
the tests it implies. The recommendations are carried verbatim into
[`task-011-final-implementation-prompt.md`](./task-011-final-implementation-prompt.md)
§8–§10 — that document is the single place ChatGPT accepts them.
Rejected-approaches check: nothing below matches or re-proposes
RA-001–RA-024 (`../05-qa/rejected-approaches-log.md`, checked in full this
session); where a recommendation touches a rejection's territory (RA-006
name-matching; RA-003 public distribution), it explicitly complies with
the rejection rather than revisiting it.

---

## D1 — Customer dedup / match-confidence thresholds (criterion 5; OP-10)

**Accepted constraints:** matching priority existing binding → email →
manual review; email is the sole automatic match key; phone/name advisory
only, never automatic (DEC-006; DEC-012 §6.4; DEC-014 point E / MBQ-31;
RA-006). No blind create — MBQ-59 two-tier gate (eligibility, then
match-quality), accepted at blueprint-policy level (DEC-014). Ambiguous
matches never create a binding row (accepted naming proposal §9, comment
`4928377625`).

**Official-source facts (re-verified 2026-07-10):**

- **[Fact]** Odoo 19 `res.partner.email` is a plain `fields.Char()` with
  **no uniqueness constraint** (official `odoo/odoo` 19.0 source,
  `odoo/addons/base/models/res_partner.py`) — 0, 1, or N matching partners
  are all real production cases.
- **[Fact]** `res.partner.active` is the standard archive Boolean; ORM
  `search()` excludes archived records by default.
- **[Fact]** Odoo provides `email_normalize` in `odoo.tools` (defined in
  `odoo/tools/mail.py`, importable without any module dependency), which
  lower-cases and extracts the bare address;
  `res.partner.email_normalized` is added only by the `mail` module's
  `mail.thread.blacklist` mixin (`addons/mail/models/mail_thread_blacklist.py`,
  19.0) and is therefore **not** relied on (the module depends on
  `shopify_connector_core` only — see D6).

**Recommended outcome (exact, final-prompt-ready):**

1. **Existing-binding match.** A `shopify.connector.customer.binding` row
   for `(store_id, shopify_gid)` exists → bind/refresh against its
   `partner_id`; `match_key = 'existing_binding'`. Always checked first.
2. **Email normalization rule — candidate discovery must be
   recall-safe (revised on control-room review, comment `4932704451`).**
   `normalized_incoming =
   odoo.tools.mail.email_normalize(<incoming defaultEmailAddress.emailAddress>)`.
   If the incoming email is missing, empty, or fails normalization, the
   record is treated under rule 5 (no automatic key available). Candidate
   comparison is performed on normalized forms on **both** sides
   (`email_normalize(partner.email) == normalized_incoming`) — case
   folding, whitespace, and display-name wrapping are therefore never a
   mismatch source. **Recall-safety rule:** candidate discovery must not
   use any database prefilter that can exclude a partner whose
   `email_normalize(partner.email)` equals `normalized_incoming` — Odoo
   partner emails may be stored in display-name/wrapped/mixed-case forms
   (e.g. `"Jane Doe" <Jane.DOE@Example.COM>`) that normalize to the same
   bare address; a narrowing exact prefilter would miss such a partner
   and fall through to the rule-4 create path, creating a duplicate. The
   always-safe baseline is to search `[('email', '!=', False)]` and
   compare normalized forms Python-side. A database prefilter is
   permitted **only** if it provably preserves recall — e.g. the
   substring form `('email', 'ilike', normalized_incoming)` followed by
   the mandatory Python-side normalized comparison. The exact-match form
   `'=ilike'` must **not** be used (it excludes wrapped/display-name
   forms) unless the implementation first proves it cannot reduce recall
   for normalized-equivalent Odoo email formats. This recall-safety rule
   applies identically to the **active-candidate search and the rule-7
   archived-inclusive search**. The Python-side normalized comparison is
   always the deciding test.
3. **Exactly one active candidate → automatic match.** Candidate set =
   **active** `res.partner` records (`active = True`; archived partners
   are never automatic candidates) whose normalized email equals
   `normalized_incoming`. Exactly one candidate, **and** that partner has
   no existing customer binding for this store with a different
   `shopify_gid` → bind; `match_key = 'email'`. If the single candidate
   **is** already bound to a different Shopify Customer in this store
   (`UNIQUE(store_id, partner_id)` would be violated) → **no** row;
   `blocked_manual_review` / `manual_review_subreason =
   'binding_conflict'`.
4. **Zero active candidates AND zero archived matches (rule 7's
   archived check runs before any create), non-empty email → confident
   no-match.** On the automated path this is the one create-eligible
   case, gated by the MBQ-59 eligibility tier already implemented at
   enqueue/start time (store connected; settings row exists;
   `sale_domain_enabled = True` — see D7): create a new `res.partner`
   plus the new binding row. The binding's `match_key` is recorded as
   `'email'` — the email was the checked identity key that proved no
   duplicate exists — mirroring Task 010's use of the checked key on
   confident no-match creates.
5. **Missing/empty/unnormalizable email → never an automated create.**
   With no automatic key checked, an automated create would be a blind
   create (the exact case Task 010 routes to `duplicate_risk`): **no**
   partner create, **no** binding row; `blocked_manual_review` /
   `'duplicate_risk'`. Phone and name are **never** used as fallback
   automatic keys (DEC-014 point E; RA-006) — restated as a hard rule, not
   re-decided.
6. **More than one active candidate → ambiguous.** **No** binding row
   (`partner_id` is `required=True` — creating one would force an
   automatic guess, forbidden by DEC-006/RA-006 and the accepted §9
   posture): `blocked_manual_review` / `'ambiguous_match'`, candidate
   detail recorded per D2. A binding row is created only once an operator
   confirms exactly one candidate (`match_key = 'manual'`,
   `matched_by_uid`/`matched_at` populated).
7. **Archived-partner rule.** Archived (`active = False`) partners are
   excluded from automatic matching (rule 3). If rule 3/4 finds **zero
   active** candidates but at least one **archived** partner's normalized
   email matches, the automated path must **not** create (it would
   duplicate an archived partner) and must **not** bind or un-archive
   (silent data mutation): route to `blocked_manual_review` /
   `'duplicate_risk'`, with the archived candidate(s) recorded in the D2
   payload (`"active": false`). Operator resolution decides.
   *(Implementation note: the ORM excludes archived records from
   `search()` by default — the archived-candidate check therefore
   requires one explicit archived-inclusive search, e.g.
   `with_context(active_test=False)`, run only after the active-candidate
   count is zero.)*
8. **No bypass.** No feature flag, setting, or configuration combination
   may bypass any rule above (Part A §I.5 no-bypass rule via DEC-013,
   restated, not weakened).

This fixes the MBQ-59 customer-domain residual **for Task 011's narrow
scope only** — exactly as Task 010's final prompt §8 fixed the product
instance; it does not resolve MBQ-59 project-wide.

**Alternatives considered:** treating archived partners as ordinary
candidates (rejected — binding would silently resurrect data; creating
would duplicate); treating archived matches as nonexistent and creating
(rejected — classic duplicate-record defect); phone as a secondary
automatic key (already rejected, DEC-014 point E — not revisited);
fuzzy/name similarity matching (binding rejection RA-006 — not
revisited).

**Tests implied:** D8 files `test_customer_import_matching.py` /
`test_customer_duplicate_prevention.py` — every numbered rule above has a
named positive or negative test.

---

## D2 — Exact job/log field(s) for ambiguous-match candidate detail (criterion 15; OP-09)

**Accepted constraint:** candidate detail lives at job/log level only,
never in a binding row (naming proposal §9/§10/§12 item 7, Accepted,
comment `4928377625`); the exact field was deliberately left open.

**Merged-code facts (read directly 2026-07-10, read-only):**
`shopify.connector.job.log` (`shopify_connector_job_log.py`) already
carries `message` (Text, required), `technical_detail` (Text),
`payload_snapshot` (Text), `event_type`, `from_state`/`to_state`,
`actor_uid`, `occurred_at` — all readonly, appended via `_system_append()`.
`shopify.connector.job._transition_blocked_manual_review(error_class,
manual_review_subreason, message, technical_detail=False)` already writes
a log row with `technical_detail` on the transition
(`shopify_connector_job.py`). The `ambiguous_match` value already exists
in `MANUAL_REVIEW_SUBREASON_SELECTION` and in the error-class registry.

**Recommended outcome (exact):**

- **No new field, no core edit.** Candidate detail is carried as a
  structured JSON payload in the **existing
  `shopify.connector.job.log.technical_detail`** field of the
  `blocked_manual_review` transition log row, written through the
  existing, unmodified
  `_transition_blocked_manual_review(error_class='ambiguous_match',
  manual_review_subreason='ambiguous_match', message=<human-readable
  one-liner>, technical_detail=<JSON>)` call. `payload_snapshot` stays
  reserved for inbound-payload snapshots; `enqueue_decisions` stays
  enqueue-time-only. (The same mechanism, with
  `manual_review_subreason='duplicate_risk'`, carries the archived-match
  candidate detail from D1 rule 7.)
- **Payload shape (exact, fixed):**

  ```json
  {
    "kind": "customer_ambiguous_match_candidates",
    "shopify_customer_gid": "<gid>",
    "incoming_email_normalized": "<normalized email>",
    "candidate_count": <int, true total>,
    "candidates": [
      {"partner_id": <int>, "display_name": "<str>",
       "email": "<str>", "active": <bool>}
    ]
  }
  ```

  `candidates` is capped at the first 20 by `partner_id` ascending;
  `candidate_count` always carries the true total. No other keys.
- **PII / redaction posture:** the payload deliberately contains the
  minimum an operator needs to disambiguate — partner id, display name,
  email, active flag — and **nothing else**: no phone, no address, no
  order history, no full profile (consistent with the accepted
  PII-minimization direction in
  `task-011-customer-import-matching-proposed.md` §UI dependencies). It
  lives only in the ACL-restricted job-log model (the four existing
  connector groups); it is never emitted to server logs, exceptions, or
  any Shopify-bound call. The existing credential-redaction contract
  (`tools/redaction.py`) is unaffected — no credential material can enter
  this payload by construction.
- **Tests (carried into D8):** ambiguous transition writes exactly one
  `blocked_manual_review` log row whose `technical_detail` parses as JSON,
  has `kind = 'customer_ambiguous_match_candidates'`, lists every
  candidate `partner_id`, sets the correct `candidate_count`, contains no
  keys beyond the fixed shape, and whose `message` is human-readable
  (non-JSON); the >20-candidates cap case; the archived-candidate
  (`"active": false`) case.

**Alternatives considered:** a new dedicated field on
`shopify.connector.job` (rejected — needs a core edit, forbidden without
a named authorization, and duplicates an existing capable field); a new
field on the binding model (rejected outright — the accepted §9 posture
forbids any binding-row representation); free-text-only detail in
`message` (rejected — not machine-readable for the future S8 reviewer
screen).

---

## D3 — Address handling (criterion 14; OP-07)

**Official-source facts (re-verified 2026-07-10):**

- **[Fact]** Shopify `Customer.defaultAddress` is a `MailingAddress`;
  `Customer.addressesV2` is the paginated connection for the full address
  list (the legacy `addresses` list field is superseded/deprecated on
  current versions). `MailingAddress` carries `address1`, `address2`,
  `city`, `zip`, `provinceCode`, `countryCodeV2`, `company`, `phone`, etc.
  (official `Customer`/`MailingAddress` reference pages).
- **[Fact]** Odoo models additional addresses as **child `res.partner`
  rows** via `parent_id` with `type` ∈ contact/invoice/delivery/other
  (exactly four values in 19.0 — Odoo 19 `res_partner.py`), and
  `sale.order` computes `partner_invoice_id` via
  `partner_id.address_get(['invoice'])` and `partner_shipping_id` via
  `partner_id.address_get(['delivery'])` (two separate `@api.depends
  ('partner_id')` computes — `_compute_partner_invoice_id` /
  `_compute_partner_shipping_id`), where `address_get` **falls back to
  the partner itself** when no typed child contact exists (Odoo 19
  `sale/models/sale_order.py`; `res_partner.py` `address_get`). The Task
  011 address choice therefore directly pre-shapes Task 012's
  invoice/shipping behavior — and, via `fiscal_position_id`'s dependency
  on `partner_shipping_id`, its tax-mapping selection too.

**Recommended outcome (exact):**

1. **`defaultAddress` only.** Task 011 reads only
   `Customer.defaultAddress` (see D7's field list). `addressesV2` is not
   queried at all.
2. **Write onto the bound partner's own address fields, only on create.**
   When (and only when) D1 rule 4 creates a **new** `res.partner`, the
   default address maps onto that partner's own flat address fields:
   `street ← address1`, `street2 ← address2`, `city ← city`,
   `zip ← zip`, `country_id ←` `res.country` looked up by
   `countryCodeV2` (lookup only — never create a country),
   `state_id ←` `res.country.state` looked up by `provinceCode` within
   the matched country (lookup only — never create a state). An
   unresolvable country/state leaves that field empty and appends an
   informational job-log line — address resolution failures never fail
   the import and never invent records.
3. **Never overwrite an existing partner.** When D1 binds to an existing
   partner (rules 1 and 3), Task 011 writes **no** address field on it —
   no drift-sync, no conditional update.
4. **No child partners.** Task 011 creates no child `res.partner` rows of
   any `type` (no invoice/delivery contacts).
5. **Task 012 implication, stated for the record:** with no typed child
   contacts, `sale.order.address_get` will resolve invoice and shipping to
   the bound partner itself. The Shopify **Order's own**
   `shippingAddress`/`billingAddress` (which can differ from the
   customer's default address) are order-domain data and are entirely
   Task 012's own future scope — nothing in Task 011 pre-decides how Task
   012 represents them.
6. **Explicit non-MVP / not-Task-011 deferrals:** full `addressesV2` list
   import; typed child-contact modeling; address updates/drift handling on
   re-import of an already-bound customer; any address-based matching
   (never — matching is email-only, D1).

**Alternatives considered:** importing `addressesV2` into child partners
(rejected for MVP — largest surface, pre-empts Task 012's order-address
design, and no accepted decision requires it); importing no address at
all (rejected — a created partner with no address forces Task 012 orders
to invoice/ship to an empty-address partner, a worse default than the
customer's own declared default address; the cost of the chosen cut is
four mapped fields + two lookups); updating addresses on every re-import
(rejected — silent mutation of operator-owned Odoo data without a
source-of-truth decision, the exact pattern RA-021 rejects for inventory
quantities).

**Tests implied (D8):** create-path maps all six fields; unknown country
code leaves `country_id` empty without failing; existing-partner match
never writes address fields; no child partner is ever created.

---

## D4 — Company/person classification (criterion 14; OP-08)

**Official-source facts (re-verified 2026-07-10):**

- **[Fact]** The Shopify `Customer` object has **no person/company
  boolean**. The only company-adjacent signals are the free-text
  `MailingAddress.company` string and the B2B construct
  `Customer.companyContactProfiles` (`CompanyContact`, part of Shopify's
  B2B feature set).
- **[Fact]** Odoo 19 `res.partner.is_company` is a plain Boolean, default
  `False`, with the computed `company_type` selection
  (person/company) (official 19.0 `res_partner.py`).

**Recommended outcome (exact):**

1. **Every imported Shopify Customer is created as a person:** Task 011
   never sets `is_company = True` (the default `False` stands;
   `company_type` remains `'person'`). No code path may classify a
   customer as a company.
2. **`MailingAddress.company` is never used for classification and is not
   mapped to any Odoo field in Task 011** (not `company_name`, not a
   custom field — nothing). It is free text with no reliable semantics;
   auto-classifying from it would be name-adjacent guessing in RA-006's
   spirit.
3. **`companyContactProfiles` is not queried, not stored** (see D7's
   field list). B2B/company modeling stays **non-MVP**, consistent with
   the accepted Phase 1 B2B-commerce exclusion (Part B "Scope and
   non-goals"; `non-mvp-and-later-phases.md`).
4. **Deferral, explicit:** any future company/B2B partner modeling
   (companies, contact hierarchies, `companyContactProfiles` import)
   requires its own research pass and ChatGPT decision — nothing in Task
   011 pre-shapes it.

**Alternatives considered:** auto-classifying `is_company` from a
non-empty address-company string (rejected — free text, no platform
semantics, silent misclassification risk on e.g. "c/o" strings);
importing the company string into `res.partner.company_name` (rejected
for first cut — that field participates in Odoo invoice/address display
logic, an unreviewed side effect; deferred with the B2B bundle).

**Tests implied (D8):** created partners have `is_company = False` /
`company_type = 'person'`; a payload with a non-empty
`defaultAddress.company` still creates a person and maps the company
string nowhere.

---

## D5 — Fallback-partner field mechanics (criterion 13; OP-11)

**Accepted constraints:** name and home are already accepted —
`customer_fallback_partner_id` on `shopify.connector.store.settings`,
contributed by `shopify_connector_sale` via the settings `_inherit`
extension seam; **Posture A** boundary: inert config substrate, zero
order-resolution behavior, zero consumption in Task 011's own flow
(naming proposal §7.3, Accepted, comment `4928377625`; MBQ-29 Resolved —
one fallback partner per store, genuine no-PII orders only, audit marker
mandatory, all Task 012 scope).

**Recommended outcome (exact):**

- **Field:** `customer_fallback_partner_id =
  fields.Many2one('res.partner', ondelete='restrict')`, declared in a
  `_inherit = 'shopify.connector.store.settings'` extension class inside
  `shopify_connector_sale`'s own model file (the same classic-inheritance
  seam the core settings model's docstring invites; no core file edit).
  `ondelete='restrict'` mirrors the core convention for every
  partner/store relational field (binding `partner_id`, `store_id`) and
  prevents silently deleting a partner that a store's configuration
  references.
- **No default.** The field defaults to unset; a store with no fallback
  partner configured is a fully valid Task 011 state.
- **No auto-creation.** Task 011 never creates any fallback partner
  record (no data file, no default-partner factory, no
  first-enablement hook). The MBQ-29 naming direction ("Shopify — No
  Customer Data") remains recorded guidance for whoever configures or
  later auto-provisions it — provisioning is Task 012+/UI-chain scope.
- **Ordinary write path.** No constraint requires it to be set; standard
  settings-model ACLs apply; no compute, no onchange side effects.
- **Task 011 consumption: none (Posture A restated verbatim).** No
  importer/matching code path reads, writes, or resolves to this field.
  Task 011 defines inert configuration only; the decision of when/how an
  order routes to it, and the mandatory order-level audit marker, are
  entirely Task 012's own future, separately-authorized scope.
- **Safety boundary test (D8):** matching outcomes are byte-identical
  whether the field is set or unset; no Task 011 code path references it
  except the field definition itself.

**Alternatives considered:** `ondelete='set null'` (rejected — a
configured fallback partner silently disappearing is exactly the class of
quiet config rot the restrict convention exists to prevent);
auto-creating the partner on module install or domain enablement
(rejected — creates business data as a side effect of a backend-only,
UI-less task, and pre-empts Task 012's provisioning/UX decisions); Posture
B — not defining the field at all (already considered and not chosen in
the accepted naming proposal §11 — not re-litigated).

---

## D6 — `shopify_connector_sale` manifest dependency (OP-12)

**Accepted constraints:** DEC-008's dependency DAG (`core → product →
{sale, inventory}`) **permits** `sale` to depend on `product`; the naming
proposal §4 left "core only now" vs "core + product now" as an explicit
in-task decision. Task 011's customer binding references only
`res.partner` (Odoo `base`) and core models.

**Recommended outcome (exact):**

- **`depends: ['shopify_connector_core']` — nothing else.** Smallest
  manifest that is truthful today:
  1. `res.partner` lives in Odoo `base`, which `shopify_connector_core`
     already depends on — no extra Odoo app is needed.
  2. **No `shopify_connector_product` dependency in Task 011.** Customer
     binding/matching reads no product binding (accepted fact, naming
     proposal §3/§11 — customers have no product-domain counterpart). The
     dependency is added by **Task 012**, in its own gated diff, when
     order-line code actually resolves product bindings — an ordinary,
     safe manifest amendment (Odoo manifests are routinely extended when
     new code lands; the same reasoning Task 010 used for its own
     `product` dependency, inverted).
  3. **No Odoo `sale` app dependency in Task 011 either** — this is the
     part of D6 the roadmap row did not spell out and is worth deciding
     explicitly: the module is *named* `shopify_connector_sale` (DEC-008's
     accepted Phase 1 home for customer + order), but Task 011 touches no
     `sale.order` model, so declaring `'sale'` now would install Odoo's
     entire Sales app as a side effect of customer import. Task 012
     declares `'sale'` when it actually references `sale.order`.
- Manifest is otherwise minimal: `installable: True`,
  `application: False`, `data` = the one ACL file (see the final prompt
  §3); version `19.0.1.0.0` mirroring `shopify_connector_product`'s
  first-release convention.

**Alternatives considered:** declaring `shopify_connector_product` now
"to match DEC-008's full DAG" (rejected — installs a hard dependency no
Task 011 code uses, couples customer import to product-domain
installability for zero benefit, and contradicts the smallest-manifest
principle both prior domain tasks followed); declaring Odoo `sale` now
because of the module's name (rejected — same reasoning; the name is a
DEC-008 boundary label, not a dependency claim).

**Tests implied (D8):** a manifest-shape test is not required (mirrors
Task 010 — manifest correctness is proven by installation itself on the
Odoo.sh run); the no-product/no-order guard tests in D8 enforce the same
boundary behaviorally.

---

## D7 — Exact GraphQL query, field list, pagination, checkpointing (OP-13)

**Official-source facts (re-verified 2026-07-10):**

- **[Fact]** On current Admin API versions, `Customer.email` and
  `Customer.phone` are **deprecated** in favor of
  `Customer.defaultEmailAddress` (`CustomerEmailAddress`, whose address
  value is its `emailAddress` field) and `Customer.defaultPhoneNumber`
  (`CustomerPhoneNumber`, whose value is its `phoneNumber` field);
  `Customer.addressesV2` supersedes the legacy `addresses` field.
- **[Fact]** `QueryRoot.customers` is a standard cursor-paginated
  connection (`first`/`after`, `pageInfo { hasNextPage endCursor }`) with
  a `query` filter supporting `updated_at` ranges and a `sortKey`
  including `UPDATED_AT`; connection page size is bounded at 250 per the
  standard connection limit.
- **[Fact]** GraphQL Admin throttling is a calculated-query-cost model
  signalled by a `THROTTLED` error in the response **body** (not HTTP
  429), with cost detail in `extensions.cost` — already handled by the
  merged Task 003 client (SRR-08 posture; re-confirmed unchanged).
- **[Open question, standing]** GraphQL cursor durability across a
  paused/resumed sync is officially undocumented
  (`sync-engine-open-questions.md` Q10/Q11 — unchanged; re-checked
  2026-07-10, still undocumented).

**Recommended outcome (exact):**

1. **One job type, one customer per job** — `customer_import_sync`
   (job payload/`shopify_target_gid` identifies one Shopify Customer GID),
   read-only, registered through the three already-proven seams (job-type
   `selection_add`; `_domain_flag_for_job_type()` override mapping
   `customer_import_sync → 'sale_domain_enabled'` — the flag **already
   exists** on `shopify.connector.store.settings`
   (`fields.Boolean(default=False)`, confirmed by direct read
   2026-07-10), so no core field is added; `_get_handlers()` override) —
   all declared inside the importer model file only, zero core edits,
   mirroring Task 010 §9 exactly.
2. **Single-customer query (the query Task 011's handler actually
   runs):** `customer(id: $gid)` selecting exactly:
   `id`, `firstName`, `lastName`, `displayName`,
   `defaultEmailAddress { emailAddress }`,
   `defaultPhoneNumber { phoneNumber }`,
   `defaultAddress { address1 address2 city zip provinceCode countryCodeV2 }`,
   `updatedAt`.
   **Nothing else** — minimal-field discipline (naming proposal §3):
   no `email`/`phone` (deprecated), no `addresses`/`addressesV2` (D3), no
   `companyContactProfiles` (D4), no `note`/`tags`/`amountSpent`/
   `numberOfOrders` (no accepted requirement consumes them). The query
   runs at the store's pinned `api_version` (MBQ-52 policy, currently
   exercised at `2026-07`) through the existing Task 003 client,
   unmodified.
3. **Multi-customer enumeration is out of Task 011's single-job scope**
   — mirroring Task 010 §9's identical boundary. Which customers to
   enqueue, and the enumeration pass itself, belong to the future
   trigger/scheduled-sync work (Area 6/OP-28). To prevent that future
   task re-deriving the posture, the final prompt **pins it now**:
   `customers(first: 100, after: $cursor, sortKey: UPDATED_AT, query:
   "updated_at:>=<checkpoint>")` with `pageInfo { hasNextPage endCursor }`;
   page size **100** (max 250; 100 keeps per-page cost conservative under
   the calculated-cost model); **checkpoint field = the last fully
   processed customer's `updatedAt`** (durable, re-queryable), persisted
   domain-side — **never** a stored GraphQL cursor as the sole resume
   state (Q10/Q11: cursor durability undocumented), and **never** a new
   field on `shopify.connector.job` or any core model (Task 010 §9's
   checkpoint-ownership rule, restated). *(Precision caveat for that
   future task, found 2026-07-10: the customers-query `updated_at`
   filter's description says "matching a whole day" while its own
   official examples use full ISO 8601 timestamps — the enumeration task
   must verify timestamp-granularity behavior empirically before relying
   on sub-day checkpoints; logged as an open question, not assumed.)*
4. **Throttling/rate handling: inherited, not reimplemented.** The
   importer performs reads only through the existing client; it adds no
   throttle handling, no retry loop, no cost accounting of its own
   (DEC-009 taxonomy + Task 006C retry scheduling own those).
5. **Fake-client test expectations (carried into D8):** the fake/stub
   client double serves canned current-shape payloads
   (`defaultEmailAddress`/`defaultPhoneNumber`/`defaultAddress` — never
   the deprecated `email`/`phone` shape); tests assert the importer issues
   **only** read/query calls (zero mutations, source-level and
   double-level), tolerates a `null` `defaultEmailAddress` (D1 rule 5),
   `null` `defaultAddress` (D3 — partner created without address fields),
   and never requests a field outside the pinned list (assertable on the
   double's recorded query strings).

**Alternatives considered:** querying deprecated `email`/`phone` for
"compatibility" (rejected — new code adopting deprecated fields blindly is
the exact drift the 2026-07-09 audit flagged; the pinned non-deprecated
fields are served at the store's pinned version); page size 250 (rejected
— maximal pages spike per-request cost for no Task 011 benefit); storing
`endCursor` as the durable checkpoint (rejected — officially undocumented
durability, Q10/Q11); implementing enumeration inside Task 011 (rejected —
scope growth beyond the Task 010-mirrored single-record boundary, and it
belongs with the trigger/scheduling work).

---

## D8 — Exact test files and coverage (criterion 9)

**Accepted starting point:** the four file names proposed by the accepted
naming proposal §4 (comment `4928377625`) — **confirmed unchanged**:

- `addons/shopify_connector_sale/tests/test_customer_binding.py`
- `addons/shopify_connector_sale/tests/test_customer_import_matching.py`
- `addons/shopify_connector_sale/tests/test_customer_duplicate_prevention.py`
- `addons/shopify_connector_sale/tests/test_customer_fallback_partner.py`

**Recommended required coverage (exact; the final prompt §10 carries the
full per-file case list):**

1. **`test_customer_binding.py`** — model requires `store_id`,
   `shopify_gid`, `partner_id`; `UNIQUE(store_id, shopify_gid)` and
   `UNIQUE(store_id, partner_id)` enforced; `status` defaults `active`;
   ACL matrix across the four existing groups (auditor read-only /
   operator read-create / reviewer read-write / admin full), mirroring the
   established per-model pattern.
2. **`test_customer_import_matching.py`** — positive: existing-binding
   priority beats email; exactly-one-active-email match binds with
   `match_key='email'`; normalization/case-folding (`Foo@BAR.com` matches
   `foo@bar.com`); **recall-safety (added on control-room review, comment
   `4932704451`): a partner stored with a display-name/wrapped,
   mixed-case email (e.g. `"Jane Doe" <Jane.DOE@Example.COM>`) is found
   and bound by incoming `jane.doe@example.com` — never missed, never a
   duplicate create**; create-path address mapping incl.
   unresolvable-country tolerance (D3); created partner is a person
   (`is_company=False`) even with a non-empty address-company string
   (D4). Negative/ambiguous:
   two active candidates → **no** binding row, job
   `blocked_manual_review`/`ambiguous_match`, D2 JSON payload complete and
   shape-exact; single candidate already bound in-store to another GID →
   `binding_conflict`, no row. Gating: a `customer_import_sync` job cannot
   reach `running` with `sale_domain_enabled=False`, or with no settings
   row; can with `True`; the `_domain_flag_for_job_type()` override
   preserves every pre-existing mapping via `super()` (incl.
   `product_import_sync → product_domain_enabled` when
   `shopify_connector_product` is installed, and all `core_*` → `None`) —
   plus the `core_dispatch_selftest` regression proof. Zero-mutation
   proof: the fake client double records reads only.
3. **`test_customer_duplicate_prevention.py`** — re-importing the same
   Customer GID binds to the existing row, never duplicates the partner or
   the binding; **recall-safety proof (comment `4932704451`): a
   wrapped/display-name-form email on an existing active partner never
   falls through to the create path, and the same wrapped-form coverage
   holds for an archived partner via the archived-inclusive search
   (`duplicate_risk`, never creates)**; missing/empty email on the
   automated path → no create, `duplicate_risk` (D1 rule 5);
   archived-only email match → no create, no bind, no un-archive,
   `duplicate_risk` with `"active": false` candidate detail (D1 rule 7); no settings flag/config combination bypasses any
   D1 rule (no-bypass test); uniqueness constraints hold as the backstop
   (direct-create attempts collide).
4. **`test_customer_fallback_partner.py`** — field exists on
   `shopify.connector.store.settings` with type
   `Many2one('res.partner')`; unset by default, no auto-created partner
   anywhere; setting/unsetting it changes **no** matching outcome
   (Posture A behavioral proof); no importer code path reads it
   (outcome-equivalence test on identical payload streams).
5. **Cross-cutting guard tests (distributed across the four files):**
   zero `sale.order`/order-model references; zero product-model
   writes; zero Shopify mutation construction anywhere in the diff
   (source-level grep-style assertion mirroring Task 010's); no
   `shopify_connector_core` file modified (enforced by review/`git diff`,
   restated as a PR-body obligation rather than a runtime test).
6. **Odoo.sh validation expectation:** all four files must run green
   (`0 failed, 0 error(s)`) on a live Odoo 19/PostgreSQL Odoo.sh branch
   database **before merge** (SRR-06 standing practice; the same
   requirement every task since PR #121 has carried). Static-only
   validation must be reported honestly as such in the draft PR if no
   runtime is reachable at coding time, with the live run then mandatory
   before merge. **Test-count reporting note (OP-43):** the validation
   record must quote the build log's own summary lines verbatim and must
   not synthesize per-module totals — the Task 010 record's unreconciled
   arithmetic (OP-43) is the lesson.

**Alternatives considered:** a fifth dedicated ACL test file (rejected —
the established convention tests access inside each model's own file); a
live-Shopify integration test (rejected — criterion 11/VAL-B2 boundary:
no live dependency beyond the Task 003 client; fake-client only).

---

## Standing boundaries restated (not new, not weakened)

No order logic; no customer export; no product/inventory/fulfillment
logic; no UI/view/menu/wizard/webhook/OAuth file; no core edits beyond
the three inheritance seams declared in the domain module's own file; no
live-Shopify call in tests; fake-client tests allowed; single-PR
rollback; draft PR + stop. (Full statements: final prompt §4–§6, §13.)

## Explicit non-authorizations

This brief does not decide D1–D8 (recommendations only), does not open
the customer-domain gate, does not authorize Task 011/012/013/014/015 or
any code, does not issue or render usable any implementation prompt, and
does not resolve OP-01/OP-02 (which close only via ChatGPT's own acts).

## Evidence / references

- [`next-gate-readiness-roadmap.md`](./next-gate-readiness-roadmap.md) §4
  (the D1–D8 list and prior decision inputs) — Accessible, this
  repository, 2026-07-10.
- [`mbq-55-customer-binding-naming-schema-proposal.md`](./mbq-55-customer-binding-naming-schema-proposal.md)
  (Accepted, comment `4928377625`) §3/§4/§7–§12 — Accessible, 2026-07-10.
- [`customer-domain-gate-criteria-proposal.md`](./customer-domain-gate-criteria-proposal.md)
  (Accepted as criteria only) §3 criteria 5/9/13/14/15 — Accessible,
  2026-07-10.
- [`task-010-product-import-final-implementation-prompt.md`](./task-010-product-import-final-implementation-prompt.md)
  §8–§10 (the accepted precedent D1/D7/D8 mirror) — Accessible,
  2026-07-10.
- Merged core code, read directly, read-only, 2026-07-10:
  `shopify_connector_job.py` (state machine, subreasons, error classes,
  `_transition_blocked_manual_review`, `_domain_flag_for_job_type`),
  `shopify_connector_job_log.py` (log fields), 
  `shopify_connector_store_settings.py` (`sale_domain_enabled`,
  extension-seam docstring), `shopify_connector_binding_mixin.py`.
- Official sources (all fetched/re-verified 2026-07-10, Accessible unless
  noted; full excerpts in
  [`../00-source-materials/shopify-customer-odoo19-partner-task-011-captures.md`](../00-source-materials/shopify-customer-odoo19-partner-task-011-captures.md)):
  Shopify `Customer`, `MailingAddress`, `customers` query, access-scopes,
  versioning, rate-limits, protected-customer-data pages; Odoo 19
  `res_partner.py`, `sale/models/sale_order.py`, `odoo/tools/mail.py`
  (`email_normalize`) from the official `odoo/odoo` 19.0 branch.

**Next step:** ChatGPT reviews this brief together with
[`task-011-final-implementation-prompt.md`](./task-011-final-implementation-prompt.md)
(which carries these recommendations as prompt content) and
[`task-011-customer-domain-gate-opening-proposal.md`](./task-011-customer-domain-gate-opening-proposal.md).
Accepting the final prompt is the act that converts D1–D8 from
recommendations into fixed prompt content — this brief performs no such
act.
