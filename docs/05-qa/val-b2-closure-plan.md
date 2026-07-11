# VAL-B2 Closure Plan

> **QA/evidence plan. Not an implementation task, not a claim that VAL-B2 has
> passed.** This document exists so that whenever a human operator with real
> Shopify Partner/Dev Dashboard account access is available, VAL-B2 can be
> closed with a single, unambiguous, evidence-recorded session — entirely
> outside the Odoo codebase, with zero code change. It operationalizes
> [`../04-decisions/DEC-023-token-acquisition-and-val-b2.md`](../04-decisions/DEC-023-token-acquisition-and-val-b2.md)
> §3.1. Status: **Proposed** — not yet executed by any session to date.
>
> **Revised 2026-07-08 (second pass), after ChatGPT review:** Path 2 below
> (cross-organizational Custom Distribution app) is a **one-store evidence
> path for VAL-B2 only**. It is not, and must not be read as, proof that
> Custom Distribution is a valid mechanism for distributing the connector to
> many unrelated customer stores — Shopify's own distribution-method
> documentation scopes Custom Distribution to one store, or multiple stores
> in the same Plus organization only. See DEC-023 §2/§3.2 for the corrected
> framing and the separate, unresolved many-customer/commercial-distribution
> question (branch B).

## Status

- **VAL-B2 remains BLOCKED, not passed, not failed**, per
  `task-003-validation-results.md` §5's Go/No-Go recommendation.
- **DEC-021's deferral of VAL-B2 from the Task 003 → Task 004 gate is
  unchanged** — this plan does not touch that deferral; it exists to actually
  close VAL-B2 itself, which DEC-021 explicitly left required "before
  customer-facing setup, activation, or any live 'connected' claim."
- **No prior session has had the access this plan requires.** PR #108/#109's
  attempt was blocked before reaching Shopify at all (no browser-automation
  tool, no Dev Dashboard credentials/login path available to that execution
  environment). This plan does not assume that access now exists — it defines
  exactly what is needed so a future session (or a human operator acting
  directly, with only the redacted outcome reported back) can execute it.

## 1. Exact preconditions

Before attempting closure, confirm all of the following are actually available
— do not proceed on an assumption:

1. **A Shopify Partner organization / Dev Dashboard account** with permission
   to view or create custom apps.
2. **A Shopify development store** reachable from that account — either the
   existing project test store (`mqiu21-yz.myshopify.com`, used in prior
   sessions per `task-003-validation-results.md`) or a fresh development store
   created via the Dev Dashboard.
3. **Check first, before doing anything else:** does this Partner
   organization already hold **any pre-2026-01-01 legacy admin-created custom
   app** on any development store? (Check Shopify admin → Settings → Apps →
   "Legacy custom apps," or the equivalent Dev Dashboard view.) If yes, this is
   the fastest, highest-confidence closure path (§3, Path 1) — do not skip this
   check in favor of a manual OAuth exchange.
4. **A secure channel to handle the resulting secret.** Per this project's
   standing rule (unchanged by this plan): a Shopify Client ID/Client Secret or
   Admin API access token must **never** be typed into chat, committed to a
   file, or pasted into any doc/PR by an agent session. Only a human operator,
   or a securely provisioned, session-scoped credential mechanism, may handle
   the actual secret value. Any session executing this plan reports only the
   **redacted outcome** (pass/fail, error class, scopes granted) — never the
   token/secret itself.
5. **A live Odoo 19 instance** with this connector's `shopify_connector_core`
   module installed, reachable by the executing session (e.g. an Odoo.sh
   branch database, matching how prior live validation sessions — PR #103/#115
   — operated).

If any precondition is missing, **stop and record which one** — do not
substitute an assumption or a dummy value for it.

## 2. Test store requirements

- Must be a genuine Shopify **development store** (not a production store) —
  this matches the existing `task-003-manual-validation-checklist.md`
  precondition and is confirmed sufficient per
  `shopify-token-acquisition-research.md` §8 (no Admin API restriction on
  development stores affects this connector's read-only
  `action_test_connection()` call beyond commerce/checkout-transaction
  restrictions that are out of scope for it).
- No real payment/checkout activity is required or possible on a development
  store — irrelevant to this test.
