# Security & PII Matrix — Waves 2–6 New Surfaces

> **Status: Proposed — Fable gap-closure mission, 2026-07-16. Planning only;
> no test executed; no gate opened.** Extends the merged Wave 1 SEC-1
> security posture (stored-field classification, redaction, ACL/negative
> tests — acceptance-matrix rows 2/19) to the surfaces the Wave 2–5 domains
> introduce. Role vocabulary is the proposed two-role model of
> [`../02-product/connector-roles-and-permissions.md`](../02-product/connector-roles-and-permissions.md)
> (Connector User / Connector Administrator; hidden PII technical group per
> its §3). PCD levels: [Fact] Shopify Protected Customer Data Level 2 =
> name, address, email, phone (access logging, minimization, retention
> discipline); Level 1 = other customer data
> ([captures §12](../00-source-materials/shopify-orders-cod-abandoned-fulfillment-captures-2026-07-16.md)).
> Redaction baseline: the existing append-only redacted `job.log`
> (`_system_append`) and
> [`security-redaction-test-plan.md`](./security-redaction-test-plan.md) /
> [`credential-security-redaction-review-checklist.md`](./credential-security-redaction-review-checklist.md).

## Matrix — one section per new surface

Column key: **Data classes** (what the surface stores/displays) · **PCD**
(Shopify level mapping) · **Role visibility** (User vs Administrator) ·
**Field groups** (field-level `groups=` requirements) · **Redaction** (log
rules) · **Retention** (sweep coverage) · **Audit** · **Residue** ·
**Credentials** · **Threats** · **Required tests**.

### 1. Order records incl. customer PII + COD amounts (Wave 2)

- **Data classes:** Shopify order identity (GID, name/number); customer
  snapshot fields (name, email, phone, addresses); financial evidence
  (totals, tax/discount/shipping breakdowns, gateway names,
  `manualPaymentGateway` flags); COD ledger values and collection events
  (amounts, courier references, actor identities, notes).
- **PCD:** customer snapshot fields = **Level 2**; order line/financial data
  = Level 1. [Inference] COD collection amounts are connector-owned
  operational data, not Shopify PCD — but they are financially sensitive
  and inherit the same masked-by-default display posture.
- **Role visibility:** User sees orders with **masked PII by default**
  (partial email, no phone/address); unmasked PII is Administrator-only
  unless the per-store Administrator toggle grants Users unmasked access
  (roles doc §3). COD ledger/collection events visible to User (operational
  duty); discrepancy resolution Administrator-only.
- **Field groups:** PII snapshot fields carry field-level `groups=` on the
  hidden PII group (re-keyed from `reviewer,admin` per roles doc §4.6), with
  computed masked display for non-members; [Fact] field-level `groups=`
  removes fields from views and `fields_get` and blocks ORM read/write
  (captures §5) — masking must be group-based, never view-only.
- **Redaction:** logs carry order GIDs and counts, never customer names/
  emails/phones/addresses; collection-event log lines carry amounts +
  event IDs, never free-text notes (notes may contain PII).
- **Retention:** order-binding PII snapshots covered by the existing PII
  retention sweep; `customers/redact`/`shop/redact` webhook handling must
  scrub order-level customer snapshots ([Fact] obligations, captures §12).
- **Audit:** every unmask access is logged (PCD Level 2 access-logging);
  every collection event append-only with actor; discrepancy resolutions
  recorded as decisions, never edits.
- **Residue:** disconnect preserves history (MBQ-08) but a redaction
  request/retention expiry leaves zero PII residue in bindings, jobs, logs,
  or attachments.
- **Credentials:** none stored on this surface; `read_all_orders` scope
  state mirrored, never the token.
- **Threats:** PII in logs via order-import error payloads (raw Shopify
  response echoes customer data — must be redacted in error detail
  expands); COD amount tampering (mitigated: append-only events +
  compensating corrections); mark-as-paid abuse (mitigated: rule L-3 +
  Administrator policy + discrepancy freeze).
- **Required tests:** PII / ORM-security (masked default, toggle unmask,
  `fields_get` omission); redaction scan over import-error logs containing
  synthetic PII; permissions matrix (User vs Administrator on discrepancy
  resolution, policy fields); retention/redaction sweep test; append-only
  enforcement test.

### 2. Abandoned checkouts (post-MVP workspace; MVP = absence)

- **Data classes:** checkout identity, line items, value, `email_state`/
  `recovery_state`/`status`, nullable customer contact, **recovery URL**.
- **PCD:** customer fields = **Level 2**; [Fact] abandoned-checkout data is
  explicitly PCD (captures §5/§12). The recovery URL grants cart access and
  is treated as sensitive.
- **Role visibility:** MVP: surface does not exist (PD-AC-1/2 — the binding
  MVP test is *absence*). Workspace, when built: User sees masked contact
  data; recovery URL Administrator-only [Recommendation — abandoned doc
  §3.1]; unmask follows the roles-doc mechanism with no checkout-specific
  exception ([Open question OQ-E of the roles doc: whether checkout PII is
  always Administrator-only]).
