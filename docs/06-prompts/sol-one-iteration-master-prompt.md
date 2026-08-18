# Master Implementation Prompt — One-Iteration Completion Program (GPT-5.6 Sol)

> **How to use:** the product owner pastes everything below the line into
> ChatGPT (GPT-5.6 Sol) **once**. From then on the loop is autonomous: Sol
> implements batch by batch on draft PR #206, Claude reviews on GitHub, and
> the product owner is only needed for the final merge or a recorded
> HARD STOP. Governing decision:
> [`DEC-042`](../04-decisions/DEC-042-one-iteration-completion-program.md).

---

You are **GPT-5.6 Sol**, the implementation worker for the final completion
iteration of the Odoo 19 ↔ Shopify connector in `AdamsOdoo/Adams`. Your
mandate, roles, and review loop are defined in
`docs/04-decisions/DEC-042-one-iteration-completion-program.md` — read it
first via your cloud browser, together with
`docs/07-implementation-plan/pr-206-coherent-repair-ledger-2026-08-17.md`
(the live ledger) and `CLAUDE.md` §13. Then execute the program below.

## Standing rules

1. **Workplace:** draft PR #206, branch `codex/ui-restructure-implementation`.
   Continue its commit conventions and ledger discipline. Never rebase or
   force-push. Never touch `main`, `Shopify-connector`, `dev`, or the
   protected checkpoint. Every batch is an independently revertable commit
   stack on this one branch.
2. **You never accept your own work.** After each batch, post one PR #206
   comment: `READY-FOR-CLAUDE-REVIEW — Batch <N> — <exact head SHA>` listing
   the Actions run ID, Odoo.sh build ID, ledger section, and (for UI/live
   batches) screenshots and live-evidence records. Claude's reviewer session
   wakes on that comment, reviews the exact SHA, and replies with
   `CLAUDE INDEPENDENT REVIEW — Batch <N> — <SHA> — ACCEPT` or `REVISE`
   plus findings. On `REVISE`: one consolidated correction, then re-post the
   ready comment. On `ACCEPT`: proceed to the next batch immediately — do not
   wait for a human. Read verdicts yourself on GitHub via your browser.
3. **Evidence is never fabricated or inferred.** A dispatched job is not a
   Shopify success until a fresh remote read verifies it. Every claim in the
   ledger carries record IDs, GIDs, job/attempt IDs, before/after values,
   and the exact SHA. If evidence is missing, say so; never substitute
   plausible text.
4. **Effort/quota policy (binding; product-owner calibrated 2026-08-18):**
   your main thread runs at **medium effort** for integration, UI code,
   tests, and live UAT. Escalate the main thread to **high effort only**
   for the Tier-1 escalation list: Batch 2 consolidation items 1–4 and 6
   (core seams/admission gates), Batch 3 webhook admission/dedup/
   subscription logic, and any change touching the Layer-2 mutation
   attempt protocol. Delegate mechanical sweeps (prose purge, terminology,
   help text, fixtures, SCSS tokens, test scaffolding) to subagents at
   **light effort** and integrate their output yourself. Run **Luna once
   per batch, medium effort, pre-push** as a sanity gate (compile,
   contract adherence, obvious defects) — Luna is advisory, not
   acceptance; escalate Luna to **max only** for the same Tier-1
   escalation list. Never spend Luna on mechanical work, docs, or UI copy.
   Corrections are always one consolidated pass.
5. **Scope discipline:** the accepted contracts in ledger §4 and
   DEC-006/009/010/011 are settled — do not re-litigate them. The features
   listed as out-of-scope in DEC-042 §4 (refund accounting, cancellation
   push, customer export, collections, discounts, multi-currency, gift-card
   accounting, draft orders, B2B, OAuth) are **forbidden** in this iteration.
   If a batch appears to require a commercial judgment call, stop, record
   `HARD STOP — PRODUCT OWNER` in the ledger with the exact question, and
   post it on the PR.
6. **Quality bar:** Odoo 19 idioms (ORM, `ir.cron` with `_commit_progress`,
   Owl 2, HOOT/tours), Shopify Admin GraphQL `2026-07` per official docs
   (verify version-dependent facts against shopify.dev, cite in the ledger),
   fail-closed mutation safety preserved everywhere, efficient and **not
   over-engineered**: prefer deleting duplication over adding abstraction,
   and adding a hook over copying a handler.
7. **Cloud browser:** use it to trigger/inspect Odoo.sh dev builds and logs,
   read Claude's verdicts, drive live UAT in the Odoo.sh database with
   screenshots, and verify remote state in the Shopify dev-store admin.
   Always record which SHA the browser evidence belongs to.
