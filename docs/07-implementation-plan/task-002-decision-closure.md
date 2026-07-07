# Task 002 Decision Closure

> Decision-closure package for **Task 002 — Credential Storage, Masking,
> and Redaction Foundation**. Prepared 2026-07-06 on branch
> `claude/task-002-decision-gate-pack-0mlsgf`, from `Shopify-connector`
> at PR #92's merge commit `f74aaf204745ce0087733870fe56bdda74bfa79a`
> (PR #92 confirmed merged before starting). This document resolves — at
> proposal level, for ChatGPT review — the three Task 002-specific
> decision points AR-024's acceptance left explicitly open, and anchors
> the companion gate-preparation package:
> [`task-002-final-implementation-prompt.md`](./task-002-final-implementation-prompt.md)
> (the copy-paste final `CLAUDE.md` §9 prompt),
> [`task-002-gate-opening-proposal.md`](./task-002-gate-opening-proposal.md)
> (the proposed narrow gate act), and
> [`../05-qa/task-002-pre-implementation-review-checklist.md`](../05-qa/task-002-pre-implementation-review-checklist.md)
> (the review gate for this package and the future Task 002 PR). Review
> row: **AR-025** in
> [`../05-qa/architecture-review-log.md`](../05-qa/architecture-review-log.md).

## Status

- **Proposed for ChatGPT review.** Nothing below is a Decision until
  ChatGPT accepts AR-025.
- **Docs-only.** No code, no model, no field, no view, no XML, no Python
  is created by this document or this PR.
- **No implementation.** Task 002 is not started; Task 003 is not
  started.
- **Does not open any gate.** The only open implementation gate remains
  the limited core-only zero-UI gate (AR-021), which explicitly forbids
  credential fields. The companion gate-opening proposal is itself only a
  proposal; the gate opens only through a separate, explicit ChatGPT act.
- **Resolves only Task 002-specific decision points if accepted.** The
  four remaining AR-024 decision points that belong to Task 003 (the
  `core_test_connection` job-type value; the `SHOP_INACTIVE`/402/423/
  403-fraudulent error-class mapping; the job-log system-append write
  path vs. ACL widening; the per-run `payload_hash` nonce) are **not**
  resolved here and remain explicitly deferred to the Task 003 decision
  round.
- Per `CLAUDE.md` §8, statements below are labelled **Fact** (official
  source cited), **Official source-code fact**, **Inference**,
  **Recommendation**, or **Open question** where ambiguity is possible.
  Nothing here is a Decision.

## Scope

**In scope (decision/gate-preparation level only):**

- Decision 1 — the compute-blank no-read-back hardening variant
  (adopt/reject/defer for Task 002).
- Decision 2 — the `token_variant` vocabulary and the MBQ-05
  acquisition-path direction *as far as Task 002 needs it*.
- Decision 3 — scope-snapshot placement (`granted_scopes` /
  `granted_scopes_checked_at`).
- The final Task 002 implementation boundary (files, model, fields, ACL,
  services, redaction contract, tests, rollback, definition of done).
- The gate-opening proposal for the narrow Task 002 credential-storage
  gate (companion document).

**Out of scope:**

- API client implementation (Task 003).
- Test connection implementation (Task 003).
- Setup wizard implementation (UI gate; Task 006 horizon).
- UI implementation of any kind (views/menus/actions/wizards).
- Webhooks, controllers, cron.
- Domain sync of any kind.
- Task 003-only decisions — listed above, explicitly deferred, not
  resolved here.
- MBQ-04 Options D/E (external secret manager / hybrid) — remain
  deferred, not rejected, per AR-022; not re-evaluated here.

## Inherited accepted decisions

This package designs strictly inside the following accepted state; it
re-litigates none of it:

- **AR-022 (accepted 2026-07-06, posture level):** MBQ-04 Option B — a
  dedicated Odoo-managed credential field (or tightly coupled field
  set), plain storage with standard Odoo field/access controls,
  connector-admin `groups=`, view-level masking wherever exposed, and a
  mandatory no-logging/redaction rule. No encryption claim may be made
  anywhere; `password=True` is display masking only; `sudo()` bypasses
  field-level `groups` (confirmed in 19.0 source); `ir.config_parameter`
  is not secure secret storage; the Odoo Cloud AES-256 statement is
  infrastructure-level with unconfirmed hosting scope and must never be
  used as a guarantee.
- **AR-023 (accepted 2026-07-06, design-specification level):** Premium
  Simplicity Standard; credential entry is one masked field, never read
  back on any connector surface for any role including Admin; allowed
  copy: "stored with restricted access and never shown again"; forbidden
  copy: "encrypted" and every at-rest security claim; token status is
  "present / last verified — never the value".
- **AR-024 (accepted 2026-07-06, implementation-planning level):** the
  credential/connection/API-client foundation planning package. **Option
  C** — the dedicated Admin-only `shopify.connector.store.credential`
  model (one row per store; secret on the credential model; non-secret
  status mirrors on `store`; Admin-only ACL with no rows for
  auditor/operator/reviewer; field-level `groups=` on the secret as a
  second layer; no unlink; no connector-surface read-back for any role
  including Admin) — accepted at planning level as a justified
  post-AR-022 addition to the AR-019 six-core-model plan. The
  **redaction/no-logging contract** (shared `redact()` utility,
  `SENSITIVE_KEYS`, `shpat_`/`shprt_` value patterns, exact-value scrub,
  source- and sink-side enforcement) accepted at planning level.
- **MBQ-04 at implementation-planning level (per the PR #92 acceptance
  patch):** Partially resolved — the exact model, field set, access
  posture, no-read-back/masking rules, redaction contract,
  rotation/replacement, disconnect/reconnect, audit metadata, and
  rollback behavior are accepted **as planned**; MBQ-04 closes fully
  only after Task 002's implementation is reviewed and accepted.
- **Task 002 status:** accepted as the **recommended next coding task —
  not authorized**. Starting it requires the explicit gate-opening act
  and the final §9 task prompt (which this package prepares).
- **Task 003 status:** accepted as the proposed follow-up — not
  authorized; its decision points are deferred to its own round.
- **Rejected-approaches check:** `../05-qa/rejected-approaches-log.md`
  (RA-001–RA-023) re-checked 2026-07-06 for this package: nothing below
  reintroduces a rejected approach; no revisit condition is invoked.

## Official source re-verification (2026-07-06)

Per this sprint's official-source requirement, the MBQ-05 Shopify facts
and the Odoo compute-blank facts were **re-verified live against
official sources on 2026-07-06** (three parallel research passes plus an
adversarial re-fetch verification pass; access status for every page:
Accessible, on 2026-07-06). Findings that matter to the three decisions:

1. **Fact — new custom apps can no longer be created in the Shopify
   admin.** "You can no longer create new custom apps in the Shopify
   admin. … To create a new custom app, use the Dev Dashboard or Shopify
   CLI." (direct quote)
   (https://shopify.dev/docs/apps/build/authentication-authorization/access-tokens/generate-app-access-tokens-admin)
2. **Fact — the cutoff is dated.** "Starting from January 1, 2026, you
   can't create any more legacy custom apps. To create and manage new
   custom apps, you need to use the Dev Dashboard. This change doesn't
   impact any of your existing custom apps." (direct quote; legacy
   custom apps are managed under Settings ▸ Apps ▸ "Legacy custom apps")
   (https://help.shopify.com/en/manual/apps/managing-apps)
3. **Fact — existing admin-created custom apps keep working**, and their
   credentials **cannot be rotated**: "You can't rotate API credentials
   for custom apps created in the Shopify admin. You need to delete the
   app and create a new custom app which has new API credentials." New
   tokens for the same app require uninstall/reinstall, with requests
   and webhooks disrupted until the new credentials are in use. (direct
   quotes)
   (https://shopify.dev/docs/apps/build/authentication-authorization/access-tokens/generate-app-access-tokens-admin)
4. **Fact — legacy offline tokens do not expire.** "No expiration:
   Tokens remain valid indefinitely until app is uninstalled or secret
   revocation." Access-token examples carry the `shpat_` prefix; refresh
   tokens `shprt_`. (direct quote)
   (https://shopify.dev/docs/apps/build/authentication-authorization/access-tokens/offline-access-tokens)
5. **Fact — Dev Dashboard apps obtain tokens programmatically via the
   client credentials grant**: `POST
   https://{shop}.myshopify.com/admin/oauth/access_token` with
   `grant_type=client_credentials` + client ID + client secret; tokens
   are "valid for 24 hours" (`expires_in` "always 86399"); "Client
   credentials is only available for apps developed by your own
   organization and installed in stores that you own." Official storage
   guidance: keep
   the client secret out of frontend code and repositories (`.env`
   excluded from version control); rotate immediately if compromised.
   (direct quotes)
   (https://shopify.dev/docs/apps/build/authentication-authorization/access-tokens/client-credentials-grant;
   https://shopify.dev/docs/apps/build/dev-dashboard/get-api-access-tokens)
6. **Fact — the expiring-offline-token model is public-apps-only, and
   custom apps are exempt.** "As of December 2025, Shopify supports
   expiring offline access tokens" (1-hour access tokens,
   `expires_in: 3600`, with 90-day refresh tokens); "Public apps created
   on or after April 1, 2026 must use expiring tokens"; earlier public
   apps must migrate by January 1, 2027. "These requirements don't apply
   to custom apps or apps created by merchants." The two official
   changelog entries list the exemptions verbatim: "Custom apps created
   at any time" and "Apps created by merchants either in the Dev
   Dashboard or in the admin." (direct quotes)
   (https://shopify.dev/docs/apps/build/authentication-authorization/access-tokens/offline-access-tokens;
   https://shopify.dev/changelog/expiring-offline-access-tokens-required-for-public-apps-april-1-2026;
   https://shopify.dev/changelog/expiring-offline-access-tokens-required-for-all-public-apps-as-of-january-1-2027)
7. **Fact — revoking a client secret kills its tokens.** "Remember that
   revoking any secret will also remove the access tokens associated
   with it." (direct quote)
   (https://shopify.dev/docs/apps/build/authentication-authorization/client-secrets/rotate-revoke-client-credentials)
8. **Historical note (not asserted as current behavior):** a 2020
   changelog entry assigned prefixes `shpat_` (public), `shpca_`
   (custom), `shppa_` (legacy private) when token length grew to 38
   characters. Only `shpat_`/`shprt_` appear on live official pages
   today; `shpca_`/`shppa_` therefore stay **out** of the asserted
   pattern list (the redaction contract's exact-match scrub covers
   arbitrary formats regardless).
   (https://shopify.dev/changelog/length-of-the-shopify-access-token-is-increasing)
9. **Official source-code fact — `res.users.password` mechanics in
   19.0.** The field is a non-stored compute/inverse Char
   (`compute='_compute_password', inverse='_set_password', copy=False`);
   `_compute_password` blanks the value on every read
   (`user.password = ''`); `_set_password` one-way-hashes via a passlib
   `CryptContext` and `_set_encrypted_password` writes the hash with raw
   SQL (`UPDATE res_users SET password=%s`); credential checks read the
   hash back with raw SQL (`SELECT COALESCE(password, '') FROM
   res_users…`); the physical `res_users.password` column exists only
   because base's raw DDL creates it (`base_data.sql`: `password varchar
   default null`), not because any stored ORM field manages it; `init()`
   sweeps plaintext values into the hash path at startup. (Verified
   against the raw 19.0 source and the official 19.0 nightly source
   tarball — the GitHub raw fetch of `base_data.sql` returned HTTP 429
   at access time, so the tarball was used for that one file.)
   (https://raw.githubusercontent.com/odoo/odoo/19.0/odoo/addons/base/models/res_users.py;
   https://nightly.odoo.com/19.0/nightly/src/odoo_19.0.latest.tar.gz)
10. **Fact — computed-field semantics.** The 19.0 ORM reference:
    "computed fields are not stored by default, they are computed and
    returned when requested"; `store` defaults to False for computed
    fields; `inverse` is the mechanism that makes a computed field
    settable; `copy` defaults to False for computed fields; `groups`
    "restricts the field access to the users of the given groups only."
    For a compute+inverse field with `store=False`, nothing is persisted
    for the field itself — persistence happens only through whatever the
    inverse writes. (direct quotes/paraphrase)
    (https://www.odoo.com/documentation/19.0/developer/reference/backend/orm.html)
11. **Re-confirmed unchanged:** `sudo()`/superuser bypasses field-level
    `groups` (`_has_field_access` short-circuits on `self.env.su`), and
    no official field-level encryption mechanism exists — identical to
    the accepted AR-022 evidence; nothing found on 2026-07-06 changes
    the accepted posture.
    (https://github.com/odoo/odoo/blob/19.0/odoo/orm/models.py;
    https://www.odoo.com/documentation/19.0/developer/reference/backend/security.html)

**Open questions carried (not asserted):** whether a Dev-Dashboard-
created app installed on the merchant's own store has any officially
documented path to a *non-expiring* offline token other than the
24-hour client-credentials tokens (the exemption quotes above establish
that custom/merchant apps are exempt from the *expiring-token mandate*;
they do not document an alternative long-lived-token acquisition path
for Dev Dashboard apps) — this is exactly the MBQ-05 residual and stays
open; the historical one-time token reveal / "last 4" behavior remains
absent from live official pages (unchanged AR-024 Open question #7).

## Decision 1 — compute-blank no-read-back hardening

**Question (AR-024 open point):** should Task 002's `access_token` field
adopt a `res.users.password`-style compute-blank read pattern (ORM reads
return empty for everyone, including Admin), or remain a stored Char
behind the two accepted access layers?

**What "adopt" would actually require (Official source-code fact #9):**
the only official precedent — `res.users.password` — achieves
compute-blank with four moving parts: a non-stored compute/inverse
field; a **hand-managed database column** created by raw DDL outside the
ORM; a **raw-SQL write path** in the inverse; and a **raw-SQL read
path** for internal use. A watered-down variant (compute-blank field
plus a companion *stored* ORM field holding the value) would **not**
deliver the promise: the companion stored field would itself remain
ORM/RPC-readable by Admin-group users, so the "no read-back" claim would
be false while looking true — the worst outcome for a project whose
credential posture is built on honest claims. The evaluation below
therefore treats "adopt" as the full `res.users`-style variant, and
names the watered-down variant only to reject it.

### Option 1A — Adopt (full `res.users`-style variant)

- **Security impact:** closes exactly one path — generic ORM/RPC
  read-back of the stored value by connector-Admin-group users outside
  connector surfaces. Real but narrow: that actor class is the same
  Admin who entered (and can replace) the token. **Unchanged:** raw
  column readable via any server-side SQL, `sudo()`-context code paths
  that issue SQL, database access, and backups. No encryption exists
  either way, and none may be claimed.
- **Implementation complexity:** high for Task 002's size: hand-managed
  column (module `init()` DDL), a raw-SQL write path and a raw-SQL read
  path in the most security-critical file of the codebase, plus cache
  invalidation — all needing line-by-line review. The official 19.0
  security guidance warns raw SQL bypasses Odoo security rules entirely,
  so every such statement becomes a standing review liability.
- **Odoo-native fit:** precedented but purpose-divergent.
  `res.users.password` never needs the plaintext back — it stores a
  one-way hash and verifies. The connector **must** read the plaintext
  back on every future API call, so the defining security property of
  the precedent (nothing retrievable exists) cannot be reproduced; only
  the read-surface shape can. Meanwhile every official Odoo example of a
  *retrievable* third-party API secret (`ir.mail_server.smtp_pass`,
  Stripe/Adyen/Authorize.Net keys, `iap.account.account_token` — AR-022
  evidence, five out of five) is a stored Char behind `groups=`.
- **Testability:** good but subtle — tests can prove ORM reads return
  empty and the internal accessor still works, but the suite cannot
  prove "the value is unreachable" (it is reachable, by SQL, by design);
  a green suite here is easy to over-read.
- **Risk of false security claims:** **the highest of the three
  options.** The mechanism invites copy and reviewer drift toward "the
  token cannot be read after save," which is false at the SQL/DB/backup
  layer. Every future doc would need to carry the correction.
- **Residual exposure:** raw column plaintext; readable by any
  server-side SQL path, DB admin, or backup holder; `sudo()`-context
  code can reach it via SQL. Only the ORM/RPC route is closed.

### Option 1B — Reject for Task 002 (stored Char behind the two accepted layers)

- **Security impact:** keeps the accepted AR-024 posture exactly: layer
  1 — model-level default-deny (no ACL row for auditor/operator/
  reviewer; `fields_get`/read/search all denied); layer 2 — field-level
  `groups=` Admin-only on the value; no views ever; write-only service
  entry; redaction everywhere. The one path 1A would close stays open
  and is **documented honestly**: an Admin-group user with generic
  ORM/RPC access can deliberately read the stored field outside
  connector surfaces.
- **Implementation complexity:** minimal — plain field declarations,
  service methods, one sanctioned `sudo()` read accessor. Review
  attention concentrates where the real risk is (ACL matrix, redaction,
  no-logging), not on hand-rolled SQL.
- **Odoo-native fit:** exactly matches all five official Odoo
  precedents for retrievable API secrets (AR-022), while exceeding them
  on every axis (dedicated default-deny model, no views, service-only
  writes, redaction contract — none of which `smtp_pass` or the payment
  keys have).
- **Testability:** crisp — the denial matrix (4 roles × CRUD +
  `fields_get`), field-`groups` stripping, service behavior, and
  token-absent-from-every-persisted-surface assertions are all
  first-class Odoo test patterns with no bespoke machinery.
- **Risk of false security claims:** lowest — the design claims only
  what it does ("restricted access, never shown again" on connector
  surfaces), and the honest-residual statement is already accepted
  AR-022/AR-024 language.
- **Residual exposure:** as 1A **plus** the deliberate Admin-group
  ORM/RPC read. Stated plainly: `sudo()` bypasses field `groups`;
  database and backup access read the plaintext column; no encryption
  exists and none is claimed.

### Option 1C — Defer (leave the field shape undecided until the final prompt or later)

- **Security impact:** none now; risk that Task 003 builds the client
  against an accessor whose storage shape then changes underneath it.
- **Implementation complexity:** deceptive — deferral converts a
  decision into a future schema migration (stored column → hidden
  column) after real tokens exist, which is strictly worse than
  deciding now.
- **Odoo-native fit / testability:** n/a — deferral is the one option
  that makes Task 002's tests unwritable as "exact" (the gate package
  requires an exact field shape).
- **Risk of false security claims:** medium — an undecided shape keeps
  the ambiguous "no read-back" wording alive longer.
- **Residual exposure:** unchanged; just undecided.

### Recommendation (exactly one)

**Recommendation — Reject the compute-blank variant for Task 002
(Option 1B).** Task 002 does **not** implement compute-blank.

- **Field-shape consequence (exact):** `access_token` is a plain stored
  `fields.Char` on `shopify.connector.store.credential` with
  `groups='shopify_connector_core.group_shopify_connector_admin'`,
  `copy=False`, not `required` (empty = cleared/absent), written only by
  the Task 002 service methods. No compute, no inverse, no raw-SQL
  write/read path, no hand-managed column, no companion field.
- **Internal token retrieval:** the future API client (Task 003) obtains
  the value **only** through the internal accessor
  `_get_access_token(store)` on the credential model — the single
  sanctioned `sudo()` in Task 002's diff, scoped to reading the one
  credential row of the store already being operated on (DEC-004's
  no-crossing rule holds: the elevation never crosses store/record-rule
  boundaries). The accessor never returns the value to callers outside
  the future client path, never logs it, and never embeds it in an
  exception.
- **What users can and cannot read:**
  - Auditor / Operator / Reviewer: **nothing** — no ACL row exists, so
    read, write, create, unlink, `search`, and `fields_get` on the
    credential model are all denied (Odoo default-deny), and the
    field-level `groups=` denies the value independently.
  - Admin (connector group): can call the service methods
    (set/replace/clear) and read the non-secret fields; **no connector
    surface ever renders `access_token`** (the model has no views, and
    Task 002 adds no UI anywhere).
  - **Honest residual:** an Admin-group user with generic ORM/RPC
    access (e.g. dev-mode RPC) *can* deliberately read the stored
    `access_token` outside connector surfaces. This is the accepted
    MBQ-04 Option B residual, restated — never papered over.
- **What stays readable regardless (either option):** `sudo()`/
  superuser-context code (bypasses field `groups` — 19.0 source fact);
  direct database access; backups. **No encryption exists at field
  level; no encryption claim may be made; hosting-level encryption
  coverage (Odoo.sh/Odoo Online/on-premise) remains unconfirmed and must
  not be asserted.**
- **Required tests (Decision-1-specific; full list in the final
  prompt):** the 4-role × CRUD + `fields_get` denial matrix; the
  field-`groups` second layer holding independently of the ACL layer;
  the dummy token provably absent from every persisted non-credential
  surface (mirrors, stamps, display_name) after every service call; no
  `sudo()` anywhere in the diff except inside `_get_access_token`.
- **Revisit condition (recorded so the rejection is not silent
  forever):** if ChatGPT later elevates the threat model for
  Admin-group-RPC actors (e.g. multi-admin deployments where connector
  Admins are not trusted with the raw value), or if the deferred MBQ-04
  Options D/E evidence pass happens, the full `res.users`-style variant
  can be introduced as its own small hardening task with a one-time
  value-relocation migration. If ChatGPT instead **overrules** this
  recommendation and wants compute-blank now, the final prompt's field
  section must be replaced with the full 1A variant (compute-blank +
  init-DDL column + raw-SQL inverse/accessor + the 1A test set) —
  the watered-down companion-stored-field variant must **not** be
  accepted in any case.

## Decision 2 — `token_variant` / MBQ-05 Task 002 direction

**Question (AR-024 open point):** which credential-acquisition paths
must Task 002's schema support now, and what does that mean for
`token_variant` and MBQ-05?

**Evidence baseline (all Facts, §Official source re-verification):**
path A tokens (existing admin-created custom apps) are non-expiring
`shpat_` values, not rotatable (delete-and-recreate or
uninstall/reinstall only), and continue to work; new custom apps can be
created only in the Dev Dashboard (cutoff January 1, 2026); the
documented Dev Dashboard own-store path (B) is the client-credentials
grant — client ID + client secret exchanged programmatically for tokens
valid 24 hours (`expires_in` always 86399); custom and merchant-created
apps are exempt from the public-app expiring-offline-token mandate.

### Option 2A — Support only path A, no seam (hard-code the single shape)

- Smallest possible schema, but removes the accepted `token_variant`
  marker (AR-024 planning already accepted it) and turns the officially
  dated MBQ-05 landscape shift into a future migration. Rejected: saves
  one Selection field at the cost of the only future-proofing the
  accepted plan asked for.

### Option 2B — Build path B (client-credentials) in Task 002

- Requires storing `client_id` + `client_secret`, a cached short-lived
  token, and expiry metadata **plus** refresh mechanics. Refresh
  mechanics are impossible inside Task 002's boundary: obtaining a token
  *is an external API call* (the grant endpoint), and Task 002 is
  defined by **zero Shopify calls**; unattended refresh would also need
  cron, which is forbidden until its own gate. Storing the B fields
  without the mechanics would create dead sensitive columns (two more
  secrets to protect and redact) that nothing can use — pure liability.
  Rejected for Task 002: this is the "overbuilding the 24-hour refresh"
  trap this sprint was explicitly told to avoid.

### Option 2C — Hybrid/seam now: Task 002 stores path A only; the model boundary is the seam; B mechanics deferred (recommended)

- Task 002 stores exactly **one** secret value (`access_token`) plus the
  accepted `token_variant` marker with a single value. The dedicated
  credential model (Option C, accepted) **is** the seam: if/when ChatGPT
  decides MBQ-05 requires the client-credentials variant, its fields
  (`client_id`, `client_secret`, cached token, expiry) land on this
  Admin-only model via `selection_add` + new fields in a future,
  separately gated task — no migration of existing data, no relocation,
  no change to the mirrors or the accessor contract
  (`_get_access_token` keeps returning "the currently valid token").
- Honest product note (Inference, flagged for ChatGPT): because new
  custom apps can no longer be created in the Shopify admin (Fact), a
  merchant starting fresh after January 1, 2026 follows the Dev
  Dashboard path — so **path B support (or an officially confirmed
  long-lived-token alternative for Dev Dashboard apps — Open question)
  must be decided before the setup wizard's copy and the GA
  acquisition story are final.** That is MBQ-05's decision, for ChatGPT,
  blocking the wizard slice only — Task 002 is deliberately neutral to
  it.

### Option 2D — Build both A and B in Task 002

- Superset of 2B; rejected for the same reasons, doubled.

### Recommendation (exactly one)

**Recommendation — Option 2C.** Task 002 supports storing **one**
long-lived offline custom-app token (path A) and nothing else; the
dedicated credential model is the seam for path B; B's mechanics are
deferred to a future ChatGPT decision (MBQ-05) and a future task.

- **Exact `token_variant` values for Task 002:** exactly one —
  `[('offline_custom_app', 'Offline Custom App Token')]`, default
  `offline_custom_app`, extensible later via `selection_add`. No second
  value is declared now (a dead `client_credentials` value would imply
  unbuilt support — dishonest schema).
- **Secret components stored by Task 002:** exactly one —
  `access_token`. **Not stored:** `client_id`, `client_secret`, any
  cached-token field, any expiry field, any refresh-token field. Their
  deliberate absence is documented in the model docstring.
- **MBQ-05 status:** **remains open** (blocks the setup-wizard/
  credential-acquisition slice only). The row gains a note (register
  impact below) recording this Task 002 containment direction and the
  2026-07-06 re-verified facts (including the now-dated January 1, 2026
  cutoff) — proposed wording only until AR-025 is accepted.
- **What setup wizard copy must not claim yet (binding on future
  tasks):** must not claim a new custom app can be created in the
  Shopify admin (officially discontinued); must not present the
  admin-created path as the universal path; must not promise 24-hour /
  client-credentials support (unbuilt, undecided); must not claim any
  token auto-refresh; must not describe storage as encrypted (standing
  rule); must not assert the historical one-time-reveal/"last 4"
  behavior (unverified on live pages).
- **What Task 003 or later must handle:** Task 003 — verification of
  the stored path-A token (test connection), `credential_state =
  'invalid'` transitions, and the empirical open questions already
  assigned to it. A future MBQ-05-gated task — the client-credentials
  variant end-to-end (fields + grant call + refresh strategy + wizard
  copy), only after ChatGPT decides MBQ-05's MVP direction.

## Decision 3 — scope snapshot placement

**Question (AR-024 open point):** do `granted_scopes` and
`granted_scopes_checked_at` live on `shopify.connector.store` (AR-024's
proposal) or on `shopify.connector.store.credential` — and does Task 002
create them?

### Options evaluated

- **3A — Store mirrors (`shopify.connector.store`), recommended:**
  scope handles are non-secret permission names (e.g. `read_products`),
  not credentials; every role legitimately reads them (the accepted
  granted-vs-required comparison UI, readiness scopes check, error type
  11 copy). On `store` they sit in the model every accepted surface
  already reads, written by the same single-writer service that writes
  every other mirror.
- **3B — Credential model:** groups the snapshot with the credential it
  describes, but the Admin-only ACL then hides non-secret data from
  auditor/operator/reviewer — so every scope surface would need a mirror
  on `store` **anyway** (duplication), and routine snapshot refreshes
  would write to the credential model, destroying its accepted audit
  property ("every write to the credential model *is* a credential
  event"). Rejected.
- **3C — Separate readiness-result model:** a new model for two fields;
  AR-024 already proposed **no** new readiness-result model (RA-012
  over-fragmentation pattern; the nine-card dashboard needs no per-check
  query model yet). Rejected — and out of Task 002's scope anyway.
- **3D — Job log only:** snapshots buried in
  `job.log.payload_snapshot` give no queryable current-state read-model;
  the UI would parse historical logs to answer "what scopes do we have
  now?", and freshness honesty (`…_checked_at`) would be reconstructed
  rather than stored. Rejected.

### Recommendation (exactly one)

**Recommendation — 3A: `granted_scopes` (Text, serialized JSON array of
scope handles) and `granted_scopes_checked_at` (Datetime) live on
`shopify.connector.store`, and Task 002 creates them** as two of the six
readonly, system-written status mirrors — empty until Task 003 first
writes them.

- **Exact model and field names:** `shopify.connector.store` →
  `granted_scopes` (Text; serialized JSON array, e.g.
  `["read_products"]`), `granted_scopes_checked_at` (Datetime). Both
  `readonly=True`, service-written only (single-writer rule), no
  defaults.
- **Why this creates no credential-leakage risk:** scope handles are
  permission *names* published in Shopify's own reference; they match
  no `SENSITIVE_KEYS` key and no `shpat_`/`shprt_` value pattern; they
  cannot contain a token (the snapshot is written from
  `accessScopes[].handle` values only, by Task 003 code that passes
  every mirror write through `redact()` defensively). Placing them on
  `store` also keeps the credential model free of any
  routinely-refreshed field — nothing ever needs to render, export, or
  report on the credential model, which is exactly what keeps the
  secret's host model out of every future view.
- **Included in Task 002:** yes — fields only, with no writer (Task 002
  makes zero Shopify calls; the fields stay empty). Creating them now
  completes the store's mirror schema in the same reviewed diff as the
  credential model, so Task 003 adds behavior only, no schema.
- **What Task 003 writes later:** on each successful test connection —
  the snapshot from `currentAppInstallation.accessScopes[].handle` and
  the check timestamp; on auth-shaped failures it leaves the last
  snapshot in place (staleness stays honest via the timestamp).
- **What the UI reads later (UI-gated):** the store form's scope
  comparison / technical-detail expand and the readiness scopes check
  read `granted_scopes` + `granted_scopes_checked_at` from `store` —
  never anything from the credential model.

## Final Task 002 implementation boundary

The authoritative, copy-paste version of everything below — including
the full test enumeration, manual validation, PR requirements, and
response format — is
[`task-002-final-implementation-prompt.md`](./task-002-final-implementation-prompt.md).
Summary of the exact boundary with the three decisions applied:

- **Model (new):** `shopify.connector.store.credential` —
  `_description = 'Shopify Connector Store Credential'`; no
  `mail.thread`; no views, ever, in this task; docstring records the
  Admin-only default-deny posture, the deliberate absence of the
  client-credentials fields (Decision 2), and the honest residual
  (Decision 1).
- **Fields (exact):**
  - `store_id` — Many2one → `shopify.connector.store`, `required=True`,
    `index=True`, `readonly=True`, `ondelete='restrict'`; SQL unique
    constraint (one credential row per store).
  - `access_token` — Char, not required, `copy=False`,
    `groups='shopify_connector_core.group_shopify_connector_admin'`;
    stored plain (Decision 1: no compute-blank); written only via the
    service methods.
  - `token_variant` — Selection
    `[('offline_custom_app', 'Offline Custom App Token')]`, default
    `offline_custom_app` (Decision 2).
  - `credential_state` — Selection `[('absent','Absent'),
    ('present','Present'), ('invalid','Invalid')]`, `required=True`,
    default `absent`, `readonly=True` (service-written; `invalid` is
    set only by Task 003+).
- **Store mirrors (exact, all `readonly=True`, system-written):**
  `credential_present` (Boolean, default False),
  `credential_last_verified_at` (Datetime),
  `credential_last_replaced_at` (Datetime),
  `credential_last_failure_reason` (Char; every write passes through
  `redact()`), `granted_scopes` (Text), `granted_scopes_checked_at`
  (Datetime) (Decision 3).
- **ACL (exact, one row added):**
  `access_shopify_connector_store_credential_admin,shopify.connector.store.credential.admin,model_shopify_connector_store_credential,shopify_connector_core.group_shopify_connector_admin,1,1,1,0`
  — no rows for auditor/operator/reviewer (default-deny), no unlink for
  anyone. No change to any existing ACL row; no new group; the
  store/settings `perm_create` gap and the `job.log` no-create posture
  are **not** touched (MBQ-44 residuals).
- **Service methods (exact, on the credential model):**
  `action_set_token(store, value)`, `action_replace_token(store,
  value)`, `action_clear_token(store)`, and the internal-only
  `_get_access_token(store)` — full behavioral contracts (mirror
  writes, stamps, atomicity, validation, redaction, the single
  sanctioned `sudo()`) in the final prompt. Write paths run as the
  calling user with **no** `sudo()` so ACL enforcement stays live.
- **Redaction utility (exact):**
  `shopify_connector_core/tools/redaction.py` — `redact(value,
  extra_secrets=None)` (str/dict/list/tuple, recursive, idempotent,
  non-string passthrough, never raises), `SENSITIVE_KEYS`
  (case-insensitive substring: `access_token`, `token`, `secret`,
  `password`, `authorization`, `x-shopify-access-token`, `api_key`,
  `apikey`, `client_secret`, `refresh_token`, `hmac`),
  `SENSITIVE_VALUE_PATTERNS` (`shpat_[A-Za-z0-9]+`,
  `shprt_[A-Za-z0-9]+`), exact-match scrub via `extra_secrets`,
  replacement marker `***`.
- **Tests (exact groups):** access matrix; field-`groups` second layer;
  redaction unit suite; service behavior + stamps-audit +
  token-absent-from-every-persisted-surface; no-job-log-rows assertion;
  single-sudo assertion. Dummy tokens only (e.g.
  `shpat_DUMMYDUMMYDUMMY0000000000000000`). Task 001A applicability
  rule: written + syntax-validated; execution status stated honestly if
  no runtime exists.
- **Forbidden areas (unchanged from the accepted spec):** no API
  client, no HTTP/`requests`/GraphQL strings, no test connection, no
  setup wizard, no views/menus/actions/wizards, no webhooks/controllers/
  cron, no domain logic, no `job.log` writes, no security-XML changes,
  no `adams_base`, no CI, no migrations, no DEC/register edits, no docs
  beyond the handoff.
- **Rollback (exact):** revert the single Task 002 PR; nothing depends
  on it; uninstall/revert drops the credential model and mirror fields —
  tokens are re-enterable by the Admin; no business data affected; no
  migration in either direction.

## Register impact proposal

**Proposed only — to be applied as *accepted* wording only by a future
ChatGPT acceptance patch.** This sprint applies the same content to
`master-blueprint-open-questions.md` as explicitly *proposed* notes (no
status changes), per the allowed-files list:

- **MBQ-04:** add a note that AR-025 proposes closure of the three Task
  002-specific decision points (compute-blank **rejected** for Task 002;
  `token_variant` = single `offline_custom_app` value; scope snapshot on
  `store`) and a gate-ready final prompt. **Status unchanged: Partially
  resolved (implementation-planning level).** MBQ-04 still closes fully
  only after Task 002's implementation is reviewed and accepted. Do
  **not** mark resolved.
- **MBQ-05:** add a note recording (a) the 2026-07-06 re-verification
  (unchanged findings, plus the now-dated January 1, 2026 legacy-cutoff
  and the "Legacy custom apps" admin management section), and (b) the
  proposed Task 002 containment direction (store path-A token only;
  seam preserved; B mechanics deferred; wizard-copy constraints). **Status
  unchanged: open** — the MVP acquisition-path decision remains
  ChatGPT's and continues to block the setup-wizard slice only. Do
  **not** mark resolved.
- **MBQ-44:** add a note that the exact credential ACL row text is now
  written out in the final implementation prompt (AR-025, proposed);
  both recorded residuals (store/settings `perm_create`; `job.log`
  system-append write path) are untouched and stay with Task 005 / Task
  003 respectively. **No status change.**
- **No other row is touched.** In particular MBQ-06/51/52/08 need no
  update (nothing here changes their AR-024 notes), and the four
  Task 003 decision points remain recorded exactly where AR-024 left
  them.
