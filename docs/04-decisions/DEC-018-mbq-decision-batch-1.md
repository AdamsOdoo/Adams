# DEC-018 — MBQ Decision Batch 1

> **Accepted decision record** for the premium **Odoo 19 ↔ Shopify
> Connector**, prepared after ChatGPT accepted
> [`DEC-017`](./DEC-017-master-blueprint-implementation-planning-bridge.md)
> (Master Blueprint Part E — Implementation-Planning Bridge) on
> **2026-07-04**, and itself **accepted by ChatGPT on 2026-07-04** — Batch 1
> **except MBQ-62**, which ChatGPT explicitly split into its own dedicated
> follow-up decision record rather than deciding here. Companion documents:
> [`../03-architecture/master-blueprint-open-questions.md`](../03-architecture/master-blueprint-open-questions.md),
> [`../03-architecture/master-blueprint-implementation-planning-bridge.md`](../03-architecture/master-blueprint-implementation-planning-bridge.md).
> Companion review-log entry:
> [`../05-qa/architecture-review-log.md`](../05-qa/architecture-review-log.md)
> (**AR-015**, Accepted by ChatGPT via DEC-018).

## Status

- **Accepted by ChatGPT on 2026-07-04.**
- **Accepted Batch 1 except MBQ-62** — ten of the eleven in-scope rows
  (MBQ-06, MBQ-08, MBQ-17 posture, MBQ-33, MBQ-34, MBQ-41, MBQ-45
  mapping/surface split, MBQ-52 policy, MBQ-54 posture, MBQ-60) are now
  **Decisions**, not recommendations; **MBQ-62 is explicitly not decided**,
  routed to its own dedicated follow-up DEC per §4's strict analysis and §8's
  recommendation, which ChatGPT accepted.
- **Documentation-only.** This acceptance creates or modifies no Odoo
  module, model, view, controller, security file, manifest, test,
  migration, or CI file.
- **Does not authorize implementation.**
- **Does not open the implementation gate.**
- **Does not create implementation tasks.**
- **Implementation remains blocked.**
- **Built after DEC-017 acceptance** (2026-07-04), starting point PR #80
  merge commit `403d17fc16c6854b0bd9f3ce3161ff61cc0e1570` into
  `Shopify-connector`.
- This acceptance patch **does** apply the ten accepted rows' register
  wording to `master-blueprint-open-questions.md` (§5 below, every prior
  undated placeholder now reads the actual acceptance date, **2026-07-04**).
  **MBQ-62, MBQ-64, and MBQ-65 are unaffected** — MBQ-62 remains open with
  only a split-note added; MBQ-64/MBQ-65 are untouched.

## Acceptance

**ChatGPT accepted Batch 1 except MBQ-62 on 2026-07-04.**

**Accepted decisions:**

1. **MBQ-06** — readiness-check essential-vs-warning split accepted.
2. **MBQ-08** — disconnect revokes/removes credentials and disables
   sync/webhook enqueue, while preserving store, bindings, jobs, logs, audit
   records, mapping history, and error history; reconnect is explicit and
   audited.
3. **MBQ-17** — reconciliation posture accepted: per-store/per-domain with a
   configurable conservative default; exact intervals/batch sizes remain
   implementation planning.
4. **MBQ-33** — first-push guard granularity accepted: no coarser than store
   + mapped Odoo Location ↔ Shopify Location pair + product/variant binding;
   batched UI allowed only if each unit is individually recorded.
5. **MBQ-34** — review-then-apply accepted as the Phase 1 default for
   ongoing inventory writes; auto-apply deferred behind a future explicit
   decision/feature flag.
6. **MBQ-41** — global/per-store notification default accepted for Phase 1,
   default off; per-order override deferred unless already exposed by
   standard Odoo without added connector UI.
7. **MBQ-45** — the four accepted roles map 1:1 to four Odoo groups in Phase
   1; one shared, role-gated surface accepted; exact access rows/XML IDs
   remain implementation planning.
8. **MBQ-52** — stable Shopify GraphQL Admin API version pinning policy
   accepted; pin per connector release/store config, surface API
   health/deprecation warnings, periodic review; exact upgrade mechanics
   remain implementation planning.
9. **MBQ-54** — disable-not-uninstall posture accepted; destructive
   domain-module uninstall is not a normal merchant-facing Phase 1
   operation; exact guard/disclosure remains implementation planning.