- The store's Shopify **API version** configured on the connector's store
  record must match a currently-supported Shopify API version (the project
  has previously used `2026-07`; use whichever version is current and pinned
  at execution time).

## 3. Token-acquisition paths, in preference order

### Path 1 — Legacy admin-created custom app (try first)

If precondition §1.3 found an existing pre-2026-01-01 legacy custom app:

1. Open the app in the Shopify admin ("Legacy custom apps" section).
2. Reveal/copy its Admin API access token directly in the admin UI (no OAuth).
3. Note the exact scopes configured on that app (must cover the six MVP scopes
   below, §4).
4. Proceed to §5 (execution steps) with this token.

This path requires zero OAuth, zero redirect endpoint, and matches the
connector's existing `token_variant='offline_custom_app'` shape exactly as
already shipped.

### Path 2 — Cross-organizational Custom Distribution app, ONE store only (recommended if Path 1 unavailable)

**Scope of this path, stated explicitly:** this is a **one-store evidence
path for VAL-B2** — it registers a single Custom Distribution app against a
single test development store, purely to obtain one token and observe one
result. **It is not, and this plan does not claim it to be, a demonstration
that Custom Distribution can serve many unrelated customer stores.** Shopify's
own distribution-method documentation scopes Custom Distribution to "one
store or multiple stores on the same Plus organization using a link"
(https://shopify.dev/docs/apps/launch/distribution/select-distribution-method
— Accessible — 2026-07-08); nothing in this path or its result should be
read as evidence about distribution scale, only about OAuth token-flow
mechanics for one app+store pair. Per `shopify-token-acquisition-notes.md` §2
and DEC-023 §2/§3.1, this is the combination Shopify's own staff guidance
indicates is most likely to support a non-expiring offline token via the
standard authorization-code-grant flow, for that one store:

1. Register a Custom Distribution app in a Shopify Dev Dashboard organization
   that is **different** from the organization that owns the test development
   store (e.g. a separate Partner account/org used specifically for this
   validation, distinct from the store-owning org).
2. Configure a redirect/callback URL for that app pointing at a location the
   executing session can actually receive a callback at (e.g. a temporary
   local HTTPS tunnel, or the test Odoo instance's own reachable URL if it
   already exists) — register this exact URL in the Dev Dashboard as required.
3. Generate the app's install link and install it on the test development
   store (a cross-organization install, completing the standard merchant
   consent screen).
4. Drive the standard authorization-code-grant flow by hand (generic tooling —
   e.g. a documented `curl` recipe — outside the Odoo codebase): redirect to
   `/admin/oauth/authorize` with the required parameters, capture the callback,
   verify its `hmac`, exchange the resulting `code` for a token via
   `POST /admin/oauth/access_token` with `expiring` omitted (or explicitly `0`)
   to request a **non-expiring** offline token.
5. Record the **observed result** (success or failure) as a fact, not an
   assumption — this is the empirical test DEC-023 §2 flags as still unverified.

### Path 3 — Same-organization own-store app (do not rely on this; try only opportunistically)

Per the new evidence, a Dev-Dashboard app built by the **same** organization
that owns the store is expected to be routed to client-credentials-grant only
(a 24-hour token) — **not** a workable single-secret path for this connector
without building a refresh loop, which is out of scope. If Path 1 and Path 2
are both unavailable, this path may be tried opportunistically purely to
confirm or deny the residual open question in
`shopify-token-acquisition-notes.md` §2, but its failure (routing to
client-credentials) should be **expected**, not treated as a connector defect.

## 4. Required scopes

The token must carry, at minimum, the six scopes the connector's shipped
`REQUIRED_MVP_SCOPES` constant checks (`shopify_connector_readiness_check.py`):

- `read_products`
- `read_customers`
- `read_orders`
- `read_inventory`
- `read_locations`
- `read_fulfillments`

