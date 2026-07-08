# Task 006A Completeness Audit

> **Audit only.** This document is a verification/completeness check of
> already-merged Task 006A research. It creates **no architecture decision**,
> **no DEC file**, and **no implementation scope**, and it **does not
> authorize any implementation**. Every finding below is classified per
> `CLAUDE.md` §8 (Fact / Inference / Recommendation / Open question). The
> only actionable output of this document is a **Recommendation** (§9),
> which remains subject to ChatGPT review and approval before any Task 006B
> session starts.

- **Audit date:** 2026-07-08
- **Audit branch:** `claude/task-006a-completeness-audit-ptq56q`
- **Audited against:** `origin/Shopify-connector` @ `b39096e475fb3c51765fb9baef8dbcbad20a1efb`
- **Scope:** verify Task 006A research completeness after four fragmented
  parallel PRs, and specifically resolve whether a standalone Shopify
  official-API research shard is missing and, if so, whether that gap must
  be backfilled before Task 006B (sync-engine architecture gate) may start.

---

## 1. Status summary

**[Fact]** All four expected Task 006A PRs (#123, #124, #125, #126) are
merged into `Shopify-connector`, and their merge/head commits are confirmed
ancestors of the current `Shopify-connector` HEAD (`b39096e`) via
`git merge-base --is-ancestor`. **[Fact]** The originally-planned standalone
file `docs/01-research/sync-engine-shopify-source-notes.md` does **not**
exist anywhere in the repository (confirmed by direct filesystem check, not
inference). **[Inference, evidence-backed]** Its intended content was not
dropped — it was distributed across four existing files (`shopify-official-
api-notes.md`, `sync-engine-source-inventory.md` §4, `sync-engine-source-
notes.md`, `sync-engine-evidence-map.md`) plus a fifth cross-referenced file
from a sibling shard (`sync-engine-queue-idempotency-source-notes.md`, PR
#126), rather than a single dedicated shard. **[Fact]** No architecture
decision, no `DEC-025`, no implementation-scope file, and no sync-engine or
Shopify-domain code exists anywhere in the repository as of this audit. See
§9 for the recommendation this audit produces.

---

## 2. Merged PR inventory

| PR | Title | Base → Head SHA | Merged? | Ancestor of current `Shopify-connector` HEAD? |
| --- | --- | --- | --- | --- |
| **#123** | Task 006A-4: competitor/common sync pattern research | base `9247fea3`, head `e50d89bc` | ✅ merged (`aeaf7eb7`) | ✅ confirmed |
| **#124** | Task 006A-2: Odoo/repo substrate research | base `9247fea3`, head `22a31603` | ✅ merged (`3735ae22`) | ✅ confirmed |
| **#126** | Task 006A-3: queue/idempotency/retry/backoff/dead-letter source notes | base `3735ae22`, head `c5cf846e` | ✅ merged (`3c9fad89`) | ✅ confirmed |
| **#125** | Task 006A: sync engine source research and evidence map (final synthesis, revision 2) | base `3c9fad89`, head `88a8d316` | ✅ merged (`b39096e4`) | ✅ confirmed (= current HEAD) |

**[Fact]** Merge order was #123 → #124 → #126 → #125, and PR #125's
merged revision 2 explicitly incorporates both PR #124 and PR #126 by
cross-reference (confirmed by reading PR #125's description and its
"Synthesis hierarchy" section, corroborated by `git log --oneline` showing
all four merge-commit lines present in `origin/Shopify-connector` history).
No PR in this set is still open, and none was force-pushed or rewritten
after merge.

---

## 3. Expected shard inventory vs. actual files

| Expected shard (original parallel plan) | File | Exists? | Source PR |
| --- | --- | --- | --- |
| Competitor/common sync pattern research | `docs/01-research/sync-engine-competitor-pattern-notes.md` | ✅ Yes (518 lines) | #123 |
| Odoo/repo substrate research | `docs/01-research/sync-engine-odoo-repo-source-notes.md` | ✅ Yes (706 lines) | #124 |
| Queue/idempotency/retry/backoff/dead-letter research | `docs/01-research/sync-engine-queue-idempotency-source-notes.md` | ✅ Yes (1,333 lines) | #126 |
| **Shopify official API research (standalone shard)** | `docs/01-research/sync-engine-shopify-source-notes.md` | ❌ **No** | *(none — never created)* |
| Final synthesis / evidence map package | `docs/01-research/sync-engine-source-inventory.md`, `sync-engine-source-notes.md`, `sync-engine-evidence-map.md`, `docs/05-qa/sync-engine-open-questions.md`, `docs/05-qa/sync-engine-risk-register.md` | ✅ Yes (all five) | #125 |

**[Fact]** Three of the four planned shard files exist exactly as scoped.
The fourth — the standalone Shopify official-API shard — was never created
as its own file at any point in the four PRs' history (confirmed by `git
log --follow` / glob search finding zero commits ever touching that
filename).

---

## 4. Missing / present / covered-by-synthesis classification

| Item | Classification |
| --- | --- |
| `sync-engine-competitor-pattern-notes.md` | **Present** — matches plan exactly |
| `sync-engine-odoo-repo-source-notes.md` | **Present** — matches plan exactly |
| `sync-engine-queue-idempotency-source-notes.md` | **Present** — matches plan exactly |
| `sync-engine-shopify-source-notes.md` | **Missing** (never created) — **but covered-by-synthesis** (see §5) |
| `sync-engine-source-inventory.md` / `-source-notes.md` / `-evidence-map.md` | **Present** — final synthesis, PR #125 |
| `sync-engine-open-questions.md` / `sync-engine-risk-register.md` | **Present** — final synthesis, PR #125 |

**[Recommendation]** Because the missing file's intended *content* is
present and traceable (§5), it should be classified as an **organizational
gap** (naming/parity with sibling shards), not a **research gap** (missing
evidence). This distinction is the crux of the §9 recommendation.

---

## 5. Shopify official API shard assessment

PR #125's `sync-engine-source-inventory.md` §4 contains a dedicated,
freshly-fetched (2026-07-08), officially-sourced inventory numbered **S1–
S16**, all citing `shopify.dev` and graded **Primary**. Representative
entries (verbatim from the inventory table):

- `S1` — Paginating results with GraphQL (`/docs/api/usage/pagination-graphql`)
- `S4` — General usage limits / cost (`/docs/api/usage/limits`)
- `S6`–`S12` — Bulk operations overview, query/import mechanics,
  `bulkOperationCancel`, `BulkOperationStatus`, `BulkOperationErrorCode`,
  `BulkOperation` object
- `S13`/`S14` — About webhooks; verify webhook deliveries (HMAC-SHA256,
  `X-Shopify-Webhook-Id` dedup, retry schedule)
- `S15`/`S16` — Idempotent requests; implementing idempotency

PR #126 independently fetched a **separate, non-overlapping** Shopify
source set (`SH-1…SH-18`, part of its 52-source inventory), which PR #125's
revision 2 cross-references rather than duplicates — most importantly
`SH-4` (GraphQL can return HTTP 200 with a `THROTTLED` body) and `SH-1`
(REST 429 + `Retry-After`, re-verified independently of PR #125's older
baseline).

**Topic-by-topic verdict** (10 topics named in the audit brief):

| # | Topic | Verdict | Primary citation(s) |
| --- | --- | --- | --- |
| 1 | Admin GraphQL overview | ✅ Covered | `shopify-official-api-notes.md` (R24) — "All apps and integrations should be built with the GraphQL Admin API." |
| 2 | GraphQL cost / rate limits | ✅ Covered | R24 (field-cost table, points/plan), S4, cross-checked by `SH-8`/`SH-2` |
| 3 | Cursor pagination | ✅ Covered | S1, S2, S3 — edges/node/cursor, `pageInfo`, 250-item max page |
| 4 | Bulk operations | ✅ Covered | S6–S12 — JSONL format, 7-day URL expiry, concurrency limits, error codes |
| 5 | Webhooks (delivery/retry) | ✅ Covered | S13, S14 — 1s/5s timeout, 8 retries over 4 hours, 8-failure auto-delete |
| 6 | Webhook HMAC / duplicate delivery | ✅ Covered | S14 — HMAC-SHA256 raw-body verification, `X-Shopify-Webhook-Id` dedup |
| 7 | Shopify idempotency mechanics | ✅ Covered | S15, S16 — 24h key TTL, `@idempotent` directive/argument styles |
| 8 | REST 429 + Retry-After | ✅ Covered (doubly) | R24 + PR #126's `SH-1` independently re-verifying the same fact |
| 9 | GraphQL HTTP 200 + THROTTLED body | ✅ Covered — **but sourced from PR #126, cross-referenced into PR #125** | `SH-4`, cited in `sync-engine-source-notes.md` and evidence-map claim 26 |
| 10 | Domain API surfaces (engine-requirement level only) | ⚠️ Partial-by-design | Inherited from pre-existing `shopify-official-api-notes.md` (R24); no new per-domain research added by Task 006A, consistent with deferring domain field-mapping to Tasks 010–014 |

**[Fact]** All 9 core protocol/mechanics topics (1–9) are backed by an
official `shopify.dev` source somewhere in the merged research
(PR #125 ∪ PR #126). **[Inference]** Topic 10's shallow treatment is
intentional scope discipline — the audit brief itself asks for "domain API
surfaces at engine-requirement level **only**" — not an oversight; treating
it as a required deep-dive here would itself risk scope creep into the
domain-implementation tasks. **[Open question, carried from prior
research, not introduced by this audit]** The `@idempotent` mutation count
discrepancy (16 per `S16`, dated 2026-02-02, vs. 17 per prior `R8`/`R10`)
remains unresolved and is explicitly flagged in both PR #125 and PR #126.

### Residual gaps identified after PR #125 and PR #126

1. **[Open question, pre-existing]** 16-vs-17 `@idempotent` mutation count
   discrepancy — unresolved, immaterial to sync-engine-level research,
   requires a future re-fetch to reconcile before any domain task relies on
   an exact count.
2. **[Open question, pre-existing, immaterial]** OCA `queue_job` minimum
   worker-count precondition cited as `--workers > 0` (PR #125 baseline) vs.
   `--workers > 1` (PR #126) — does not touch Shopify coverage and does not
   affect RA-004 either way.
3. **[Recommendation, this audit]** The "engine-requirement level only"
   scoping boundary for domain API surfaces (topic 10) is followed in
   practice but is not written down anywhere as an explicit, named boundary
   in PR #125's files. A future session (Task 006B or a light documentation
   pass) could state this boundary explicitly so it is not re-litigated.
4. **No topic among the 10 is left without any official-source coverage.**
   No blocking gap was found.

---

## 6. Evidence-map completeness assessment

**[Fact]** `docs/01-research/sync-engine-evidence-map.md` (62 lines)
contains **26 total claims**: Part A "Mandatory claims" (18 rows) and Part
B "Supplementary claims" (8 rows, explicitly labeled "beyond the mandatory
18"). A spot-check across five claims spanning the full range (claims 1, 9,
13, 18, 26) found every one backed by at least one named source ID
(`R#`/`S#`/`O#`/`Q#`/`E#`) or an explicit, disclosed negative finding (claim
18's "no Lite/Full packaging concept found in any reviewed doc" is itself
cited as a search result, not left uncited). **No claim in the evidence map
was found without a citation.** This satisfies `CLAUDE.md` §7's "no
unsupported claims" rule at the sampled rate; a full line-by-line
re-verification of all 26 rows was not performed by this audit (see §7 for
why a lighter-touch verification was judged sufficient here).

---

## 7. Open-question status

All six items the audit brief required to remain open are **confirmed
still open**, each with a direct quote and citation:

| Item | Status | Citation |
| --- | --- | --- |
| **VAL-B2** | Deferred / not passed | `DEC-024-task-005-closure.md`: *"No VAL-B2 pass is claimed... VAL-B2 remains deferred, not passed"* |
| **MBQ-05** | Partially routed / Open | `master-blueprint-open-questions.md`, MBQ-05 row: *"Status: Partially routed / Open — not Resolved."* |
| **TD-002** | Open | `technical-debt-register.md`, TD-002 row, Status column: `Open` |
| **Fulfillment scope/API model** | Cannot be finalized yet | `sync-engine-open-questions.md` item 36: *"Fulfillment scope/API model cannot be finalized yet... remain undecided"* |
| **Product first-sync deduplication** | Requires domain design | `sync-engine-open-questions.md` item 37: *"Product first-sync deduplication still requires domain design"* |
| **Token acquisition (many unrelated customers)** | Not fully resolved | `sync-engine-open-questions.md` item 38 + `shopify-token-acquisition-options.md`: branch B *"Not evaluated by this document. Must be separately researched and accepted by ChatGPT..."* |

**[Fact]** `sync-engine-open-questions.md` contains 43 numbered open
questions (39 from the original PR #125 session, plus 40–43 added in
revision 2 from PR #126's findings). **[Fact]**
`sync-engine-risk-register.md` contains 9 evidence-backed risks (SRR-01
through SRR-09, with SRR-08/SRR-09 added in revision 2). None of these
required-open items has been closed, resolved, or silently dropped.

---

## 8. Risks of proceeding to Task 006B

**[Risk]** If Task 006B (the sync-engine architecture gate) begins without
resolving the 16-vs-17 `@idempotent` mutation count, an architecture
decision could implicitly rely on the wrong count when scoping idempotent
mutation handling — low likelihood of direct impact (both counts are close
and the exact figure does not currently gate any named claim), but worth a
one-line re-verification before or during Task 006B rather than after.

**[Risk]** If Task 006B does not explicitly restate the "engine-requirement
level only" boundary for domain API surfaces, there is a moderate risk that
architecture-gate discussion drifts into per-domain field-mapping decisions
(product/order/customer/inventory/fulfillment shapes) that are out of scope
for a domain-neutral sync engine and are supposed to be deferred to Tasks
010–014. This is a **process risk**, not an evidence risk — the research
itself stayed correctly scoped; the risk is in how a future session
*uses* it.

**[Risk]** The token-acquisition architecture for "many unrelated
customers" (MBQ-05 branch B) and the fulfillment API model choice
(TD-002/DEC-011/MBQ-42/MBQ-60) are both still open. Task 006B's
sync-engine design should treat these as **explicit unknowns it must not
silently assume an answer to** — e.g., a sync-engine retry/backoff design
that implicitly assumes single-tenant OAuth, or a webhook-topic design that
implicitly assumes one fulfillment API model, would be premature
architecture built on an unresolved foundation.

**[Inference]** None of these three risks are blocking in the sense of
"missing evidence" — they are all already-disclosed, already-tracked open
items that Task 006B's own design work is expected to either respect as
constraints or explicitly route to a separate research/decision task (per
`DEC-023` §3.2 for the token-acquisition item, and per the existing
fulfillment-domain routing for TD-002/MBQ-42/MBQ-60).

---

## 9. Recommendation

**[Recommendation — subject to ChatGPT review; this audit does not decide
anything]**

**Recommendation A: proceed to Task 006B.** The Shopify official-API
research that Task 006B will need is present and officially sourced across
PR #125's S1–S16 inventory plus PR #126's cross-referenced `SH-` sources —
all 9 core protocol/mechanics topics required for sync-engine design
(pagination, rate limits, bulk operations, webhooks, HMAC/dedup,
idempotency, REST 429, GraphQL 200+THROTTLED) have at least one official
`shopify.dev` citation, and the one topic given lighter treatment (domain
API surfaces) is intentionally out of scope at this stage. The missing
`sync-engine-shopify-source-notes.md` file is an **organizational
naming/parity gap**, not a **substantive research gap** — a standalone
Shopify shard backfill PR would mostly re-package already-cited,
already-verified evidence into a new file rather than add new coverage.

**Recommendation B would only be warranted if** ChatGPT's review determines
that (i) shard-file parity with the other three sibling shards is itself a
governance requirement independent of content coverage, or (ii) the two
residual open discrepancies (§5, items 1–2) must be resolved via fresh
research rather than flagged for later reconciliation, or (iii) the
implicit "engine-requirement level only" scoping boundary (§5, item 3)
needs to be made explicit before Task 006B can safely proceed. None of
these three conditions is, in this audit's assessment, currently met by the
evidence — but they are exactly the kind of judgment call this audit
defers to ChatGPT rather than deciding unilaterally.

**This audit's recommendation is A: proceed to Task 006B**, carrying
forward the three residual items in §5 as tracked open questions (not
blockers), unless ChatGPT's review reaches a different conclusion.

---

## 10. Explicit non-decision statement

This document is an **audit only**. It:

- Creates **no architecture decision** and modifies no file under
  `docs/03-architecture/`.
- Creates **no `DEC-025`** or any other decision record under
  `docs/04-decisions/`.
- Creates **no implementation-scope file** under `docs/07-implementation-plan/`.
- **Does not authorize implementation** of any kind — no addon file,
  Python, XML, CSV, manifest, security, migration, CI, controller, view,
  wizard, OAuth, or domain-sync code was created or modified by this
  session.
- Does not itself decide between Recommendation A and B — that decision
  belongs to ChatGPT's review per `CLAUDE.md` §2 and §8 (a Recommendation is
  not a Decision until accepted and recorded in `docs/04-decisions/`).

**Next step:** ChatGPT review of this audit and its Recommendation A. If
accepted, Task 006B (sync-engine architecture gate) may proceed without a
separate Shopify shard backfill session. If ChatGPT instead selects
Recommendation B, a follow-up backfill PR should create
`docs/01-research/sync-engine-shopify-source-notes.md`, consolidating the
already-cited S1–S16/`SH-` evidence into a single named shard for parity
with the other three, plus resolving the two residual discrepancies noted
in §5.