10. **MBQ-60** — fulfillment tracking dependency posture accepted;
    `stock_delivery`/`delivery` dependency required for tracking write-back;
    if absent, tracking write-back is readiness-blocked/disabled, not
    silently degraded.

**Explicitly not accepted as decided:**

- **MBQ-62** — split to a dedicated follow-up DEC, per §4's strict analysis
  and §8's recommendation, both accepted by ChatGPT.
- **MBQ-64** — excluded (separate currency/webhook residual decision
  sprint).
- **MBQ-65** — excluded (separate currency/webhook residual decision
  sprint).
- **Any other MBQ not named above** — unchanged, exactly as open as before
  this acceptance.

**What this acceptance does NOT authorize:** no implementation; no code; no
Odoo modules; no implementation-gate opening (a separate, explicit ChatGPT
act per
[`../05-qa/quality-feedback-loop.md`](../05-qa/quality-feedback-loop.md)
§10, not performed here); no implementation-task creation; no change to
DEC-003 through DEC-017; no weakening of accepted Master Blueprint Parts
A–E.

## 1. Purpose

Master Blueprint Part E (`master-blueprint-implementation-planning-bridge.md`
§4), accepted as a **routing/sequencing plan only** by DEC-017, identified a
cluster of implementation-blocking open questions it calls the **"ChatGPT
batch"** — MBQ-06, MBQ-08, MBQ-17 (posture), MBQ-33, MBQ-34, MBQ-41, MBQ-45
(surface split), MBQ-52, MBQ-54, MBQ-60, and MBQ-62 — each already carrying a
recommendation from an accepted Master Blueprint part (mostly DEC-013/
DEC-015) that ChatGPT has not yet decided. Part E's own reading (§4, "the
single largest lever") is that deciding this batch costs ChatGPT one review
pass, not new research, and unblocks the first `core`/`inventory`/
`fulfillment` implementation tasks once the gate itself is separately opened.

This document turned that plan into a **small, controlled, evidence-linked
decision packet**: for each of the eleven MBQs above, it stated the evidence
already on record, the options the evidence supports, a recommended decision,
and the risk of getting it wrong. **ChatGPT has now accepted ten of those
eleven rows as Decisions** (§"Acceptance" above; §5's register wording is
applied, not merely drafted) — **MBQ-62 remains a recommendation, not a
decision**, per the strict analysis in §4 and the explicit split ChatGPT
accepted in §8. This acceptance does not widen MVP scope beyond
DEC-003/DEC-007, does not touch DEC-003 through DEC-017, and does not open
or approximate the implementation gate — that remains a separate, explicit
ChatGPT act per
[`../05-qa/quality-feedback-loop.md`](../05-qa/quality-feedback-loop.md) §10,
unaffected by this document under any outcome.

MBQ-64 and MBQ-65 remain explicitly **out of scope** for this batch (§6).

## 2. Sources reviewed

- [`../03-architecture/master-blueprint-open-questions.md`](../03-architecture/master-blueprint-open-questions.md)
  — read in full; this is the register every proposed decision below is
  checked against, and the source of every MBQ's current-status wording
  quoted in §4/§5.
- [`../03-architecture/master-blueprint-implementation-planning-bridge.md`](../03-architecture/master-blueprint-implementation-planning-bridge.md)
  (Part E) — read in full, specifically §3 (gate checklist), §4 (MBQ decision
  plan / "ChatGPT batch"), and §12 (open risks).
- [`DEC-017`](./DEC-017-master-blueprint-implementation-planning-bridge.md) —
  read in full; confirms Part E's acceptance status and that no ChatGPT-batch
  item was decided by it.
- [`../03-architecture/master-blueprint-core-substrate.md`](../03-architecture/master-blueprint-core-substrate.md)
  (Part A) — read directly, specifically §B.1 (store/disconnect), §B.3
  (API version/health), §D.2 (fixed job-source enum), §E.1–§E.6 (setup
  wizard / readiness checks), §I.3–§I.4 (feature-flag mechanism / safe
  enable-disable), and §J.1–§J.2 (roles/groups blueprint).
- [`../03-architecture/master-blueprint-inventory-fulfillment.md`](../03-architecture/master-blueprint-inventory-fulfillment.md)
  (Part C) — read directly, specifically §A.5 (first-push guard), §A.7
  (ongoing apply-mode / sync triggers), §B.5 (tracking-field source /
  `stock_delivery`), §B.6 (notification-UI posture), and the Part C MBQ
  status table.
