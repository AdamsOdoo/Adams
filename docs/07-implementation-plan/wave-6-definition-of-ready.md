# Wave 6 — Definition of Ready (E2E, UAT & Release)

> **Status: Proposed — Fable gap-closure mission, 2026-07-16. NOT accepted.**
> Acceptance authority: product owner + Claude control room. Compact DoR for
> [`wave-6-e2e-uat-release-packet.md`](wave-6-e2e-uat-release-packet.md);
> gates the opening of Wave 6 only — it authorizes nothing by itself.

## Gates — all must hold before Wave 6 opens

- [ ] **G6-1 — Waves 2–5 merged.** Every prior wave is merged into
      `mvp/program-integration` with an accepted Claude control-room wave
      review (Wave 1 already merged, PR #172); no wave PR is open or
      partially landed; the base SHA is verified against the program state.
- [ ] **G6-2 — All UAT matrices exist.** The execution inputs are committed
      and current:
      [`../08-release-readiness/mvp-uat-scenarios.md`](../08-release-readiness/mvp-uat-scenarios.md),
      [`../08-release-readiness/final-mvp-uat-plan.md`](../08-release-readiness/final-mvp-uat-plan.md),
      [`../05-qa/mvp-acceptance-matrix.md`](../05-qa/mvp-acceptance-matrix.md),
      [`../05-qa/domain-e2e-test-matrix.md`](../05-qa/domain-e2e-test-matrix.md),
      the fulfillment-mode UAT matrix (`../05-qa/fulfillment-mode-uat-matrix.md`
      — companion deliverable named by
      [`../02-product/fulfillment-operating-modes.md`](../02-product/fulfillment-operating-modes.md) §9),
      the COD test/UAT matrix
      ([`../02-product/cod-lifecycle-and-reconciliation.md`](../02-product/cod-lifecycle-and-reconciliation.md) §8),
      and the export UAT scenarios
      ([`../02-product/product-export-operating-model.md`](../02-product/product-export-operating-model.md) §14).
      Any matrix still marked pending blocks this gate.
- [ ] **G6-3 — Dev-store credentials provisioned.** Human-provided Shopify
      dev-store/Partner access is in place per the DEC-028 posture (hard-stop
      5 discharged *before* the wave opens, not mid-wave); VAL-B2 is
      executable on day one.
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