**Known caveat, carried from `shopify-token-acquisition-notes.md` §3 and
DEC-023 §5:** `read_fulfillments` is required here **only for current-code
compatibility** with the shipped `REQUIRED_MVP_SCOPES` check — per official
Shopify documentation it does not actually gate read access to order
fulfillment data (it governs `FulfillmentService` only); `read_orders`
(already in this list) is the scope that actually covers `Fulfillment` reads.
Grant `read_fulfillments` anyway for this closure attempt (matching the
shipped code's current check, so the readiness-check's required-scopes gate
reports `pass` rather than an unrelated `fail`), but do not treat its
presence as proof that fulfillment-object reads are covered by it. **This is
a least-privilege correctness concern, not merely a naming nitpick:**
requiring a scope that does not grant the access its name implies is exactly
the kind of over-broad/mis-scoped grant DEC-004's least-privilege posture
exists to avoid, and it must be explicitly routed (corrected or justified) by
ChatGPT/a future task **before** this connector makes any customer-facing
setup-readiness claim — it is flagged here, not resolved, and is not fixed by
this closure plan.

Do not grant broader scopes than these six for this validation. Any
additional scope needed later belongs to a future domain task's own scope
decision, not this closure.

## 5. Test command / manual execution steps

Once a compatible token is obtained (via Path 1 or 2 above) and pasted into
the connector's existing credential-entry mechanism (Task 002's shipped
`action_set_token`/`action_replace_token` on
`shopify.connector.store.credential` — no new code, no new field):

1. In the live Odoo shell/instance, call
   `store.action_test_connection()` on the store record configured with the
   new token.
2. Record, verbatim, the resulting field values on the store record:
   - `last_test_connection_result`
   - `last_test_connection_reason`
   - `credential_last_verified_at`
   - `granted_scopes` (the raw JSON array of scope handles returned)
   - `granted_scopes_checked_at`
   - `credential_state` on the linked credential row
3. Record the resulting `job` row's `state`, `job_type`
   (`core_test_connection`), and `job_source`.
4. Record the exact count and `event_type` of the `job.log` rows created for
   that job.