- **Field groups:** customer fields + recovery URL behind the hidden PII
  group (URL possibly admin-group only, pending OQ-E).
- **Redaction:** checkout logs carry checkout IDs and counts only; never
  contact data or recovery URLs.
- **Retention:** **the PII retention sweep must cover the checkout cache**
  (PD-AC-3); `customers/redact`/`shop/redact` must purge/scrub cache rows —
  a cache outliving redaction is a compliance defect.
- **Audit:** every unmask access-logged; manual quotation action audited
  (actor, checkout id, store, timestamp — PD-AC-4).
- **Residue:** feature disable / uninstall drops the cache; MVP residue test
  = no checkout-derived record of any kind exists.
- **Credentials:** none; uses existing `read_orders` scope [Fact].
- **Threats:** recovery-URL leakage (cart takeover); dead-PII accumulation
  (mitigated: short default window, retention sweep); demand pollution via
  auto-quotations (structurally absent — PD-AC-1).
- **Required tests:** MVP: UAT-AC-1/2 absence tests + residue sweep.
  Workspace: masked-display, URL role gate, retention/redact purge,
  audit-log presence, reconnect re-scan without duplicates.

### 3. Fulfillment addresses and tracking (Wave 4)

- **Data classes:** delivery addresses (via order linkage), tracking
  numbers/URLs, carrier identity, fulfillment event timelines, FO assigned
  locations, external-fulfillment actor attribution (app title / staff
  user).
- **PCD:** destination address = **Level 2** (address); tracking/carrier =
  Level 1. [Inference] Tracking numbers are weak PII (correlatable to a
  person + address) — displayed to Users (operational necessity), excluded
  from logs beyond identifiers.
- **Role visibility:** User works fulfillment review cases and sees
  tracking/locations; the address itself follows the order-surface masking
  (§1). Mode selection/switching Administrator-only.
- **Field groups:** address snapshots inherit §1's PII group; mode setting
  is Administrator-only via Python-level `groups=` (modes doc §8).
- **Redaction:** [Fact — Task 014 §4 posture] recipient names are never
  logged; fulfillment logs carry picking/FO/Fulfillment GIDs, quantities,
  tracking refs, and the notification decision — never name/address.
- **Retention:** inbound evidence records and event timelines join the
  retention sweep with job-aligned windows; redaction requests scrub
  address-bearing snapshots.
- **Audit:** every Mode 2 auto-application stores its full 16-condition
  evidence snapshot; every manual validation/acknowledgement/tracking import
  audited; mode switches audited (who/when/from→to).
- **Residue:** mode-switch abort and Mode 2 rollback leave no partial stock
  effects (UAT-FM-3.2/3.3); uninstall drops evidence records per DEC-030.
- **Credentials:** none; merchant-managed FO scopes only (D-014-2).
- **Threats:** notification abuse (customer emails triggered
  unintentionally — mitigated: RA-009 default-off, persisted at enqueue);
  inbound spoofing of external fulfillments (mitigated: webhook HMAC at the
  receiver + live re-read condition 14); over-fulfillment as a stock-drain
  vector (mitigated: conditions 6/12 ledger).
- **Required tests:** redaction test asserting no recipient name in any log
  produced by the full Mode 1/2 suites; permissions test on mode switching;
  audit-snapshot presence test for every auto-application; residue tests on
  switch abort.

### 4. Layer 2 attempt records / fingerprints (Waves 3–5)

- **Data classes:** attempt identity (UUIDs), mutation intent (mutation name
  + target GIDs/handles/SKUs — identifiers only), preconditions snapshots
  (redacted JSON), SHA-256 request fingerprints, Shopify idempotency keys,
  remote evidence refs (GIDs, counts, error codes).
- **PCD:** none by design — [Fact — L2 design §12] payload bodies are never
  stored; fingerprints are SHA-256 hashes with **no PII derivable**;
  `preconditions_snapshot` is defined as redacted.
- **Role visibility:** attempt records are diagnostic: User read (review
  cases present attempt evidence — L2-D10); the audited
  `resolved_applied`/`resolved_not_applied` override is
  **Administrator-only with mandatory reason**.
- **Field groups:** no PII fields; override action server-side
  Administrator-gated.
- **Redaction:** enforced structurally (identifiers/counts/reasons only);
  a test must assert no field of the attempt model can contain a payload
  body (schema + negative content scan).
- **Retention:** terminal-job attempt rows pruned by the retention sweep
  after the configurable window (proposed 180 days — L2-D14); a `running`
  job's attempt row never pruned.
- **Audit:** the attempt table **is** audit evidence; after any mutation
  domain has run, rollback retains it even if the feature is disabled
  (L2-D14).
- **Residue:** pre-ship rollback drops fields/model cleanly; uninstall
  follows DEC-030 export-then-drop.
- **Credentials:** idempotency keys are not secrets but are replay-relevant
  — never logged outside the attempt record.
- **Threats:** **override abuse** (an Administrator marking an uncertain
  attempt resolved to force a replay — mitigated: override is local-only,
  audited, reasoned; corrective remote action is always a new wrapped job);
  wrapper bypass (mitigated: source-AST-guard — no mutation call site
  outside the wrapper).
