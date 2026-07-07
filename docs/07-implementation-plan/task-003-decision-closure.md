# Task 003 Decision Closure

> Decision-closure package for **Task 003 — API Client Shell and Test
> Connection**. Prepared 2026-07-07 on branch
> `claude/task-003-decisions-xx7u85`, from `Shopify-connector` at PR #97's
> merge commit `7498ba181a01e571204e471d6880ea0c2068fd87` (confirmed the
> tip of `Shopify-connector` before starting; `git diff
> origin/Shopify-connector..HEAD --stat` was empty at session start). This
> document resolves the four Task 003-specific decision points that
> AR-024 (2026-07-06) named and left explicitly open, and that AR-025
> (2026-07-06/07, Task 002's own decision closure) explicitly deferred to
> this round:
> [`task-003-api-client-test-connection-proposed.md`](./task-003-api-client-test-connection-proposed.md)
> §Status. Review row: **AR-027** in
> [`../05-qa/architecture-review-log.md`](../05-qa/architecture-review-log.md).
> **Originally proposed 2026-07-07; accepted by ChatGPT the same day with
> an F1 revision narrowing Decision 4's scope** (see §Acceptance below —
> this acceptance patch was applied within this same PR, per the
> AR-025/PR #94 convention).
>
> **Session constraint — no external research performed.** This session
> was explicitly scoped without network access. No new Shopify/Odoo
> official-source lookups were made. Every Shopify/Odoo platform
> statement below is **reused, verbatim-cited, from already-accepted or
> already-written repo documents** (chiefly
> [`../03-architecture/credential-connection-api-client-planning.md`](../03-architecture/credential-connection-api-client-planning.md),
> accessed/cited 2026-07-06, and
> [`DEC-009`](../04-decisions/DEC-009-error-retry-idempotency-strategy.md)).
> Nothing below asserts a Shopify behavior that is not already cited
> somewhere in the repo; anything the repo does not already cite is
> labelled **[Requires external validation before implementation]**, not
> asserted as fact.

## Acceptance

- **Accepted by ChatGPT on 2026-07-07** (PR #98 F1 revision;
  [`AR-027`](../05-qa/architecture-review-log.md)) — **decisions 1–3
  accepted as proposed; Decision 4 accepted with a scope-narrowing
  revision.**
- **Decision 1 accepted:** `core_test_connection` is confirmed as the
  `job_type` value, added directly to the base Selection on
  `shopify.connector.job`. **This amends AR-019's "exactly two
  core-owned `job_type` values" statement to three**, effective once
  this PR merges (see Register impact below).
- **Decision 2 accepted:** `SHOP_INACTIVE`, HTTP 402 (frozen shop), HTTP
  423 (locked shop), and HTTP 403 (fraudulent-store or similar Shopify
  shop-state block) all map to `shopify_permission_scope_auth` for Task
  003. The specific behavioral shapes not already cited in the repo
  (exact `THROTTLED` body; 401 vs. 200+`ACCESS_DENIED`; missing-scope
  shape; whether `shop`/`currentAppInstallation` need any scope) remain
  `[Requires external validation before implementation]` — **not**
  resolved by this acceptance. The `credential_state`-gating refinement
  (flips to `invalid` only for a genuine token-invalid signal, never for
  a shop-account-state condition) is accepted. **Distinct plain-language
  failure reasons per condition are mandatory**, not optional — a single
  generic message reused across `SHOP_INACTIVE`/402/423/403 fails this
  acceptance.
- **Decision 3 accepted:** a single, internal, documented
  `sudo()`-wrapped job-log system-append write method is the sanctioned
  path for Task 003 (and future log-writing tasks). **No ACL widening
  and no `security/ir.model.access.csv` /
  `shopify_connector_security.xml` change for Task 003.** The
  one-narrow-documented-`sudo()` rule (mirroring the Task 002
  `_get_access_token` precedent) applies — exactly one new `sudo()` call
  site, justified in writing in the eventual implementation PR.
- **Decision 4 accepted with revision (F1):** a per-run UUID4 nonce in
  `payload_hash` is accepted **for `core_test_connection` job creation
  only**. The earlier proposal's implication that Task 003 should also
  populate the nonce for the already-merged `core_readiness_check` job
  type is **rejected as written** — that is a **separate, pre-existing
  latent risk**, now recorded as **`TD-001`**
  (`../05-qa/technical-debt-register.md`), and is **not** part of Task
  003's implementation scope. A future Task 003 (or later) gate may
  include a `core_readiness_check` fix **only if ChatGPT explicitly
  authorizes it by name**; otherwise it is routed to its own separate,
  tiny, explicitly-scoped follow-up patch (candidate name: "Task 001B —
  job-framework target-less idempotency patch," not created by this
  patch).
- **No code is authorized.** API client, test connection, setup wizard,
  UI/views/menus/actions/wizards, webhooks/controllers/cron, domain
  modules, external network calls, and any change to
  `core_readiness_check`'s behavior all remain forbidden until a
  separate, explicit Task 003 gate-opening act. **No implementation gate
  is opened by this acceptance.**

## Status

- **Accepted by ChatGPT on 2026-07-07, with an F1 revision to Decision 4
  (see Acceptance above; originally proposed 2026-07-07 in this same
  PR).**
- **Docs-only.** No code, no model field, no view, no XML, no Python, no
  API client, no test-connection mechanism, no external network call, no
  Shopify API call of any kind is created by this document or this PR.
- **No implementation gate opened.** The only implementation gate open
  today is the narrow Task 002 credential-storage gate (AR-026); it does
  not authorize an API client, test connection, or any external call.
  Opening a Task 003 gate — the **first conscious widening of the
  no-external-API-call rule** — is a separate, explicit, future ChatGPT
  act, not performed here, and is not proposed by this document.
- **No final Task 003 implementation prompt is written here.** Unlike
  the Task 002 round (AR-025), this package does not include a
  copy-paste-ready final `CLAUDE.md` §9 prompt or a gate-opening
  proposal — accepting these four decisions prepares, but does not
  perform, that later, separate session (mirroring how AR-025's decision
  closure preceded AR-026's later, separate gate-opening act for Task
  002).
- **Resolves only the four Task 003-specific decision points.** Nothing
  about Task 002 (closed by AR-025/AR-026 and implemented in PR #97) is
  re-litigated. **`core_readiness_check`'s identical latent collision
  defect is explicitly NOT resolved here** — see Decision 4 and `TD-001`.
- Per `CLAUDE.md` §8, statements below are labelled **Fact** (official
  source cited, reused from an already-cited repo document),
  **Inference**, **Recommendation**, or **Open question** where
  ambiguity is possible. The labels reflect the document as originally
  written for review; per the Acceptance section above, decisions 1–3's
  recommendations and Decision 4's narrowed recommendation are now
  accepted at decision level (everything else, including the flagged
  `[Requires external validation before implementation]` items, keeps
  its original label).

## Scope

**In scope (decision level only):**

- Decision 1 — the `core_test_connection` `job_type` value (confirm,
  reject, or propose an alternative).
- Decision 2 — the `SHOP_INACTIVE`/402/423/403-fraudulent error-class
  mapping.
- Decision 3 — the `job.log` system-append write path vs. ACL widening.
- Decision 4 — the per-run `payload_hash` nonce for `core_test_connection`
  job creation (accepted, F1 revision); `core_readiness_check`'s
  identical latent exposure is recorded (`TD-001`) but is explicitly
  **out of scope** for Task 003 unless separately, explicitly authorized
  by name.
- A QA/acceptance checklist for the future Task 003 implementation PR
  (companion document,
  [`../05-qa/task-003-pre-implementation-review-checklist.md`](../05-qa/task-003-pre-implementation-review-checklist.md)).
- A dated amendment note on the existing Task 003 proposal document
  pointing at this package (companion change,
  [`task-003-api-client-test-connection-proposed.md`](./task-003-api-client-test-connection-proposed.md)
  §Status).

**Out of scope:**

- Any code: API client, test-connection service, setup wizard, UI,
  webhooks, controllers, cron, domain sync logic of any kind.
- Any external network call or Shopify API call.
- A final Task 003 implementation prompt.
- A Task 003 gate-opening proposal or act.
- New official-source research (session constraint — see above).
- Fixing `core_readiness_check`'s identical latent collision defect —
  tracked as `TD-001`, not fixed here or by Task 003 unless separately
  authorized by name.
- Re-litigating Task 002 (AR-025/AR-026, PR #97 — accepted and
  implemented).

## Inherited accepted decisions

This package designs strictly inside the following accepted state; it
re-litigates none of it:

- **AR-019 (accepted 2026-07-05):** the six core-model schema, including
  `shopify.connector.job`'s `job_type` Selection fixed at exactly **two**
  core-owned values (`core_readiness_check`, `core_manual_maintenance`)
  and the `idempotency_key` (`store_id`+`job_type`+`res_model`+`res_id`+
  `shopify_target_gid`+`payload_hash`, unique per store, persists for the
  job's life) kept explicitly distinct from `operation_scope_key` (the
  non-permanent, terminal-state-cleared serialization guard).
- **AR-006/DEC-009 (accepted 2026-07-02):** the fixed **16-class**
  `ERROR_CLASS_SELECTION` registry and its retry taxonomy — no 17th
  class; `shopify_permission_scope_auth` and `shopify_user_errors_validation`
  both carry "no automatic retry, manual fix then retry"; `unknown_system_error`
  carries a single safety-net auto-retry, then human, as an
  `[Implementation-planning default]`.
- **AR-024 (accepted 2026-07-06, implementation-planning level):** the
  credential/connection/API-client foundation planning package —
  including the read-only test-connection GraphQL contract, the
  API-client error-normalization boundary, and the four Task
  003-specific decision points this document now closes — accepted at
  planning level, explicitly leaving those four points open.
- **AR-025 (accepted 2026-07-07):** closed the three Task 002-specific
  decision points only (compute-blank rejected; `token_variant` =
  `offline_custom_app`; scope snapshot on `store`); explicitly deferred
  all four Task 003 points to this round.
- **AR-026 (accepted 2026-07-07) and PR #97 (merged):** opened and used
  the narrow Task 002 credential-storage gate. The credential model
  (`shopify.connector.store.credential`), six store status mirrors,
  `tools/redaction.py`, four credential service methods, and one
  Admin-only ACL row now exist in `addons/shopify_connector_core`. No
  API client, no test connection, no job-log write path, no `job_type`
  change, no `payload_hash` change exist yet anywhere in the codebase —
  confirmed by direct inspection of
  `addons/shopify_connector_core/models/shopify_connector_job.py` and
  `shopify_connector_job_log.py` this session (both files are
  unmodified schema/state-machine code with no service method, no
  `sudo()`, and no group/ACL logic in either file).
- **Rejected-approaches check:**
  [`../05-qa/rejected-approaches-log.md`](../05-qa/rejected-approaches-log.md)
  (RA-001–RA-023, 321 lines) checked 2026-07-07 for this package: zero
  matches for `test_connection`, `job_type`, `payload_hash`, `nonce`, or
  `readiness_check` — no rejected approach exists for any of the four
  decision points, and none is reintroduced below.

## Decision 1 — `core_test_connection` job-type value

**Question (AR-024 open point):** should Task 003 add a **third**
core-owned `job_type` Selection value, `core_test_connection`, to
`shopify.connector.job` (currently fixed at exactly two,
`core_readiness_check` / `core_manual_maintenance`, per accepted AR-019),
or reuse `core_readiness_check` with a distinguishing log entry?

**Grounding:**

- **Fact (job.py:93–101):** `job_type` is a `required=True` Selection
  with exactly two values today.
- **Fact (credential-connection-api-client-planning.md:945–955):** the
  architecture package already proposes `core_test_connection` as a
  direct addition to the base selection (not via the domain-module
  `selection_add` seam, "reserved for domain-module extensions, not
  core-owned values") and names the reuse alternative explicitly:
  reusing `core_readiness_check` "with a distinguishing log" is "workable
  but muddies the job list's honesty."
- **Fact:** the entry-point method name already anticipated in
  [`task-003-api-client-test-connection-proposed.md`](./task-003-api-client-test-connection-proposed.md)
  §Allowed files is `action_test_connection()` — a verb-first name that
  matches `core_test_connection`'s phrasing, not `core_readiness_check`'s.
- **Fact:** `job_source='setup_readiness_check'` (job.py:76) is a
  different, already-accepted axis (why/how the job was created) from
  `job_type` (what operation the job performs); reusing `job_source` to
  disambiguate does not answer the `job_type` question, since
  `job_source` is already fixed and unrelated to this decision.

### Option A — Add `core_test_connection` (recommended)

- Keeps `job_type` an honest, specific label: a reader of the job list
  can tell "this was a test-connection run" without inspecting log rows.
- Matches the existing `core_<verb_phrase>` naming convention exactly
  (`core_readiness_check`, `core_manual_maintenance` → `core_test_connection`)
  and the already-anticipated `action_test_connection()` method name.
- Low cost: one Selection tuple added to the base list in
  `shopify_connector_job.py`, exactly as already scoped by the Task 003
  proposal's conditional allowed-files clause.
- Cost: this is a genuine widening of AR-019's fixed-at-two-values
  acceptance to three — it is a decision, not a mechanical addition, and
  must be recorded as an explicit amendment to AR-019 if accepted (see
  Register impact proposal below).

### Option B — Reuse `core_readiness_check`

- Zero schema change, no vocabulary widening, no ChatGPT sign-off needed
  for the enum itself.
- But `core_readiness_check` currently has no other consumer anywhere in
  the codebase, so the "muddying" the architecture package warns about is
  not yet observable — the cost of Option B is a **future** risk (a
  later, distinct core-owned readiness-check operation would become
  indistinguishable from test connection in the job list by `job_type`
  alone), not a present one. Still, `job_type` is meant to answer "what
  operation is this," and collapsing two operationally distinct
  intents into one value trades that clarity away for no present
  savings, since the schema change itself is a one-line addition.

**Recommendation:** Adopt **Option A** — confirm `core_test_connection`
as proposed. This is a **Recommendation**, not a Decision, pending
ChatGPT's acceptance of AR-027; if accepted, it formally amends AR-019's
"exactly two core-owned `job_type` values" statement to three (see
Register impact proposal). If rejected, `shopify_connector_job.py`
remains untouched for this decision and `core_readiness_check` is reused,
exactly as the Task 003 proposal's allowed-files clause already
contemplates.

## Decision 2 — `SHOP_INACTIVE`/402/423/403-fraudulent error-class mapping

**Question (AR-024 open point):** which of the fixed 16 `error_class`
values should a Shopify test-connection failure signalling
`SHOP_INACTIVE`, HTTP 402 (frozen shop), HTTP 423 (locked shop), or HTTP
403 ("the store has been marked as fraudulent") map to?

**What is already a cited Fact (no external validation needed for
these four codes existing):**

- **Fact — `credential-connection-api-client-planning.md:257–273`,
  citing shopify.dev directly, accessed 2026-07-06:** "The GraphQL API
  can return a 200 OK response code in cases that would typically
  produce 4xx or 5xx errors in REST" (direct quote); documented
  `extensions.code` values include `THROTTLED`, `ACCESS_DENIED`,
  `SHOP_INACTIVE`, `INTERNAL_SERVER_ERROR`, and `MAX_COST_EXCEEDED`; "the
  GraphQL reference's HTTP status section lists 200, 400, **402 (frozen
  shop)**, **403 ("the store has been marked as fraudulent")**, 404,
  **423 (locked shop)**, and 5xx — it lists neither 401 nor 429 as
  direct GraphQL HTTP responses" (paraphrase of a direct citation to
  `https://shopify.dev/docs/api/admin-graphql` and
  `https://shopify.dev/docs/api/usage/response-codes`).
- This Fact is **already in the repo**, already cited to an official
  source with an access date, and satisfies this session's "use only
  already-cited repo documentation" constraint — it is **not** a gap.
  (Separately, `docs/01-research/shopify-official-api-notes.md` — the
  dedicated research corpus — does **not** contain this content; the
  citation lives only in the architecture planning document. Both are
  repo documents; neither is external research performed this session.)

**What is genuinely open (Inference/Recommendation, not Fact — and, for
the specific behavioral shapes named below, `[Requires external
validation before implementation]`):**

- **Which `error_class` these four conditions should map to** — the
  Fact above establishes that the codes exist; it does not establish
  which of the 16 classes is the correct semantic home for them. That
  choice is this decision.
- `credential-connection-api-client-planning.md:935–943` already
  proposes: DNS/TLS/5xx/`INTERNAL_SERVER_ERROR` → `shopify_temporary_server_network`;
  401/`ACCESS_DENIED` → `shopify_permission_scope_auth`; `THROTTLED`/429 →
  `shopify_throttling_rate_limit`; **402/423/403-fraudulent/`SHOP_INACTIVE`
  → `shopify_permission_scope_auth`**, explicitly flagged: "Proposed as
  the least-bad fit of the fixed 16 … Flagged for ChatGPT confirmation —
  the alternative is `shopify_user_errors_validation`; no new class may
  be invented."
- `[Requires external validation before implementation]` — none of the
  following are cited anywhere in the repo and must not be asserted as
  fact: the exact GraphQL `THROTTLED` error-body shape; whether an
  invalid/revoked token yields HTTP 401 or a 200-OK body with
  `ACCESS_DENIED`; the exact missing-scope error shape; whether the
  `shop`/`currentAppInstallation` query fields require any access scope
  at all. These are already labelled as open questions in
  `task-003-api-client-test-connection-proposed.md` §Error normalization
  and §Manual validation, and remain so — this package does not resolve
  them, only the class-mapping choice for the four already-cited codes.

### Option A — Map all four to `shopify_permission_scope_auth` (recommended)

- **Structural fit:** `shopify_user_errors_validation` (the named
  alternative) is a GraphQL **mutation**-input-validation concept — the
  `userErrors` field a mutation's payload returns for bad input
  (job.py:40; DEC-009 error taxonomy). The test-connection operation is
  a **read-only query with no mutation** (per the Task 003 proposal's
  structural read-only guarantee); it has no `userErrors` surface to
  populate at all, making `shopify_user_errors_validation` a poor
  structural fit regardless of retry semantics.
- **Retry-semantics fit:** both candidate classes carry identical DEC-009
  retry treatment — "no automatic retry, manual fix then retry" — so
  retry behavior does not distinguish them; the query-vs-mutation
  structural mismatch above is the deciding factor, not retry policy.
- **Registry discipline:** keeps the fixed 16-class registry intact, as
  the Task 003 proposal's own error-normalization section already
  requires ("the fixed 16-class registry — no 17th class"); a distinct
  `shop_state_blocked`-style class was considered and rejected as
  unnecessary schema growth for four conditions whose operator-facing
  remedy (see below) does not depend on the internal class value.
- **Distinct plain-language reasons, not a distinct class:** the four
  conditions must not read identically to the operator. `store`'s
  existing `credential_last_failure_reason` field (Task 002) carries
  free text — this is where the distinction belongs, e.g. "Shopify has
  frozen this store, most commonly for a billing/payment issue — resolve
  it in Shopify, then retry" (402) vs. "This store has been locked by
  Shopify" (423) vs. "Shopify has flagged this store as fraudulent" (403)
  vs. "This store is inactive" (`SHOP_INACTIVE`) vs. "Your access token
  appears invalid or was revoked — replace it" (401/`ACCESS_DENIED`) —
  same `error_class`, different, honest, actionable text.
- **`credential_state` must not be flipped uniformly.** The Task 003
  proposal already anticipates this nuance: "`credential_state='invalid'`
  **where the signal is auth-shaped**" (not unconditionally). A shop
  frozen for non-payment, locked, marked fraudulent, or inactive is a
  **shop-account-state** problem, not proof the stored token itself is
  wrong — flipping `credential_state` to `invalid` for these would
  mislead the operator into re-entering a token that was never the
  problem. **Recommendation:** only a genuine token-invalid signal
  (401/`ACCESS_DENIED` with no other explanation) sets
  `credential_state='invalid'`; `SHOP_INACTIVE`/402/423/403-fraudulent
  leave `credential_state` unchanged and rely on the distinct
  plain-language reason (and, if a future task adds one, a dedicated
  shop-account-state field — out of scope here) to tell the operator the
  real cause.

### Option B — Map all four to `shopify_user_errors_validation`

- Rejected: no mutation exists on this query, so there is no `userErrors`
  field being populated in the first place; this class would be
  structurally meaningless for a read-only query failure. Named only
  because the architecture package names it as the alternative
  considered — not recommended.

**Recommendation:** Adopt **Option A** exactly as already proposed in
`credential-connection-api-client-planning.md:935–943`, with the two
refinements above (credential_state gating; distinct plain-language
reasons per condition) made explicit as part of the resolution. This is
a **Recommendation**, not a Decision. If accepted, `shopify_user_errors_validation`
as the rejected alternative should be logged in
`../05-qa/rejected-approaches-log.md` at acceptance time (per the ADR
template convention — not logged by this proposal-level document). The
specific behavioral shapes flagged `[Requires external validation before
implementation]` above remain unresolved and must be empirically verified
during Task 003's own manual validation step (already specified in
`task-003-api-client-test-connection-proposed.md` §Manual validation,
item 3) — this decision does not, and cannot, resolve them from repo
documentation alone.