5. Run `store.action_test_connection()` a **second** time immediately
   afterward (this repeats the connector's existing VAL-B3 idempotency check)
   and record whether a second, distinct `job` row is created with no
   unique-constraint collision.
6. If time and access permit, also run `shopify.connector.readiness.check.run_for_store(store)`
   and record its aggregated result and the six-scope check's individual
   outcome — this is supplementary evidence, not a substitute for steps 1–5.

## 6. Evidence to capture

For the resulting record in `task-003-validation-results.md` (or a successor
results file — this plan does not itself edit that file), capture:

- Which path (1, 2, or 3) was used, and why.
- The Shopify development store handle/domain used.
- The Shopify API version configured at execution time.
- Every field value listed in §5, verbatim.
- The exact scopes granted (from the `granted_scopes` snapshot), compared
  against the six required in §4.
- Whether the token was non-expiring or expiring (and, if expiring, its
  `expires_in`/refresh-token behavior) — this matters because the connector's
  shipped schema has no expiry/refresh field; an expiring token would surface
  a gap, not a pass, per §7 below.
- **Never** the token or client secret value itself — only redacted
  confirmation that a value was present and accepted.
- A plain statement of whether Path 2's cross-organizational
  authorization-code-grant hypothesis (DEC-023 §2) succeeded or failed, since
  this is independently valuable evidence regardless of VAL-B2's own outcome.

## 7. Pass / fail criteria

**VAL-B2 passes only if all of the following are true, exactly as
`task-003-manual-validation-checklist.md` already defines it:**

- `store.action_test_connection()` completes with the job's `state='succeeded'`.
- `last_test_connection_result == 'pass'`.
- `credential_last_verified_at`, `granted_scopes`, and
  `granted_scopes_checked_at` are all populated (non-empty).
- `last_test_connection_reason` is cleared (`False`/empty).
- The token used was obtained via a real Shopify development store (not a
  dummy/synthetic value) and is compatible with the shipped
  `token_variant='offline_custom_app'` shape (i.e., a single static secret —
  not a 24-hour client-credentials token requiring an unimplemented refresh
  loop).

**VAL-B2 fails if:** `action_test_connection()` raises `ShopifyClientError`,
`last_test_connection_result == 'fail'`, or the only token obtainable is a
24-hour client-credentials token that would expire before any realistic sync
cycle without connector-side refresh logic that does not exist today — a
failure here is evidence for DEC-023 §3.2 (build real OAuth), not a defect in
the already-shipped code.

## 8. What does NOT count as VAL-B2 passing

- **A dummy or synthetic token succeeding** does not count — VAL-B1 already
  covers invalid-token behavior; VAL-B2 requires a **genuine** development-store
  token.
- **A 24-hour client-credentials token being pasted in and working once**
  does **not** count as a pass in the sense DEC-021 requires — it would prove
  the connection call itself works, but not that the connector's *shipped,
  no-refresh* credential model is viable for ongoing use. If this is the only
  token obtainable, record it honestly as a **partial/qualified** result and
  escalate to ChatGPT per DEC-023 §3.2, not as an unqualified VAL-B2 pass.
- **Reading `store.granted_scopes` or `store.last_test_connection_result`
  after the fact without ever having run a live `action_test_connection()`
  call against a real Shopify store** does not count — the readiness check's
  own `_check_credential_test_connection` is explicitly documented as
  stored-evidence-only and must never be treated as a substitute for the live
  call (`DEC-021` §4's fail-closed rule).
- **Any claim of "connected"/"pass" made in this document itself** — this
  document does not claim VAL-B2 has passed; it defines how it would be
  closed, by a future session with the required access.
- **Any code, schema, or configuration change made in order to make the test
  pass** — if the shipped code needs a fix to pass validly (e.g., the
  `read_fulfillments` finding in §4 turning out to matter), that is a separate,
  explicitly-gated implementation task, not part of this closure.
- **A successful Path 2 attempt does not count as proof that Custom
  Distribution can serve many unrelated customer stores.** It is one-store
  evidence only (§3, Path 2); the many-customer/commercial-distribution
  question is separate and unresolved (DEC-023 §3.2 branch B).

## 9. Security constraints (binding, unchanged from existing policy)

All items from
[`credential-security-redaction-review-checklist.md`](./credential-security-redaction-review-checklist.md)
apply unchanged to this closure attempt. In particular:

- The token/secret is never pasted into chat, a commit, a PR body, or any file
  under `docs/`.
- No encryption claim is made anywhere in the recorded evidence.
- The token never appears in any log, job-log row, or exception message
  captured as evidence — only the redacted field values listed in §5/§6.
- Any `sudo()` used to retrieve the token for entry remains exactly the two
  already-justified, already-shipped elevations (`_get_access_token`, the
  job-log system-append writer) — no new elevation is introduced.
- If a cross-organizational app (Path 2) is registered, its Client Secret is
  handled only by the human operator or a securely provisioned, session-scoped
  mechanism — never typed into an agent's chat context.

## 10. How to record results

1. Execute the applicable path (§3) and steps (§5) in a live Odoo + Shopify
   session, exactly as prior live-validation sessions (PR #103, #107, #115)
   have done.
2. Update `task-003-validation-results.md`'s VAL-B2 row and its Go/No-Go
   section (§2 and §5 of that file) with the observed, redacted evidence — do
   not edit this closure plan itself to record a pass; this plan is the
   procedure, not the results ledger.
3. Update `research-handoff.md` with a compact entry naming the session,
   branch/PR, and the observed pass/fail outcome.
4. If VAL-B2 passes: note this explicitly does **not**, by itself, resolve
   MBQ-05 or authorize a setup wizard/OAuth build — those still require their
   own separate ChatGPT decision and gate, per DEC-023 §7/§8.
5. If VAL-B2 fails (including the "qualified/partial" case in §8): escalate to
   ChatGPT with the exact failure evidence, per DEC-023 §3.2's recommended next
   step (build real OAuth, using the vendor-owned cross-organizational app
   shape).

## 11. Explicit non-claims

This document does not itself close VAL-B2, does not resolve MBQ-05, does not
authorize any code, and was not executed by this session — no Shopify account,
Odoo instance, or real token was reachable from this documentation-only
session. It is the procedure a future, appropriately-provisioned session (or
human operator) should follow.

## 12. Planning-completion addendum (2026-07-10, AR-042 session — plan audit; procedure above unchanged)

> Appended by the MVP planning-completion session after auditing this
> plan against the required VAL-B2 planning dimensions. **VAL-B2 is
> hereby classified `[External validation required]` — a live-execution
> item, not a research gap.** All research-closable planning is complete;
> what remains needs a human operator with Shopify Partner/Dev Dashboard
> access. Nothing below changes §1–§11's procedure or claims a pass.

### 12.1 Status refresh against DEC-026 (2026-07-10)

**[Verified repository state]** ChatGPT has since accepted DEC-026
(strategic direction: branch A unchanged; B-1 public/limited-visibility
is the Phase-2+ target; B-3 not the commercial-scale answer). This
changes nothing in this plan: Path 1/Path 2 remain the branch-A
one-store evidence paths exactly as DEC-023 accepted them. A proposed
branch-A scope rule (single pilot by default, per-customer ChatGPT
approval, soft ceiling of three) is now drafted as
[`../04-decisions/DEC-027-branch-a-pilot-customer-scope-proposal.md`](../04-decisions/DEC-027-branch-a-pilot-customer-scope-proposal.md)
— Proposed, not accepted; it does not alter this plan's one-store scope.

### 12.2 Result template (copy into `task-003-validation-results.md` §VAL-B2 when executed)

```text
VAL-B2 execution record — <date>
Operator: <human operator role — no personal data required>
Path used (§3): <1 | 2 | 3> — reason: <why>
Store: <dev store domain>   API version: <e.g. 2026-07>
App type: <legacy admin custom app | custom-distribution app (cross-org)>
Scopes granted (verbatim granted_scopes JSON): <redact nothing here — scope
  handles are not secrets>
Token type observed: <non-expiring offline | expiring (expires_in=…) | 24h client-credentials>
--- Odoo-side observations (verbatim field values, §5) ---
last_test_connection_result: <pass|fail>
last_test_connection_reason: <empty|value>
credential_last_verified_at: <ts>   granted_scopes_checked_at: <ts>
credential_state: <present|invalid>
job: state=<…> job_type=core_test_connection job_source=<…>
job.log rows: <count + event_type list>
Second run (§5.5): distinct job created without constraint collision: <yes|no>
Readiness run (§5.6, optional): aggregate=<pass|warning|fail>; required_scopes check=<…>
--- Verdict (§7/§8) ---
VAL-B2: <PASS | FAIL | PARTIAL/QUALIFIED — reason>
Path-2 cross-org authorization-code-grant hypothesis (DEC-023 §2): <succeeded|failed|not attempted>
Anomalies / deviations from plan: <…>
```

### 12.3 Rollback / cleanup after execution

1. If the run used a **temporary cross-org app** (Path 2): uninstall the
   app from the test store and delete (or archive) the app registration
   in the Dev Dashboard once evidence is recorded — do not leave an
   unused credentialed app installed.
2. In Odoo: either keep the store record for continued validation, or
   run `action_disconnect()` (clears the token via the credential
   service, cancels non-terminal business jobs, preserves history —
   merged Task 005 behavior). **Never** delete job/job.log rows — they
   are the audit trail.
3. Rotate/invalidate the token in the Shopify admin if the store record
   is being kept but active validation is finished.
4. No repository rollback is needed — the plan requires zero code change;
   if any code change was made to force a pass, the run is invalid (§8).

### 12.4 Escalation path

- **PASS** → record per §12.2; notify ChatGPT; VAL-B2's register rows
  (OP-06; sync-engine Blocking Question 2) may then be closed by
  ChatGPT, not by the executing session.
- **FAIL / PARTIAL** (incl. only-24h-token obtainable) → escalate to
  ChatGPT with the exact evidence per §10.5; expected consequence per
  DEC-023 §3.2 is prioritizing the real-OAuth build inside the Phase-2+
  B-1 path — not a hotfix to shipped code.
- **Blocked precondition** (§1) → record which one; no substitute values.

### 12.5 Follow-up empirical checks to piggyback on the same live session (optional, evidence-only)

If time permits after §5, the same store/token may be used to close
live-Shopify empirical unknowns (OP-34), each recorded as observations
only: GraphQL cursor reuse after a pause (Q10); THROTTLED response-body
shape (Q40 — requires deliberately exceeding cost limits; skip if
impractical); `orders(query: "updated_at:>…")` sub-minute granularity
behavior. None of these is required for the VAL-B2 verdict.
