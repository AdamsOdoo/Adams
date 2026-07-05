# MBQ-04 Credential Persistence Decision Proposal

## Status

**Proposed for ChatGPT review. Not accepted. Not implemented.** This document
proposes a recommended direction only; it creates no credential model, no
credential field, no API client, no setup wizard, no test-connection
mechanism, and does not itself change MBQ-04's recorded status in
`../03-architecture/master-blueprint-open-questions.md` (out of this session's
allowed-files scope). Any acceptance/register update is a separate future act.
Grounded in
[`../01-research/odoo-credential-storage-official-notes.md`](../01-research/odoo-credential-storage-official-notes.md)
(access date 2026-07-05).

## Problem

MBQ-04 ("Exact credential encryption/storage-at-rest mechanism") blocks four
concrete, connected pieces of work that cannot honestly proceed without it:

- **Setup wizard** — DEC-004 already commits to "masked token entry" and
  "least-privilege scope selection" in the wizard (`DEC-004` §UX implications),
  but no wizard can be built without a real field/model to write the entered
  token into.
- **Test connection** — DEC-004's "inline test-connection/readiness check"
  needs a live credential value to call the Shopify Admin API with; there is
  nothing to read until a storage location exists.
- **Shopify API client** — every authenticated GraphQL/REST call the connector
  makes needs to read the stored token at call time; the client cannot be
  designed against an undefined storage shape.
- **Sync execution (scheduled and manual)** — `ir.cron` jobs and
  manually-triggered syncs both need to authenticate identically; without a
  settled storage/access mechanism, the job-execution context's access to the
  credential (including whether it runs under `sudo()`) is undefined.

AR-019 (2026-07-05) explicitly declined to resolve this for the accepted
core-only slice 1, stating **no official Odoo encryption-at-rest evidence was
reviewed that session**, and AR-020 (2026-07-05) confirmed MBQ-04 as one of the
rows **explicitly descoped from the first implementation gate**, pending
"official Odoo encryption-at-rest evidence and a separate ChatGPT decision."
This document supplies that evidence.

## Evidence summary

Full detail, citations, and adversarial verification in
[`odoo-credential-storage-official-notes.md`](../01-research/odoo-credential-storage-official-notes.md).
Headline findings:

- **`password=True` is not an ORM storage mechanism at all.** It is a
  view-architecture XML attribute consumed only by the JS web client for
  **display-only masking**, after the true value has already been delivered to
  the browser by a prior `read()`. It provides no read-restriction and no
  encryption.
