# CORE-R2 Slice 2B — Customer Call-Site Migration: Session Handoff

> **Session type:** one narrow customer-domain implementation session (Prompt C /
> RD-C). **Static validation only — NOT runtime-green.** SRR-03 OPEN. Prompt E
> BLOCKED. No live Shopify call. No merge.

**Model:** Opus 4.8.
**Date:** 2026-07-14.
**Branch:** `claude/core-r2-customer-callsite`.
**Draft PR base:** `claude/core-r2-slice-2b-integration`.
**Architecture:** AR-047. **Packet:** `task-core-r2-slice-2b-callsite-runtime-packet.md` §5.2/§9.
**Companion:** `docs/05-qa/task-core-r2-customer-callsite-validation.md`.

---

## 1. Heads

- **Starting head (required):** `4f2cd7e4e09c591d4b63dd77888dd22f355f5c79`
  (== the `claude/core-r2-slice-2b-integration` staging tip; == the working
  branch tip at session start).
- **Final head:** *(the documentation commit on `claude/core-r2-customer-callsite`
  — the last of the three commits below; recorded in the draft PR.)*
- **Post-Slice-2A Shopify-connector base:** `a3fd6cd…` (ancestor of `4f2cd7e`).
- **Accepted sources (both ancestors of `4f2cd7e`, both open/draft/unmerged):**
  PR #150 customer `10d0034…`, PR #151 product `e4669aa…`.

---

## 2. Exact changed files (3)

1. `addons/shopify_connector_sale/models/shopify_connector_customer_importer.py` — production call-site migration.
2. `addons/shopify_connector_sale/tests/test_customer_import_matching.py` — adapted transport-stub tests + rewritten AST guard + new `TestCustomerCallsiteExecuteBusiness`.
3. `addons/shopify_connector_sale/tests/test_customer_matching_scalability.py` — adapted opt-in genuine-race concurrency test.

No core/product/manifest/XML/security/data/CI/shared-handoff file changed.

---

## 3. Old / new call-site shape

See `…/task-core-r2-customer-callsite-validation.md` §3. In one line: the
value-returning `execute()` → `normalize` → `apply` shape became a single
`with client.execute_business(job, store, CUSTOMER_IMPORT_QUERY, variables=…) as
result:` context wrapping `normalize` + `apply` + `flush_all` + `return`, with the
`ShopifyClientError → JobHandlerError` mapping around the `with`.

---

## 4. Lease boundary

One committed admission lease spans: Admin GraphQL call → API normalization →
`_normalize_payload` → full `_apply_import` reconciliation → `env.flush_all()`
(materialize-in-transaction, not commit) → return. Release on `with`-exit, after
reconciliation. No explicit commit. (Validation §4.)

---

## 5. Job thread-through

`_handle_customer_import_sync` already passes `job=job` to `import_customer_sync`
(unchanged). `import_customer_sync` now passes that `job` as the **first
positional** argument to `execute_business` — where it is the admission credential
(a business call is refused at admission without a valid job) **and** the existing
country/state note thread. Direct test callers now pass a real `job` accordingly.

---

## 6. Exception behaviour

`ShopifyClientError` (admission missing-credential / transport) →
`JobHandlerError(error_class, reason, technical_detail) from exc`, DEC-009 class
preserved. `ShopifyQuiescedError` propagates **uncaught** (the sole `except`
catches only `ShopifyClientError`) for the integrated Slice 2A dispatcher's
fail-closed `skipped` routing. Reconciliation `JobHandlerError`s propagate through
`__exit__` (lease released once) unchanged. (Validation §5.)

---

## 7. Matching-behaviour proof

Reconciliation code (`_apply_import` and everything below it) is byte-for-byte
unchanged — the diff touches only `import_customer_sync`'s transport/lease
boundary and three docstrings. Proven by: (a) the AST invariant scan (16/16); (b)
the unchanged Task 011/011B suites (`TestCustomerImportMatching`,
`TestCustomerDuplicatePrevention`, `TestCustomerFallbackPartner`,
`TestCustomerBinding`, `TestCustomerMatchingScalability`, + opt-in benchmark);
(c) 0 existing assertions removed/weakened (53 added). (Validation §6.)

---

## 8. Static results

py_compile OK; compileall OK; no conflict markers; 3 allowed files only; AST
invariant scan 16/16 PASS; secret/PII scan clean (placeholder token + reserved
domains only); 0 assertions weakened. (Validation §7.)

---

## 9. Adversarial self-review

A parallel diverse-lens adversarial review (five independent reviewers:
lease-boundary, exception-routing, matching-unchanged, test-correctness,
scope-contamination), each reading the actual diff, importer,
`shopify_connector_api_client.py`, and test files, with an independent
adversarial verification pass on any finding.

**Result: 0 raw findings, 0 confirmed findings.** Every reviewer returned an
empty finding set after substantive analysis (each with a genuine multi-tool
read of the code). This is in addition to the author's own AST invariant scan
(16/16 PASS), `py_compile`/`compileall`, conflict-marker scan, secret/PII scan,
and changed-assertion review.

**Key adversarial checks — all clear:**

- No api result escapes the context (AST: `result` loads all inside the `with`).
- `flush_all` inside the context, before `return`; no commit.
- `job` never lost (first positional; dispatcher thread-through intact).
- `ShopifyQuiescedError` never remapped or broad-caught.
- Matching / candidate-search / fallback-partner / binding-uniqueness / savepoint
  unchanged (reconciliation code untouched).
- No product/core contamination; no legacy `execute()` fallback; no new file.

---

## 10. Runtime status

**Runtime pending.** No Odoo runtime this session. Integrated exact-head Odoo.sh
evidence is captured on the staging head after merge-back (packet §7 steps 5–7).
No runtime-green claimed.

---

## 11. Gates & rollback

- **Prompt E BLOCKED** (core-only public-`execute()` closure; runs after both
  call sites are migrated + merged to staging — packet §9c).
- **SRR-03 OPEN.**
- No merge, no live Shopify, no PR closure, no runtime-green claim.
- **Rollback:** normal revert of this child PR before integration; no schema/data
  migration; inherited Task 011B `import_customer_sync` restored intact.

---

## 12. Open questions

- **OQ (carried):** exact-head integrated Odoo.sh evidence + the deployed
  multi-worker proof are produced on the staging head, not here.
- **OQ-5 (packet):** `flush_all` materialize-not-commit semantics are asserted
  structurally here (AST) and behaviourally in `TestCustomerCallsiteExecuteBusiness`
  (binding materialized before lease release); final confirmation is the
  integrated Odoo 19 runtime.

---

## 13. Exact next-session prompt (proposed — for ChatGPT to authorise)

> Merge `claude/core-r2-customer-callsite` and `claude/core-r2-product-callsite`
> back into `claude/core-r2-slice-2b-integration` (packet §7 step 5), then run the
> integrated exact-head Odoo.sh validation on the staging head (fresh install +
> core/product/sale suites + CORE-R2 admission classes + both domains'
> call-site activation tests + the deployed multi-worker proof ×3). Do **not**
> start Prompt E until both call-site branches are merged back. SRR-03 stays OPEN.
