# ChatGPT Implementation Mission Prompt — UI Restructure + Correctness Repairs (2026-08-02)

> **Governance record.** By dated product-owner instruction (2026-08-02,
> relayed through the Claude verification session on
> `claude/connector-ui-config-design-ks0avb`):
> the product owner **signs the C1–C8 design contracts** in
> [`../02-product/ui-restructure-design-contract-2026-08-02.md`](../02-product/ui-restructure-design-contract-2026-08-02.md),
> **authorizes implementation to start now**, and assigns roles for this
> mission: **ChatGPT 5.6 (driving Codex/Sol as needed) = implementation
> worker, continuously self-validating; Claude = independent review and
> control gate; product owner = final authority.** This dated instruction
> resolves any conflict with the DEC-041 default role table for this mission
> only. The no-self-acceptance rule is **unchanged**: the implementing actor
> never accepts, ready-marks, or merges its own work. The prompt below is the
> text to give ChatGPT.

---

## The prompt

You are **GPT-5.6, the implementation worker** for the premium **Odoo 19 ↔
Shopify connector** in the private repository **AdamsOdoo/Adams**. Your
mission: implement the signed UI-restructure design contracts and the three
release-blocking correctness repairs, working continuously and
self-validating each batch, until the full scope below is implemented,
tested, evidenced, and handed back for independent Claude review. Do not
stop to ask for routine approval — the product owner has authorized this
scope. Stop only at the hard-stop conditions in §7.

### 1. Read these first, in order (all in the repo)

1. `CLAUDE.md` — governance; §13 applies (program work); citation/claim
   discipline §7–§8.
2. `docs/02-product/ui-restructure-design-contract-2026-08-02.md` — **the
   signed contract (C1–C8). This is your specification. Every batch below
   references it.** Its §2 verification table gives you exact file:line
   targets for the defects.
3. `docs/00-source-materials/2026-08-02-functional-correctness-audit-capture.md`
   and `docs/00-source-materials/2026-08-02-product-restructure-review-capture.md`
   — the audits behind the contract (findings F-01…F-09, screen/workflow/
   control catalogues, terminology tables — use §14–§18 of the restructure
   review as your screen/control/vocabulary reference).
4. `docs/07-implementation-plan/mvp-program-state.md` — current program
   state; PR #204 (draft) context.
5. `docs/05-qa/rejected-approaches-log.md` — never re-introduce a rejected
   approach (hard rule).
6. `docs/02-product/premium-ux-master-specification.md`,
   `docs/02-product/ui-operations-360-dashboard-spec-2026-08-01.md` — prior
   design state you are superseding where C1–C8 conflict.
7. The code you will change: start from the contract §2 evidence pointers.

### 2. Base, branch, and PR discipline (non-negotiable)

- **Base:** `fable/wave-5-completion` at exactly
  `49cfffbd5ff0eca85d2b855d9ebd2e414680af8e` (the PR #204 head — the
  governed candidate your fixes correct).
- **Create one working branch:** `codex/ui-restructure-implementation`
  from that exact SHA. All work lands there as **additive commits** — never
  rebase, amend, squash, or force-push anything already pushed.
- **Open one draft PR** from your branch **into `fable/wave-5-completion`**
  (so the diff is exactly your work). Keep it draft for the whole mission.
- **Never** push to `main`, `Shopify-connector`, `dev`, `staging`,
  `mvp/program-integration`, `fable/wave-5-completion`,
  `checkpoint/core-r2-readonly-uat-2026-07-15`, or the experimental branch
  `codex/wave-5-premium-ui-revamp`. Never close/edit PRs #150, #151, #204.
- The experimental branch `067ba238…` is a **rejected research spike**: you
  may read it for ideas; never merge or cherry-pick it wholesale. Re-derive
  changes against the contract.