## Decision 3 — `job.log` system-append write path vs. ACL widening

**Question (AR-024 open point):** every future job-log-writing path
(test connection now; readiness checks, credential events, and domain
sync later) needs to append `shopify.connector.job.log` rows, but the
merged Task 001/002 ACL grants **no group any `perm_create`** on that
model. Should Task 003 widen that ACL, or build a sanctioned
service-layer write path?

**Grounding (confirmed by direct inspection this session):**

- **Fact — `addons/shopify_connector_core/security/ir.model.access.csv`:**
  `shopify.connector.job.log` has four rows (auditor/operator/reviewer/
  admin), **every one `perm_create=0`** — no role, including Admin, can
  create a `job.log` row through the ORM under its own identity. By
  contrast, `shopify.connector.job` itself already grants operator/admin
  `perm_create=1` — the gap is specific to the log (child) model, not the
  job (parent) model.
- **Fact — `shopify_connector_job_log.py:6–13`:** the model's own
  docstring states it is "append-only" and that `job_id` uses
  `ondelete='restrict'`, "not `cascade`," because "a job's log rows are
  its audit history, not disposable children" — the no-create ACL is a
  deliberate design choice ("system-appended, not user-authored," per
  the architecture package), not an oversight.
- **Fact — neither `shopify_connector_job.py` nor
  `shopify_connector_job_log.py` contains any service method, `sudo()`,
  or group/ACL logic today** (confirmed by direct read this session) —
  the "core job-log writing choke point" referenced in the architecture
  package does not exist yet; Task 003 would be creating it, not
  modifying an existing one.