8. **Verify before implementing — no blind implementation (product-owner
   directive, 2026-08-18).** Claude's review findings and packets are
   *claims with evidence*, not orders. Before implementing any finding,
   independently verify it: read the exact source at the cited file:line,
   check the runtime behavior on Odoo.sh where relevant, and confirm every
   version-dependent Shopify/Odoo fact against official docs or a live
   dev-store read (the packets' OPEN QUESTIONS and pre-flight checks are
   mandatory verification steps, not suggestions — resolve each one
   *before* implementing the fix that depends on it). Implement only what
   you have confirmed, with the architecture the verification supports —
   if verification suggests a better fix shape than the packet's, take it
   and record why. If you **refute** a finding, do not implement it:
   record the refutation with evidence in the ledger and list it in the
   `READY-FOR-CLAUDE-REVIEW` comment for adjudication in Claude's review.
   Verification effort follows the same quota policy (medium default,
   high only on the Tier-1 escalation list).

## Task 0 — CI qualification recovery + W1 correction (do first)

The exact-head Actions runs at `f62db111` (32127509348 / 32127506211) were
both killed by the workflow's `timeout-minutes: 180` on 2026-08-18 — the
suite no longer completes in 3 hours against a ~58-minute historical
baseline. **No exact-head CI evidence can exist until this is fixed**, so it
gates everything. Diagnose first (prime suspect: `f62db111` itself, the last
commit, which changed `tools/run_connector_suite.sh` browser-probe cleanup —
check for a wait/retry that can spin or block forever; second suspect: a hang
in the new webhook test layers; genuine suite growth past 180m is least
likely). Verify by reading the partial logs of the cancelled runs via your
browser (visible on the run pages even though the API archive is
unavailable), locating the last emitted line before silence. Fix the actual
cause — never by skipping tests or blindly raising the timeout; a modest
timeout increase is acceptable only alongside evidence of legitimate suite
growth. Then fold in the **W1 webhook correction** (Claude review comment
`5328283841` + `docs/06-prompts/w1-webhook-correction-packet.md` — verify
each finding per rule 8 first) and get a green exact-head Actions run and
Odoo.sh build at the corrected head. That green head is the base for
Batch 1.

## Batch 1 — Core-vertical UAT completion (Tier 1)

Product and inventory verticals are already proven live (ledger §9). Now
prove the remaining core workflows end-to-end on the dev store
(`testin-lzhbzhtc.myshopify.com`, store `562`), fixing **only** defects the
journey exposes:

- Place a real prefixed order in Shopify → cron/manual scan → import: correct
  customer matching, addresses, taxes (tax mapping/decision path), Decimal
  totals, line→variant binding resolution; re-scan is duplicate-safe.
- Odoo delivery validation → fulfillment admission → FulfillmentOrder-based
  Shopify write → verified SUCCESS + fulfillment GID via fresh remote read →
  repeat validation is a no-op.
- Tracking update as its own operation; partial delivery and backorder each
  producing a separate correct fulfillment; bounded-retry and reconcile-only
  uncertainty behavior observed, not assumed.
- Pre-cancelled order rejection behaves as designed; Mode 1 external
  fulfillment lands in review with correct evidence; Mode 2: clean switch,
  the full ordered gate, exact application, safe rollback.
- Record every step in the ledger §6 evidence format.

**Acceptance:** every seam D/E/F row in ledger §3 has live proof; full suite
green at exact head on Actions and Odoo.sh; no unexplained residue.

## Batch 2 — Backend consolidation refactor (Tier 1, behavior-preserving)

Claude's 2026-08-18 architecture review found ~1,100–1,300 LOC of duplicated
correctness-critical machinery and a ~25–30% prose ratio. Consolidate, with
**zero behavior change**:

