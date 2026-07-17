# Wave 6 — Definition of Ready (E2E, UAT & Release)

> **Status: Proposed — Fable gap-closure mission, 2026-07-16. NOT accepted.**
> Acceptance authority: product owner + Claude control room. Compact DoR for
> [`wave-6-e2e-uat-release-packet.md`](wave-6-e2e-uat-release-packet.md);
> gates the opening of Wave 6 only — it authorizes nothing by itself.
>
> **Current program state (2026-07-16):** Wave 1 is **merged** and **SRR-03 is
> CLOSED**. All UAT matrices (COD, fulfillment-mode, reconnect/backfill,
> security/PII, cross-domain) **exist**.

## What Wave 6 must execute (scope reminder)

Wave 6 proves the complete MVP and includes, at minimum:

- the **deferred read-only dev-store order UAT** carried over from Wave 2
  (if read-only Shopify credentials were unavailable then — BLOCK-5 rule);
- **all mutation-domain UAT** (inventory Wave 3, fulfillment Mode 1 **and**
  Mode 2 Wave 4, product export Wave 5) with genuine dev-store evidence;
- **two-role UAT** (exactly User/Administrator) and **no-PII-masking UAT**
  (assert no masked-PII surface, no unmask toggle, no separate PII tier);
- **raw-PII role-access** verification (both roles read the raw operational
  PII their permitted operations require) alongside mandatory
  **log/audit/credential/header redaction** verification (redaction stays in
  force — it is not masking);
- **visual-fidelity**, **performance/SLO**, and **release-readiness** proof.

Detailed scope lives in the Wave 6 packet; this DoR only gates the opening.

## Gates — all must hold before Wave 6 opens

- [ ] **G6-1 — Waves 2–5 merged.** Every prior wave is merged into
      `mvp/program-integration` with an accepted Claude control-room wave
      review (Wave 1 already merged, PR #172); no wave PR is open or
      partially landed; the base SHA is verified against the program state.
- [ ] **G6-2 — All UAT matrices exist and are current.** The execution inputs
      **exist** (2026-07-16) and are re-verified current against the
      post-Wave-5 head:
      [`../08-release-readiness/mvp-uat-scenarios.md`](../08-release-readiness/mvp-uat-scenarios.md),
      [`../08-release-readiness/final-mvp-uat-plan.md`](../08-release-readiness/final-mvp-uat-plan.md),
      [`../05-qa/mvp-acceptance-matrix.md`](../05-qa/mvp-acceptance-matrix.md),
      [`../05-qa/domain-e2e-test-matrix.md`](../05-qa/domain-e2e-test-matrix.md),
      the fulfillment-mode UAT matrix
      (`../05-qa/fulfillment-mode-uat-matrix.md` — covers Mode 1 **and** Mode 2,
      per [`../02-product/fulfillment-operating-modes.md`](../02-product/fulfillment-operating-modes.md) §9),
      the COD test/UAT matrix
      ([`../02-product/cod-lifecycle-and-reconciliation.md`](../02-product/cod-lifecycle-and-reconciliation.md) §8),
      the reconnect/backfill UAT matrix (`../05-qa/reconnect-backfill-uat-matrix.md`),
      the **security/PII matrix** (`../05-qa/security-pii-matrix-waves-2-6.md` —
      two-role, raw-PII role access, no-masking, redaction-mandatory) and the
      cross-domain matrix (`../05-qa/waves-2-6-cross-domain-test-matrix.md`),
      and the export UAT scenarios
      ([`../02-product/product-export-operating-model.md`](../02-product/product-export-operating-model.md) §14).
      Any matrix out-of-date against the final head blocks this gate.
- [ ] **G6-3 — Dev-store credentials provisioned.** Human-provided Shopify
      dev-store/Partner access is in place per the DEC-028 posture (hard-stop
      5 discharged *before* the wave opens, not mid-wave); VAL-B2 is
      executable on day one. This access covers the **read-only dev-store order
      UAT deferred from Wave 2** (if it could not run then) as well as all
      mutation-domain UAT (inventory, fulfillment Mode 1 + Mode 2, export).
- [ ] **G6-4 — Release checklist re-baselined.**
      [`../08-release-readiness/mvp-release-readiness-checklist.md`](../08-release-readiness/mvp-release-readiness-checklist.md)
      is refreshed against the post-Wave-5 head (its last addendum predates
      the 2026-07-15 checkpoint — program §3 item 23): stale items corrected,
      Waves 2–5 outcomes reflected, known-limitations list current (including
      the 015B detach-only/orphan-file limitation), and the checklist
      re-accepted as the sign-off instrument.

## Definition of ready confirmed by

Claude control room records gate verification in `mvp-program-state.md`;
the product owner confirms G6-3 explicitly. Then, and only then, the Wave 6
packet's scope may start.