- **Fact — Task 002 precedent
  (`shopify_connector_store_credential.py:150–164`,
  `_get_access_token`):** "the only sanctioned `sudo()` in this module,"
  scoped to one store's own record via a plain `search()`, never crossing
  record-rule boundaries, never logged/returned outward, documented in
  the model docstring. The model's other three service methods
  (`action_set_token`/`action_replace_token`/`action_clear_token`) run
  **without** `sudo()` so ACL enforcement stays live for the calling
  user. This is the established, reviewed shape of "sanctioned
  elevation" in this codebase: one narrow, single-purpose, documented
  `sudo()` per concern — not a general elevation, not an ACL change.
- **Fact —
  `credential-connection-api-client-planning.md:1146–1160`:** already
  proposes exactly a second such elevation — "the core job-log writing
  choke point's system-append write" — and states the alternative,
  widening the `job.log` ACL, "is not recommended," because it would let
  users author audit rows directly.
- **Fact —
  `../05-qa/credential-security-redaction-review-checklist.md`** already
  hard-codes a review gate anticipating exactly this: "only the two
  named sanctioned elevations (the client's internal credential read;
  the core job-log system-append writer, per ChatGPT's write-path
  resolution) are permitted — any other `sudo()` in the diff is a review
  failure."

### Option A — Widen the `job.log` ACL (e.g., grant operator/admin `perm_create`)