- **`res.users.password`** (Odoo's own login password) uses a *different*,
  purpose-built mechanism — compute-blanking on every read plus a one-way
  `CryptContext` hash written via raw SQL — not something `password=True`
  grants generically to any field.
- **`ir.config_parameter`** is plain `Char`/`Text` key-value storage with a
  single `group_system`-only ACL for the whole table, no encryption anywhere in
  its source, and no official documentation characterizing it as secure secret
  storage. Odoo's own `database.secret` value is stored through this exact
  mechanism with no special protection.
- **Field-level `groups`, `ir.model.access`, and `ir.rule` are access control,
  not encryption**, and are **all explicitly bypassed by `sudo()`/superuser
  mode** — confirmed at the field-`groups` level in source, not just at the
  model/record level.
- **Five real official examples** of third-party API credential storage
  (`ir.mail_server.smtp_pass`; Stripe/Adyen/Authorize.Net payment-provider
  secret keys; `iap.account.account_token`) all follow the **identical
  pattern**: plain `Char`, `groups='base.group_system'`, no `password=True`, no
  encryption before storage.
- **The only official encryption-at-rest claim found is infrastructure-level**
  (Odoo's corporate security page: AES-256 whole-database/whole-backup
  encryption), scoped explicitly to **"Odoo Cloud (the platform)"**
  (Odoo Online/Odoo.sh) — not confirmed for on-premise, and not a field-level
  ORM mechanism. No official 19.0 developer-reference page recommends any
  Odoo-internal secret-storage mechanism; the one page that discusses API keys
  directly says "store it securely" and points to an external OWASP cheat
  sheet.

**Net evidence conclusion:** Odoo 19 provides **no built-in field-level
encryption-at-rest** for any stored value, credential or otherwise. The
strongest protection any official Odoo mechanism offers a stored secret is
**access control** (`groups=` + `ir.model.access` + `ir.rule`), which every
real official example uses, and which is itself bypassed by `sudo()`. Genuine
encryption-at-rest exists only as an **infrastructure-level, Odoo-Cloud-only**
claim, outside the ORM/schema layer entirely.

## Options considered

### Option A — Continue full descope

No credential model or fields yet; MBQ-04 stays explicitly open pending a
future session.

- **Pros:** Zero risk of committing to a mechanism before ChatGPT reviews the
  evidence; keeps the no-code gate simple.
- **Cons:** Blocks setup wizard, test connection, API client, and sync
  execution indefinitely; the evidence gap that justified descoping (AR-019/
  AR-020) is now closed, so continuing to descope would no longer be an
  evidence problem, only a scheduling one.
- **What remains blocked:** everything named in "Problem" above, with no new
  information to change that until a future session repeats this research.

### Option B — Store token in Odoo using standard field/access controls

A dedicated credential field (or small set of fields: token, scopes, connected
status, last-verified timestamp) on the core substrate (`shopify.connector
.store` or a closely related model per the AR-019 naming), stored as a plain
`Char`/`Text`, restricted with `groups=` to an admin-equivalent group (mirroring
`base.group_system`'s role), paired with the view-arch `password` attribute for
UI masking and a `SENSITIVE_KEYS`-style log-redaction rule.

- **This is exactly what the evidence supports evaluating** — it is the
  identical mechanism every real official Odoo credential field uses
  (`smtp_pass`, Stripe/Adyen/Authorize.Net, IAP token), and it is what DEC-004
  already committed to at a policy level ("masked storage... field-level
  `groups`... least-privilege scopes").
- **UI masking vs. real security, made explicit:** the `password` view
  attribute stops the token appearing on screen; it does **not** stop the raw
  value being retrievable via `sudo()`, via any explicit ORM `read()` by a user
  in the allowed group, or via direct database/backup access. This must be
  documented as access control, never described internally or to the merchant
  as "encrypted."
- **Pros:** Matches Odoo's own de facto standard; no new/unproven mechanism;
  fastest path to unblocking the wizard/client/sync; consistent with the
  already-accepted DEC-004 posture (no DEC-004 amendment needed).
  **Cons/risks:** Plaintext-in-DB is real — any `sudo()` code path (including
  the connector's own background jobs, which commonly need elevated context to
  run at all) sees the token; a DB backup or dump exposes it; this is **not**
  "encryption at rest" and must never be represented as such in UX copy,
  security docs, or an App Store security review.

### Option C — Store token in `ir.config_parameter`

- **Evidence supports evaluating and then setting this aside**, not adopting
  it: `ir.config_parameter` gives **no** protection beyond a dedicated model
  field — same plain-`Text` storage, same `sudo()` bypass — while being **less
  granular** (one shared `group_system` ACL for the *entire* system-parameters
  table, vs. a dedicated field's own `groups=` scope) and less structured (no
  natural place for scopes/connected-status/rotation metadata alongside the
  secret; would need a parallel model anyway).
- **Pros:** None found that a dedicated field lacks. **Cons/risks:** Coarser
  access control than a dedicated field; conflates the credential with
  unrelated system configuration; Odoo's own core uses this exact mechanism for
  `database.secret` with no extra protection, so it sets no better precedent
  than Option B.
- **Recommendation within this option:** do not adopt as the primary
  mechanism; the evidence does not support it as superior to Option B on any
  axis checked.

### Option D — External secret manager / deployment-level secret injection

The actual token value lives outside Odoo's database entirely (an external
vault/secret manager, or a deployment-level environment variable/config
injected at process start); Odoo holds only a reference/handle (and possibly
connection metadata), not the secret itself.

- **Pros:** Removes the token from the Odoo database/backup exposure surface
  entirely; aligns with the OWASP guidance the official External API doc itself
  points to; a natural fit for a sophisticated on-premise deployment with its
  own secret-manager tooling already in place.
- **Cons/risks:** **No official Odoo 19 documentation, this session, describes
  any supported mechanism for a module to read a deployment-level secret at
  runtime** (no evidence of a sanctioned "read from environment/vault" pattern
  for a business-object credential) — this option would need its own,
  separate, official-evidence pass before being designable, which is outside
  MBQ-04's evidence scope as researched here. It is also unclear how this fits
  **Odoo.sh** (a managed build/deploy pipeline; whether admins can inject
  per-store custom secrets/env vars into a running Odoo.sh build was not
  checked this session) versus **on-premise** (straightforward: `odoo.conf`/
  environment variables are already the on-premise norm for `admin_passwd`/
  `db_password`) versus **Odoo Online SaaS** (already established elsewhere in
  this project's research as **incompatible with custom modules at all** —
  `odoo-official-architecture-notes.md`, RB-14 Part 2 — so moot for this
  connector regardless).
  This option would also likely require **revisiting DEC-004's "storage
  location"** wording, which currently reads as committing to storage inside
  an Odoo-managed field ("stored masked behind Odoo access rights and
  field-level `groups` on the credential field(s)").
- **Not designed further here**, per the task's instruction not to design
  implementation unless evidence supports it — evidence does not, yet.

### Option E — Hybrid: metadata-in-Odoo, secret outside Odoo

Store non-secret **lifecycle/status/scope metadata** in Odoo (connected
status, granted scopes, token type/expiry, last-verified timestamp, rotation
history) on the core model, while the actual secret value is held by whichever
mechanism Option D would use.

- **Pros:** Gets most of Option D's exposure-reduction benefit while giving the
  setup wizard/dashboard/error-center something concrete to render (status,
  scopes, health) without ever displaying or holding the secret in the
  ORM/database at all.
- **Cons/risks:** Inherits Option D's core evidence gap (no official Odoo
  mechanism confirmed for the secret-outside-Odoo half) and its DEC-004
  wording conflict; adds a second moving part (Odoo metadata + external secret)
  that must stay consistent, which is more implementation surface than Option
  B for a Phase 1 / Early Access single-store MVP.
- **Not designed further here**, for the same evidence-gap reason as Option D.

## Recommended decision

**Recommended (proposed only): Option B** — a dedicated credential field (or
small field set) on the Odoo-managed core substrate, using the exact pattern
every real official Odoo secret field uses today: plain storage,
`groups='<admin-equivalent group>'` access control, the view-arch `password`
attribute for UI masking, and a mandatory log-redaction rule for that field
name. This is recommended because it is (a) the only option the evidence
directly and repeatedly demonstrates as Odoo's own real-world practice, (b)
already consistent with DEC-004's accepted posture with no amendment needed,
and (c) immediately unblocks the setup wizard, test connection, API client,
and sync execution work this MBQ-04 gap has been holding back since AR-019.

**Explicitly not recommended as the primary mechanism, but named for ChatGPT's
own weighing:** Options D/E (external secret / hybrid) may be a stronger
security posture for a security-conscious on-premise deployment, but they rest
on an official-evidence gap this session did not close (no confirmed Odoo
mechanism for reading a deployment-level secret at runtime) and would require
revisiting DEC-004's "storage location" wording. If ChatGPT wants that
security posture evaluated, it should be routed as its **own follow-up
architecture-review row**, not folded into this MBQ-04 acceptance, since it
would need a dedicated evidence pass (Option D's own gap) before being
decidable.

## MVP impact

- **Store connection:** unblocked in principle once Option B's exact
  model/field names are decided (still a follow-up item below) — no new
  evidence gap remains.
- **Setup wizard:** DEC-004's "masked token entry" step becomes buildable
  against a real field; still requires the field/model naming follow-up before
  any code.
- **Test connection:** buildable once a credential field exists to read at
  call time; this document does not decide the exact check performed.
- **Scheduled sync:** `ir.cron` jobs reading the stored token will very likely
  do so under an elevated (`sudo()`-equivalent) execution context — per the
  evidence, that context bypasses field-level `groups`, so the retry/backoff
  and job-execution design (DEC-009) must treat "the job process itself can
  always read the token" as a given, not a gap to close.
- **Manual sync:** an operator-triggered sync runs as the operator's own user;
  if that operator is not in the credential field's allowed `groups`, the sync
  action itself would need to run through a scoped, audited elevation (e.g. an
  `@api.model` service method that reads the token internally rather than
  exposing it to the triggering user) — a follow-up design detail, not decided
  here.
- **Deployment assumptions:** the connector's security posture now honestly
  differs by hosting choice — **Odoo Cloud (Odoo Online/Odoo.sh)** gets the
  documented AES-256 infrastructure-level at-rest claim as a backstop;
  **on-premise** gets no such documented backstop at all. This asymmetry should
  be surfaced honestly in future setup/health UX and security documentation,
  not glossed over. (Odoo Online itself remains out of scope for a custom
  module per existing research, so this mainly concerns Odoo.sh vs.
  on-premise.)
- **App Store packaging later:** if distribution ever moves to the public App
  Store (currently deferred per DEC-004), the credential field's access
  control, masking, and log-redaction posture recommended here would need to
  be re-demonstrated as part of that review; nothing here decides App Store
  readiness.

## Security risks

- **Database backup exposure:** a plain-column secret is present, unencrypted
  at the application layer, in any database dump/backup; Odoo Cloud's
  AES-256 claim covers the backup file at rest but not a restored/opened copy
  of that backup elsewhere.
- **Admin/user access exposure:** anyone in the field's allowed `groups` can
  read the value through the ORM/API; anyone with `sudo()`/superuser context
  (confirmed to bypass field-`groups` too) or direct database access can read
  it regardless of group membership.
- **Logging exposure:** must be designed for explicitly — Odoo's own
  `SENSITIVE_KEYS` payment-module precedent shows this is treated as a
  separate duty from storage; the connector needs an equivalent redaction rule
  for its own credential field name(s) from day one, in job logs and error
  records alike.
- **Accidental token display:** the `password` view attribute prevents casual
  on-screen display but not a deliberate reveal-toggle click, an API/RPC
  response inspection, or a misconfigured view/report that omits the
  attribute — view-authoring discipline is a real, ongoing risk, not a one-time
  setup task.
- **Token rotation:** no official Odoo mechanism reviewed provides rotation
  tooling; this is 100% connector-designed, and not decided by this document
  (see Follow-up).
- **Revocation:** same — no official mechanism found; the connector must
  define its own reconnect/revoke flow (DEC-004 already anticipates a
  reconnect-on-refresh-failure UX for an expiring-token variant).
- **Least privilege/scopes:** DEC-004 already commits to least-privilege scope
  selection at setup time; this document adds nothing new here beyond noting
  that scope metadata is a natural companion field to whatever credential
  mechanism is chosen.
- **Odoo.sh vs. on-prem differences:** Odoo.sh/Odoo Online get the documented
  AES-256 infrastructure claim; on-premise deployments get no equivalent
  documented guarantee at all and are entirely dependent on the customer's own
  disk/backup encryption practice — a materially different risk profile the
  connector's documentation should state plainly rather than imply parity.

## Required follow-up before coding

The following are **not decided by this document** and must be settled (by
ChatGPT, in a future session or acceptance patch) before any credential-related
code is written:

- **Model name(s)** — whether the credential field(s) live directly on
  `shopify.connector.store` or a separate, closely-coupled model.
- **Field name(s)/type(s)** — exact names and Char/Text typing for the token,
  and for any companion scope/status/expiry metadata fields.
- **Storage mechanism** — final confirmation of Option B (plain field +
  `groups`) versus routing Option D/E to its own follow-up evidence pass, per
  ChatGPT's weighing above.
- **Masking behavior** — confirming the view-arch `password` attribute is used
  on every view exposing the field, with no exception.
- **Access groups** — the exact group XML ID(s) gating the field (AR-019
  proposed four groups: `admin`/`operator`/`reviewer`/`auditor` — which of
  these, if any, get credential-field access is not decided here).
- **Audit metadata** — what gets logged about credential changes (who/when),
  without ever logging the value itself.
- **Rotation/revocation behavior** — the reconnect/rotate/revoke UX and any
  backing job/state machine.
- **Test-connection behavior** — exactly what the pre-flight check calls and
  what it reports on failure.
- **No-logging rule** — the connector's own `SENSITIVE_KEYS`-equivalent
  redaction list and where it is enforced (job logs, error records, any future
  telemetry).
- **Rollback behavior** — how a failed/partial credential setup is safely
  undone (e.g. a store left in a "connecting" vs. "connected" state).

## Proposed MBQ-04 classification

**Partially resolved.**

Justification: the evidence gap that blocked MBQ-04 since AR-019/AR-020 — "no
official Odoo encryption-at-rest evidence was reviewed" — is now closed with a
definitive, adversarially-verified answer: **no official Odoo 19 field-level
encryption-at-rest mechanism exists; the strongest official mechanism is access
control (`groups=`), which every real Odoo example uses and which `sudo()`
bypasses; genuine encryption-at-rest is infrastructure-level and Odoo-Cloud-
only.** That is a real, citable resolution of the *evidence* question MBQ-04
asked. However, MBQ-04 also asks for a *decision* on "storage location," and
this document only **proposes** Option B rather than deciding it — the exact
model/field names, access groups, and rotation/audit design remain open
follow-up items requiring ChatGPT's review of this proposal. It is therefore
neither fully "resolved" (no decision has been accepted yet) nor still
"explicitly descoped" (the evidence blocker AR-019/AR-020 cited is gone) nor
"still open" in the same sense as before (a concrete, evidence-backed
recommendation now exists). **Partially resolved** — evidence resolved in
full; mechanism selection pending ChatGPT acceptance of Option B (or a
different option) from this proposal.
