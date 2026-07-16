# Wave 6 — End-to-End Integration, UAT & Release-Readiness Packet

> **Status: Proposed — Fable gap-closure mission, 2026-07-16. NOT accepted.**
> Acceptance authority: product owner + Claude control room (per
> [`mvp-completion-program.md`](mvp-completion-program.md) §4 Wave 6 and the
> DEC-032 operating model). This is the previously missing Wave 6 packet:
> every earlier wave has an owning packet; Wave 6 had only the program §4
> paragraph. Structure per
> [`../06-prompts/implementation-task-template.md`](../06-prompts/implementation-task-template.md).
> Companion: [`wave-6-definition-of-ready.md`](wave-6-definition-of-ready.md).

## 1. Objective

Prove the complete MVP — end-to-end integration, live dev-store UAT, and the
release-readiness decision. **This wave proves the MVP; it does not extend
it** (program §4 Wave 6: "no new feature scope of any kind"). Its output is
evidence and documentation, culminating in a release-readiness proposal that
the **product owner** accepts or rejects — the wave is never self-executing
(program §7).

## 2. Scope

### 2.1 Lifecycle proof across the full 6-module family

Fresh-install, upgrade, uninstall, and reinstall proof for the complete
module family
([`../03-architecture/modular-architecture-recommendation.md`](../03-architecture/modular-architecture-recommendation.md)
§2.7/§3): `shopify_connector_core`, `shopify_connector_product`,
`shopify_connector_sale`, `shopify_connector_inventory`,
`shopify_connector_fulfillment`, `shopify_connector_product_export` — per the
accepted DEC-030 lifecycle design and the LC-1 precedent (Wave 1), now
exercised with all six modules in every combination the packaging model
allows (Lite subset and Full), including uninstall-residue checks and
reinstall-after-uninstall.

### 2.2 First continuous full-suite run

The first continuous (non-one-off) execution of the entire test suite across
all modules in a single, reproducible session (acceptance-matrix row 21 —
historically every "green" was a one-off dev-build; no CI exists).

### 2.3 Cross-domain E2E scenarios

True cross-domain flows (beyond `../05-qa/domain-e2e-test-matrix.md`'s
planning rows), at minimum:

1. **Order → confirm → deliver → fulfill → track → COD-collect → reconcile:**
   import a COD order, confirm per policy, reserve/validate delivery,
   observe the outbound fulfillment + tracking on Shopify, record collection
   events, converge the five-value COD ledger to outstanding = 0
   (`../02-product/cod-lifecycle-and-reconciliation.md` scenario 1, plus at
   least one partial/backorder variant from scenarios 8–13). Run the
   fulfillment leg in **both operating modes** — Mode 1 (explicit User
   validation) and Mode 2 (16-condition auto-application, with at least one
   fail-to-review case) — per the fulfillment-mode UAT matrix, since both
   Mode 1 and Mode 2 backend ship in Wave 4.
2. **Reconnect mid-flow:** disconnect a store with in-flight jobs, create
   external activity during the gap (an order, an external fulfillment, an
   inventory change), reconnect, and verify quiescence + watermark catch-up +
   review-case landing per the reconnect/backfill policy and
   fulfillment-operating-modes §7 — no duplicates, no silent applies.
3. **Multi-location:** orders/fulfillments/inventory across at least two
   mapped Shopify locations, including the FO-per-location decomposition and
   a location-mismatch review case.

### 2.4 Live dev-store UAT (VAL-B2)

The first live Shopify Admin API interaction in the project's history
(program §2 finding 9), executing:

- VAL-B2 connection/readiness proof;
- **the read-only dev-store order-import UAT deferred from Wave 2** — Wave 2
  was allowed to close on Odoo.sh evidence alone with the read-only live
  order UAT deferred here when read-only Shopify credentials were unavailable
  (BLOCK-5 rule; recorded, no product-scope waiver). It is executed here
  against a real dev store as part of the full UAT set;
- every scenario in
  [`../08-release-readiness/mvp-uat-scenarios.md`](../08-release-readiness/mvp-uat-scenarios.md)
  and the per-domain UAT matrices (fulfillment-mode matrix covering **Mode 1
  and Mode 2**, COD §8 matrix, reconnect/backfill matrix, export §14
  scenarios) against a real dev store, with **genuine mutation evidence** for
  every mutation domain (inventory, fulfillment, export);
- **credential-provisioning hard-stop:** dev-store/Partner access and
  credentials are provided by a human (program hard-stop 5). The wave stops
  and waits — it never fabricates, simulates, or borrows "live" evidence.
  DEC-028 deployment posture is a hard gate before any real-customer PII
  enters UAT.

### 2.5 Security, PII-model, and residue audits

Full-family **log/audit/credential/header redaction** scan (no token/PII in
logs, filestore, test artifacts — redaction is mandatory and stays in force);
repeat of the zero-residue audit pattern from Wave 1 across all six modules;
effective-permission spot-audit of the **two-role** model (exactly
User/Administrator) on the final head. **No-PII-masking UAT:** assert that no
masked-PII surface, no unmask toggle, and no separate PII permission tier
exists anywhere in the product; **raw-PII role-access UAT:** verify that
Connector User and Connector Administrator each read the raw operational
customer/order PII their permitted operations require, governed by ordinary
Odoo access control, company boundaries, and connector-model ACLs. (Credential
`•••` masking / no-read-back per DEC-004 is unaffected — it is credential
masking, not PII masking, and stays.)

