# Shopify Token-Acquisition Decision Brief (MBQ-05 Follow-Up)

> **Decision brief for ChatGPT review — not an accepted decision record.** This
> is not filed as a numbered `DEC-XXX` ADR because the evidence, while
> substantial, does not settle the single most decision-critical question
> (whether OAuth authorization-code-grant actually works end-to-end against a
> Dev-Dashboard-created custom app) — per the instruction not to create a final
> accepted decision unless the evidence is strong enough. If ChatGPT accepts a
> direction below, that acceptance should be recorded as a proper `DEC-XXX` (or
> as an MBQ-05 closure note in
> [`../03-architecture/master-blueprint-open-questions.md`](../03-architecture/master-blueprint-open-questions.md)),
> not by editing this file's status in place.

## Status

**Proposed for ChatGPT review.** Prepared 2026-07-07. Supersedes nothing;
extends the still-open **MBQ-05** row and the still-open "exact custom-app
creation surface and token-acquisition mechanics" item in
[`DEC-004`](./DEC-004-distribution-api-auth-strategy.md) ("What remains
blocked"). Does not reopen DEC-004's accepted offline/unattended access model,
masked storage, or least-privilege posture — all unchanged.

## 1. Problem statement

Task 003's live manual validation (PR #107,
[`../05-qa/task-003-validation-results.md`](../05-qa/task-003-validation-results.md))
recorded VAL-B2 (the valid-token positive-connection test) as **BLOCKED**: no
real Shopify Admin API access token compatible with the connector's shipped
credential shape (`token_variant='offline_custom_app'`, a single long-lived
secret, no OAuth) was obtainable from the Shopify Dev Dashboard app used during
that session. This is not a test-environment inconvenience — it reflects a real
Shopify platform change: **as of January 1, 2026, new custom apps can no longer
be created directly in the Shopify admin**, closing the exact "reveal a token in
the UI" path the connector's setup story implicitly assumed. Before continuing
Task 003 validation, or starting Task 004, this project needs a decided
direction for how a *new* merchant obtains a compatible token.

## 2. Evidence summary

Full detail, quotes, and citations:
[`../01-research/shopify-token-acquisition-research.md`](../01-research/shopify-token-acquisition-research.md).
Key points (all **[Fact]**, independently re-verified live on 2026-07-07 against
`shopify.dev`/`help.shopify.com`/`changelog.shopify.com`, unless marked
otherwise):

- **[Fact]** Admin-created custom apps can no longer be newly created since
  **January 1, 2026**; existing (legacy) ones keep working but cannot have their
  token rotated except by uninstall/reinstall or full delete-and-recreate (the
  latter is now impossible for admin-created apps specifically).
- **[Fact]** New custom apps are created via the **Dev Dashboard or Shopify
  CLI**. Shopify's own tutorial for "building apps for your own store" via the
  Dev Dashboard shows **only** the client-credentials grant: a 24-hour token,
  obtained programmatically via Client ID + Client Secret, never shown in the
  admin, and restricted to apps and stores in the *same* Shopify organization.
- **[Fact]** Client credentials grant is explicitly **not** how "public or
  custom apps" in general are meant to acquire tokens — those must use token
  exchange or the OAuth authorization code grant instead. Shopify explicitly
  tells developers "building apps for other merchants" to use Shopify CLI
  instead of the client-credentials tutorial.
- **[Fact]** The OAuth authorization code grant, by default, still yields a
  **non-expiring offline token** — the same shape the connector already stores
  — and Shopify explicitly names ERP integrations (like this connector) as
  apps that don't need to be admin-embedded (i.e., standalone-app-eligible).
- **[Fact]** Custom apps and merchant-created apps (Dev Dashboard or admin) are
  **explicitly and repeatedly exempt** from Shopify's new (Dec 2025) mandatory
  expiring-offline-token model — that mandate applies only to public apps, on a
  phased 2026-04-01 / 2027-01-01 timeline. The connector's non-expiring,
  single-secret model is not at risk of being sunset by this change.
