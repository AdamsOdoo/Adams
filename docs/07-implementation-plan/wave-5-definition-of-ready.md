# Wave 5 — Definition of Ready (Premium Operator Experience)

> **Status: Proposed — Fable gap-closure mission, 2026-07-16. NOT accepted.**
> Acceptance authority: product owner + Claude control room (per
> [`mvp-completion-program.md`](mvp-completion-program.md) §4 Wave 5 and the
> DEC-032 operating model). This checklist gates the *opening* of Wave 5; it
> authorizes no implementation by itself. Structure follows
> [`../06-prompts/implementation-task-template.md`](../06-prompts/implementation-task-template.md),
> adapted to the macro-wave model.
>
> **Current program state (2026-07-16):** Wave 1 is **merged** and **SRR-03 is
> CLOSED**; the premium UX master specification **exists** and is committed.
> Both fulfillment Mode 1 and Mode 2 **backend** behavior are delivered in
> Wave 4 — **Wave 5 builds only the Mode 2 UI, never the Mode 2 backend.**
> SEC-2 in this wave both collapses four internal groups to two customer-facing
> roles **and** removes PII masking (there is no PII masking in the MVP; both
> roles read raw operational PII per permitted operations).

## 1. Wave objective

Deliver the premium operator experience and complete the accepted DEC-003
scope, as one wave with internally sequenced stages:

1. **SEC-2** — the 4-internal-groups → 2-customer-facing-roles migration
   **and the PII-masking removal correction**
   ([`../02-product/connector-roles-and-permissions.md`](../02-product/connector-roles-and-permissions.md) §3–§4):
   Administrator inherits User, both roles read raw operational PII per their
   permitted operations, and the Wave-1 masking implementation is removed;
   log/audit/credential/header redaction stays mandatory.
2. **UI U1 → U2 → U3** per
   [`ui-implementation-phases-packet.md`](ui-implementation-phases-packet.md)
   (U1 locked prompt exists; U2/U3 locked prompts added by that packet's
   2026-07-16 addendum), building against the accepted
   `../02-product/premium-ux-master-specification.md`, **including the
   fulfillment Mode UI** — the Administrator mode selector, the mode
   explanation/confirmation screen, the unresolved-external-fulfillment UI, the
   User review workspace, reconciliation visualizations, mode-switch history,
   and fulfillment dashboards/timelines — all wired to the **already-delivered
   Wave 4 Mode 1 + Mode 2 backend**.
3. **Manual/scheduled sync controls** (Area 6 remainder: manual triggers,
   operator-visible cadence) and the mapping/configuration, job/log,
   error-center/manual-review screens (`action_resolve_manual_review`).
4. **PERF-1** queue-throughput calibration
   ([`task-perf1-core-queue-throughput-calibration-packet.md`](task-perf1-core-queue-throughput-calibration-packet.md)).
5. **Task 015 / 015B** controlled product export + basic media export
   (own module, own packets/gates), under Layer 2.

**No Mode 2 backend deferral:** Mode 2 auto-application logic is NOT a Wave 5
deliverable — it ships in Wave 4. Wave 5's only Mode 2 work is the UI in
stage 2 above.

## 2. Gates — every box must be checked before the wave opens

- [ ] **G5-1 — Premium UX master specification accepted.**
      `../02-product/premium-ux-master-specification.md` **exists and is
      committed** (2026-07-16) and must be accepted; its screen groups are the
      binding deliverable inventory for U1/U2/U3. Until it is accepted, no UI
      stage prompt may be issued.
- [ ] **G5-2 — Two-role + no-masking migration design accepted + SEC-2 packet
      exists.** The proposed-decision block of
      `connector-roles-and-permissions.md` §6 (Option M-A, hidden legacy
      groups, single privilege selection, migration script, and the
      **PII-masking removal** — both roles read raw operational PII per
      permitted operations; no masked-PII experience, no unmask toggle, no
      separate PII permission tier) is accepted, and a dedicated **SEC-2
      implementation packet**
      ([`task-sec2-two-role-and-pii-simplification-packet.md`](task-sec2-two-role-and-pii-simplification-packet.md):
      groups + privilege + exhaustive ACL re-key CSV per §4.5/OQ-C + migration
      script per §4.7 + the §4.9 test set + Wave-1 masking-removal disposition)
      is written and accepted. That document itself states: **Wave 5 role-gating
      work must not start until this decision is accepted or amended.**