- **DEC-012, DEC-013, DEC-015, DEC-016** — reviewed as directly quoted and
  cited in
  [`../05-qa/architecture-review-log.md`](../05-qa/architecture-review-log.md)
  (AR-009 through AR-013 rows and their acceptance-patch notes, read in
  full) and in the open-questions register's own DEC-013/014/015/016/017
  acceptance-patch blockquotes (§2 above) — **not** re-read as standalone
  files in this session; every claim attributed to one of these four DECs
  below is paraphrased from that quoted acceptance-note text, not from a
  fresh reading of the DEC file itself. Flagged here per `CLAUDE.md` §7 so
  the citation trail is precise, not implied to be more direct than it is.
- [`../05-qa/rejected-approaches-log.md`](../05-qa/rejected-approaches-log.md)
  — checked (row IDs/titles only, via targeted search) to confirm no
  proposed decision below re-introduces RA-008 (blind first-inventory-push),
  RA-009 (hidden/default-on fulfillment notification), or any other binding
  rejected approach. None of the eleven proposed decisions below does.

No external (Shopify/Odoo official-doc) research was performed this session,
per the scope instruction to avoid external research unless absolutely
necessary — every proposed decision below rests on evidence Master Blueprint
Parts A–E and DEC-003 through DEC-017 have already established and cited.

## 3. Decision principles

Every recommendation in §4 was checked against these principles before being
proposed:

- Preserve safety over automation.
- Prefer review-first defaults where irreversible external writes are
  involved.
- Do not destroy audit history.
- Do not widen MVP beyond DEC-003/DEC-007.
- Keep one shared surface, role-gated, not forked.
- Use Odoo-native mechanisms where possible.
- Keep implementation gate closed until separate approval.

## 4. Proposed decisions table

