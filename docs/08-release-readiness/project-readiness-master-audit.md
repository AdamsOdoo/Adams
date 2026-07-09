# Project Readiness Master Audit — Post-PR #140 Pre-Implementation Checkpoint

> **Status: [Recommendation] per `CLAUDE.md` §8. Docs-only. Audit/planning
> only. Does not authorize implementation of any kind, does not open any
> gate, does not merge anything.** Prepared 2026-07-09, after PR #140 (Task
> 011 customer import readiness and binding schema proposal) **merged** into
> `Shopify-connector` (merge commit `0e138d9ad8e14a9d0766122f30beea2e19df549a`,
> merged 2026-07-09T19:00:34Z — verified via GitHub `pull_request_read`,
> `merged: true`, base `Shopify-connector`). This audit consolidates
> already-recorded facts, decisions, and open items from the cited files and
> from direct read-only inspection of the merged addon code — it does not
> itself resolve, narrow, or decide any of them, and it does not reopen or
> reinterpret any accepted decision. Every claim below is a **[Fact]**
> (cited, verifiable in this repository or against the named official
> source), a restated **[Decision]** / **[Open question]** (cited from its
> own record), or this document's own **[Recommendation]** / **[Inference]**,
> labelled per `CLAUDE.md` §8. Subject to ChatGPT review, revision, or
> rejection in whole or in part.
>
> Companion documents produced by the same session:
> [`open-points-closure-register.md`](./open-points-closure-register.md)
> (the complete open-point register with per-item classification),
> [`implementation-readiness-map.md`](./implementation-readiness-map.md)
> (per-task/per-gate readiness map),
> [`final-pre-implementation-roadmap.md`](./final-pre-implementation-roadmap.md)
> (the sequenced roadmap to and beyond implementation resumption), and
> [`uat-readiness-gap-analysis.md`](./uat-readiness-gap-analysis.md)
> (UAT scenario-by-scenario gap analysis).

## 1. Audit scope and method

- **Repo evidence:** direct reads of `CLAUDE.md`, the full
  `docs/01-research/research-handoff.md` timeline, all of
  `docs/04-decisions/`, `docs/05-qa/architecture-review-log.md` (all 37
  rows), the QA registers (`technical-debt-register.md`,
  `rejected-approaches-log.md`, `sync-engine-open-questions.md`,
  `sync-engine-risk-register.md`, `val-b2-closure-plan.md`), the
  implementation-plan corpus (`docs/07-implementation-plan/`), the
  product/release corpus (`docs/02-product/`, `docs/08-release-readiness/`),
  the master-blueprint register
  (`docs/03-architecture/master-blueprint-open-questions.md`), and
  read-only inspection of `addons/shopify_connector_core/` and
  `addons/shopify_connector_product/`.
- **Git evidence:** `git log --first-parent origin/Shopify-connector`
  (PR #88 → PR #140 merge line), individual merge commits, and GitHub
  `pull_request_read` for PR #140.
- **Official-source evidence (all fetched 2026-07-09, Accessible):**
  Shopify protected-customer-data, `Customer` object, `MailingAddress`
  object, API versioning, and access-scopes pages; Odoo 19 `res_partner.py`
  and `sale/models/sale_order.py` from the official `odoo/odoo` 19.0
  branch. Exact URLs in §9.
- **High-power mode:** this session was explicitly authorized as a
  high-power audit. Parallel read-only reader agents swept the doc
  subsystems, addon code, and PR history; every load-bearing claim was
  additionally verified first-hand by the coordinating session before being
  asserted here. No file outside this session's allowed-files list was
  modified.

## 2. Verified project state (Facts)

### 2.1 Branch/PR state

- **[Fact]** `Shopify-connector` HEAD is
  `0e138d9ad8e14a9d0766122f30beea2e19df549a` = the PR #140 merge commit.
  PR #140 is `merged: true`, merged 2026-07-09T19:00:34Z, base
  `Shopify-connector`, head `claude/task-011-customer-readiness-5xunqw`
  (GitHub `pull_request_read`, 2026-07-09).
- **[Fact]** The branch's first-parent merge line runs PR #88 (Task 001
  core scaffold, 2026-07-05) through PR #140 (2026-07-09) with no direct
  non-PR commits observed on the first-parent line other than PR-merge
  commits and squash-merge commits carrying their PR number (`git log
  --first-parent`, run 2026-07-09). PR #112 does not appear on the branch
  (never merged into it).