- [ ] **G5-3 — U1 prototype-fidelity criteria fixed.** The accepted U0
      prototype (`docs/09-ui-prototype/`, extended by the gap-closure
      workspaces) is named as the fidelity baseline; the design-system
      acceptance set (tokens/scales only, five states per surface,
      accessibility gates, screenshot set, tours + HOOT browser tests — UI
      packet §4/§5) is confirmed as the U1 acceptance bar.
- [ ] **G5-4 — PERF-1 budgets accepted.** The PERF-1 packet's decision
      closures (the `_commit_progress()` drain-loop transaction model and the
      ≥600 jobs/hour PB-19 budget with its measurement method, packet §3/§7)
      are accepted, so UI throughput/progress surfaces are built against the
      calibrated dispatcher, not the known-deficient 240/h ceiling.
- [ ] **G5-5 — Export operating-model PDs accepted.** PD-PX-1..7 of
      [`../02-product/product-export-operating-model.md`](../02-product/product-export-operating-model.md)
      §16 are accepted; Task 015/015B packets are re-accepted with the
      2026-07-16 addendum (field ownership, changed-since-read gate,
      destructive-list guard, Layer 2 reconciliation); the named dev-store
      empirical checks (OQ-PX-1/2/5) are scheduled as Wave 5 preflight items.
- [ ] **G5-6 — Layer 2 in place.** DEC-031 Layer 2 is accepted, implemented
      (Wave 3), and proven for mutation domains; PD-PX-6 (no export apply
      outside Layer 2) is enforceable. Waves 1–4 are merged runtime-green —
      every backend action a screen exposes must already exist (program §4
      Wave 5 dependency rule).
