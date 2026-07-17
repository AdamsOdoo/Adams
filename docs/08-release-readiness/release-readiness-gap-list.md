# Release-Readiness Gap List — Post-Wave-1 Baseline

> **Status: Proposed — Fable gap-closure mission, 2026-07-16. Planning only;
> no test executed; no gate opened.** Current release-readiness gap list as
> of the Wave 1 merge (PR #172, `d18f9a9`, build `34995642` green
> `0/0/644`). Keyed 1:1 to the 23 rows of
> [`../05-qa/mvp-acceptance-matrix.md`](../05-qa/mvp-acceptance-matrix.md)
> (the authoritative release checklist — this list adds only *what is still
> missing, which wave owns it, and what evidence is required*; where the two
> ever disagree, the acceptance matrix wins and the conflict must be
> raised). Statuses here are a [Fact]-level restatement of that matrix's
> "Current status"/"Blocking issue" columns on 2026-07-16; wave ownership
> follows [`../07-implementation-plan/mvp-program-state.md`](../07-implementation-plan/mvp-program-state.md).

| # | MVP item | Still missing (gap) | Owning wave | Evidence required to close |
| --- | --- | --- | --- | --- |
| 1 | Store connection & lifecycle | Operator-facing lifecycle UI (backend runtime-green) | Wave 5 (U-waves) | Store reaches `connected` via UI in a dev-store session; Odoo.sh green; zero residue |
| 2 | Secure credentials | DEC-028 deployment posture proven before real-customer PII | Wave 6 (pre-UAT gate) | Deployment-posture evidence + clean leak/security scan carried into Wave 6 |
| 3 | Test connection | VAL-B2 live dev-store connection evidence | Wave 6 (with row 22) | VAL-B2 passes against a real/dev Shopify store per [`../05-qa/val-b2-closure-plan.md`](../05-qa/val-b2-closure-plan.md) |
| 4 | Guided setup wizard | Entire U2 implementation | Wave 5 | Operator completes all 11 accepted steps end-to-end; screenshot evidence |
| 5 | Operational dashboard | U1 implementation (SEC-1 substrate merged) | Wave 5 | Dashboard reflects live store/job state in a dev-store UAT session; PB-2/3/8 measured |
| 6 | Product/variant import & export | Export side entirely (Task 015/015B); Layer 2 prerequisite | Wave 3 (Layer 2) + Wave 5 (export) | Import reconfirmed Wave 6; export Layer-2-aware Odoo.sh + dev-store mutation evidence; [`../02-product/product-export-operating-model.md`](../02-product/product-export-operating-model.md) §14 dev-store verifications run |
| 7 | First-sync matching / duplicate prevention | Nothing (complete at checkpoint) | Wave 6 re-confirmation only | Dev-store UAT re-confirmation |
| 8 | Customer import & matching | Nothing (complete; 100k benchmark obtained) | Wave 6 re-confirmation only | Dev-store UAT re-confirmation |
| 9 | Order import into Odoo SOs | Entire Task 012 implementation + confirmation-policy/COD-import layers ([`../02-product/sales-order-lifecycle-and-confirmation-policy.md`](../02-product/sales-order-lifecycle-and-confirmation-policy.md)); Wave 2 not yet authorized | Wave 2 | Packet accepted; Odoo.sh fresh-install + focused-class green + full existing-domain regression + security/duplicate-prevention tests + exact-head evidence + Claude wave review (all mandatory); Wave-2 rows of [`../05-qa/waves-2-6-cross-domain-test-matrix.md`](../05-qa/waves-2-6-cross-domain-test-matrix.md); **read-only** dev-store order-import UAT strongly preferred but **not a Wave 2 merge blocker** — deferrable to Wave 6 if Shopify credentials are unavailable (VAL-B2 not presented as completed) |
| 10 | Basic inventory sync | DEC-031 Layer 2 acceptance + implementation; Task 013/013B | Wave 3 | Layer 2 runtime proof (multi-worker, crash/sweep); Odoo.sh green; PB-20 dev-store run; first-push UAT |
| 11 | Bidirectional inventory behavior | Apply-mode MBQs + [`../02-product/inventory-operating-model.md`](../02-product/inventory-operating-model.md) acceptance | Wave 3 | Regression tests matching the accepted rule set; divergence-review UAT |
| 12 | Fulfillment/tracking updates | Task 014 (revised) + operating modes + status model implementation | Wave 4 (Mode 1 + Mode 2 backend) | Odoo.sh green; [`../05-qa/fulfillment-mode-uat-matrix.md`](../05-qa/fulfillment-mode-uat-matrix.md) executed; correct merchant-managed scopes evidenced |
| 13 | Scheduled synchronization | Area 6 (needs Task 012 first) | Wave 2+ | All domains scan/enqueue on schedule with operator-visible cadence |
| 14 | Manual synchronization | Area 6 + trigger UI | Waves 2–5 | Operator triggers a sync from the UI and observes the result |
| 15 | User-friendly job/sync logs | Log UI (backend merged) | Wave 5 | Operator reads logs from a screen; PB-6 measured |
| 16 | Retry & recovery controls | Operator UI (backend + JOB-ACTIONS merged) | Wave 5 | Retry/cancel/resolve from a screen; four-retry-case UI negative test (no bypass) |
| 17 | Duplicate prevention & idempotency | Layer 2 design acceptance + implementation for every mutation domain | Wave 3 (design/impl) → Waves 3–5 (domains) | Per-domain replay policy declared; [`../03-architecture/dec-031-layer-2-mutation-safety-design.md`](../03-architecture/dec-031-layer-2-mutation-safety-design.md) §13 suite green incl. AST guard + multi-worker proof |
| 18 | Mapping/configuration screens | U3 implementation | Wave 5 | Location-mapping / store-settings UAT walkthrough |
| 19 | Basic roles & permissions | Two-role model acceptance + SEC-2 migration + roles UI (four-group backend green) | Wave 5 (SEC-2 before UI) | Roles-doc §4.9 suite green; migration idempotency; roles walkthrough; [`../05-qa/security-pii-matrix-waves-2-6.md`](../05-qa/security-pii-matrix-waves-2-6.md) §6 |
| 20 | Install/upgrade/config documentation | Final guide (LC-1 runtime-green) | Wave 6 | Guide validated against Wave 6 install/upgrade/uninstall runs |
| 21 | **End-to-end tests / CI** | **No CI exists; full suite has only one-off runs; Waves 2–5 domains untested (unbuilt)** | Wave 6 (CI + continuous run); each wave adds its suite | First **continuous (non-one-off)** execution: full suite green in a single reproducible Wave 6 session covering every implemented domain, per [`../05-qa/waves-2-6-cross-domain-test-matrix.md`](../05-qa/waves-2-6-cross-domain-test-matrix.md) §5; CI workflow authorization is itself gated (`.github/workflows/*` is research-phase-forbidden — raise before creating) |
| 22 | **Dev-store UAT evidence (VAL-B2)** | Dev-store credentials/access not yet provisioned; zero live Shopify calls have been made so far. [Product-direction update — 2026-07-16] This is **no longer a blanket hard stop on all waves**: Odoo.sh evidence is mandatory every wave, and the **read-only** Wave 2 order-import dev-store UAT is strongly preferred but is **not a Wave 2 merge blocker** (deferrable to Wave 6 if read-only Shopify credentials are unavailable — VAL-B2 not presented as completed). **Mutation waves 3–5 and this Wave 6 run still require genuine dev-store mutation evidence** before their closure. DEC-028 posture required before any real PII | Wave 6 (mutation waves 3–5 also require dev-store mutation evidence; provisioning is a product-owner action) | VAL-B2 executed; per-domain UAT scenarios ([`cod-uat-matrix.md`](../05-qa/cod-uat-matrix.md), [`fulfillment-mode-uat-matrix.md`](../05-qa/fulfillment-mode-uat-matrix.md), [`reconnect-backfill-uat-matrix.md`](../05-qa/reconnect-backfill-uat-matrix.md)) executed; no token/PII leakage in the post-run scan |
| 23 | **Release package** | Scaffolding predates the checkpoint (see the README re-baseline note); final package must aggregate rows 1–22 | Wave 6 | Every acceptance-matrix row at its release criterion or explicitly waived by the product owner; sign-off via [`mvp-release-readiness-checklist.md`](./mvp-release-readiness-checklist.md); measured [`../05-qa/performance-slo-benchmark-plan.md`](../05-qa/performance-slo-benchmark-plan.md) table attached (silence is not a waiver) |

## Reading notes

- [Inference] The **critical path** through this list is: Layer 2 (row 17)
  → Wave 2 orders (row 9) → Wave 3 inventory (rows 10–11) → Wave 4
  fulfillment (row 12) → Wave 5 UI/export/roles (rows 1, 4–5, 6, 14–16, 18,
  19) → Wave 6 (rows 2–3, 20–23). Rows 7–8 are re-confirmation only.
- [Fact] Wave 2 remains unauthorized as of 2026-07-16; nothing in this list
  authorizes it.
- Update discipline: when a wave merges, update the acceptance matrix and
  this list **together** (mirroring the matrix's own rule for
  `mvp-completion-program.md` §3).
