# MVP Planning-Completion Audit — Baseline Reconciliation, Full Planning Inventory, and Closure Results

> **Status: Proposed for ChatGPT review. NOT accepted. Docs-only.** This
> document is the master audit of the 2026-07-10 MVP planning-completion
> session (AR-042 candidate). It records (§1) the verified current
> repository/GitHub state, (§2) the authoritative inventory of every
> remaining planning item with a reconciliation verdict, and (§3–§7,
> appended by later phases of the same session) the closure results,
> contradictions found and corrected, evidence-quality assessment,
> the final readiness verdict, and the adversarial red-team review
> record. **Nothing in this document opens a gate,
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

> **SUPERSEDED 2026-07-11:** ChatGPT's control-room review (comment
> `4942966937`) found this verdict premature — eleven material gaps.
> The operative verdict is the revised signoff's planning-complete
> statement plus §8 below; the exact next step is **Task CORE-R1**,
> not Task 012. This section is preserved unedited below as the
> 2026-07-10 historical record.

**Planning-complete per the session's §22 standard, as a proposal
package** — see `mvp-planning-completion-signoff.md` for the ten
answers and the exact statement. The repository now contains: the
reconciled state (§1), closure for every §2 item (§3), three proposed
decision records (DEC-027/028/029), the six architecture proposed
decisions (PD-1..PD-6), the packet-level flagged D-items, seven
implementation packets with locked prompts (012, 013, 014, 015, Area
6, UI-U1, W1), the UAT and release plans, and one unambiguous next
step (Task 012). Nothing herein is accepted, no gate is open, and no
external validation is claimed to have occurred.

## 7. Adversarial red-team review record (session §21)

Five independent adversarial reviewers (governance/scope, architecture
vs merged code, engineering feasibility, packet cross-consistency,
evidence/citation integrity) reviewed the full Phase-A–D output
against the merged codebase and the registers. Findings and
dispositions (all fixes applied in this same session, before the PR
was opened; nothing was silently dropped):

### 7.1 Blocker-class findings — all fixed

1. **No store can reach `connected`.** The merged core registers three
   ESSENTIAL readiness placeholder checks (`webhook_hmac`,
   `mapped_location`, `cron_queue_health`) that return `not_proven`
   unconditionally; the aggregate is fail-closed and
   `action_activate` requires a pass/warning readiness result — so
   every mutation task's dev-store validation was unreachable, and
   `cron_queue_health` was owned by no packet at all. **Fix:** new
   Area-6 design item D-A6-7 (readiness pending-slot closure) owns
   all three slots, with the webhook_hmac relaxation explicitly
   flagged as its own ChatGPT call; sequencing note added (Area 6
   before any mutation task's dev-store validation); master plan §1
   item 9 and §2 row 2 updated.
2. **A normally-returning handler can never produce `skipped`.** The
   merged dispatcher overwrites a normal handler return to
   `succeeded`; Task 012's skip-by-policy design was unimplementable
   as written. **Fix:** D-012-3 re-specified on the `JobPolicySkip`
   dispatcher-exception seam (one named additive core edit, flagged);
   recovery path = manual retry from `skipped` (D-A6-5 updated to
   include `skipped` in its allowed-from set, with retry_count reset).
3. **Area-6 scan jobs collided on `operation_scope_key`.** The merged
   key excludes `job_type`, so two domains' scans for one store would
   serialize against each other (and the original design's key would
   never distinguish them). **Fix:** synthetic
   `shopify_target_gid='scan:<domain>'` marker + per-run
   `payload_hash` nonce; both now stated in the packet and its locked
   prompt.
4. **Undeclared `sale_stock` dependency.** Task 014's design consumes
   `picking.sale_id`/`sale_line_id`, which live in the `sale_stock`
   bridge module, absent from the declared dependency set. **Fix:**
   dependency added to the fulfillment module row, the DAG, and the
   Task-014 packet.
5. **Uninstall claims contradicted the merged FK posture.**
   `job_log.job_id` is `ondelete='restrict'`, so the documented
   cascade-uninstall story would fail at the database. **Fix:**
   architecture §8 and the packaging proposal rewritten to the
   disable-only/documented-loss posture actually supported.

### 7.2 Major findings — all fixed

Inventory-level binding needs `shopify_gid` `required=False` (an
explicit, documented mixin deviation — Task 013); the `@idempotent`
retry key must persist on the binding (`last_push_idempotency_key` +
params hash), not in `payload_hash` (Task 013); Task 015 omitted the
`write_products` scope and its readiness/hold classes; the readiness
`_get_checks()` append seam cannot *replace* a core check — Task 013's
mapped-location integration re-specified as an `_inherit` override on
the D-A6-7 baseline; FulfillmentOrder `status` is not a server-side
query filter — selection re-specified client-side over
OPEN/IN_PROGRESS; Task 014's pre-send dedup honesty (only
`operation_scope_key` serialization is proven; stated as such);
Area-6 §1 falsely claimed "no core edits" while its allowlist named
core files — rewritten to the three named additive pieces; Task 014's
`trigger_origin` value is an extension of the accepted DEC-019
vocabulary and is now flagged as a review call (master plan §1 item
7), as is Task 012's `sale.order.line` field (item 5).