- [ ] **G5-7 — SEC-1 surface intact.** The merged SEC-1 hardening (Wave 1,
      PR #172) still passes at the Wave 5 base SHA; UI buttons wire only to
      sanctioned services (UI packet §3); any model added by Waves 2–4 has
      its SEC-1-pattern guards before a screen touches it.
- [ ] **G5-8 — Fulfillment Mode 2 backend delivered by Wave 4.** Wave 4
      merged both Mode 1 and Mode 2 **backend** behavior runtime-green (the
      per-store mode field, 16-condition engine, mode-switch state machine,
      reconnect reconciliation). Wave 5 builds only the Mode 2 **UI** (mode
      selector, confirmation screen, review workspace, dashboards) against that
      existing backend — it must not re-implement or defer any Mode 2 backend
      logic (fulfillment-operating-modes §8/§10).
- [ ] **G5-9 — Rejected-approaches check recorded** for every stage
      (`../05-qa/rejected-approaches-log.md`, CLAUDE.md §10).

## 3. Sequencing inside the wave — SEC-2 first (recommendation with justification)

Two orderings were considered for the SEC-2 ↔ U1 dependency:

- **Option A — U1 on the old four groups, SEC-2 flips afterwards.** Rejected:
  every U1 visibility-matrix test, `groups=` attribute, and button gate would
  be written against operator/reviewer and rewritten within the same wave;
  the visibility matrix would be proven twice; a mid-wave flip risks a window
  where UI gating and server-side ACLs disagree — exactly the failure class
  SEC-1's negative cells exist to prevent (UI packet §3).
- **Option B — SEC-2 first, then U1/U2/U3 build role-gated views against the
  final two-role model.** **Recommended.** The roles document itself reaches
  this conclusion (§5: accept before Wave 5; "the UI wave must build
  role-gated affordances against the two-role model, not the four-role model,
  or it will be reworked"; "Recommend SEC-2"). SEC-2 is purely additive
  (Option M-A: new group + implied_ids; no XML-ID rename), so it is a small,
  crisply reviewable security diff with its own rollback (§4.10) — the
  cheapest possible first stage, and it de-risks everything after it.

**Binding sequence:** SEC-2 → PERF-1 (backend-only; parallelizable with
SEC-2 review) → U1 → U2 → U3 → Task 015 → Task 015B. The fulfillment Mode UI
(mode selector, review workspace, dashboards) ships as part of the U1–U3
domain workspaces against the Wave 4 backend — there is **no separate Mode 2
backend stage in Wave 5**. Task 015/015B may start once SEC-2 + Layer 2 gates
hold — they are backend-first and only their S7 preview/diff screen waits for
U3. Each stage retains its own packet gate inside the single wave PR cadence.

## 4. Allowed / forbidden paths (wave-level; stage packets are exhaustive)

- **Allowed:** SEC-2 packet allowlist (security data/CSV/migration/tests in
  existing modules); UI stage allowlists (views/actions/menus/wizards, Owl
  surfaces per the PD-7 list, copy decks, browser tests); PERF-1 packet
  allowlist (core dispatcher/cron/config + `test_dispatch_throughput.py`);
  `addons/shopify_connector_product_export/**` per Task 015/015B allowlists;
  Wave 5 evidence docs, AR rows, handoff, program state.
- **Forbidden:** UI wiring to any model without SEC-1/SEC-2 hardening; new
  backend business logic beyond what a screen needs to call already-accepted
  actions (program §4 Wave 5); `inventoryQuantities` anywhere in export;
  auto-apply/no-preview export paths; automatic `fileDelete`; renaming any
  legacy group XML ID; webhooks/OAuth/CI; protected references; `adams_base`.

## 5. Wave acceptance criteria (observable)

1. Exactly two customer-facing roles (User/Administrator) on the user form;
   SEC-2's §4.9 test set green (ACL matrix, migration idempotency,
   no-privilege-escalation, **raw operational PII readable by both roles per
   permitted operations with no masking surface** — assert no masked-compute
   field and no unmask toggle exist, company/ACL boundaries and `fields_get`
   for genuinely restricted fields verified — UI hiding, implication closure);
   log/audit/credential/header redaction remains in force.
2. Every accepted premium-UX screen group implemented at prototype fidelity:
   U1 core surface, U2 setup/readiness, U3 domain workspaces — with tours +
   HOOT green, screenshot set, accessibility evidence, PB measurements
   (UI packet §5), and every button wired to a sanctioned hardened service.
3. Operator can: trigger manual sync and see scheduled cadence; read
   job/sync logs from a screen; retry/cancel/resolve manual-review jobs
   (`action_resolve_manual_review` tested); configure mappings/settings from
   screens (acceptance-matrix rows 5, 13–16, 18, 19).
4. PERF-1: drain loop follows the official `_commit_progress()` contract; no
   row lock held across another job's network call; measured sustained
   ≥600 jobs/hour on topology A with recorded evidence.
5. Task 015/015B: preview → confirm → apply as the only export path; field
   allowlist + ownership matrix enforced; destructive-list guard blocks
   unenumerated variant deletions; Layer-2 reconciliation on ambiguous
   outcomes; media two-phase READY-gated, detach-only; dev-store mutation
   evidence (or recorded waiver) including the named empirical checks.
6. **Fulfillment Mode UI wired to the Wave 4 backend:** the Administrator
   mode selector, the mode explanation/confirmation screen, the
   unresolved-external-fulfillment UI, and the User review workspace are
   implemented and wired to the already-delivered Wave 4 Mode 1 + Mode 2
   backend (per-store mode field, 16-condition engine, mode-switch state
   machine). **No Mode 2 backend logic is (re-)built in Wave 5** — the UI
   only surfaces and drives the existing backend.

## 6. Hard stops

- Any UI button reachable whose server-side call is not denied for an
  unauthorized role (UI/ACL disagreement) → stop (hard-stop 9).
- SEC-2 migration found non-idempotent or escalating privileges beyond §4.5's
  target table → stop.
- An export mutation path reachable without a confirmed unexpired preview or
  outside Layer 2 → stop (hard-stop 4).
- Prototype-fidelity or accessibility acceptance cannot be met without
  violating design-system tokens → stop and escalate (never ad-hoc styling).
- Dev-store credentials needed for 015/015B evidence but not provisioned →
  stop (hard-stop 5).

## 7. Definition of done (wave)

Claude control-room wave review accepts and merges into
`mvp/program-integration`; acceptance-matrix rows 4–6, 13–19 updated; the
Wave 6 DoR ([`wave-6-definition-of-ready.md`](wave-6-definition-of-ready.md))
prerequisites re-verified; handoff + program state updated.