**Reading this table:** "Proposed decision" is a **recommendation**, not a
decision — per `CLAUDE.md` §8, every row stays classified as Recommendation
until ChatGPT accepts DEC-018, at which point it becomes a Decision. No row
below invents new architecture; each proposed decision adopts, verbatim or
near-verbatim, a direction Master Blueprint Parts A/C already put on the
table and explicitly left for ChatGPT to decide (per Part E §4's own
"ChatGPT batch" framing) — except MBQ-62, which this table declines to force
(see its own row and §4's closing note).

| MBQ | Proposed decision | Why | Affected scope | Remaining implementation detail | Risk if wrong | Register impact if accepted |
| --- | --- | --- | --- | --- | --- | --- |
| **MBQ-06** | Essential (blocking) readiness checks: credential validity / test-connection result; required Shopify scopes granted; Shopify API-version health; store identity (shop domain) confirmed; `web.base.url` / externally reachable base URL; webhook HMAC secret configured (only if webhooks are enabled for the store); cron/queue health (worker present, threads available); at least one mapped Shopify Location where an inventory/fulfillment domain is enabled; domain feature flags intentionally (not silently) enabled. All other candidate checks are nice-to-have: they **warn**, they never block setup completion. | Part A §E.1 step 6 and §E.3 already list this exact candidate-check set and explicitly flag only the essential-vs-nice-to-have split as **[Open question — MBQ-06]**; this recommendation fixes that split without adding or removing any candidate check. | Setup wizard readiness surface (Part A §E), dashboard connection-health card (§F). | Exact copy/wording (MBQ-22); exact XML IDs (MBQ-03); exact cron/queue-health thresholds. | Too strict blocks a legitimate store (e.g. requiring an HMAC secret when webhooks are disabled for that store); too lax lets a store reach "connected" that silently fails on its first real sync — named directly as MBQ-06's own "why it matters." | MBQ-06 → **Accepted by ChatGPT via DEC-018** — essential-vs-nice-to-have split fixed as at left; exact copy/XML IDs/thresholds remain Implementation planning. |
| **MBQ-08** | Disconnect revokes/removes stored credentials and disables sync/webhook enqueue (no new business job is enqueued or executed for that store while disconnected), but **preserves** the store record, bindings, jobs, logs, audit records, and mapping/error history. Reconnect is an explicit, separately-audited operator action — never implicit or automatic — and must re-run readiness checks (MBQ-06) before business sync resumes. | Part A §B.1 names exactly this posture question as **[Open question — MBQ-08]**; the recommendation is the disconnect-specific instance of the already-**[Accepted — DEC-013]** Part A §I.4 rule "disabling must not delete history" — a direct, non-widening extension of an already-accepted principle, not new architecture. | Disconnect flow (Part A §B.1), store settings. | Exact field/state-machine implementation (MBQ-01/02); exact reconnect-matching mechanics. | Destroying audit history (compliance/debugging loss) or leaving stale credentials live (security leak) — both named directly in MBQ-08's own "why it matters." | MBQ-08 → **Accepted by ChatGPT via DEC-018** — disconnect preserves bindings/jobs/logs/audit history, revokes credentials and sync only; reconnect is explicit and audited. |
| **MBQ-17** | Reconciliation runs **per-store, per-domain** (product/customer/order/inventory/fulfillment each reconciled within their own scope) — never one global cross-domain job. Cadence is **configurable per store/domain** with a conservative (infrequent) default, chosen for rate-limit/GraphQL-cost awareness rather than a fixed aggressive interval. Exact interval values and batch sizes are **not** decided here — they remain implementation-planning constants (MBQ-18-adjacent). | DEC-005/DEC-009 (as summarized in AR-003/AR-006, `architecture-review-log.md`) already establish reconciliation as the mandatory correctness backstop; Part E §4 explicitly routes only MBQ-17's **posture** (not its constants) to the ChatGPT batch; per-domain scope is consistent with the already-**[Accepted — DEC-008]** domain-isolated module boundaries and avoids a single monolithic job that would defeat that isolation. | Reconciliation job across all domain modules; queue/cron substrate. | Exact interval/batch-size constants (MBQ-18); exact per-domain scope boundaries at code level. | Too infrequent risks silent drift going undetected too long; too frequent or globally scoped risks a GraphQL cost/throttle storm across every domain at once — both named in MBQ-17's own register row. | MBQ-17 → **Accepted by ChatGPT via DEC-018 (posture only)** — per-store/per-domain scope, configurable conservative-default cadence; exact constants remain Implementation planning. |
| **MBQ-33** | First-push guard fires **no coarser than per (store + mapped Odoo-Location ↔ Shopify-Location pair) + product/variant binding** — the first inventory push for a given product/variant at a given mapped location pair requires its own confirmation; one store-wide "confirm all inventory" action is not sufficient, though a batched review UI covering many such pairs at once is permitted as long as each pair's confirmation is individually recorded. | This is DEC-015's own carried recommendation (`master-blueprint-inventory-fulfillment.md` §A.5), explicitly logged as **"a recommendation for ChatGPT's direct decision... not decided by that acceptance"**; adopting it accepts what is already on the table rather than introducing new architecture. | Inventory first-push guard (Part C §A.5); confirmation-record schema (MBQ-38, already partially resolved). | Exact confirmation-record schema/fields (MBQ-38); batched-review UI/UX design. | Too coarse silently permits an unreviewed bulk first push — the exact **RA-008** "blind first push" anti-pattern this project has already rejected; too granular without batched-UI relief could create excessive confirmation friction. | MBQ-33 → **Accepted by ChatGPT via DEC-018** — guard granularity fixed as at left; no coarser guard is permitted. |
| **MBQ-34** | **Review-then-apply** is the Phase 1 default for all ongoing (post-first-push) inventory writes. Auto-apply is **not** offered as a Phase 1 default and may only be introduced later behind an explicit, separately-decided feature flag. Every apply action — manual now, automatic only if ever separately enabled later — remains logged with who/when. | This is DEC-015's own carried recommendation (`master-blueprint-inventory-fulfillment.md` §A.7), explicitly consistent with the already-**[Accepted — DEC-003]** "auto-apply not accepted as default MVP behaviour" and with **RA-008**'s binding rejection of blind pushes; confirms, does not widen, DEC-003/DEC-007 MVP scope. | Ongoing inventory write-back (Part C §A.7). | Exact review-queue UX/copy; any future auto-apply feature-flag design (explicitly out of scope for this decision). | Auto-apply-by-default risks unreviewed overselling/underselling drift; review-then-apply carries an accepted operator-friction cost as the safer Phase 1 trade-off. | MBQ-34 → **Accepted by ChatGPT via DEC-018** — review-then-apply is the Phase 1 default; auto-apply deferred behind a future, separately-decided flag. |
| **MBQ-41** | A **global/per-store** notification-default setting is sufficient for Phase 1 MVP (default **off**, per the already-**[Accepted — DEC-007 §5; RA-009]** guard, changeable only as an explicit per-store opt-in). No per-order override ships in Phase 1 unless standard Odoo's own delivery flow already exposes one **without** added connector UI, in which case it may be surfaced, not built new. Per-order override is deferred to a later phase. | This is DEC-015's own carried recommendation (`master-blueprint-inventory-fulfillment.md` §B.6), consistent with the already-accepted DEC-007 §5 default-off guard and RA-009's rejection of hidden/default-on notification. | Fulfillment notification UI (Part C §B.6). | Whether standard Odoo's delivery flow already exposes a per-order notification toggle — an implementation-time check, not asserted here either way. | Building a per-order override UI now would be premature scope growth beyond DEC-003/DEC-007's MVP boundary; permanently never revisiting it could frustrate a legitimate single-order need — the deferral is explicit, not a permanent rejection. | MBQ-41 → **Accepted by ChatGPT via DEC-018** — global/per-store default sufficient for Phase 1; per-order override explicitly deferred, not rejected. |
| **MBQ-45** | The four already-**[Accepted — DEC-013]** roles (Administrator, Operator, Reviewer, Auditor) map **1:1** to four Odoo security groups in Phase 1 (no finer-grained composition); the connector uses **one shared, role-gated application surface**, not a forked admin-app/functional-app pair. | DEC-013 already accepts the role hierarchy and Part A §J.1's proposed group-name directions (`group_shopify_connector_admin/operator/reviewer/auditor`); the already-accepted Part D screen-design blueprint (DEC-016) already designs one shared, role-gated surface (RA-013); this closes the two residuals Part A/J.1 explicitly leaves open — 1:1-vs-finer mapping, and one-surface-vs-two-surface — in the direction those blueprints already point, not a new direction. | Security-group design (Part A §J); naming pass (MBQ-44's access rows depend on this); dashboard/settings navigation (Part D). | Exact `ir.model.access.csv` rows and record rules (MBQ-44); exact group XML IDs (MBQ-01/02/03 naming pass). | Finer-grained groups add access-control complexity the accepted §J.2 capability matrix does not currently need; a forked surface would contradict the already-accepted single-shared-surface design (RA-13) and double the UI maintenance burden. | MBQ-45 → **Partially resolved [roles→groups mapping / surface split] by DEC-018** — 1:1 mapping, one shared role-gated surface; role hierarchy itself remains as already resolved by DEC-013; exact CSVs/XML IDs remain Implementation planning. |
| **MBQ-52** | Pin **one stable** Shopify GraphQL Admin API version per connector release; store the active pinned version per store/config (Part A §B.3 already models this field); surface API-version health/deprecation warnings on the existing API-health surface (§B.3); commit to a **planned, periodic** (e.g. quarterly, aligned to Shopify's own release cadence) review/upgrade window. Never track Shopify's "latest" version live in production. | Part A §B.3 already models a "targeted Shopify API version" field and an API-health state as accepted concepts; this fixes only the pinning/review-cadence policy around that already-modeled field — motivated by the register's own citation that mutation semantics (e.g. `@idempotent` requirements) are version-dated, so uncontrolled drift silently changes write behaviour. | Transport client (Part A §B.2/§B.3); store settings. | Exact upgrade-execution mechanics; exact deprecation-warning copy/thresholds. | No pinning risks a silent breaking-mutation-semantics change on Shopify's own release cadence; an overly rigid "never upgrade" policy risks running an eventually-unsupported API version. | MBQ-52 → **Accepted by ChatGPT via DEC-018 (policy only)** — pin-per-release + periodic review window; exact mechanics remain Implementation planning. |
| **MBQ-54** | Phase 1 does **not** support destructive domain-module **uninstall** as a normal merchant-facing operation. A merchant who wants to stop using a domain **disables** it via the already-**[Accepted — DEC-013]** feature-flag mechanism (Part A §I), which already guarantees "disabling must not delete history" (§I.4). A full Odoo-level module uninstall is either technically guarded/blocked, or — if Odoo's own uninstall mechanics cannot be fully blocked — is treated as an explicitly unsupported operation whose data-loss risk is documented and disclosed, never silently assumed prevented. | Part A §I.4 already accepts "disabling must not delete history" as the safe, supported path; MBQ-54 (Part A §I "what remains open") asks only about the harder uninstall case — this decision resolves it by directing merchants to the already-safe disable path instead of building new uninstall-safety mechanics in Phase 1. | Module lifecycle (Part A §I); any future migration/uninstall hooks. | Exact technical mechanism to guard/block uninstall, or exact disclosure copy if it cannot be fully blocked — Implementation planning. | If uninstall cannot actually be blocked at the Odoo level and this is not clearly documented, a merchant could silently lose binding/audit history via a path the connector claims is guarded. | MBQ-54 → **Accepted by ChatGPT via DEC-018 (posture: disable-not-uninstall is the supported Phase 1 path)**; exact technical guard mechanism/disclosure remains Implementation planning. |
| **MBQ-60** | `shopify_connector_fulfillment` declares a dependency on Odoo's `stock_delivery` (or the lighter `delivery`) module, specifically for the `carrier_tracking_ref`/`carrier_tracking_url`/`carrier_id` write-back fields already verified in `master-blueprint-inventory-fulfillment.md` §B.5 (DEC-015). If a merchant's database lacks that module, tracking write-back is **disabled and reported as a named, specific readiness/health blocker** (MBQ-06) — never a silent no-op or a degraded partial write. | DEC-015 already verifies these fields belong to `stock_delivery`, not core `stock`, and explicitly surfaces this as new, undecided MBQ-60; requiring the dependency is the conservative reading of that verified fact — the alternative (an optional/"best effort" dependency) risks a silently degraded feature, contrary to the project's no-silent-failure posture (`CLAUDE.md` §9). | `shopify_connector_fulfillment` manifest dependencies (once implementation opens); readiness checks (MBQ-06). | Manifest `depends` mechanics; exact readiness-check wording for the missing-module case. | Requiring a dependency most merchants already have (Odoo's Inventory app commonly includes `stock_delivery`) is low-risk; the alternative (soft/optional dependency with unclear degraded behaviour) risks a silent feature gap, the worse failure mode. | MBQ-60 → **Accepted by ChatGPT via DEC-018** — `stock_delivery`/`delivery` required; tracking write-back disabled/readiness-blocked without it, never silently degraded. |
| **MBQ-62** | **Not forced to a decision in this batch — see below.** | — | — | — | — | **No register wording change proposed** — row stays open exactly as it is; see the strict analysis and split recommendation immediately below. |