- Lets any user in the granted group author `job.log` rows directly via
  generic ORM/UI/RPC — including fabricating `event_type`, or `from_state`/
  `to_state` values disconnected from any real job transition —
  undermining the audit-trail purpose the append-only/`ondelete=restrict`
  design exists to serve.
- Contradicts the already-recorded "not recommended" framing in the
  architecture package and the review-gate wording already written into
  the redaction checklist.
- Not recommended.

### Option B — Sanctioned system-append service method (recommended)

- A single internal write path — e.g., a method on
  `shopify.connector.job` (or a small mixin shared by job and job.log),
  invoked **only from other core/domain service code, never registered
  as a standalone user-facing action** — that applies the Task 002
  `redact()` utility to every free-text argument
  (`message`/`technical_detail`/`payload_snapshot`) and then creates the
  log row via exactly one documented `sudo()` call, mirroring the
  `_get_access_token` shape precisely (one narrow, single-purpose,
  justified elevation).
- **Why this does not create a new privilege-escalation surface:** the
  method takes an already-obtained `job` recordset as its argument — the
  calling code must already hold whatever ACL-gated reference to that
  job it used to obtain the recordset in the first place. Since all four
  roles already hold `perm_read=1` on both `job` and `job.log` today (the
  ACL gap is specifically about `create`, not `read`), this design adds
  no new visibility; it only lets already-legitimate service code append
  the audit trail that ACL alone cannot, by design.