- **[Open question — decision-critical, unresolved]** No official Shopify page
  gives a worked example confirming that a Dev-Dashboard-created custom app
  (built for a merchant's own store) can actually complete the standard OAuth
  authorization-code-grant flow to obtain a non-expiring offline token. Nothing
  forbids it in the general documentation, but nothing officially demonstrates
  it either. This is the load-bearing unknown behind every option below.
- **[Fact]** A development store (the environment Task 003's checklist already
  requires) has no documented Admin API restriction that would affect the
  connector's read-only test-connection call, beyond commerce/checkout-specific
  test restrictions that are out of scope for it.

## 3. Options

Full comparison:
[`../03-architecture/shopify-token-acquisition-options.md`](../03-architecture/shopify-token-acquisition-options.md).
Summary:

- **Option A — offline/custom-app token only.** Keep today's shipped model
  as-is; a merchant supplies a static long-lived token by whatever means
  available. **As implemented, this is not yet a self-serve story for new
  merchants** — no in-product path exists today for a merchant without a
  pre-2026-01-01 legacy app to obtain a compatible token.
- **Option B — OAuth/token acquisition before MVP customer-facing setup.**
  Build a real authorization-code-grant flow (hosted redirect endpoint, HMAC
  verification, code exchange) before treating setup as customer-ready. Real
  implementation effort; also currently unvalidated against the specific
  Dev-Dashboard-custom-app scenario.
- **Option C — dual path.** Keep Option A's storage/shape for MVP; treat the
  "how does a new merchant mint a compatible token today" gap as a **research
  validation step** (attempt the standard OAuth exchange by hand, outside the
  Odoo codebase, against the same blocked development store), with Option B
  scoped as an explicit, gated follow-up once that step's result is known.

## 4. Recommended decision

**Recommend Option C**, specifically:

1. **Immediately** (a future, separately-scoped Task-003-continuation session,
   not this one): attempt the standard OAuth authorization-code-grant flow, by
   hand, using generic tooling outside the Odoo codebase (e.g. a documented
   `curl` recipe or a small standalone script), against a fresh Dev-Dashboard
   custom app built for the **same** development store already used in the
   blocked validation session (`mqiu21-yz.myshopify.com`), explicitly requesting
   a **non-expiring** offline token (`expiring` omitted/`0`). Record the actual,
   observed result — success or failure — as a **[Fact]**, not an assumption.
2. **If that attempt succeeds:** the resulting token is compatible with the
   existing `access_token` field and `token_variant='offline_custom_app'` value
   with **zero code change**. VAL-B2 should be re-attempted with that token,
   and the connector's setup documentation should be updated to describe this
   one-time manual exchange step honestly (it is materially more involved than
   the old admin-UI reveal, and that must not be hidden from new merchants or
   from future validators).
3. **If that attempt fails** (e.g. Shopify enforces client-credentials-only
   behavior for Dev-Dashboard custom apps in practice): this is decisive
   evidence that Option B (a real OAuth build) — or a schema extension
   supporting the client-credentials/24-hour-refresh model — is required before
   MVP can honestly claim self-serve setup for new merchants, and that decision
   should be escalated back to ChatGPT with the empirical result attached.
4. Either way, **do not build Option B's implementation before step 1's result
   is known** — building against the unconfirmed combination risks wasted
   effort if Shopify does not actually support it as the general documentation
   implies.

This recommendation is offered as a **[Recommendation]** per `CLAUDE.md` §8,
tied to the facts above — it is not a **[Decision]** until ChatGPT accepts it.

## 5. Required follow-up if ChatGPT accepts

- Schedule a small, explicitly-scoped, **docs/QA-only** follow-up session (no
  addon code, no manifest, no test file — mirroring this session's and the
  Task 003 validation session's own scope discipline) whose sole deliverable is
  running the manual OAuth-exchange experiment above and recording the result
  in an update to
  [`../05-qa/task-003-validation-results.md`](../05-qa/task-003-validation-results.md)
  and this brief.
- Once that result is known, route the actual acquisition-path decision (Option
  A/B/C, finalized) through a proper `DEC-XXX` ADR and update MBQ-05 to
  "Resolved" in
  [`../03-architecture/master-blueprint-open-questions.md`](../03-architecture/master-blueprint-open-questions.md).
- If Option B is ultimately required, that becomes its own
  `CLAUDE.md` §9-style implementation task (allowed files, forbidden files,
  acceptance criteria, tests, rollback notes) — not started by this brief.

## 6. What remains blocked

- **Task 003 manual validation is not complete.** VAL-B2, VAL-E1, VAL-B4–B7,
  VAL-A4, VAL-C3, VAL-D1–D2, and VAL-G1–G4 remain blocked or not tested (see
  [`../05-qa/task-003-validation-results.md`](../05-qa/task-003-validation-results.md)).
  This brief does not change that.
- **Task 004 remains blocked** — see §8 below.
- **No code, test, manifest, or security-file change is authorized by this
  brief.** It is a documentation/decision-prep artifact only.
- **MBQ-05 remains open**, not resolved, until ChatGPT accepts a direction and
  the recommended empirical follow-up (§5) is executed.

## 7. Explicit non-goals

- This brief does **not** decide whether the connector will ever support public
  App Store distribution (still deferred per DEC-004/RA-003).
- This brief does **not** decide the exact field/model shape for a future
  client-credentials or expiring-offline-token variant — that is Task 004+
  implementation-planning work, contingent on the §5 follow-up's result.
- This brief does **not** propose, authorize, or begin any OAuth
  implementation code.
- This brief does **not** mark Task 003 complete or reclassify VAL-B2 as
  passed, failed, or waived.
- This brief does **not** assert that the manual OAuth-exchange experiment in
  §4 will succeed — that is an explicitly unvalidated hypothesis, not a claimed
  fact.

## 8. Can Task 003 continue without OAuth being built?

**Yes, conditionally.** Task 003 validation can continue in a future session
without the connector implementing any OAuth code, by running the manual
authorization-code-grant experiment described in §4 entirely outside the Odoo
codebase (generic tooling, not a connector feature) and feeding whatever token
results into the **existing** Task-002 credential-entry mechanism exactly as
Option A already works. If that experiment fails, Task 003's VAL-B2 remains
blocked pending a further ChatGPT decision (Option B or a schema change) — it
would **not** be appropriate to mark Task 003 "complete" by silently
re-scoping VAL-B2 away without that decision.

## 9. Can Task 004 start before this is resolved?

**No.** Per `CLAUDE.md` §6 and the existing handoff record, Task 004 (or any
next-feature work) remains blocked until: (a) Task 003 manual validation is
complete or ChatGPT explicitly accepts a formal re-scope of VAL-B2, and (b) the
token-acquisition direction in this brief (or a corrected version of it) is
accepted by ChatGPT. Building next-feature sync logic on top of a connection
path that has never been proven to establish a real, valid Shopify connection
would risk building on an unvalidated foundation — exactly the risk `CLAUDE.md`
§9's "definition of done" and the Task 003 checklist's own preconditions exist
to prevent. This brief does not unblock Task 004, and no part of it should be
read as doing so.

## 10a. Continuation-session attempt (2026-07-07) — blocked before execution

A session was run, scoped exactly as §5 recommended — a docs/QA-only
follow-up whose sole deliverable was to attempt the manual
authorization-code-grant experiment described in §4. **The experiment was
not executed.** The session could not obtain either of the two prerequisites
needed to reach the Shopify Dev Dashboard / Shopify Admin at all:

1. **No Fable (or equivalent authenticated browser-automation) tool or
   connector was available** in that execution session. Checked and
   confirmed absent via the session's tool-discovery mechanisms (no matching
   tool, no matching installed/enabled connector, no matching plugin or
   skill).
2. **No Shopify Dev Dashboard Client ID/Client Secret or account
   login/2FA path was available** to that session (checked the process
   environment; nothing found). Per this project's secret-handling rules,
   such credentials must never be typed into chat/docs by an agent session
   in any case — they require a human operator or a securely provisioned,
   session-scoped credential channel.

**This is not evidence for or against the decision-critical open question
in §2** (whether authorization-code-grant actually works against a
Dev-Dashboard-created custom app) — no request reached Shopify. The
recommendation in §4 stands entirely unchanged and unvalidated. Full record:
`docs/01-research/research-handoff.md`'s continuation-session entry and
`docs/05-qa/task-003-validation-results.md` §8.

**Updated required follow-up:** before this experiment can be attempted
again, a future session needs both (a) an enabled Fable-equivalent
browser-automation tool/connector, and (b) a secure way to exercise the
Shopify Dev Dashboard consent/token-exchange steps without exposing secrets
to the agent's chat, docs, or logs (e.g. a human operator performing the
browser/consent steps directly and reporting back only the redacted
outcome). §5's original recommendation (run the experiment, record the
result, then route the acquisition-path decision through a `DEC-XXX` ADR) is
otherwise unchanged.

