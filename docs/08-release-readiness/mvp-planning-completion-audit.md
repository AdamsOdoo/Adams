# MVP Planning-Completion Audit — Baseline Reconciliation, Full Planning Inventory, and Closure Results

> **Status: Proposed for ChatGPT review. NOT accepted. Docs-only.** This
> document is the master audit of the 2026-07-10 MVP planning-completion
> session (AR-042 candidate). It records (§1) the verified current
> repository/GitHub state, (§2) the authoritative inventory of every
> remaining planning item with a reconciliation verdict, and (§3–§6,
> appended by later phases of the same session) the closure results,
> contradictions found and corrected, evidence-quality assessment, and
> the final readiness verdict. **Nothing in this document opens a gate,
> issues a prompt, authorizes implementation, resolves a register row
> beyond explicitly-cited documentary facts, or converts a
> recommendation into a decision.** Claim classes per `CLAUDE.md` §8.

## 1. Verified current state (Phase A baseline)

All facts below verified directly against GitHub and the working tree on
2026-07-10 — not taken from any handoff or status document.

- **[Verified repository state]** `Shopify-connector` tip:
  `21d59ec06db13d72c1266913c2d9214c7e7caa82` ("Merge PR #147: Accept
  DEC-026 strategic direction") — matches the session prompt's expected
  tip exactly. This session's branch is based on that exact commit.
- **[Verified repository state]** PR #145 (Task 011 customer
  import/matching, `shopify_connector_sale`): `merged: true`,
  2026-07-10T11:56:01Z, merge commit `7e83abba…`. Runtime-green:
  `0 failed, 0 error(s) of 268 tests` (operator-provided Odoo.sh log,
  quoted in `../05-qa/task-011-customer-import-validation-results.md`
  §J). Task 011 gate closed/exhausted.
- **[Verified repository state]** PR #146 (MBQ-05 branch B decision
  package, AR-041): `merged: true`, 2026-07-10T13:15:20Z, merge commit
  `e97764b…`.
- **[Verified repository state]** PR #147 (DEC-026 acceptance/status
  patch): `merged: true`, 2026-07-10T17:08:08Z, merge commit `21d59ec…`
  (the current tip).
- **[Verified repository state]** DEC-026 is **accepted as strategic
  direction only**: DEC-023 branch A unchanged in its limited scope;
  Public distribution/Limited Visibility (B-1) is the target scalable
  branch-B architecture; B-3 per-customer custom apps not adopted as the
  standing commercial-scale answer; Phase 2+ under RA-003's revisit
  condition; **no public-app implementation authorized**. Five named
  prerequisites remain open: MBQ-04 posture DEC, OP-23/Q27, OP-46,
  an RA-003 deferral-lift act, OP-45.