### 2.6 Performance benchmark execution

Execute the performance-budget suite
([`../03-architecture/performance-budgets.md`](../03-architecture/performance-budgets.md))
against the final head — PB calibration re-run including the PERF-1
≥600 jobs/hour evidence at release scale, import benchmarks re-confirmed,
and UI PB measurements carried from Wave 5 re-checked on the release build.

### 2.7 Documentation completeness

User-facing install, upgrade, and configuration guides (acceptance-matrix
row 20; program §4 Wave 6), validated against the §2.1 runs — every
documented step actually executed at least once.

### 2.8 Release-readiness decision flow

1. Bring every row of
   [`../05-qa/mvp-acceptance-matrix.md`](../05-qa/mvp-acceptance-matrix.md)
   to its stated release criterion (or a recorded product-owner waiver).
2. Complete
   [`../08-release-readiness/mvp-release-readiness-checklist.md`](../08-release-readiness/mvp-release-readiness-checklist.md)
   with per-item evidence links.
3. Claude control-room wave review per the wave-review template.
4. **Explicit product-owner sign-off** — the release decision is a human
   act; neither Sol nor Claude may execute it (program §7). Promotion of
   `mvp/program-integration` toward `Shopify-connector`/`main` remains a
   separate, later, product-owner-approved act outside this wave.

## 3. Allowed files

- `docs/08-release-readiness/**` (evidence, checklist completion, sign-off
  records), `docs/05-qa/**` (audit/validation results, matrix updates),
  `docs/01-research/research-handoff.md`, program state, user-facing guides
  under `docs/**`.
- Test suites across all connector addons (`addons/shopify_connector_*/tests/**`)
  — new cross-domain E2E tests are in scope.
- **CI configuration (`.github/workflows/*` or equivalent) ONLY if separately
  and explicitly authorized** — flagged as its own gate: CI files are on the
  standing forbidden list (CLAUDE.md §11) and the "first continuous run" can
  be satisfied by a scripted, reproducible Odoo.sh session without CI. If the
  control room + product owner authorize CI, that authorization must name the
  exact workflow files; absent it, no CI file is touched.

## 4. Forbidden files

- **Feature code changes of any kind** in `addons/**` non-test files —
  **except accepted defect fixes, each behind its own mini-gate**: a Wave 6
  defect fix requires a recorded defect (repro + classification), a
  control-room acceptance of the fix's exact allowed files, its own tests,
  and its own rollback note. No drive-by refactoring, no scope absorption.
- Every protected reference (checkpoint branch, `Shopify-connector`, `main`,
  issue #165, PR #150/#151); `adams_base`; plain `dev`.

## 5. Acceptance criteria

1. **All 23 rows of `mvp-acceptance-matrix.md` green** — each at its stated
   release criterion, with evidence linked, or explicitly product-owner-waived
   on the record.
2. All UAT matrices executed against the live dev store with recorded,
   genuine evidence (mvp-uat-scenarios 1–15 + domain matrices + the §2.3
   cross-domain flows).
3. §2.1 lifecycle proof recorded for the 6-module family; §2.2 full suite
   green in one reproducible session; §2.5 audits clean; §2.6 budgets met;
   §2.7 guides validated.
4. Release-readiness checklist complete; control-room review accepted;
   product-owner sign-off recorded (or a recorded no-go with the gap list).

## 6. Tests

The full existing suite (all modules), the new cross-domain E2E tests
(§2.3), lifecycle/residue test runs (§2.1/§2.5), and the benchmark suite
(§2.6). Every previously logged defect pattern
(`../05-qa/defect-pattern-log.md`) has a regression assertion in the final
run.

## 7. Rollback

The wave is evidence + docs + tests: revert the wave PR to restore the
pre-wave state; no schema or feature surface changes to unwind (any accepted
defect fix carries its own rollback note per its mini-gate). A failed
release decision is not a rollback event — the wave's evidence stands and
the gap list drives follow-up work.

## 8. Definition of done

Claude control-room wave review accepts; every acceptance criterion in §5
met; `mvp-program-state.md` records "Wave 6 complete + release decision:
<go/no-go>"; handoff updated with the sign-off record or gap list. **Done
never means released** — release/promotion is the product owner's separate
act.

## 9. Hard stops

- Any acceptance-matrix row unreachable without new feature scope → stop
  (hard-stops 8/10); Wave 6 never grows features.
- Credentials/dev-store access unavailable → stop and request provisioning
  (hard-stop 5); never simulate live evidence.
- A critical defect found that cannot be fixed inside the mini-gate rules →
  stop (hard-stop 6).
- Token/PII leakage or a security exposure found in the audits → stop
  (hard-stop 9).
- Any pressure to self-execute the release decision → stop; product-owner
  sign-off is not delegable.