**Option C is neither confirmed nor rejected by this continuation session —
it remains this brief's [Recommendation], not a [Decision], exactly as in
§10 below.** Task 003 remains incomplete; Task 004 remains blocked; MBQ-05
remains open. OAuth implementation remains a future, not-yet-required item
pending the still-unrun empirical step.

## 10b. ChatGPT deferral decision for Task 004 gate (2026-07-07)

ChatGPT has reviewed the state recorded above (§10a: the OAuth/Fable
experiment blocked before execution) together with PR #110's static/offline
sweep and PR #111's Task 004 readiness preflight package, and has issued a
**deferral decision**, recorded in full in
[`DEC-021-val-b2-deferral-for-task-004.md`](./DEC-021-val-b2-deferral-for-task-004.md).
Summary — this section does not restate DEC-021's full content, only its
effect on this brief:

- **Option C remains recommended but unproven.** DEC-021 does not accept,
  reject, or confirm Option C — the empirical OAuth authorization-code-grant
  experiment described in §4 above has still never been run. Option C
  remains this brief's **[Recommendation]**, not a **[Decision]**.
- **The OAuth/manual token experiment is deferred from the Task 004 gate.**
  DEC-021 defers VAL-B2 (and, with it, the requirement that this experiment
  succeed before Task 004 can be gate-reviewed) — it does **not** mark the
  experiment complete, does **not** run it by proxy, and does **not** change
  §10a's blocked-before-execution record in any way.