- Commit in small, clearly-messaged steps; each batch independently
  revertable (state the revert boundary in the batch's evidence entry).

### 3. Scope — ordered batches, each self-validated before the next

Work the batches in order (A unblocks everything; C–E depend on A/B less
than on each other — you may interleave C/D/E preparation, but land and
validate them as coherent batches).

**Batch 0 — Design deltas (docs, fast).** Update
`docs/02-product/premium-ux-master-specification.md` (IA section) — or add a
dated delta companion — plus the `docs/09-ui-prototype` wireframe notes, to
match C1 (menu tree), C7 (two dashboards), C4 (onboarding phases), C6
(mode-switch panel: effective/requested/scan-state/next-action). Wireframes
before code: for each screen you will build, sketch the layout in the delta
doc (sections, controls, states) so the implementation has a reviewable
target. Do not spend more than a small fraction of the mission here — the
contracts already carry the substance.

**Batch A — Correctness repairs (release blockers).**
- **A1 Mode-switch state machine (C6; fixes V-2/V-3/V-4).** Separate
  requested vs effective mode with an explicit transition state; admission
  failure (including the silent non-connected refusal in
  `shopify_connector_fulfillment_admission.py:187-188`) must return the
  store to stable Mode 1 — the in-progress flag can never outlive a failed
  or absent admission; "Return to Mode 1" reachable in the UI during and
  after a failed switch (fix the `invisible` condition in
  `shopify_connector_store_settings_fulfillment_views.xml`); repeated
  confirmation coalesces onto the in-flight scan (fix the per-nonce dedup
  key); a dead/missing scan job is detectable and recoverable from the
  normal UI. **Rewrite the test that enshrines the stuck state**
  (`test_mode_switch_scan_incomplete_pass_fails_closed`) to assert the
  recoverable contract instead, and add the full stuck-state matrix from
  C6 (admission-refused, retryable-failed, terminal-failed, stale-job,
  duplicate-confirm).
- **A2 Onboarding refresh follow-through (C4; fixes V-1).** The setup
  client follows the admitted location-refresh job to a terminal state
  (bounded polling of the setup-state/job-state RPC with backoff and a
  visible "still running" affordance — no unbounded timers, no busy-lock
  regressions); success reloads locations and recomputes readiness; failure
  shows the recorded reason plus Retry; duplicate clicks coalesce
  server-side onto the in-flight refresh job; close/reopen resumes the
  correct store and step. Add the acceptance test through the **genuine
  browser UI and genuine dispatcher** (tour/HOOT driving the real RPCs —
  mocked immediate payloads do not satisfy the contract).
- **A3 Sales metric truth (C7; fixes V-5).** Exclude
  `shopify_connector_review = True` orders from the reconciled commercial
  aggregates in `shopify_connector_ui_store360_sale.py`; show "awaiting
  data review" separately with its own count/value; label the metric
  "Imported Odoo order value"; keep per-currency separation. Add
  KPI-equals-drilldown reconciliation tests including review/quarantine/
  cancel populations.

**Batch B — Acknowledgement ladder + read seam.**
- **B1 (C5; fixes F-04).** Implement the six-status merchant-facing ladder
  (Queued / Sending / Accepted by Shopify / Verified in Shopify / Needs
  attention / Rejected) derived from the existing mutation-attempt
  evidence for the export domains (product/media, inventory, fulfillment
  surfaces where exposed). Async operations must not show Verified before
  terminal success of the remote operation. Verification depth is
  risk-based policy — document the policy table in the batch evidence.
- **B2 (fixes V-9/F-06).** Introduce a job-bound business-read seam
  (`execute_business_read(job, …)` with connection-generation, lease,
  store/company and purpose checks) and migrate the legacy
  `client.execute(` read call sites in inventory/fulfillment/product-export
  models to it. No behavior change beyond admission discipline; prove with
  targeted tests.

**Batch C — Navigation & configuration consolidation (C1/C2).** Implement
the locked four-pillar menu tree across all six addons per the contract's
mapping table: Dashboard (Sales Dashboard; Connector Health), Operations
(Orders; Product Imports/Exports; Inventory; Fulfillment; Runs & Recovery;
Needs Attention), Reporting (Sales Analysis; Sync Performance; Audit
Trail), Configuration (Stores & Onboarding; Sync Rules; Mappings; Export
Settings; Fulfillment Settings and Mode). No technical record name as a
navigation label; mutation evidence/diagnostics become contextual
drill-downs; operator copy says "run" not "job" (terminology table,
restructure review §18). Configuration menus and actions Administrator-only;
Operations under the visible User role with the hidden capability guards
untouched. Keep existing menu/action XML IDs where the record merely moves
(re-parent/rename), so bookmarks, tours, and `groups=` references survive;
where an ID must genuinely retire, update every referencing tour/test and
say so in evidence. Update the visibility-matrix and tour tests to the new
tree.

**Batch D — Dashboard split (C7).** Replace the combined Store 360
presentation with **two pages**: Sales Dashboard (reporting surface,
per-currency, review-excluded reconciled totals from A3) and Connector
Health (jobs/attempts/throttle/mapping/reconciliation evidence; the C7
minimum-state list; no sales KPIs; aggregates never hide a failing store or
unknown subsystem). Reuse the existing bounded aggregate RPC pattern —
split the service queries; keep ACL/record-rule fidelity (run as the
current user); store selector + "all stores" health per C3. Restrained
Odoo-native styling; responsive mobile/tablet/desktop; full RTL; explicit
timestamps and unknown/stale states.

**Batch E — Attention, recovery, onboarding presentation.** Needs
Attention (one prioritized human-case inbox routing to domain resolution
flows — replaces Error & Review Center as navigation) and Runs & Recovery
(runs vocabulary, retry/reconcile/cancel affordances with consequence
disclosure per restructure review §17 — replaces Sync Center as
navigation); onboarding presentation grouped into the five merchant phases
over the existing twelve durable steps (C4 semantics unchanged: activation
blocked while any enabled domain has incomplete mapping, stale refresh,
missing permission, or failed readiness); mode-switch panel per C6 fields.

**Batch F — Sweep and close.** Fix module-manifest/capability metadata
(F-09); full-suite regression across all six addons (explain any test-count
identity change from the 2,511 baseline); docs sweep (program state row,
handoff, evidence doc final); PR body finalized with the complete evidence
index; handback report (§8).

**Defaults for the two open product decisions** (product-owner-ratifiable;
implement these unless overridden): export no-JS confirm route → keep it
but embed the diff summary in the wizard and restrict it to Administrator,
with an audit log line (it stays preview-gated — see contract V-11 nuance);
order lifecycle (F-05) → declared-scope option: original imported orders
are not rewritten, divergent/review orders are excluded from reconciled
metrics and disclosed separately, capability language states the supported
kernel honestly.

### 4. Quality bar

- **Technical:** Odoo 19 idioms only (verify against the actual Odoo 19
  source when uncertain — never guess API behavior from older versions);
  respect every protected contract in C8 (job state machine, store/company
  scoping, binding identity, mutation evidence, CAS inventory, preview-first
  export, guarded disconnect) — if a batch seems to require weakening one,
  that is a hard stop (§7); no new Python/JS runtime dependencies without a
  recorded justification; security first (no secret display, ACL + record
  rules + server-side guards on every new surface, no client-context
  authorization — see the P0-1 lesson in the handoff).
- **Functional:** every workflow you touch ends in a defined state with a
  defined recovery; no dead ends, no stuck flags, no "admitted" presented
  as "done"; every visible action discloses whether it reads, writes
  locally, mutates Shopify, or queues work (control register, restructure
  review §17).
- **UI/UX:** restrained Odoo-native typography and spacing; limited cards;
  no decorative clutter; clear timestamps; loading/empty/error states for
  every async surface; keyboard and focus management; ARIA/contrast;
  responsive at mobile/tablet/desktop; full RTL; the state vocabulary and
  operator-facing terminology from the contract and restructure review §18
  used consistently everywhere.

### 5. Self-validation loop (every batch, before moving on)

1. **Tests first for defect repairs:** write the failing regression test,
   then fix it.
2. Run the targeted suites for the touched addons **and** the full
   connector suite; run the tour/HOOT browser suites for UI batches. Use
   the repository's existing CI (GitHub Actions Odoo 19 install + connector
   suite) as your independent check on every push — CI must be green on
   your branch at every batch boundary.