- **Required tests:** unit (no-payload-storage schema test); AST guard;
  permissions (override Administrator-only, reason mandatory); retention
  prune test incl. never-prune-running; redaction content scan of attempt
  rows after the full mutation suites.

### 5. Backfill previews (Wave 2)

- **Data classes:** aggregate counts (new/changed/duplicate/skipped/
  needs-review), sample order records (which include customer identity),
  requested date ranges, scope/access-window findings.
- **PCD:** sample records expose the same Level 2 fields as §1.
- **Role visibility:** the wizard (and its samples) is
  **Administrator-only** (PD-RB-8); Users see only post-enqueue progress
  counts.
- **Field groups:** samples render through the same masked-field
  infrastructure as §1 — Administrator sees per their own rights; a future
  role relaxation must not leak samples.
- **Redaction:** preview job logs carry counts and range parameters only —
  never sample contents.
- **Retention:** previews are ephemeral (no records created — PD-RB-8 §5.3);
  a test asserts zero persisted preview artifacts beyond the audit entry
  (range, counts, actor, confirm/abort).
- **Audit:** preview run + confirmation (or abandonment) audited with actor
  and parameters; batch id links enqueued jobs to the confirming preview.
- **Residue:** aborted/expired previews leave zero rows; interrupted
  backfills leave only generation-fenced jobs + progress records.
- **Credentials:** surfaces the *absence* of `read_all_orders` — must never
  display token material while doing so.
- **Threats:** mass-PII exfiltration via repeated wide-range previews
  (mitigated: Administrator-only + access audit); silent-truncation
  dishonesty (mitigated: UAT-RB-3.2's mandatory pre-scan disclosure).
- **Required tests:** permissions (User cannot open/confirm — UAT-RB-3.7);
  residue (no records from preview); redaction of preview logs; audit
  presence for confirm and abort paths.

### 6. Two-role migration (SEC-2, Wave 5)

- **Data classes:** group definitions, `implied_ids` links, privilege
  records, user↔group membership rows, migration audit log lines.
- **PCD:** none directly — but the migration **controls** every PII gate
  above, so its failure modes are PII failures.
- **Role visibility:** user form shows exactly one "Shopify Connector"
  selection with *User* / *Administrator*; the four legacy groups hidden
  (developer-mode only, "Technical /" prefixed).
- **Field groups:** PII field `groups=` re-keyed from `reviewer,admin` to
  the hidden PII group with **default membership = Administrator** — the
  migration must not widen PII visibility as a side effect.
- **Redaction:** migration log lines carry logins and group names — no PII
  concern beyond ordinary log access control.
- **Retention:** n/a (security data is permanent); legacy memberships
  deliberately retained for rollback (roles doc §4.7/§4.10).
- **Audit:** one log line per changed user; migration re-run produces
  identical membership (idempotency) and no duplicate audit spam.
- **Residue:** rollback deletes only the new group + links; uninstall drops
  all six groups together ([Fact] module-owned XML-ID cascade, captures §7).
- **Credentials:** `access_token` field `groups=` stays admin-only
  throughout — a migration bug here is the worst-case escalation.
- **Threats — privilege escalation via role migration (primary):**
  (a) legacy Operators silently gaining admin-tier acts — mitigated by the
  no-escalation test (exactly reviewer-tier acts gained, credentials/
  settings/destructive overrides still denied); (b) hidden groups manually
  assigned in developer mode bypassing UI gates — mitigated: server-side
  gates must hold regardless (roles doc §4.9.5); (c) PII group membership
  accidentally defaulted to all Users — mitigated by the §4.9.4 field-level
  test; (d) `noupdate` group data silently not applying implied_ids edits
  (OQ-B) — mitigated by asserting the post-migration closure explicitly.
- **Required tests:** the full roles-doc §4.9 suite — ACL matrix (5 user
  archetypes × every model), migration idempotency (script twice),
  no-privilege-escalation, field-level PII, UI hiding + server-side-holds,
  implication closure (admin → 5 groups, user → 4).

## Cross-cutting requirements (all surfaces)

1. **Token/PII leak scan** after every Wave 6 UAT session: zero secrets or
   Level 2 fields in logs, job records, attempt rows, or error expands
   (acceptance-matrix rows 2/22 criteria).
2. **DEC-028 deployment posture** must be evidenced **before any
   real-customer PII** enters a UAT environment — dev-store synthetic data
   only until then ([Fact] acceptance-matrix row 2).
3. **Redaction webhooks** (`customers/redact`, `shop/redact`) must
   enumerate every surface above in their handler coverage test — orders,
   COD events (customer-linked), fulfillment snapshots, checkout cache
   (when built).
4. **No new role, no new error class, no new manual-review sub-reason** is
   introduced by any of these surfaces — a matrix test asserts vocabulary
   closure.

## Open items

- [Open question] OQ-A/OQ-E (roles doc): PII toggle mechanism and checkout
  PII strictness — both change §1/§2 rows' test details when resolved.
- [Open question] Whether COD collection-event *notes* should be
  structurally PII-restricted or covered by guidance + redaction only —
  proposed for the Wave 4 packet's security section.