**MBQ-62 — strict analysis (required by scope instruction).** The Part A
§D.2 job-source enum is fixed at exactly six values:
`webhook`, `manual_sync`, `scheduled_sync`, `reconciliation`,
`setup_readiness_check`, `export_preview_dry_run` — **[Accepted — DEC-009]**.
Checking each against the two Odoo-side event triggers MBQ-62 actually names
(an inventory push enqueued by a relevant Odoo stock change, §A.7; a
fulfillment creation triggered by a validated `stock.picking`, §B.3/§B.12):

- `webhook` — describes an **incoming external** Shopify-originated event.
  Wrong direction entirely; an Odoo-side trigger is not a webhook.
- `manual_sync` — describes an **explicit operator "sync now" action**. A
  routine stock adjustment or picking validation is a warehouse operation,
  not an operator invoking sync — mapping it here would mislabel the
  trigger and corrupt the dashboard's "how did this job start" filter
  (Part A §G.1) into showing false operator-initiated activity.
- `scheduled_sync` — describes a **timer/cron-driven periodic** run. The
  Odoo-side event is immediate and one-off, not periodic — mapping it here
  would key retry/backoff policy lookups (MBQ-16, which may legitimately
  differ for scheduled vs. event-triggered jobs) on the wrong bucket.
- `reconciliation` — describes the **drift-detection backstop** that
  compares full state. A single event-triggered push is not a reconciliation
  pass; conflating them would let reconciliation-cadence tuning (MBQ-17,
  decided above) inadvertently throttle or skip genuinely immediate
  event-triggered pushes.