- Preserves least privilege (no group ever gets a standing, generic
  `create` grant on `job.log`), preserves auditability (every row still
  originates only from code paths the project authors and can shape,
  redact, and review), and requires **no `security/ir.model.access.csv`
  or `shopify_connector_security.xml` change** — both stay exactly as
  merged by Task 001/002.
- Cost: `sudo()` bypasses ACL/record rules by design (Task 002's own
  cited source-level fact), so this single choke point becomes a
  standing, review-sensitive site — mitigated by keeping it to exactly
  one call site with a written justification, exactly as the redaction
  checklist's gate already anticipates.

**Recommendation:** Adopt **Option B**. This is a **Recommendation**, not
a Decision. If accepted, Task 003's final implementation prompt (a later,
separate session) names the exact method signature, its single call
site, and its `sudo()` justification; **no ACL/security-file change** is
authorized by accepting this recommendation — if ChatGPT instead chooses
Option A, the Task 003 proposal's own forbidden-files clause already
states that `security/ir.model.access.csv` would need to move into
Allowed files by name in that final prompt, which this document does not
do.

## Decision 4 — per-run `payload_hash` nonce for target-less jobs

**Question (AR-024 open point):** does Task 003 need a per-run
nonce/hash component in `payload_hash` for repeat target-less
test-connection jobs, to avoid a uniqueness collision?