- **[Verified repository state]** ID sequences: highest AR row in use is
  **AR-041** (next: AR-042 — used by this session's package); highest
  DEC is **DEC-026** (next: DEC-027); highest RA is RA-024; highest OP
  is OP-46. Verified by direct grep of the registers and the
  `docs/04-decisions/` listing; a repo-wide search for `AR-042` and
  `DEC-027` returned nothing prior to this session.
- **[Verified repository state]** Merged addon tree:
  `shopify_connector_core` (v19.0.1.5.0, depends `['base']`; 10 models
  incl. store/settings/credential/location/binding-mixin/job/job-log and
  4 AbstractModel services; 4 security groups; 1 ir.cron drain record;
  11 test files), `shopify_connector_product` (depends
  `['shopify_connector_core', 'product']`; template + variant binding
  models + read-only importer; 4 test files), `shopify_connector_sale`
  (depends `['shopify_connector_core']` **only**; customer binding +
  read-only importer + inert `customer_fallback_partner_id`; 4 test
  files). Zero views, zero webhooks, zero OAuth, zero Shopify-mutation
  code anywhere in the tree. No enqueue-trigger call site exists — the
  merged import domains are backend-only (OP-28).
- **[Verified repository state]** Tasks 012, 013, 014, 015 are **not
  authorized**; no order/inventory/fulfillment/export gate exists; the
  UI implementation gate has never been opened; no webhook, OAuth, App
  Store, billing, or Lite/Full implementation gate is open.
- **[Fact]** All 24 decision records DEC-003–DEC-026 carry an Accepted
  status (several at explicitly bounded levels: DEC-016 screen-design
  level; DEC-017 planning guidance; DEC-023 limited routing; DEC-025
  architecture gate; DEC-026 strategic direction). Zero
  proposed-not-accepted DECs existed at session start.

### 1.1 Stale text found during baseline reconciliation

| # | Stale text | Superseding fact | Handling |
| --- | --- | --- | --- |
| S-1 | AR-040 row Status cell: "Proposed for ChatGPT review", body "PR #145 remains draft, unmerged" | GitHub: PR #145 merged, runtime-green; `implementation-readiness-map.md` §4.2 records closure | **Fixed this session** — dated documentary status-refresh note appended in `../05-qa/architecture-review-log.md`; Status-cell wording call left to ChatGPT |
| S-2 | `task-011-final-implementation-prompt.md`, `task-011-decision-closure-brief.md`, `customer-domain-gate-criteria-proposal.md` per-criterion statuses: "NOT issued / gate closed / criteria not satisfied" | Task 011 cycle completed (PR #144 gate act → PR #145 merged) | Historical drafting-time records — left unedited (established convention); noted here so no future session re-executes them |
| S-3 | `task-012/013/014-*-proposed.md` preconditions text ("Depends on Task 010 and Task 011 … existing") | Tasks 010/011 merged and runtime-green | Superseded-in-fact for those preconditions; remaining genuine blockers restated in §2 and closed/routed by this session's packets |
| S-4 | `task-013-inventory-sync-proposed.md` "MBQ-33/34 … remain formally open per DEC-015" | DEC-018 decided both (per-mapped-pair granularity; review-then-apply default) — confirmed against the live register | Task 013 packet carries the register-verified DEC-018 state |
| S-5 | Master-blueprint files' six-value job-source lists and "MBQ-33/34/41/60–63 remain open" trailers | DEC-019 added `odoo_event` (7 values); DEC-018/019 decided 33/34/41/60/62 | Historical baselines with later dated addenda elsewhere — left unedited; final architecture doc (this session) states the current contract |
| S-6 | `sync-engine-open-questions.md` Q36 wording "fulfillment API model … remain undecided" | DEC-011 decided the write model (FulfillmentOrder-only); only the exact scope set is open (TD-002 clarification note, CL-2) | Already clarified by CL-2; Task 014 packet proposes the exact scope set |
| S-7 | `shopify-official-api-notes.md` Sprint-B baseline body (2026-06-30, `latest`=2026-04) | RB-14/Task-011 dated patches (latest=2026-07) supersede version-sensitive facts | Already flagged in-file; this session's fresh captures are dated 2026-07-10 |
| S-8 | UI/UX final-design-spec set (2026-07-06) still lists MBQ-05 walkthrough content as fully open | DEC-026 accepted B-1 strategic direction (2026-07-10) | Noted; wizard packet (this session) plans the branch-A token-paste step for MVP and marks OAuth as Phase 2+ |

No stale text was found that contradicts an accepted decision in
substance; every instance is a frozen snapshot superseded by a later
dated addendum, consistent with the repo's append-only convention.

## 2. Authoritative planning inventory and reconciliation table

Legend — "Session closure" column values:
**Closed-by-research** (official-source research this session closes the
gap at planning level), **Proposed-DEC** (closure drafted as a proposed
decision, requires ChatGPT acceptance), **Planned** (complete
implementation-ready planning produced this session; execution remains
gated), **External-live** (precisely-defined external/live validation —
not closable by any planning session), **External-legal** (blocked on an
external legal/commercial source), **Deferred** (explicitly out of MVP),
**ChatGPT-only** (a one-line governance/register call only ChatGPT can
make), **No-action** (tracked, nothing to do now).

### 2.1 Items on the Task 012–015 critical path

| Item | Current verified state | Source of truth | Blocks what | Session closure | Required action |
| --- | --- | --- | --- | --- | --- |
| OP-14 / MBQ-55 order portion | Order-binding naming pass never run; product/customer portions accepted (PR #136/#140 precedent) | MBQ register; both MBQ-55 passes | Task 012 | **Proposed-DEC** | Order-binding naming proposed in the Task 012 packet following the accepted naming precedent; ChatGPT accepts with the packet |
| OP-15 | Order-domain gate criteria nonexistent | OP register | Task 012 gate | **Planned** | 15-criteria proposal included in Task 012 packet (customer-gate template) |
| OP-16 / MBQ-56 | Total-check tolerance/comparison mechanism open; register says it blocks Task 012 | MBQ register; DEC-020 | Task 012 final prompt | **Proposed-DEC** | Exact tolerance mechanism + exact Shopify total field proposed in Task 012 packet (grounded in fresh Order-API captures + `res.currency` rounding facts) |
| OP-17 / MBQ-27 | Odoo-side representation of Shopify-computed tax open; "requires a dedicated ADR + ChatGPT decision" | MBQ register | Task 012 final prompt | **Proposed-DEC** | Evidence-backed mechanism proposal in the Task 012 packet, verified against Odoo 19 source |
| DEC-020 residual | Error-class/sub-reason for blocked divergent-currency order open | DEC-020 §5 | Task 012 final prompt | **Proposed-DEC** | Exact class mapping proposed in Task 012 packet |
| OP-18 | Inventory naming pass + gate criteria nonexistent | OP register | Task 013 | **Planned / Proposed-DEC** | Both included in Task 013 packet |
| OP-19 / MBQ-32 residual | Quantity-source selection open (`free_qty` vs `stock.quant.available_quantity`, verified non-equivalent) | MBQ register; DEC-015 C1 | Task 013 final prompt | **Proposed-DEC** | Source selection proposed in Task 013 packet with fresh Odoo 19 source verification |
| MBQ-38 residual | First-push confirmation-record schema open | MBQ register | Task 013 final prompt | **Proposed-DEC** | Exact record schema proposed in Task 013 packet |
| OP-20 | Fulfillment naming pass + criteria + exact scope set nonexistent; write model decided (DEC-011) | OP register; TD-002 CL-2 | Task 014; TD-002 fix routing | **Planned / Proposed-DEC** | All included in Task 014 packet, incl. exact `*_fulfillment_orders` scope set from fresh captures |
| OP-03 / TD-002 | `read_fulfillments` mis-scoped in `REQUIRED_MVP_SCOPES`; fix routing open | TD register | Customer-facing readiness claims; Task 014 | **Planned** | Fix routed as a named mandatory acceptance criterion inside the Task 014 packet (ChatGPT may alternatively split a tiny patch) |
| OP-21 | Task 015 unproposed (in MVP scope per DEC-003/PR #55) | OP register | MVP write-back half of product domain | **Planned / Proposed-DEC** | Full Task 015 packet produced (carries MBQ-23/MBQ-24 closures as proposals) |
| MBQ-23 / MBQ-24 | Variant-write mutation strategy partial; productSet delete-on-omit media residual open | MBQ register | Task 015 | **Proposed-DEC** | Both closed as proposals in Task 015 packet from fresh productSet/bulk-mutation captures |
| OP-33 / Q4 / Q26 | 16-vs-17 `@idempotent` mutation-count discrepancy | Sync-engine Qs | Any write-domain task hard-coding the list | **Closed-by-research** | Fresh count recorded in source captures; packets reference the current list, and each write task re-verifies at build time (standing rule preserved) |
| MBQ-58 / MBQ-12 | Order-identity / GID permanence accepted-open risks | MBQ register | Nothing (contained) | **No-action** | Defensive stale/review design already accepted |
| MBQ-30 | Gateway→journal mapping classification-only concept, partial | MBQ register | Nothing for 012 (evidence capture only) | **No-action** | Task 012 packet restates the classification-only boundary; config UI deferred to UI packet |

### 2.2 Cross-cutting architecture/product items

| Item | Current verified state | Source of truth | Blocks what | Session closure | Required action |
| --- | --- | --- | --- | --- | --- |
| OP-23 / Q6 / Q21 / Q27 | Lite/Full undefined ("no such concept exists anywhere in the corpus"); Q27 asks whether it maps onto domain-enablement flags or needs module sets/licensing | Sync-engine Qs; OP register | Packaging, pricing, install shape, release | **Proposed-DEC** | Complete Lite/Full packaging proposal (`../02-product/lite-full-packaging-final-proposal.md`) + proposed DEC-027 answer to Q27 |
| MBQ-04 / OP-40 / Q22 | Option B posture accepted (plain storage + ACL + masking + redaction); encryption-at-rest tension with PCD Level 2 named as public-app prerequisite; register upgrade call open | MBQ register; AR-022/024/025; DEC-026 acceptance note | Phase 2+ public app; hosting-neutral packaging claims | **Proposed-DEC** | Proposed DEC-028 credential/PCD posture ladder (MVP custom-distribution posture reaffirmed; Phase 2+ requirements defined; no Odoo field-encryption claim) |
| OP-45 | Partner Program fee schedule / Enforcement page never sourced | OP register §3.7 | Commercial model finalization (Phase 2+) | **Closed-by-research / External-legal residue** | Official billing/revenue-share + enforcement pages fetched and captured this session; anything not publicly documented is recorded as requiring legal/commercial confirmation |
| OP-46 | DEC-023 branch A "a single pilot customer" (singular) vs plural pilots unresolved | OP register §3.7 | Hybrid (B-4-style) posture operations | **Proposed-DEC** | Proposed decision with alternatives/consequences; recommendation: case-by-case ChatGPT approval with a small explicit cap; NOT marked accepted |
| Module map / dependency DAG | Hypothesis accepted at direction level (DEC-008); exact final module set incl. Lite/Full and Phase-2+ surfaces never consolidated | DEC-008; CHATGPT.md §1 | Task packets; packaging | **Planned** | `../03-architecture/final-mvp-module-and-dependency-architecture.md` produced this session |
| Q7 | Checkpoint/pagination ownership (core vs domain) undesigned | Sync-engine Qs | First multi-record enumeration task (Area 6) | **Proposed-DEC** | Ownership contract proposed in the architecture doc + Area 6 packet (domain-owned checkpoint fields on store settings, per Task 011 D7 precedent) |
| MBQ-51 | GraphQL cost/throttle pacing parameters open | MBQ register | Dashboard API-health card detail | **No-action / Planned** | Client already surfaces `throttleStatus` verbatim; pacing constants remain implementation-planning inside Area 6/UI packets; bucket sizes now captured from official docs |
| MBQ-16 / MBQ-18 | Retry/backoff + cadence constants = adjustable implementation-planning defaults | MBQ register | Nothing (defaults shipped in core) | **No-action** | Restated in packets; production tuning is a release-hardening item |
| MBQ-50 / Q42 | OCA `queue_job` accepted-open (reference only, RA-004) | MBQ register | Nothing | **No-action** | Revisit triggers unchanged |
| OP-37 | API version pinning policy accepted; store exercised at `2026-07` | OP register | Release readiness item | **Closed-by-research** | Currently-supported version list re-verified and captured; release plan carries the quarterly re-check |
| OP-42 | quality-feedback-loop §10/§11 binding status ambiguous | OP register | Governance clarity only | **ChatGPT-only** | One-line confirmation remains with ChatGPT (restated in signoff) |
| OP-43 | Task 010/011 test-count arithmetic unreconciled (green outcomes undisputed) | OP register | Nothing | **No-action** | Verbatim-quote rule already baked into prompts |
| OP-24 / OP-25 / OP-44 / OP-39 | Closed in prior sessions (docs-only), residue routed | OP register §3.6 | — | **No-action** | OP-25 residue (DEC-021/024/025 wording artifacts, QA-package headers) still needs its ChatGPT-authorized micro-patch — unchanged |
| OP-32 | Blocked competitor sources (VT Confluence, private Google Doc) | Resource inventory | Nothing (down-weighted) | **No-action** | Owner-granted access or permanent evidence downgrade — unchanged |
| OP-41 | Minor per-task residuals in their own records | OP register | Nothing | **No-action** | Surface naturally in future gated tasks |

### 2.3 Operator-surface, trigger, webhook, UAT, release items

| Item | Current verified state | Source of truth | Blocks what | Session closure | Required action |
| --- | --- | --- | --- | --- | --- |
| OP-28 / Area 6 | No enqueue-trigger call site exists; merged domains operator-invisible | OP register; addon tree | Operator-usable behavior; UAT | **Planned** | Complete Area 6 packet (service methods, crons, schedules, manual actions, permissions, duplicate-enqueue prevention, tests) with locked prompt |
| OP-26 / UI Groups 1–15 | Zero views exist; UI gate never opened; design accepted (DEC-016/AR-023) | OP register; addon tree | All interactive UAT; release | **Planned** | UI implementation plan with exact XML IDs (MBQ-03 closure proposal), grouping into implementation phases, locked prompts per phase |
| MBQ-03 / MBQ-22 / MBQ-44 residuals | XML IDs / copy / ACL rows open (descoped to task specs) | MBQ register | Each UI-bearing task | **Proposed-DEC (03, 44) / Planned (22)** | Exact XML ID scheme + per-domain ACL row plan proposed in UI packet; copy deck planned as a UI-phase deliverable with voice rules (full copy pass stays a UI-phase task) |
| OP-27 / MBQ-63 / MBQ-65 residuals / Q23 / OP-36 | Webhook posture accepted (layered, never webhook-only; enqueue-only); zero webhook code; PII redaction field list undefined | OP register; DEC-005/020 | Phase-2 webhook slices; public-app compliance | **Planned** | Complete webhook plan: per-domain subscription posture, HMAC/replay/dedup/ordering, compliance webhooks (Phase 2+), reconciliation backstop, PII redaction field list proposal, test strategy |
| OP-29 / UAT | 0/15 scenarios executable; 2 scenario gaps flagged (product manual-review path; ambiguous customer) | UAT gap analysis | Release | **Planned / External-live** | Final UAT catalogue (scenarios extended), prerequisites, evidence templates, entry/exit criteria; execution remains human/live |
| OP-30 / release checklist | Template ready, nothing executable | OP register | Release | **Planned / External-live** | Release-readiness plan produced (install/upgrade/uninstall/demo data/support diagnostics/app-review readiness/rollback/notes/limitations) |
| OP-06 / VAL-B2 | BLOCKED, never executed; closure plan accepted (DEC-023) and near-complete | val-b2-closure-plan.md | UAT; any "connected" claim; release | **External-live** | Plan audited against §8.5 dimensions; small addendum (result template, rollback/cleanup) added; classified as external live validation, not a research gap |
| OP-22 / SRR-03/04/09 / Q17/Q18/Q30/Q31/Q41/Q43 / Q24 | Nine-scenario concurrency plan merged (PR #134), never executed | concurrency validation plan | Release hardening; trust in claim/dispatch under real concurrency | **External-live** | Plan audited against §8.6 dimensions (perf metrics addendum added); classified as live/runtime validation |
| OP-34 / Q10–Q16 / Q40 | Live-Shopify behavioral unknowns (cursor durability, bulk-op semantics, bucket sizes, webhook duplicate window, THROTTLED body) | Sync-engine Qs | Nothing now (defensive designs) | **External-live / partially Closed-by-research** | Officially-documentable subset re-checked this session; empirical subset folded into VAL-B2 follow-up appendix |
| OP-35 | Live-Odoo runtime unknowns | Sync-engine Qs | Same as OP-22 | **External-live** | Same runtime sessions as OP-22 |
| OP-05 / MBQ-05 impl | Strategic direction accepted (B-1); implementation Phase 2+ gated; RA-003 not lifted | DEC-026 | Phase 2+ OAuth/wizard/App Store | **Deferred (Phase 2+)** | Named in roadmap tail; five prerequisites tracked; nothing implementable now |
| OP-31 | App Store packaging Phase 2+ (RA-003; DEC-026) | OP register | Nothing now | **Deferred (Phase 2+)** | Release plan carries an app-review-readiness section as Phase 2+ forward work |
| MBQ-61 | FULFILLMENT_ORDERS_* lifecycle family excluded from Phase 1 | MBQ register | Nothing (conservative exclusion) | **Deferred** | Restated in Task 014 packet exclusions |
| MBQ-53 full closure | Screen blueprint accepted; full closure needs MBQ-03/22/44 (+45/06 already decided) | MBQ register | UI implementation | **Proposed-DEC (partial)** | UI packet's XML-ID/ACL proposals + copy plan advance the siblings; MBQ-53 remains open until they are accepted and built |
| Q19 | `_notify_admin` override question | Sync-engine Qs | Nothing (job/log surface is the operator signal) | **Planned** | Observability section of UI/Area-6 packets confirms the documented assumption; no override in MVP |
| Q20 | Log copy/wording | Sync-engine Qs | UI copy pass | **Planned** | Routed into the UI copy deliverable |
| Q24 | Concurrency test harness choice | Sync-engine Qs | OP-22 execution | **External-live** | Stated in the concurrency plan (live scenarios, not TransactionCase) |

### 2.4 Completeness statement (Phase A)

Every open item named in: the OP register (OP-01–OP-46 incl. §3.6–§3.8
addenda), the MBQ register's non-resolved rows, sync-engine questions
Q1–Q43, SRR-01–SRR-09, TD-002, the UAT gap analysis, the release
checklist's must-pass list, the final pre-implementation roadmap steps
6–17 and parallel tracks P1–P5, and the five DEC-026 prerequisites is
present in §2.1–§2.3 (or was already closed with proof in its own source
record before this session — e.g. TD-001, OP-01/02/07–13 via the
completed Task 011 cycle, OP-24/OP-39/OP-44, MBQ rows resolved through
DEC-018/019/020/AR-019/AR-020). No MBQ, OP, Q, SRR, TD, UAT, release, or
roadmap item has been silently dropped. Items OP-01, OP-02, OP-04 and
OP-07–OP-13 are consumed/closed by the completed Task 011 lifecycle
(gate act PR #144, implementation PR #145) and are not restated as open.

## 3. Closure results (Phases B–D, 2026-07-10)

Per-row outcomes against §2's "Session closure" plan — every planned
closure was produced; none silently changed class:

| Item(s) | Outcome | Artifact |
| --- | --- | --- |
| OP-45 | **Closed-by-research** — the fee schedule is public (PPA Part C: 0% first $1M lifetime / 15% / $19 / 2.9%; 80/20 unregistered) and the Enforcement page is captured; residual legal unknowns named (review SLA; dashboard-only limits) | captures §6 |
| OP-46 | **Proposed-DEC** | DEC-027 |
| MBQ-04 / OP-40 / Q22 | **Proposed-DEC** — posture ladder on fresh evidence (encryption-at-rest = PCD **Level 1** requirement, superseding older Level-2 phrasing) | DEC-028; captures §7 |
| OP-23 / Q6 / Q21 / Q27 | **Proposed-DEC** — two-layer model | DEC-029 + packaging proposal |
| VAL-B2 | **External-live**, plan completed (result template, cleanup, escalation, piggyback checks) | val-b2-closure-plan §12 |
| OP-22 / SRR-03/04/09 / Q17/Q18/Q24/Q30/Q31/Q41/Q43 | **External-live**, plan audited + performance capture added | concurrency plan §13 |
| OP-14/15/16/17, MBQ-55-order, MBQ-56, MBQ-27, DEC-020 residual | **Proposed-DEC / Planned** — D-012-1..12 | Task 012 packet |
| OP-18/19, MBQ-32 residual, MBQ-38 | **Proposed-DEC / Planned** — D-013-1..8 | Task 013 packet |
| OP-20, OP-03/TD-002, MBQ-40/42/43 residuals | **Proposed-DEC / Planned** — D-014-1..8 (exact scope set: merchant_managed family; TD-002 fix routed as the one named core edit) | Task 014 packet |
| OP-21, MBQ-23/24/25 residuals | **Proposed-DEC / Planned** — D-015-1..8 | Task 015 packet |
| OP-28 | **Planned** — Area-6 split (Lite-trio retrofit; Full modules ship native triggers) | area-6 packet |
| OP-26, MBQ-03, MBQ-44 residual, MBQ-22 (plan) | **Planned / Proposed-DEC** — U1–U3 phases, XML-ID scheme, ACL plan, copy-deck process | ui packet |
| OP-27, Q23/OP-36, MBQ-65 residual | **Planned** — W1–W5; PII redaction list proposed | webhook packet |
| OP-29 / UAT gaps | **Planned / External-live** — 24-scenario catalogue + entry/exit | final-mvp-uat-plan |
| OP-30 | **Planned / External-live** | release-readiness-execution-plan |
| Q7, MBQ-51, OP-33/Q4/Q26, OP-37, Q19 | **Closed at proposal level / Closed-by-research** — PD-5 checkpoints; runtime-read throttle posture; fresh idempotent-list count (17 entries, inventory/location/refund only — the old 16-vs-17 discrepancy dissolved by the 2026-01/2026-04 changes); versions re-verified; `_notify_admin` assumption confirmed | ARCH §5/§6; captures §3/§9 |
| OP-05/OP-31 (Phase 2+), MBQ-61/63 exclusions, OP-24/25/32/38/39/41/42/43/44 | **Deferred / No-action / ChatGPT-only** — unchanged, restated where consumed | master plan §3/§4 |

New IDs created this session: DEC-027/028/029 (all Proposed); AR-042
(this package's row); no new OP/MBQ/RA/TD numbers (deferred items
013B/015B are task candidates, not register rows, until ChatGPT
chooses to number them).

## 4. Contradictions found and corrected

1. AR-040 status cell vs GitHub merge state — corrected via a dated
   documentary note (§1.1 S-1).
2. Older repo phrasing tying encryption obligations to PCD Level 2 vs
   the current official Level-1 placement — superseded by captures §7
   (DEC-028 evidence item 1); no historical file rewritten.
3. The blueprint's fulfillment-binding key sketch (FO GID) vs the
   backorder-independence rule — refined to Fulfillment-GID +
   (store,picking) anchoring, explicitly flagged (ARCH §3, D-014-1).
4. Task 013's "MBQ-33/34 remain formally open per DEC-015" vs the
   register's DEC-018 decisions — resolved in DEC-018's favor by
   direct register read (packet carries them as settled).
5. The 16-vs-17 `@idempotent` count discrepancy — dissolved: the
   current official list has 17 entries but a different composition
   than the old research assumed (inventory/location/refund;
   fulfillment never on it); packets no longer depend on the count.
6. Shopify's own docs carry two internal inconsistencies (stale
   `ignoreCompareQuantity` prose on the 2026-07 mutation page; stale
   one-bulk-op wording in the bulk page's Rate-limits section) —
   recorded in captures §3/§9 so no future session cites them.

## 5. Evidence-quality assessment

Strong (official, dated, adversarially re-verified 24/24 CONFIRMED,
plus raw-HTML spot checks on the four highest-stakes pages): all
API-shape, scope, versioning, PPA-fee, PCD, and webhook-mechanics
claims. Strong (source-level, 19.0 branch): all Odoo claims. Medium
(officially undocumented → converted to named empirical checks):
null-variant semantics, negative-available sets, customId upsert
behavior, list-not-supplied boundary, tip line items, webhook
duplicate-window, cursor durability. Known weak spots deliberately
avoided: WebFetch summarizer text was not trusted for load-bearing
quotes after the caught "30%" hallucination (captures header records
the methodology caution).

## 6. Readiness verdict

**Planning-complete per the session's §22 standard, as a proposal
package** — see `mvp-planning-completion-signoff.md` for the ten
answers and the exact statement. The repository now contains: the
reconciled state (§1), closure for every §2 item (§3), six proposed-
decision records/points sets (DEC-027/028/029 + PD-1..6 + the packet
D-items), seven implementation packets with locked prompts (012, 013,
014, 015, Area 6, UI-U1, W1), the UAT and release plans, and one
unambiguous next step (Task 012). Nothing herein is accepted, no gate
is open, and no external validation is claimed to have occurred.