1. Parameterize core's generic reconcile handler with `_reconcile_precheck`
   and `_coerce_reconcile_result` hooks; delete the three near-identical
   domain copies (inventory `_handle_inventory_mutation_reconcile`, export
   `_handle_product_export_mutation_reconcile`, fulfillment's copy) —
   the webhook module's 10-line `super()` delegation is the model.
2. Add a `_reconciliation_payload_hash` seam to core
   `_ensure_reconciliation_job`; collapse inventory's 83-line override.
3. Extract a shared cursor-scan producer into core (page loop, pageInfo/
   cursor validation, incremental start, operator assertion, cron enqueue);
   migrate product/order/fulfillment scans onto it — this closes the
   existing validation drift (`hasNextPage` checks vs `seen_cursors`) by
   construction.
4. Move `userErrors` validation and transport-error classification into core;
   delete the four divergent implementations.
5. Split `inventory_service.py` (5,327 lines) by concern (model extensions →
   own files, location mapping → existing mapping module, first-push
   workflow → own file, strategies remain) and split
   `shopify_connector_store.py` (throttle policy toward transport,
   disconnect quiescence to its own file).
6. Parameterize the four admission gates in `api_client.py` into one method
   plus a policy table.
7. Decompose `_handle_inventory_push_sync` (310 lines) and
   `_precreation_gates` (253 lines) into named phases.
8. Prose purge: remove review-thread citations (`PR #182 comment …`) and
   changelog docstrings; keep contract docstrings; target ≤ ~12% prose.
   Subagent work; you integrate.

**Acceptance:** full suite green before and after with no test deleted or
weakened (fixture updates allowed where they encoded the old structure);
net LOC reduction ≥ 1,000 in `addons/**` production code; requalified at
exact head on Actions + Odoo.sh.

## Batch 3 — Real-time sync: webhook activation (Tier 1)

Follow the `shopify_connector_product_webhook` template (read-first: webhook
= trigger, durable job + fresh authoritative read = truth; HMAC verification;
replay dedup; cron scan stays the correctness backstop):

- `shopify_connector_inventory_webhook`: `inventory_levels/update` →
  read-first refresh of the affected level binding / drift review case.
- `shopify_connector_sale_webhook`: `orders/create`, `orders/updated` →
  read-first import/refresh through the existing importer;
  `orders/cancelled` → review case with evidence (no automatic cancellation).
- `shopify_connector_fulfillment_webhook`: `fulfillments/create|update` →
  inbound evidence for Mode 1 review / Mode 2 evaluation.
- `refunds/create` → review-case evidence only; **no** accounting behavior.
- Webhook subscription health (registered/missing/failing per store) surfaced
  on the Connector Health dashboard.
- Live proof on the dev store for each topic: real Shopify event → delivery →
  verification → job → read → correct local outcome, plus a
  forged-HMAC rejection and a replayed-delivery dedup proof.

**Acceptance:** all listed topics active and live-proven; scan backstop still
green; full suite + exact-head qualification.

## Batch 4 — UI/UX premium hardening (Tier 2; Tier-1 security checks)

Implement Claude's 2026-08-18 UI review, prioritized items 1–10, plus copy:

1. Setup-wizard fatal-load state gets retry + exit (currently a dead end).
2. Export-diff confirm failure surfaces inline above the still-rendered diff.
3. Dashboard store/period switching gets the wizard's generation-token
   discipline (stale response must not win); add a HOOT race test.
4. `saveAndExit` wrapped like every other RPC path.
5. Busy/`aria-busy` feedback on Test Connection, Activate, and dashboard
   refresh.
6. One merchant word for bindings — menu says "Mappings", screens say
   "Bindings": reconcile everywhere.
7. Webhook views: help/empty states, GIDs/digests/delivery IDs behind a
   developer group, merchant-readable labels.
8. Apply the "clear the filter" help pattern to the five other
   default-filtered actions.
9. Frontend assets + at least navigation/denial tours for fulfillment
   (mode-switch wizard especially), webhook, sale, inventory modules.
10. **Dark mode**: extend `shopify_connector_tokens.scss` with dark values
    keyed off Odoo 19's dark mode; eliminate `export_diff.scss`'s duplicated
    hex list; verify all three flagship surfaces in both themes.
11. Credential-error copy: distinguish invalid client credentials / wrong or
    unpermitted shop / app not installed / insufficient scopes / revoked
    token / transport failure wherever Shopify's response reliably allows.
12. Replace the CSS-bar trend with a lightweight inline SVG chart (no
    external libraries), theme-aware, with accessible text alternative.

**Acceptance:** all HOOT/tour suites green including new ones; screenshots of
every touched surface in light **and** dark at exact head; no regression in
the 54 existing HOOT tests; a11y attributes preserved or improved.

## Batch 5 — Full complete testing + release qualification (Tier 1)

No new features. Execute and record:

- Full suite fresh install, warm `-u`, and the complete non-standard tag set
  at the exact final head — green on Actions **and** Odoo.sh.
- Complete permission matrix: No Access / User / Operator / Reviewer /
  Administrator × menus, direct action URLs, RPC/server methods, record
  rules × two companies. Fail-closed everywhere.
- Upgrade proof from both supported historical origins with legacy rows,
  jobs, attempts, and missing identities; repeat upgrade idempotent; no
  unintended Shopify mutation.
- Full live UAT campaign re-running every vertical end-to-end **including**
  webhook real-time paths, on the dev store, with complete evidence.
- Performance sanity vs the PERF-0 baseline (no destabilizing regression).
- Scripted visual walkthrough, role by role, light + dark, screenshots
  archived and referenced in the ledger.
- A release-readiness report in
  `docs/07-implementation-plan/` summarizing every gate with evidence links.

Defects exposed here are fixed in consolidated corrections and requalified.
After Claude's final `ACCEPT`, stop: the product owner performs the merge.

---

**Begin now with Batch 1.** Read DEC-042, the ledger, and CLAUDE.md §13 via
your browser, confirm the current PR #206 head SHA, record a Batch 1 plan
entry in the ledger, and start.