- `setup_readiness_check` / `export_preview_dry_run` — both structurally
  **read-only/preview-only** (Accepted — DEC-012). These are real writes.
  Clearly inapplicable.

**None of the six existing values is a defensible fit.** Recommending one
anyway would repeat, with a different unexamined value substituted in, the
exact failure mode Fable's own finding C2 already caught and corrected during
DEC-015's review — an earlier Sprint C draft silently treated "event-driven
enqueue" as if it were a Part A job-source value, which Fable flagged and the
sprint corrected by routing the question to MBQ-62 instead of asserting an
answer (`architecture-review-log.md` AR-012). Forcing a same-batch answer now,
under review-batch time pressure, risks reintroducing that exact defect one
level removed.

**Recommendation: split MBQ-62 out of Batch 1 into its own dedicated
follow-up DEC**, so ChatGPT can weigh, with dedicated attention, either (a) a
narrow, explicitly-named seventh job-source value for an Odoo-side event
trigger (exact name not proposed here — DEC-010's original acceptance
explicitly reserved the Odoo-side event trigger as a "sync-trigger layer,"
not a job-source value, so this is a real vocabulary widening, not a
formality), or (b) a documented exception/tagging rule that records the
originating Odoo event as metadata on an existing source value without
changing that value's own semantics. Both options have different
consequences for the dashboard filter (§G.1) and retry-policy lookup
(MBQ-16) design that deserve a dedicated session, not a same-batch bundling
alongside ten lower-risk posture calls.

