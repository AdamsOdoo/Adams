# Release-Readiness Execution Plan (MVP)

> **Status: Proposed for ChatGPT review. NOT accepted. Nothing here is
> executed; the merged `mvp-release-readiness-checklist.md` remains the
> item-level checklist — this plan sequences and operationalizes it.**
> Produced 2026-07-10 (AR-042 candidate); **revised 2026-07-11** per
> the PR #148 control-room review (comment `4942966937`): §2.3
> uninstall corrected to the DEC-030/LC-1 lifecycle (the prior text
> contradicted the merged FK mechanics), §2.7 now requires the
> measured performance-budget table, §2.8 adds SEC-1 suites + the
> DEC-028 point-2 production-entry evidence rows, §2.5/§2.14 updated
> for 013B/015B and the corrected D-012-7. Execution is
> **[External validation required]** end-to-end (runtime + live store
> + human operator).

## 1. Release definition

MVP release = the Full edition (six modules, ARCH §1) at a pinned
version set, runtime-green, UAT-exited (final-mvp-uat-plan §6),
distributed under DEC-023 branch A within the DEC-027 pilot scope.
Lite is released implicitly (subset of the same artifacts).

## 2. Execution sections (each produces evidence into the checklist run)

1. **Installation:** clean-database install of Lite; clean install of
   Full; install on a database with existing products/partners/orders
   (brownfield — matching flows exercised); every install: zero
   errors/warnings attributable to connector modules in the install
   log (docutils/RST rule from the merged validation records applies);
   demo data — **none shipped** (decision: connector modules carry no
   demo data; UAT fixtures are operator-seeded — avoids demo bindings
   against nonexistent stores).
2. **Upgrade:** module upgrade (`-u`) across the release's own commit
   range on a populated database; settings/checkpoint fields additive
   (no migration scripts expected for MVP — any task introducing one
   invalidates this line and adds its own tested migration).
3. **Uninstall/downgrade (REVISED 2026-07-11 — the prior text
   contradicted the merged FK mechanics; review item 9):** the
   data-survival matrix of
   `../03-architecture/module-lifecycle-uninstall-design.md` §5
   (proposed DEC-030) walked exactly: flags-off path (everything
   survives); pre-uninstall export step executed and archived;
   Full-module uninstall path **via the merged Task LC-1 mechanism**
   (business data survives; job/log history survives with
   `historic_domain_job` retyping and `original_job_type` preserved;
   binding/mapping tables lost per platform semantics — screenshot
   evidence of each); reinstall re-match (deterministic keys re-bind;
   manual matches redone or re-imported from the export). LC-1 merged
   is a prerequisite for this section's execution.
4. **Permissions:** UAT scenario 24 evidence + ACL-matrix suites green.
5. **Documentation:** operator install/setup guide (incl. the
   Task 012 confirmation-policy choice and its stock consequences,
   and the 013B baseline-before-first-push onboarding order); the
   DEC-028 Rung-1 point-2 production-entry criteria list (the guide
   carries the same list the Go/No-Go checks); known-limitations page
   (§2.14); the DEC-030 uninstall consequences + export procedure;
   the 60-day order-window note; the PII export/deletion operator
   procedure (SEC-1 D-SEC1-6); troubleshooting (reading the Error
   Center; retry semantics).
6. **Support diagnostics:** the readiness check + job/log export
   (existing surfaces) documented as the support bundle; no new code.
7. **Performance (REVISED 2026-07-11 — budgets exist before
   implementation, review item 10; PERF-1 owns throughput, re-review
   `4945129824` item 5):** the full
   `../03-architecture/performance-budgets.md` table measured
   (concurrency plan §13.2 + UAT scenarios 27/28/34 + the packet
   benchmarks are the measurement vehicles); **PB-19 (≥ 600 jobs/hour)
   is delivered by Task PERF-1 — core queue throughput calibration —
   merged before the performance UAT scenarios, because the accepted
   5-min × batch-20 dispatch defaults cap at ~240/h**; every row
   measured-pass, or carrying an explicit dated ChatGPT waiver —
   silence is not a waiver; release hardening (Area 8) owns any
   residual tuning.
8. **Security (REVISED 2026-07-11):** credential redaction suite
   green (existing); masked-entry/no-read-back re-verified in UI;
   no-encryption-claim copy audit (grep of views/copy decks); PII
   redaction lists in place (Task 012 / W1); **Task SEC-1 suites
   green** (transition matrix, protected-field guards, binding
   override audit, PII field-groups, retention sweep — the negative
   RPC matrix re-run on the release build); sudo inventory audit =
   exactly the named sanctioned elevations (2 merged + D-013-5's
   third if accepted + the itemized SEC-1 write-site elevations);
   **DEC-028 Rung-1 point-2 production-entry evidence rows completed
   per receiving deployment** (encryption at rest; backup encryption
   or documented equivalent; staff/access restrictions;
   retention/deletion policy; incident/access governance) — each
   evidenced, reviewed at Go/No-Go; a deployment missing a row does
   not receive production customer data.
9. **API versioning:** store pinned 2026-07; the quarterly re-check
   procedure (MBQ-52) recorded with the next check date (2026-10
   release: `FULFILLMENT_NOT_REQUIRED` enum + `ITEM_NOT_STOCKED_AT_
   LOCATION` removal are the named watch items — captures §9);
   fall-forward behavior documented for operators.
10. **Webhooks (MVP tail):** W1+W2 merged and their subscription
    self-healing verified live; if ChatGPT descopes W1/W2 from the MVP
    release, DEC-003's C-SYNC-01/02/03 rows must be explicitly
    re-scoped by that decision (flagged — this plan does not make that
    call).
11. **Shopify app-review readiness:** **Phase 2+ (B-1)** — the DEC-028
    Rung-2 ladder + compliance webhooks (W5) + App Store requirements
    are pre-listed for that future gate; explicitly NOT an MVP release
    item (RA-003 unchanged).
12. **Odoo Apps packaging (if ChatGPT chooses that channel):** six
    listings with dependency metadata per DEC-029; icons/descriptions
    from the copy pass; LGPL-3 declared; not required for branch-A
    delivery.
13. **Rollback:** per-module single-PR revert map (each task packet's
    rollback note aggregated); database restore procedure for a failed
    production install (operator doc); Shopify-side: no automatic
    un-doing — documented manual cleanup list (delete test
    fulfillments, etc.).
14. **Release notes & known limitations (REVISED 2026-07-11):**
    generated from the AR log rows of the release range; limitations
    at minimum: 60-day order window; same-currency-only;
    duties/divergent orders skipped by policy;
    single-fulfillment-location; no refunds/payouts/B2B/Markets;
    media: basic image export only (015B — gallery/video are the
    named 010C/015C candidates); uninstall: binding/mapping tables
    lost on physical uninstall (DEC-030 matrix — export procedure
    documented); concurrency proof status (whatever OP-22's state is
    at release — stated honestly); webhook posture. (The former
    "no media export" and "Lite orders gain no pickings" lines are
    deleted — superseded by Task 015B and the corrected D-012-7.)

## 3. Go/No-Go gate

ChatGPT holds the release act. Inputs: checklist run with evidence per
section; UAT exit record; open-register review (no open S1/S2, TD
register clean or explicitly accepted); the §2.10 webhook scope
confirmation; DEC-027 pilot-scope confirmation for the receiving
customer(s). The release act, like every gate act, is a distinct
recorded ChatGPT decision.