**What uniqueness collision is being avoided (Fact, confirmed by direct
inspection this session):**

- `idempotency_key` is computed (`shopify_connector_job.py:159–178`) by
  joining `store_id`, `job_type`, `res_model`, `res_id`,
  `shopify_target_gid`, and `payload_hash` with `'|'`, and is unique per
  `(store_id, idempotency_key)` (lines 146–151) — a constraint that
  **persists for the job's entire life and is never cleared**, unlike
  `operation_scope_key` (lines 180–206), which is explicitly cleared once
  a job reaches a terminal state or is superseded.
- A test-connection job is target-less: `res_model`, `res_id`, and
  `shopify_target_gid` are all empty for it. If `payload_hash` is also
  empty (or a fixed value) for every run, every test-connection job for
  the same store computes the **identical** `idempotency_key`
  (`"<store_id>|core_test_connection||||"`) — and because the
  `(store_id, idempotency_key)` unique constraint is never cleared by
  terminal state, a **second** test-connection run for the same store
  would collide with the first, forever, even after the first job
  succeeded or failed. This would make the interactive "Test Connection"
  button in the eventual UI unusable after its first click for the life
  of the store — a real defect, not a hypothetical one, and is exactly
  what the Task 003 proposal's own acceptance test already guards
  against ("a second run on the same store succeeds — per-run key
  resolution proven — no `store_idempotency_key_uniq` collision").
- **Fact —
  `../07-implementation-plan/core-naming-schema-planning.md:476–481`:**
  `payload_hash`'s originally-planned semantics are "a hash of the
  normalized outbound payload … exact hashing algorithm/normalization …
  an implementation-time detail" — i.e., the field was designed to
  fingerprint a **real** operation payload (e.g., "is this the same
  product-export payload already processed?"), not to hold an arbitrary
  per-run nonce. Using it for a nonce on a payload-less operation is a
  **repurposing** of the field, not its originally-planned use.

**What should — and must not — contribute to the value:**

- **Should:** a value that is unique **per run**, not per store or per
  job type — e.g. a UUID4 (`str(uuid.uuid4())`), generated fresh at job
  creation. A coarse, time-bucketed value (e.g., truncated to the
  minute) is **not** sufficient — two rapid manual clicks of a future
  "Test Connection" button within the same bucket would still collide;
  a genuinely unique generator avoids this without needing to reason
  about click cadence.
- **Must not:** the access token, any credential-derived value, any
  portion of the GraphQL response body, or any other secret — the value
  exists solely to guarantee row uniqueness, not to carry information;
  it must never be logged or handled as if it were sensitive, but it
  also must never be *derived from* something sensitive (e.g., never
  `hash(access_token)`), since a derived value could theoretically leak
  structure about its input even where the raw secret is absent.
- **No schema change is required.** `payload_hash` already exists as a
  plain, non-computed `fields.Char(readonly=True)`
  (`shopify_connector_job.py:123`) — Task 003 only needs to **populate**
  it with a per-run nonce at job-creation time for target-less job
  types; `_compute_idempotency_key` already incorporates whatever value
  is stored there with no further change. This decision therefore
  requires **no edit to `shopify_connector_job.py`'s field list or
  compute methods** — only a documented convention at the job-creation
  call site (inside Task 003's own service code) and, per the Task 003
  proposal's conditional allowed-files clause, a short docstring/comment
  note on `payload_hash` and/or `_compute_idempotency_key` explaining
  the dual use (real payload fingerprint for domain jobs; per-run nonce
  for target-less jobs) so a future reader is not misled by the field's
  name.
- **`core_readiness_check` shares the identical latent defect — but is
  NOT automatically in Task 003's scope (F1 correction, 2026-07-07).**
  An earlier draft of this section implied Task 003 should populate the
  nonce for "every target-less job type," which would have silently
  pulled a fix to already-merged Task 001 schema into Task 003's
  implementation boundary without a named authorization. That overreach
  is corrected here: `core_readiness_check`'s exposure to the same
  collision is real (see below) and must not be lost, but fixing it is
  **not** part of what Task 003 is authorized to touch unless a future
  gate names it explicitly. See "Is this a Task 003 requirement…" and
  the Acceptance section above for the corrected scope, and the Register
  impact section for where this follow-up is now recorded
  (`TD-001`, `../05-qa/technical-debt-register.md`).

**Is this a Task 003 requirement or a later generic job-framework
requirement? (F1-corrected scope, 2026-07-07)**

- **Task 003 requirement, now — scoped to `core_test_connection` only.**
  The collision is real today for `core_test_connection` (Decision 1)
  and would be immediately triggered by Task 003's own acceptance
  criteria (a second test-connection run must succeed). Task 003's
  implementation is authorized to populate `payload_hash` with a per-run
  nonce **for `core_test_connection` job creation only**.
  `_compute_idempotency_key` itself is untouched (it already incorporates
  whatever value `payload_hash` holds), so this does not require
  touching any other job type's behavior.
- **`core_readiness_check` is a separate, pre-existing latent risk —
  explicitly NOT part of Task 003's scope.** It shares the identical
  collision defect (target-less, same `idempotency_key` formula,
  already-merged in Task 001), but it is a **different, already-shipped
  code path** with its own callers; silently changing its behavior
  inside a PR authorized for test-connection work would be undocumented
  scope creep into already-accepted Task 001 schema. **Recorded as
  `TD-001`** in `../05-qa/technical-debt-register.md` as an open,
  pre-existing latent risk, not resolved by Task 003.
  - **The future Task 003 gate may include a `core_readiness_check` fix
    only if ChatGPT explicitly authorizes it by name** in that gate's
    scope (i.e., a one-line addition to the gate's allowed-files/scope
    section naming `core_readiness_check` alongside
    `core_test_connection`).
  - **Otherwise, it is routed to its own separate, tiny, explicitly
    scoped follow-up patch** — candidate name: "Task 001B — job-framework
    target-less idempotency patch" (not created by this document; naming
    only, for the control room to schedule).
- **The deeper naming question remains a later, generic job-framework
  residual, independent of which job type(s) get the nonce fix:** whether
  a future schema revision should give target-less jobs a dedicated nonce
  field (distinct from `payload_hash`) rather than overloading an
  existing field's name. Also logged under `TD-001` — does not block
  Task 003 either way.

**Decision (accepted by ChatGPT, 2026-07-07, F1 revision — see
Acceptance section above):** Task 003 populates `payload_hash` with a
per-run UUID4 nonce **for `core_test_connection` job creation only**;
`shopify_connector_job.py`'s field list and compute methods are
untouched beyond an explanatory comment. `core_readiness_check`'s
identical exposure is **not** fixed by Task 003 and is **not** silently
included — it is tracked as `TD-001` and routed to a separate,
explicitly-named future gate/patch, per the scoping above.

## Final Task 003 implementation-boundary note

**This is not a final implementation prompt and authorizes nothing.**
Now that the four decisions are accepted (Decision 4 with its
scope-narrowing revision), the separate, later session that prepares
Task 003's final `CLAUDE.md` §9 prompt and gate-opening act (mirroring
AR-025 → AR-026 for Task 002) fixes, in addition to what
`task-003-api-client-test-connection-proposed.md` already specifies:

- `job_type` gains one value, `core_test_connection` (Decision 1), added
  directly to the base selection in `shopify_connector_job.py`.
- The error-normalization table maps `SHOP_INACTIVE`/402/423/403-fraudulent
  to `shopify_permission_scope_auth`, with `credential_state` flipped to
  `invalid` only for genuine token-invalid signals, not for shop-account-state
  conditions, and a distinct, mandatory plain-language reason per
  condition (Decision 2).
- A single, internal, `sudo()`-wrapped job-log system-append method
  exists (exact signature to be named in the final prompt), with no
  `security/ir.model.access.csv` or `shopify_connector_security.xml`
  change (Decision 3).
- **`core_test_connection` job creation only** populates `payload_hash`
  with a per-run UUID4 nonce, documented in place, with no field/compute
  schema change (Decision 4). **`core_readiness_check` is explicitly out
  of scope** for this future session unless ChatGPT's own final prompt
  names it — see `TD-001` for that separate follow-up.
- Every other contract in `task-003-api-client-test-connection-proposed.md`
  (API client boundary, structural read-only guarantee, redaction
  guarantee, tests required, manual validation, rollback, acceptance
  criteria, explicit exclusions) stands unchanged by this package.

**Preconditions for that later session remain exactly as already
stated:** Task 002 merged and reviewed (done — PR #97); a separate,
explicit ChatGPT gate-opening act authorizing outbound read-only Shopify
Admin API calls for the first time (not performed here) — the four
decisions above are now accepted, but accepting a decision is not the
same act as opening the gate.

## Register impact

**Applied by this F1 acceptance patch** (same PR, per the AR-025/PR #94
convention — proposal and its acceptance both land in the same PR/branch
before merge):

- **AR-019** (`../05-qa/architecture-review-log.md`): amendment note
  added to AR-019's row recording that AR-027 (accepted, F1 revision)
  extends `job_type` from exactly two core-owned values to three,
  adding `core_test_connection`. AR-019's own six-model/schema substance
  is otherwise unchanged.
- **MBQ-44** (`../03-architecture/master-blueprint-open-questions.md`):
  note added recording that AR-027 (accepted, F1 revision) resolves the
  `job.log` system-append write-path residual this row already names —
  the sanctioned internal `sudo()`-wrapped write method, no ACL
  widening. **Status unchanged: Partially resolved** — the row's own
  "gated code artifact" framing is untouched; the actual method does not
  exist until Task 003's implementation is reviewed and accepted.
- **`../05-qa/rejected-approaches-log.md`:** new entry **RA-024** added —
  mapping `SHOP_INACTIVE`/402/423/403-fraudulent to
  `shopify_user_errors_validation` (the named alternative to the now
  accepted `shopify_permission_scope_auth` mapping) is logged as a
  rejected approach, per the ADR template convention that rejected
  alternatives are recorded at acceptance time. No other approach is
  logged.
- **`../05-qa/technical-debt-register.md`:** new entry **TD-001** added —
  `core_readiness_check`'s identical target-less `payload_hash`/
  `idempotency_key` collision defect, open, not fixed by Task 003,
  routed to a future explicitly-named gate inclusion or its own tiny
  follow-up patch. This is the register's first real entry.
- **No other row is touched.** MBQ-05/06/08/51/52 and every other
  MBQ/DEC/AR row need no update; nothing here changes their existing
  notes.

## What ChatGPT should review

**Resolved by this F1 acceptance (2026-07-07):** decisions 1–3 as
proposed; Decision 4 with the `core_test_connection`-only scope
narrowing. Remaining for a future round:

1. When to schedule `core_readiness_check`'s follow-up fix (`TD-001`) —
   folded into the Task 003 gate by name, or its own separate "Task
   001B"-style patch.
2. The specific behavioral shapes still flagged `[Requires external
   validation before implementation]` under Decision 2 (exact
   `THROTTLED` body; 401 vs. 200+`ACCESS_DENIED`; missing-scope shape;
   `shop`/`currentAppInstallation` scope requirements) — these are
   verified empirically during Task 003's own manual validation step,
   not resolved by acceptance of the mapping itself.
3. The final Task 003 `CLAUDE.md` §9 prompt and gate-opening proposal
   themselves, once prepared in a later, separate session.

## Recommended next session

A separate, scoped session to prepare the final Task 003 `CLAUDE.md` §9
implementation prompt and a narrow Task 003 gate-opening proposal
(mirroring the AR-025 → AR-026 → PR #97 sequence), fixing the exact
`job_type`/error-mapping/job-log-method/nonce contracts accepted above,
and explicitly stating whether `core_readiness_check` (`TD-001`) is
folded in by name or left for its own follow-up patch — each still
requiring their own separate ChatGPT gate-opening act before any code is
written.

## Stop confirmation

This session stops here. No API client, no test-connection code, no
setup wizard, no UI, no XML, no webhook/controller/cron, no
product/customer/order/inventory/fulfillment logic, no external network
call, and no Shopify API call were created or made. No implementation
gate was opened. Task 003 remains not started; accepting these four
decisions is not itself an authorization to write code.