## 5. Register-impact wording (applied)

**ChatGPT accepted DEC-018 on 2026-07-04.** The wording below for MBQ-06,
MBQ-08, MBQ-17, MBQ-33, MBQ-34, MBQ-41, MBQ-45, MBQ-52, MBQ-54, and MBQ-60
has now been **applied** to `master-blueprint-open-questions.md` (this is
the record of exactly what was inserted, dated **2026-07-04**). MBQ-62's own
row is **unaffected in substance** — only a short split-note citation was
added, per its own bullet below.

- **MBQ-06:** *"Accepted by ChatGPT via DEC-018 (2026-07-04): essential
  readiness checks are credential validity/test-connection, required scopes,
  API-version health, store identity, `web.base.url` reachability, webhook
  HMAC secret (if webhooks enabled), cron/queue health, at least one mapped
  Location with an enabled domain, and intentional domain-flag enablement;
  all other candidate checks warn, never block. Exact copy/XML IDs remain
  open for implementation planning."*
- **MBQ-08:** *"Accepted by ChatGPT via DEC-018 (2026-07-04): disconnect
  revokes credentials and disables sync/webhook enqueue but preserves
  bindings, jobs, logs, audit records, and mapping/error history; reconnect
  is explicit, audited, and re-runs readiness checks (MBQ-06)."*
- **MBQ-17:** *"Posture accepted by ChatGPT via DEC-018 (2026-07-04):
  reconciliation is per-store, per-domain, never a single global job;
  cadence is configurable per store/domain with a conservative default.
  Exact interval/batch-size constants remain implementation planning."*
- **MBQ-33:** *"Accepted by ChatGPT via DEC-018 (2026-07-04): the first-push
  guard fires no coarser than per (store + mapped Odoo-Location ↔
  Shopify-Location pair) + product/variant binding; batched review UI is
  permitted if each pair is individually recorded."*
- **MBQ-34:** *"Accepted by ChatGPT via DEC-018 (2026-07-04): review-then-
  apply is the Phase 1 default for all ongoing inventory writes; auto-apply
  is not a Phase 1 default and requires a future, separately-decided feature
  flag."*
- **MBQ-41:** *"Accepted by ChatGPT via DEC-018 (2026-07-04): a global/
  per-store notification default (off) is sufficient for Phase 1; per-order
  override is explicitly deferred, not built in Phase 1 unless already
  exposed by standard Odoo without added connector UI."*
- **MBQ-45:** *"Partially resolved [roles→groups mapping / surface split] by
  DEC-018 (2026-07-04): the four DEC-013 roles map 1:1 to four Odoo security
  groups; one shared, role-gated application surface is used, not a forked
  admin/functional pair. Exact `ir.model.access` rows and XML IDs remain
  implementation planning (MBQ-44)."*
- **MBQ-52:** *"Accepted by ChatGPT via DEC-018 (2026-07-04), policy only:
  one stable Shopify GraphQL Admin API version is pinned per connector
  release, with a planned periodic review/upgrade window and surfaced
  deprecation warnings. Exact upgrade mechanics remain implementation
  planning."*
- **MBQ-54:** *"Accepted by ChatGPT via DEC-018 (2026-07-04), posture only:
  Phase 1 does not support merchant-facing domain-module uninstall;
  disabling via the accepted feature-flag mechanism (which already preserves
  history) is the supported path. Exact technical uninstall-guard mechanism
  or disclosure remains implementation planning."*
- **MBQ-60:** *"Accepted by ChatGPT via DEC-018 (2026-07-04):
  `shopify_connector_fulfillment` requires Odoo's `stock_delivery` (or
  `delivery`) module for tracking write-back; absent that module, tracking
  write-back is disabled and readiness-blocked (MBQ-06), never silently
  degraded."*