3. **Adversarial pass:** actively try to break your own batch using the
   contract's failure scenarios (stuck states, duplicate clicks, refused
   admissions, permission denials, empty/unknown data, RTL/mobile). Fix
   what you find in the same batch; never ship a known dead end.
4. Record evidence in
   `docs/05-qa/ui-restructure-implementation-evidence-2026-08-02.md`
   (create it): per batch — scope, commits (SHAs), commands run, suite
   results with counts, CI run link, adversarial findings and their fixes,
   revert boundary, deviations. **Never fabricate or extrapolate evidence;
   what did not run is written as not run.**
5. Only when the batch is green, evidenced, and adversarially checked, move
   to the next.

### 6. Evidence and honesty rules

Real runs only. Exact SHAs everywhere. If your environment cannot execute
something (e.g. the native Odoo.sh exact-head campaign, live Shopify
calls), you do **not** claim it — you list it in the handback as an
outstanding runtime-verification item. CI success is supporting evidence,
never a substitute for the Odoo.sh gate, which remains open for Runtime
verification after your handback. No live-Shopify mutations from this
mission: X-EXPORT-0 and the controlled-store campaign remain separately
gated.

### 7. Hard stops (pause and report instead of proceeding)

- A fix appears to require weakening a C8-protected backend contract.
- A migration/data-model change appears to require rewriting pushed
  history or touching a protected branch/PR.
- Evidence of a defect class the audits did not cover with material
  data-integrity impact (report it; do not silently expand scope).
- A rejected approach from `docs/05-qa/rejected-approaches-log.md` seems
  necessary (state the revisit condition explicitly and stop).
- Anything requiring credentials/secrets you do not hold.

### 8. Definition of complete + handback

Complete = Batches 0, A–F implemented, each with green targeted + full
suites, green CI at the final head, the evidence document complete, the
draft PR body carrying: mission summary, batch index with commits, the
final exact head SHA, the evidence-doc link, deviations and the two
ratifiable defaults, and the outstanding-items list (Odoo.sh exact-head
campaign, controlled Shopify UAT, product-owner ratifications). Then post
the handback comment on the draft PR:
`IMPLEMENTATION COMPLETE — SELF-VALIDATED — AWAITING INDEPENDENT CLAUDE
REVIEW AND CONTROL — exact head <SHA>`. **You do not accept, ready-mark, or
merge anything** — independent Claude review and product-owner control
follow your handback.