- **Token acquisition remains unresolved for customer-facing setup.** Nothing
  in DEC-021 lets the connector claim a self-serve, proven token-acquisition
  path for new merchants. That gap, and the "no in-product path exists today
  for a merchant without a pre-2026-01-01 legacy app" limitation named in §3
  above (Option A), stand exactly as before.
- **MBQ-05 is deferred for Task 004 only, not resolved.** See the
  corresponding MBQ-05 row update in
  [`../03-architecture/master-blueprint-open-questions.md`](../03-architecture/master-blueprint-open-questions.md),
  which links back to DEC-021. MBQ-05 continues to block the setup-
  wizard/credential-acquisition slice and any customer-facing setup claim.
- **Task 004 must not implement OAuth or claim live connection proof.** Per
  DEC-021 §4: no OAuth implementation, no setup wizard, no customer-facing
  connection flow, no domain sync, no activation/lifecycle actions, and no
  claim anywhere (code, tests, docs, or PR description) that a live valid
  Shopify connection has been proven, until VAL-B2 or an accepted replacement
  validation actually passes.

This section does not change §§1–10a above in any way — it only records
where the control room's review of this brief's own open items landed, for
the narrow, explicitly-scoped purpose of letting Task 004 gate-opening
*review* proceed. See DEC-021 for the full decision, its non-decisions, and
its constraints.

## 10. Recommendation for ChatGPT

Accept the Option C direction in §4, and authorize the narrow, docs/QA-only
follow-up session in §5 as the next scoped piece of work — before any further
Task 003 validation attempt and before any Task 004 planning. If ChatGPT
prefers to skip the empirical step and commit directly to Option A (accepting
the new-merchant onboarding gap as a documented limitation for now) or Option B
(commit to building OAuth immediately), say so explicitly; either is a
reasonable call given the evidence, but this brief's own recommendation is the
lower-risk, evidence-gathering path in §4.