- **MBQ-62:** *No register wording change to the row's substance.* ChatGPT
  accepted DEC-018's recommendation to split this row: the only register
  change is an added citation noting DEC-018 evaluated MBQ-62 and routed it
  to a dedicated follow-up decision record rather than deciding it in Batch
  1 — the row's own open status and text are otherwise unchanged.

## 6. Items intentionally excluded from Batch 1

- **MBQ-64** (Shopify `MoneyBag`/presentment-currency order-money model vs.
  Odoo's single `sale.order.currency_id` design/selection question) and
  **MBQ-65** (Shopify product-webhook payload-shape/subscription-scope/
  Phase-1-implementation-scope residual) are **excluded from this batch**.
  Per the task scope, both require a **separate, dedicated currency/webhook
  residual decision sprint** because they need tighter technical treatment
  than a posture-level batch review can safely give them — DEC-017 already
  accepts their underlying platform facts at fact-verification level only,
  and neither row's own remaining design/selection question is a same-shape
  posture call like the eleven rows in §4.
- **MBQ-62** is nominally in this batch's assigned scope but, per §4's strict
  analysis, receives a **recommendation to split into its own follow-up
  DEC**, not a decision — for a different reason than MBQ-64/65 (a weak
  mapping onto existing vocabulary, not a currency/webhook technical-depth
  gap), but the same practical effect: no register wording changes for it in
  this batch.
- No other MBQ requiring fresh code inspection or official-doc research not
  already performed by an accepted Master Blueprint part was considered for
  this batch — every one of the ten decided rows above rests on evidence
  Parts A/C, DEC-013, and DEC-015 already established and cited.

## 7. Implementation gate impact

- **Even though DEC-018 is now accepted, the implementation gate remains
  closed** unless ChatGPT explicitly opens it via a separate, dedicated act
  per `master-blueprint.md`'s gate criteria and
  [`../05-qa/quality-feedback-loop.md`](../05-qa/quality-feedback-loop.md)
  §10. Accepting this batch moves criterion 2 ("blocking MBQs resolved or
  consciously accepted as risk") closer to satisfied for ten specific rows —
  it does not by itself satisfy criterion 2 in full (roughly 35 other
  "Blocks implementation: Yes" rows remain, per the PR #78 audit's count),
  and it does not touch criterion 3 (explicit gate-opening act) at all.
- **This batch reduces blockers but does not create implementation
  tasks.** No file matching CLAUDE.md §9 /
  `../06-prompts/implementation-task-template.md` is written by this
  document or by its acceptance.
- **No code follows directly from this PR.** DEC-018's acceptance changes
  documentation status only; it authorizes no Odoo module, model, view,
  controller, security file, manifest, test, migration, or CI file.

## 8. Recommendation to ChatGPT — accepted

**Accept Batch 1 except MBQ-62** — accept MBQ-06, MBQ-08, MBQ-17 (posture),
MBQ-33, MBQ-34, MBQ-41, MBQ-45 (mapping/surface split), MBQ-52, MBQ-54, and
MBQ-60 exactly as proposed in §4, and route MBQ-62 to its own dedicated
follow-up decision record rather than deciding it here (the mechanism §4's
strict analysis recommends, functionally equivalent to "split weak rows into
a follow-up batch" applied to this one row only). **ChatGPT accepted this
recommendation on 2026-07-04** (see "Acceptance" above).

**Justification:** the ten accepted rows each adopt a direction an already-
accepted Master Blueprint part (mostly DEC-013/DEC-015) already placed on the
table as "a recommendation for ChatGPT's direct decision" — none introduces
new architecture, none widens DEC-003/DEC-007 MVP scope, and none
re-introduces a binding rejected approach (checked against
`rejected-approaches-log.md`). MBQ-62 is different in kind: every existing
Part A §D.2 job-source value is a poor semantic fit for an Odoo-side event
trigger, and forcing one in under batch-review time pressure risks repeating
the exact defect (Fable finding C2) this project has already caught and
corrected once. Treating ten of eleven in-scope rows as decidable now and
carving out the one row that is not is a more defensible outcome than either
forcing all eleven or deferring the whole batch over one weak row.

---

**Change control:** further changes to this record require ChatGPT review,
mirroring the DEC-013 through DEC-017 change-control pattern. This record
does not re-litigate DEC-003 through DEC-017, does not reopen accepted
Master Blueprint Parts A–E, and does not reintroduce any row from
`../05-qa/rejected-approaches-log.md`.