- **[Fact]** `main` is untouched by this session; no plain `dev` branch ref
  exists on the remote clone used by this session (`git branch -a`).

### 2.2 Merged implementation (code that exists today)

- **[Fact]** `addons/shopify_connector_core` (manifest version
  `19.0.1.5.0`, depends `['base']`, data: security XML + ACL CSV + cron
  XML, **no views/UI of any kind**) contains: store, store-settings,
  location, binding-mixin, job, job-log models; credential model +
  masking/redaction (`tools/redaction.py`); read-only GraphQL API client +
  test-connection service; readiness-check substrate
  (`REQUIRED_MVP_SCOPES = read_products, read_customers, read_orders,
  read_inventory, read_locations, read_fulfillments` —
  `shopify_connector_readiness_check.py:53-60`); connection lifecycle
  actions; and the Task 006C sync-engine skeleton
  (enqueue/claim/dispatch/retry, cron drain). Job state machine: `draft,
  queued, running, succeeded, failed_retryable, failed_final,
  blocked_manual_review, skipped, cancelled` with terminal set
  `('succeeded','failed_final','skipped','cancelled')` and a constraint
  requiring `manual_review_subreason` exactly when state is
  `blocked_manual_review` (`shopify_connector_job.py`).
- **[Fact]** `addons/shopify_connector_product` (manifest version
  `19.0.1.0.0`, depends `['shopify_connector_core', 'product']`, data: ACL
  CSV only) contains the Task 010 product-template/product-variant binding
  models and the read-only `shopify.connector.product.importer` service
  with the accepted match-key priority (existing binding → SKU → barcode →
  manual review) and the MBQ-59 two-tier no-blind-create policy, registered
  through three narrow extension seams with **zero edits to
  `shopify_connector_core`** (manifest description; PR #138).
- **[Fact]** Post-merge Odoo.sh runtime evidence (user-provided, recorded
  in `../05-qa/task-010-product-import-validation-results.md` §K):
  `shopify_connector_core` 187 tests + `shopify_connector_product` 61
  tests = **0 failed, 0 error(s) of 220 tests**, database
  `adamsmen-shopify-connector-34704468`, 2026-07-09.
- **[Fact]** No `shopify_connector_sale`, inventory, or fulfillment module
  exists; no webhook controller, OAuth file, setup wizard, view, menu, or
  action exists anywhere in the addon tree (directory listing, 2026-07-09).
  This matches the gate record: Tasks 011–015, UI, OAuth, webhooks, and
  packaging are all unimplemented and unauthorized.

### 2.3 Decisions and reviews

- **[Fact]** Every numbered decision record DEC-003 through DEC-025 is
  **Accepted** by ChatGPT (several at explicitly limited levels: DEC-016
  screen-design-blueprint level; DEC-017 planning-guidance level;
  DEC-019/DEC-020 decision/posture level; DEC-022 gate-opening level;
  DEC-023 limited routing only; DEC-024 closure record). No DEC remains in
  Proposed status (per-file `Status` sections, verified 2026-07-09).
- **[Fact]** All 37 real architecture-review rows (AR-001 – AR-037) end in
  **Accepted** status. AR-036 (Task 010 implementation) and AR-037 (Task
  011 readiness package) each passed recorded REVISE cycles before
  acceptance (AR-036: comments `4927037139`/`4927278355`/`4927455927`,
  accepted post-merge with the 0/220 runtime evidence; AR-037: REVISE
  comment `4928244425`, accepted comment `4928377625`). No AR row is left
  dangling in Proposed/REVISE.
- **[Fact]** The rejected-approaches log carries 24 binding final
  rejections (RA-001 – RA-024), each with a revisit condition. No new
  rejection was warranted or added by this audit (checked 2026-07-09).
- **[Fact]** Technical debt register: TD-001 **Resolved** (PR #115,
  2026-07-08, regression-tested live); TD-002 (`read_fulfillments`
  scope-naming) **Open** — see the clarification note added this session
  (`../05-qa/technical-debt-register.md`, TD-002 row) and
  [`open-points-closure-register.md`](./open-points-closure-register.md)
  OP-03.

### 2.4 Gate state (all implementation gates closed)

- **[Fact]** Every implementation gate ever opened (Tasks 001, 002, 003,
  004, 005, 006C, 010) was scoped to exactly one implementation session and
  is now **exhausted/closed** by its own merged PR (per each gate document
  and the AR log). The product-domain gate closed when PR #138 opened as
  draft and remains closed post-merge
  (`../07-implementation-plan/product-domain-gate-criteria-proposal.md`
  §7–§8).
- **[Fact]** The **customer-domain gate has never been opened.** Its
  15-criterion list is **Accepted as criteria only** (comment `4928377625`);
  7 of 15 criteria are satisfied (1, 2, 6, 7, 8, 10, 11) and 8 are not
  (3, 4, 5, 9, 12, 13, 14, 15)
  (`../07-implementation-plan/customer-domain-gate-criteria-proposal.md`
  §3/§5).
- **[Fact]** No order-domain, inventory-domain, or fulfillment-domain gate
  criteria have ever been proposed; the UI implementation gate has never
  been opened; no OAuth/webhook/packaging gate exists.

## 3. Status corrections identified (docs-only, evidence-backed)

These are stale statuses found by this audit. Items marked **(patched this
session)** are corrected in files on this session's allowed list; the rest
are routed in [`open-points-closure-register.md`](./open-points-closure-register.md).

1. **PR #140 merge not yet recorded in-tree** — AR-037's row and the top
   handoff entry still read "PR #140 remains draft, unmerged," which was
   accurate when written but is now stale (merge commit `0e138d9`).
   **(patched this session:** AR-037 merge-record note in
   `../05-qa/architecture-review-log.md`; new top handoff entry.)
2. **MBQ register rows stale** — `master-blueprint-open-questions.md`
   (last edited by the DEC-023 patch, 2026-07-08, per `git log`): the
   MBQ-55 row does not record the product-portion (PR #136 / AR-034) or
   customer-portion (PR #140 / AR-037) acceptances, and the MBQ-04 row
   still awaits Task 002 "implemented and reviewed" though PR #97 merged.
   The register understates progress on both rows. **(routed:** the
   register is not on this session's allowed-files list — see OP-24.)
3. **`docs/04-decisions/README.md` index stale** — narrates only DEC-003 –
   DEC-017; DEC-018 – DEC-025 are absent. **(routed:** OP-25.)
4. **`docs/02-product/README.md`, `docs/07-implementation-plan/README.md`,
   and `docs/08-release-readiness/README.md` all still say "Current
   status: Empty"** while those directories hold the accepted product
   baseline, the project's gate corpus, and the UAT/release documents
   (since PR #95). The 2026-07-07-era status headers of the MVP
   QA/test-strategy package lag the same way, and
   `quality-feedback-loop.md` §10/§11's binding status is textually
   ambiguous. **(routed:** OP-25, OP-42.)
5. **Release checklist / UAT scenarios freshness notes end at the
   2026-07-07 (Task-002-era) revision** — they predate Tasks 002/003/004/
   005/006C/010 all merging. Their per-item planning content remains valid;
   only their "state of the world" preambles lag.
   **(partially addressed this session:** the current state-of-the-world
   mapping is provided by
   [`uat-readiness-gap-analysis.md`](./uat-readiness-gap-analysis.md)
   without editing the historical documents; a wording refresh of those two
   files is routed as OP-25.)
6. **TD-002 dependency wording imprecise** — TD-002 says the fix "depends
   on which fulfillment API model … the connector ultimately adopts …
   which is not yet decided," but DEC-011 (Accepted 2026-07-02) already
   fixed the write-side model: FulfillmentOrder-based mutations
   exclusively, legacy flow never used (RA-022). What actually remains
   open is the **exact fulfillment scope set** (the
   assigned/merchant-managed/third-party `*_fulfillment_orders` scope
   family vs `read_fulfillments`, which governs only `FulfillmentService`
   per the official access-scopes page, re-verified 2026-07-09).
   **(patched this session:** clarification note on the TD-002 row —
   status remains **Open**; no code change proposed or authorized.)
7. **`sync-engine-open-questions.md` contains questions later answered by
   merged work** — e.g. Q5/Q29 (job-claiming design — answered by the
   merged Task 006C `try_lock_for_update()` claim/dispatch mechanism,
   AR-031 Decision A/AR-032), Q28 (next-task selection — answered by
   DEC-025/AR-030 → Task 006C → Task 010 history), Q37's product-domain
   instance (thresholds fixed by Task 010's accepted final prompt; the
   customer-domain instance remains open for Task 011).
   **(patched this session:** a dated status-refresh revision note appended
   to that file; question numbering and historical text preserved.)

## 4. What this audit confirms is genuinely open

The complete register with per-item classification, evidence, impact,
owner, and next action is
[`open-points-closure-register.md`](./open-points-closure-register.md).
Summary of the highest-order items (all restated, none resolved here):

| Item | Class | Blocks |
| --- | --- | --- |
| Customer-domain gate-opening act (criteria accepted; gate closed) | Requires ChatGPT decision | Task 011 |
| Task 011 final implementation prompt (8 unsatisfied criteria are all final-prompt-resolvable) | Requires ChatGPT decision + a drafting session | Task 011 |
| MBQ-55 order-binding portion (naming pass never run) | Requires future docs-only naming pass + ChatGPT acceptance | Task 012 |
| Order-domain gate criteria (never proposed); MBQ-56 tolerance; MBQ-27 tax mechanism | Requires future docs-only pass + ChatGPT decisions | Task 012 |
| Inventory-domain gate criteria (never proposed); MBQ-32 quantity-source residual | Requires future docs-only pass + ChatGPT decisions | Task 013 |
| Fulfillment-domain gate criteria (never proposed); exact fulfillment scope set; TD-002 fix routing | Requires future docs-only pass + ChatGPT decisions | Task 014 |
| Task 015 (product export/update) planning | Deferred until sequenced | Task 015 |
| MBQ-05 branch B (scalable many-unrelated-customer distribution/auth) | Requires ChatGPT-authorized research/decision task (docs-only, available now) | Setup wizard / OAuth / commercial distribution / release |
| VAL-B2 (no live Shopify connection ever made) | Requires live access (human operator with Partner/Dev Dashboard) | UAT, release, any live "connected" claim |
| SRR-03/04/09 concurrency proofs (plan merged via PR #134, never executed) | Requires live Odoo.sh/multi-server runtime | Release hardening (not Task 011) |
| TD-002 scope-set correction (code fix) | Requires future implementation (fulfillment task or its own gated patch) | Customer-facing readiness claims, release |
| Lite/Full packaging (Blocking Question 6/Q21/Q27) | Requires ChatGPT clarification + dedicated planning task | Packaging/release posture (not backend tasks) |
| UI/setup-wizard/webhook/OAuth implementation | Requires their own future gates | UAT, release |
| Blocked research sources (Teqstars docs 403; VentorTech Confluence children; project Google Doc) | Requires owner/human access | Nothing MVP-blocking; tracked |

## 5. Answers to the audit's required questions

1. **Is the project ready to resume implementation after this PR is
   reviewed and merged?** **[Recommendation] Yes — for exactly one next
   implementation task (Task 011), via the established two-step pattern.**
   The foundation (core substrate + product domain) is merged and
   runtime-green; every decision record and AR row is accepted; the
   customer-binding naming and gate criteria are accepted. What stands
   between now and Task 011 code is entirely decision/drafting work: a
   final-prompt + gate-opening-proposal session, then ChatGPT's explicit
   gate-opening act. No research blocker was found for Task 011's narrow
   backend scope.
2. **Exact next gate/planning step:** a single docs-only session that
   drafts (a) Task 011's file-exact final implementation prompt (marked
   DO NOT USE until ChatGPT issues it) and (b) the customer-domain
   gate-opening proposal — the exact analogue of PR #137 for Task 010.
   See [`../07-implementation-plan/next-gate-readiness-roadmap.md`](../07-implementation-plan/next-gate-readiness-roadmap.md).
3. **Is Task 011 ready for that session?** **Yes.** All 8 unsatisfied
   criteria (3, 4, 5, 9, 12, 13, 14, 15) are of the kind that only a final
   prompt (plus the point-in-time criterion-12 reconfirmation) can satisfy
   — none requires new research, new code, or live access. Decision inputs
   for the two open scope questions (address handling; company/person
   classification) are assembled, with official citations, in
   [`open-points-closure-register.md`](./open-points-closure-register.md)
   OP-07/OP-08.
4. **Which Task 011 criteria remain unsatisfied?** 3 (file-exact names in
   a final prompt), 4 (allowed/forbidden files), 5 (dedup/match-confidence
   thresholds fixed or explicitly scoped in-task), 9 (exact test files
   confirmed), 12 (point-in-time blocker-classification reconfirmation),
   13 (fallback-partner field exact type/default/creation mechanics +
   boundary restated), 14 (address handling + `is_company` explicitly
   scoped), 15 (ambiguous-match handling incl. exact job/log
   candidate-detail field names).
5. **What must the final prompt decide?** The eight-item decision list in
   [`../07-implementation-plan/next-gate-readiness-roadmap.md`](../07-implementation-plan/next-gate-readiness-roadmap.md) §4.
6. **Should MBQ-05 branch B run now or after Task 011?**
   **[Recommendation] Now, in parallel.** It is docs-only, non-competing
   with Task 011's backend scope (Task 011 consumes an existing store
   connection and performs no OAuth), and it sits on the critical path of
   the setup wizard, OAuth, packaging, and any commercial-distribution
   claim. One additional evidence-backed reason found this audit: if
   branch B lands on Public distribution, Shopify's protected-customer-data
   **Level 2** requirements (formal review; encryption/retention/incident
   obligations for name/address/email/phone fields) become app-review
   obligations that touch customer/order data handling — cheaper to know
   before Tasks 011/012 implementations harden than after (official PCD
   page, fetched 2026-07-09; consistent with RA-003's revisit condition —
   this recommends *evaluating*, not adopting, public distribution,
   exactly as DEC-023 §3.2 branch B already frames it).
7. **Before Task 012 can be planned:** Task 011 merged and closed; the
   MBQ-55 order-binding naming pass; an order-domain gate-criteria
   proposal; decision inputs for MBQ-56 (total-check tolerance) and MBQ-27
   (tax representation); and the order-domain answers to the same
   binding-model ambiguity check the customer pass just went through
   (an order-binding model with required `sale_order_id` must not
   represent an unresolved match as a row — the twice-confirmed lesson,
   handoff 2026-07-09).
8. **Before Tasks 013/014 can be planned:** their own naming passes +
   gate-criteria proposals; for 013, the MBQ-32 quantity-source residual
   decision; for 014, the exact fulfillment scope set (which also routes
   the TD-002 fix) — the write-side model is already decided (DEC-011).
9. **Before Lite/Full packaging can be decided:** ChatGPT must first answer
   the framing question already on record (`sync-engine-open-questions.md`
   Q27): is "Lite/Full" the existing per-store domain-enablement mechanism,
   or separate installable module sets/licensing? Then a dedicated
   packaging planning task (interacting with MBQ-05 branch B's
   distribution outcome). Not a blocker for any backend domain task.
10. **Before UAT:** see
    [`uat-readiness-gap-analysis.md`](./uat-readiness-gap-analysis.md) —
    in one line: Tasks 011–014 implemented, an operator-facing trigger/UI
    layer (currently zero views exist), VAL-B2 passed with a live store,
    and a live Odoo runtime for interactive execution.
11. **Before release readiness:** all of §4's release-blocking rows closed
    (VAL-B2, TD-002 fix, concurrency proofs, UI layer, UAT pass,
    MBQ-05 branch B decision, packaging posture), then the existing
    `mvp-release-readiness-checklist.md` executed item-by-item with
    evidence.
12. **What should ChatGPT review next?** This audit PR (docs-only), then
    issue the Task 011 final-prompt/gate-opening-proposal session using the
    next-session prompt in the handoff.

## 6. Architecture validation (Loop E summary)

- **[Fact/Inference]** Modular boundaries hold as accepted: two modules
  merged, strict one-directional dependency (`product` → `core`), zero
  core edits from the domain module, no one-giant-module drift (RA-011
  respected). The accepted future family
  (core/product/sale/inventory/fulfillment, DEC-008) remains intact in all
  planning documents.
- **[Fact]** Binding strategy, duplicate prevention, manual-review posture,
  retry/backoff/dead-letter, redaction, readiness checks, and idempotency
  exist in merged code exactly as the accepted decisions describe them
  (spot-verified against `shopify_connector_job.py`,
  `shopify_connector_binding_mixin.py`,
  `shopify_connector_readiness_check.py`; independently confirmed by the
  code-inventory reader).
- **[Inference]** The core substrate is sufficient for the next domain
  task (Task 011): the job framework, binding mixin, store-settings home
  for the fallback-partner field, and `read_customers` (already in
  `REQUIRED_MVP_SCOPES`) are all in place; Task 011 needs no core edit per
  its accepted naming proposal.
- **[Open question, restated]** Operator visibility remains backend-only:
  job/log records exist but no view/menu/dashboard exists. This is by
  design (UI gate closed) but is the single largest gap between "domain
  merged" and "domain UAT-able" — restated in the UAT gap analysis.
- **[Open question, restated]** Concurrency behavior under multi-worker /
  multi-server topologies is proven only at `TransactionCase` level;
  SRR-03/04/09 and the merged-but-unexecuted concurrency validation plan
  (PR #134) remain the standing runtime-proof debt.

## 7. Self-review / red-team record (Loop H)

Checks run against this audit package before commit:

- **Gate-status overclaim check:** every gate stated closed above was
  verified against its own gate document; no document produced this
  session states or implies any gate is open, opening, or openable without
  a distinct ChatGPT act. The words "authorize," "gate opened," and
  "implementation may proceed" appear only inside negations or future
  ChatGPT-act descriptions.
- **Merged/accepted/proposed confusion check:** PR #140's merge is asserted
  only from GitHub API + git evidence; acceptance comment IDs
  (`4928244425`, `4928377625`) are quoted from the in-repo records, not
  from memory. Items accepted "as criteria only" or "in limited scope" are
  labelled as such everywhere they appear.
- **Unsupported-claim check:** every Shopify/Odoo behavior claim carries
  either an official URL fetched 2026-07-09 or a repo citation. Claims this
  audit could not trace (none remained after drafting) were required to be
  dropped or logged as open questions.
- **Rejected-approaches check (`CLAUDE.md` §10):** no approach proposed in
  this package matches RA-001 – RA-024. The MBQ-05 branch B
  recommendation explicitly routes through RA-003's stated revisit
  condition (evaluate, not adopt).
- **Accidental-implementation check:** `git status`/diff confirms only the
  allowed Markdown files changed; no `*.py`, `*.xml`, `*.csv`, manifest,
  workflow, or addon file is touched.
- **Blocker-miss check:** the open-point register was cross-checked against
  (a) the handoff's own "remains open" lists, (b) the AR log's per-row
  residuals, (c) the sync-engine open-questions/risk registers, (d) the
  TD register, (e) the MBQ register header, and (f) the Task 011 blocker
  table — every item present in any of those appears in the register or is
  explicitly recorded as resolved with proof.
- **Findings of this red-team pass that changed the drafts:** (i) an early
  draft described TD-002's dependency as "fulfillment API model undecided"
  — corrected to the precise scope-set residual after re-reading DEC-011;
  (ii) an early draft treated the release-checklist freshness note as a
  defect — reclassified as historical-preamble staleness only, since the
  checklist is a forward-looking template; (iii) the MBQ-05
  parallel-track recommendation was tightened to cite RA-003's revisit
  condition explicitly so it cannot be read as re-proposing a rejected
  approach.

## 8. Explicit non-authorizations

This audit does not:

- Open the customer-domain gate or any other gate; not the UI, OAuth,
  webhook, packaging, order, inventory, or fulfillment gates.
- Authorize Task 011, 012, 013, 014, 015, any UI/wizard/webhook/OAuth
  work, any Lite/Full packaging work, or any code of any kind.
- Issue, or render usable, any implementation prompt.
- Resolve VAL-B2, MBQ-05 (either branch), MBQ-55's order portion, TD-002,
  MBQ-56, MBQ-27, MBQ-32, address handling, company/person classification,
  Lite/Full packaging, or SRR-03/04/09.
- Merge anything, touch `main`, or touch plain `dev`.
- Reopen, weaken, or reinterpret any accepted decision or binding
  rejection.

## 9. Evidence / references

Repository files as cited inline (all Accessible, this repository,
observed 2026-07-09). External official sources, all fetched 2026-07-09,
all Accessible:

- Shopify, "Protected customer data" —
  https://shopify.dev/docs/apps/launch/protected-customer-data
- Shopify GraphQL Admin API, `Customer` object —
  https://shopify.dev/docs/api/admin-graphql/latest/objects/Customer
- Shopify GraphQL Admin API, `MailingAddress` object —
  https://shopify.dev/docs/api/admin-graphql/latest/objects/MailingAddress
- Shopify, "API versioning" —
  https://shopify.dev/docs/api/usage/versioning
- Shopify, "Access scopes" —
  https://shopify.dev/docs/api/usage/access-scopes
- Odoo 19 official source, `res_partner.py` —
  https://raw.githubusercontent.com/odoo/odoo/19.0/odoo/addons/base/models/res_partner.py
- Odoo 19 official source, `sale_order.py` —
  https://raw.githubusercontent.com/odoo/odoo/19.0/addons/sale/models/sale_order.py
- GitHub PR #140 (`AdamsOdoo/Adams`) — merge metadata via
  `pull_request_read`.

**Next step:** ChatGPT reviews this audit PR (docs-only, draft, into
`Shopify-connector`). Merging it authorizes nothing; the recommended next
act after merge is issuing the Task 011 final-prompt/gate-opening-proposal
session per the handoff's next-session prompt.