### 7.3 Consistency/citation findings — all fixed

Ten-vs-eleven review-call count reconciled (eleven = ten binding + one
optional, stated in master plan §1 and signoff §9); DEC-029 §5/§6
citations in the release plan and UAT scenario 23 corrected to the
packaging proposal (the DEC-029 decision record has no such sections);
UAT scenario 16 moved Wave 1 → Wave 3 (needs the U3 matching center);
U-1's closure condition stated in the UAT plan header; signoff §3
citation corrected to master plan §1 items 6/8/10; §6 of this audit
recounted; webhook phase labeling aligned (W1/W2 "MVP tail"
everywhere; W1 row now names the D-A6-7 `webhook_hmac` slot
handover).

### 7.4 Open items surviving the red-team (by design, not oversight)

The external-validation set (signoff §6) — VAL-B2, concurrency proof,
dev-store empirical checks, UAT execution, webhook live delivery —
plus every ChatGPT review call in master plan §1. No red-team finding
remains unfixed and unrecorded.

## 8. PR #148 revision record (2026-07-11) — control-room review closure map + second adversarial pass

ChatGPT's control-room review (PR #148 comment `4942966937`) returned
**REVISE** with eleven blocking items. §8.1 maps each to its closing
artifact(s) in this same PR; a finding counts as closed at planning
level only where the repo now contains a complete decision or
implementation packet with exact sequence and acceptance criteria —
not merely a mention (the review's own bar, applied).

### 8.1 Review-item closure map

| # | Review item | Closing artifact(s) — all Proposed, NOT accepted |
| --- | --- | --- |
| 1 | Product-import completeness must precede order import | `task-010b-product-import-completeness-packet.md` (locked; D-010B-1..12; grounded in the verified merged-code limitations §8.3.1); master plan step 2; Task 012 prerequisites revised; **no DEC-003 narrowing proposed — scope completed** |
| 2 | Customer-matching scalability | `task-011b-customer-matching-scalability-packet.md` (locked; indexed normalized lookup, equivalence proof, 100k benchmark, migration/backfill, concurrency); master plan step 3, before 012 |
| 3 | 013B/015B silently deferred | `task-013b-initial-inventory-baseline-packet.md` + `task-015b-product-media-export-packet.md` (both complete locked packets, sequenced before UAT/release; D-013-8/D-015-7 rewritten from "deferral" to "split") |
| 4 | Premium UI/UX | `premium-ui-ux-design-system.md` (PD-7; tokens/scales/icons/motion/reduced-motion/responsive/RTL/states/accessibility/budgets/checklists/screenshot rules; §9 dashboard hierarchy replacing nine-equal-cards — flagged revision of accepted content); UI packet rewritten (U0 prototype gate blocking U1; selective Owl, no SPA; tours+HOOT mandatory; SEC-1 prerequisite); the two referenced design docs verified to EXIST at `docs/02-product/ui-ux-final-design-spec.md` and `docs/02-product/screen-inventory-and-navigation-map.md` (the review's "no such files" premise was checked and is factually incorrect — references are now exact relative paths so no future search can miss them) |
| 5 | Split the readiness correction | `task-core-r1-readiness-correction-packet.md` (D-R1-1..4; capability-aware; drain-cron+stall health; Lite-reaches-`connected` regression); Area-6 packet revised (D-A6-7 superseded marker; prompt no longer touches the readiness file); master plan step 1 |
| 6 | Order-import corrections | Task 012 packet revised in place: D-012-7 (sale_stock auto-install fact — captures-11 §1; no-retroactive-pickings withdrawn; no-default operator confirmation policy with hold), D-012-9 (mapping-model-first taxes; `order_tax_autocreate` default False, admin-gated + audited), D-012-2 (component-based tolerance, currency-relative 10×rounding cap, JPY/BHD test rows + named three-decimal dev-store check), D-012-11 warehouse wording; packaging proposal §2 Lite definition revised |
| 7 | Security hardening missing | `task-sec1-security-hardening-packet.md` (D-SEC1-1..7: transition matrix binding even sudo; su-guarded protected fields; sanctioned doors incl. resolve; audited binding override; PII field-groups + masking; retention/deletion/export; negative RPC matrix) — sequenced after Area 6, before U1 |
| 8 | DEC-028 Rung 1 too weak | DEC-028 revised: point 2 is now five named **production-entry criteria** with per-deployment recorded evidence, reviewed at Go/No-Go (encryption at rest; backup encryption or documented equivalent; access restrictions; retention/deletion; incident/access governance); no field-encryption invention, no certification claim; release plan §2.8 carries the rows |
| 9 | Uninstall contradiction + lifecycle | `module-lifecycle-uninstall-design.md` (options A–E, recommendation, data-survival matrix, LC-1 task spec) + DEC-030 + PD-8; release plan §2.3 corrected (its cascade text was the false side); packaging §5/§6 and ARCH §8 revised to cite the matrix |
| 10 | Performance budgets undefined | `performance-budgets.md` (PB-1..23 + pagination/virtualization rules; recalibration protocol; honesty note on the merged drain constants); ARCH §5.11 deferral withdrawn; release plan §2.7 requires the measured table |
| 11 | UAT undervalues UX failures | UAT plan revised: S2-UX release-blocking class (health-status honesty, inaccessible actions, unusable recovery, responsive breakage, >2× budget miss, keyboard/contrast failures, misleading destructive preview); cosmetic copy stays S4; scenarios 25–36 added with pass/fail criteria; §7 numeric measurement |

Master-plan/global corrections: critical path re-sequenced (CORE-R1
→ 010B → 011B → 012 → Area 6 → SEC-1 → U0∥ → U1 → domains+B-tasks →
W1/W2 → UAT → release); signoff §10 next-task = CORE-R1; every
"planning complete" statement re-qualified (signoff, this §8,
handoff); new review calls enumerated (master plan §1 B1–B10).

### 8.2 New/changed identifiers this revision

New packets: CORE-R1, 010B, 011B, 013B, 015B, SEC-1, LC-1 (spec in
the lifecycle doc §7). New decision records: DEC-030. New ARCH
proposed decisions: PD-7/PD-8/PD-9. New captures file:
`odoo19-shopify-official-captures-2026-07-11.md`. New deferred names:
010C, 015C, dark mode. New UAT scenarios: 25–36; new severity class
S2-UX. No new RA rows (checked against the rejected-approaches log —
no rejected approach reintroduced; RA-006/008/014/018/020/021
explicitly honored in the new packets). No code changed.

### 8.3 Second adversarial pass (fresh red-team, 2026-07-11) — method

The fresh pass required by the review ran against: (1) the actual
merged Task 010 limitations (line-cited code inspection **before**
drafting — §8.1 row 1); (2) actual merged Task 011 performance
behavior (same method — §8.1 row 2); (3) accepted DEC-003 scope
(completed, not narrowed); (4) official Odoo 19 auto-install/
dependency behavior (captures-11 §1); (5) the premium UI/UX
objective; (6) accessibility/performance; (7) cross-document
uninstall/downgrade consistency; (8) security/RPC mutation
boundaries; (9) every "planning complete" statement; (10) every
locked prompt's dependency chain. Executed as: two pre-drafting
code-inspection passes, an in-session grep/consistency sweep (stale
D-A6-7 ownership, nine-card assertions, Lite/sale_stock inference,
fixed-cap tolerance, autocreate default, planning-complete
qualifications, cross-file link existence), a strict
review-item-completeness audit over all eleven workstreams, and an
adversarial merged-code-fidelity pass over the CORE-R1/010B/011B/
SEC-1 packets. Nothing is reported as fixed merely because it was
documented — §8.4 lists what the pass itself found wrong in the
revision and how each finding was fixed in this same session.

### 8.4 Second-pass findings and dispositions (all fixed in-session before push-final)

**Blocker-class (3):**
1. **SEC-1 missed a protected-field writer:** the merged
   `shopify_connector_store.py` writes job `state`/`error_class`/
   timestamps without sudo (test-connection mirrors, lifecycle audit
   jobs, disconnect sweep — lines 108–205/233–248/351–364); under
   D-SEC1-2 as first drafted, Test Connection/Activate/Disconnect/
   Reconnect would raise. → Store file added to the §5 allowlist with
   each elevation itemized.
2. **SEC-1's transition matrix outlawed merged behavior:** the
   dispatcher routes gate-blocked starts
   `draft|queued|retry_waiting→failed_retryable`
   (`job_dispatch.py` 186–200; green tests at
   `test_job_dispatch.py` 238–286). → Blocked-start edges added to
   D-SEC1-1 explicitly.
3. **CORE-R1 was insufficient for its own regression:** a FOURTH
   never-passable ESSENTIAL check exists — `api_version_health`
   passes only on `api_health_state=='normal'`, and no merged path
   ever writes `'normal'` (only `'degraded'` on fall-forward;
   no default). → New D-R1-5: one named store-file write site
   (`'normal'` on full non-fallforward test-connection success),
   flagged, with a named rejected alternative; D-R1-4 regression
   re-specified as real-behavior-only (no fixture force-writes).

**Major (3):**
4. SEC-1 create-vs-write guard inconsistency (forgery channel open at
   `create()`; operator holds create on jobs and bindings) →
   D-SEC1-2 now applies at `create()` with the named su-elevated
   creation doors and the ACL-matrix test updates called out.
5. CORE-R1's "never attempted" lacked a discriminator (`retry_count`
   counts scheduled retries, not attempts) → fixed to
   `state='queued' AND NOT started_at`, with the Area-6 re-queue
   boundary stated honestly.
6. CORE-R1's cron-record read requires an unstated `ir.cron` sudo
   (connector groups hold no ir.cron ACL) → named, flagged read-only
   sudo elevation added to D-R1-1 and the release-plan §2.8
   inventory.

**Minor (5), all fixed:** missing `tests/__init__.py` lines in five
packets' allowlists; 011B's source guard was string-literal (defeated
by multi-line formatting) and its file scope forbade updating the
stale full-scan docstrings → AST/domain-pattern guard + docstring
scope; SEC-1 §1 misattributed the domain-flag gate to business
sources only (it runs for every job) → corrected; the SEC-1
customer-importer allowlist wording omitted its binding-create sites
→ "snapshot/binding-write"; D-SEC1-6's core sweep had no
dependency-safe way to see sale-module PII fields → mixin-level
`_pii_snapshot_fields()` declaration seam.

**Also found by the completeness audit:** the lifecycle options table
mapped two of the review's six named candidates into one option
without saying so → explicit mapping note + a genuine sixth option
(F: core-registered job types, rejected on the DEC-008/RA-013
boundary). **Also found by the fidelity spot-checks:** Task 010B
cited a nonexistent error class (`shopify_temporary_unavailable` →
the merged `shopify_temporary_server_network`) and an unverified
`price_source_of_truth` value set (now the exact merged selection);
Task 013/015 gate criteria lacked the new 010B prerequisite; the §6
verdict above lacked its superseded marker. **Factual note recorded
for ChatGPT:** the review's item-4 premise that
`ui-ux-final-design-spec.md` and `screen-inventory-and-navigation-map.md`
do not exist is incorrect — both are present at
`docs/02-product/…` (verified against the base branch tree); every
reference is now an exact relative path so no search can miss them.

**Open items surviving the second pass (by design):** the external
validations (signoff §6), every ChatGPT call in master plan §1
(A1–A11, B1–B10), the base-module `ir.cron` ACL re-verification at
the CORE-R1 gate, and the named build-time verifications inside
packets (dynamic-variant API, quant-adjustment API, staged-upload
shape). No second-pass finding remains unfixed or unrecorded.
