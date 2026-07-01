# Product Vision

> The product vision for the premium **Odoo 19 ↔ Shopify Connector**. It states
> what we are building, who it is for, the problems it solves, what "premium"
> means for us, and the principles and non-negotiables that govern quality — all
> grounded in **already-merged repo evidence**. It is a **strategy/synthesis**
> artifact, not a scope or an architecture. Companion: the setup/UX principles in
> [`./setup-ux-principles.md`](./setup-ux-principles.md).

## Status

- **Sprint:** Product Sprint E (RB-11). **Phase:** product strategy / synthesis —
  **no-code gate in force** (`CLAUDE.md` §4–§5). This document **decides nothing**.
- **Governance:** everything here is a **product thesis / principle / inference /
  recommendation / input**. **No MVP scope is finalized** (that is RB-13, gated),
  **no architecture is decided** (RB-14 / AR-002…AR-008, all "Not decided /
  Evidence pending"), **no ADRs, no module boundaries or names, no data models**.
- **Evidence discipline (DP-003 / DP-004 / DP-006):** competitor claims stay
  **claims**; a configuration field is **not** demonstrated support; a market
  promise is **not** demonstrated bidirectionality; conditional platform
  requirements stay **conditional**; improvement opportunities are **inference**,
  not demonstrated competitor capability. Nothing here promotes a claim to a fact
  or a candidate to a decision (evidence-consistency gate).
- **Dates:** competitor evidence access date **2026-06-30** (Sprint C); session
  date **2026-07-01**. No new sources were crawled for this sprint.
- **Claim labels used below:** **[Fact]** (Tier-1 Shopify/Odoo official),
  **[Competitor claim]**, **[Demonstrated]** (a specific competitor workflow /
  screenshot / dated release note), **[Inference]**, **[Recommendation]**,
  **[Open question]**. Where a sentence is unlabelled it is product framing.

## Purpose

Give the project a single, evidence-anchored answer to *what product are we
building and why is it better*, so that the later gated sprints — MVP implications
(RB-13), architecture preparation (RB-14), setup/menu/UX design, and (only when
authorised) implementation — inherit a shared, defensible product direction
instead of re-deriving it. This vision converts the research baseline
([`../01-research/`](../01-research/)) and the canonical capability model
([`./feature-taxonomy.md`](./feature-taxonomy.md),
[`./capability-evidence-map.md`](./capability-evidence-map.md)) into product
intent — **without** hardening any candidate into a commitment.

## Evidence base

This vision is a synthesis of merged repo evidence only (no new research):

- **Tier-1 platform facts** — [`../01-research/shopify-official-api-notes.md`](../01-research/shopify-official-api-notes.md)
  and [`../01-research/odoo-official-architecture-notes.md`](../01-research/odoo-official-architecture-notes.md)
  (with excerpts under [`../00-source-materials/`](../00-source-materials/)).
- **Competitor evidence (Sprint C)** — [`../01-research/competitor-deep-dives.md`](../01-research/competitor-deep-dives.md),
  [`../01-research/competitor-feature-matrix.md`](../01-research/competitor-feature-matrix.md),
  [`../01-research/ux-ui-benchmark.md`](../01-research/ux-ui-benchmark.md),
  [`../01-research/common-patterns.md`](../01-research/common-patterns.md),
  [`../01-research/best-in-class-observations.md`](../01-research/best-in-class-observations.md).
- **Opportunities & anti-patterns (Sprint C)** — [`../01-research/gaps-opportunities.md`](../01-research/gaps-opportunities.md)
  and [`../01-research/avoid-list.md`](../01-research/avoid-list.md).
- **Canonical capability model (Sprint D)** — [`./feature-taxonomy.md`](./feature-taxonomy.md),
  [`./capability-evidence-map.md`](./capability-evidence-map.md),
  [`./product-research-handoff.md`](./product-research-handoff.md).
- **Quality memory** — [`../05-qa/defect-pattern-log.md`](../05-qa/defect-pattern-log.md)
  (DP-001…DP-006), [`../05-qa/architecture-review-log.md`](../05-qa/architecture-review-log.md)
  (AR-002…AR-008), [`../05-qa/rejected-approaches-log.md`](../05-qa/rejected-approaches-log.md).

**Evidence weighting.** The most robustly demonstrated competitor evidence comes
from **Emipro (EM, ~29 real screenshots)** and **VentorTech (VT, dated
release notes)**; **sh_shopify_connector (SH)** rests on captions; **Webkul (WK)**
on inline guide screenshots; **ecommerce_shopify (EC)** has no screenshots; and
**Teqstars (TQ)** docs are 403-blocked → **claims only**
([`../01-research/ux-ui-benchmark.md`](../01-research/ux-ui-benchmark.md) evidence
base). Product claims below weight EM/VT-demonstrated evidence over SH/WK/EC/TQ
claims accordingly.

## What we are building

A **best-in-class, modular, reliable connector** that synchronises commerce data —
catalog, variants/media, pricing, inventory, customers, orders, payments,
fulfilment, refunds/returns, and (as premium add-ons) payouts and advanced Shopify
surfaces — between **Odoo 19** and **Shopify**, to a higher quality bar than
existing market offerings (`CLAUDE.md` §1).

In product terms, it is:

- a **correct, observable synchronisation core** that keeps the two systems in
  agreement and can **prove** it (reconcile, detect drift, recover), rather than a
  broad feature list that silently drifts;
- wrapped in an **operator experience** — guided setup, a command center, a
  recovery-first error surface, safe-by-default actions, honest status — that a
  non-developer can run with confidence;
- delivered as a **modular addon family**, isolated from customer/base code (e.g.
  `adams_base`), that is **customizable** and **upgrade-safe**;
- **simple for normal users** (opinionated defaults, progressive disclosure) and
  **powerful for advanced users** (directional/testable mappings, feature flags,
  extension points) — **premium, but not bloated**.

The connector's positioning, in one line: **the connector that is correct by
design and honest by default — and can prove both to the operator.**

## Product thesis

The market's breadth is largely commoditised, but its **correctness and operator
experience are not** — that gap is where a premium product wins. Grounded in
evidence:

1. **Broad object coverage is table stakes, not a differentiator.** Product /
   order / inventory / customer coverage is claimed by all six competitors;
   demonstrated directional depth is uneven (**[Competitor claim]**; EC product
   export **not found**, WK customer export **not found**, TQ listing-claim only —
   [`../01-research/common-patterns.md`](../01-research/common-patterns.md) §"strongly
   common", DP-004). Matching the demonstrated baseline is necessary but does not
   make us premium.
2. **The biggest un-owned whitespace is demonstrated correctness.** Only VT
   mechanises idempotency; **no competitor** surfaces first-class reconciliation or
   rate-limit/cost-aware throttling — yet Tier-1 **requires** reconciliation
   (webhook delivery is not guaranteed) and `@idempotent` on inventory/refund
   writes (from 2026-04) (**[Fact]** + **[Inference]**;
   [`../01-research/gaps-opportunities.md`](../01-research/gaps-opportunities.md)
   O-REL-1/O-REL-2, [`../01-research/common-patterns.md`](../01-research/common-patterns.md)
   whitespace). Correctness the market only *claims*, we can *demonstrate*.
3. **The second un-owned whitespace is the operator experience.** SH has the best
   monitoring and VT the best diagnostics, but **neither combines** a unified
   command center with a recovery-first error center (**[Inference]** on
   **[Demonstrated]** parts; O-DASH-1, O-LOG-1). Owning the whole operator loop —
   see, diagnose, recover — is a durable advantage.
4. **Trust is a feature, and it is cheap.** Honest latency labels, a dated
   changelog that discloses fixes, open screenshot-rich docs, and visible
   reconciliation/throttle status are low-cost and directly rewarded; opacity
   (TQ docs blocked, SH no changelog, EC no screenshots) is a real evaluation
   weakness (**[Inference]**; O-PREM-4,
   [`../01-research/avoid-list.md`](../01-research/avoid-list.md) A-DOC-1…4).

**Thesis:** *win on demonstrated correctness and the operator experience, deliver
the demonstrated breadth as a clean baseline, and offer premium breadth as
optional add-ons — all on an honest, modular, upgrade-safe core.* (**[Recommendation]**;
synthesises [`../01-research/gaps-opportunities.md`](../01-research/gaps-opportunities.md)
"top differentiation themes".)

## Target users and buyer personas

> **[Inference]** — personas are deduced from the evidence (the UX benchmark's
> explicit **admin vs functional-user** split; SH's access-right-gated setup; the
> modularity/isolation and docs/trust findings). They are **not** validated buyer
> research; treat as inputs, not a segmentation decision.

- **P1 — The operations / e-commerce user (primary daily user).** Runs and
  monitors syncs, reads logs, and recovers from failures. Often **not** a
  developer. Needs: a command center, reason-coded errors with fix hints, one-click
  recovery, honest status. Evidence for the need: the recovery/observability
  findings in [`../01-research/ux-ui-benchmark.md`](../01-research/ux-ui-benchmark.md)
  ("Logs, errors, retries, and recovery UX").
- **P2 — The Odoo administrator / implementation consultant (setup & configuration
  owner).** Installs, connects, maps fields, sets permissions, and tunes sync
  behaviour. Needs: guided OAuth-style onboarding, pre-flight readiness checks,
  directional/testable mappings, progressive disclosure, and role gating
  (O-SET-1/2, O-CFG-1/2, C-MULTI-03). *Onboarding friction is the #1 drop-off*
  (**[Inference]**; O-SET-1).
- **P3 — The business owner / finance stakeholder (economic buyer).** Cares about
  correctness (no double refunds / oversell), trust/evaluability (docs, changelog,
  demo), reporting, and total cost. Needs: demonstrable correctness, transparency,
  and honest limitation disclosure (O-PREM-1/4).
- **P4 — The Odoo partner / integrator (deployer & reseller).** Deploys for many
  clients; cares about **modularity, isolation from customer/base code,
  customizability, and upgrade-safety** (O-MOD-1,
  [`../01-research/avoid-list.md`](../01-research/avoid-list.md) A-MOD-1…4). A poor
  module structure is a maintenance tax on this persona.

**Primary product tension to resolve for all personas:** *approachable for P1/P3,
powerful for P2/P4* — served by progressive disclosure and feature flags, not by
two separate products. **[Open question]** which persona is the primary MVP target
(RB-13).

## Core customer problems

Grounded in the competitor avoid-list, gaps, and Tier-1 facts:

1. **Silent data drift and correctness failures.** Webhook-only or cron-only
   designs, missing idempotency, and no reconciliation cause missed orders,
   duplicate records, double refunds, and multi-location double-decrement
   (**[Fact]** webhook delivery not guaranteed / `@idempotent` required; **[Inference]**;
   [`../01-research/avoid-list.md`](../01-research/avoid-list.md) A-SYNC-1/2,
   A-RET-3, A-INV-2, A-PAY-2). *This is the most damaging and least-owned problem.*
2. **Fragile, high-friction onboarding.** Long manual scope pastes with
   trailing-slash footguns (EM **[Demonstrated]**), heavy self-hosted installs that
   exclude Odoo Online (VT **[Demonstrated]**), and sign-in-gated setup guides
   (EC/R5) make first sync hard (O-SET-1, A-CFG-2, A-DOC-1).
3. **Opaque operations and dead-end recovery.** Email-only errors (EC), manual-only
   recovery (WK/EM/EC/SH), opaque status, and scattered menus leave operators
   unable to answer "is everything OK, what failed, what do I do" (A-LOG-1,
   A-RET-1, O-DASH-1, O-LOG-1).
4. **Dishonest expectations.** "Real-time" labels over cron/queue models (WK/EC/SH
   **[Competitor claim]** downgraded by verification), no freshness indicators, and
   no rate-limit feedback erode trust (A-UX-1, O-UX-1, A-SYNC-5).
5. **Configuration overwhelm.** Toggle-dense screens, unexplained jargon, and blind
   mappings with no dry-run push errors onto users (A-UX-3, A-CFG-1/3, O-CFG-1/2).
6. **Failure at scale.** No rate-limit/GraphQL-cost handling → 429 storms; long
   syncs inside web requests; no bulk strategy (**[Fact]** rate limits / worker
   limits / Bulk Operations; A-SYNC-5, A-IMP-3, O-PERF-1/2).
7. **Poor evaluability and trust.** Blocked/gated docs (TQ 403, EC), no changelog
   (SH), no screenshots (EC), stale platform figures (EM) make the product hard to
   trust and evaluate (A-DOC-1…4, O-DOC-1).
8. **Lock-in and upgrade fragility.** One-giant-module designs and coupling to
   base/customer code make maintenance and Odoo upgrades risky (**[Inference]** +
   **[Fact]** Odoo modularity guidance; O-MOD-1, A-MOD-1/4).

## Product principles

The connector's product identity, each tied to evidence. These are **product
principles (recommendations)**, not architecture.

1. **Correctness-first.** We would rather sync **less** and be **right** than sync
   broadly and drift. Idempotency, reconciliation, and duplicate-prevention are
   design defaults, not add-ons (O-REL-1, DP guardrails).
2. **UX-first.** A non-developer operator can install, run, understand, and recover
   without reading source or filing a ticket (ux-ui-benchmark UX principles).
3. **Recovery-first.** Every failure is isolated, reason-coded, and recoverable —
   automatically where safe, one-click where manual (O-LOG-1, A-RET-1).
4. **Observable.** The operator can always see what synced, what failed and why,
   and how fresh the data is (O-DASH-1, O-UX-1).
5. **Honest by default.** Accurate latency labels, disclosed limitations, no
   "real-time" overstatement, visible reconciliation/throttle status (A-UX-1,
   O-PREM-4).
6. **Modular & customizable.** A layered addon family isolated from `adams_base`,
   with documented extension points and feature flags (O-MOD-1; boundaries **not
   decided** — AR-004).
7. **Performance-aware.** Rate-limit/cost-aware pacing, batched/bulk operations for
   scale, and no long syncs in a request (O-PERF-1/2; approach is AR-002/003).
8. **Evidence-based.** Every capability we build traces to demonstrated need or a
   Tier-1 requirement (the capability evidence map is the source of truth).
9. **Upgrade-safe.** In-place extension over fragile delegation; migration-aware;
   don't leak platform internals that break on upgrade (**[Fact]** Odoo guidance;
   A-MOD-4).
10. **Premium, not bloated.** Breadth ships as **optional add-ons** on a correct
    core; defaults stay simple; power is opt-in (O-PREM-3, O-UX-2).

## Premium quality bar

"Premium" for this product is defined by **correctness, experience, and trust**,
not by feature count. To call a capability "premium-done" it should meet this bar
(**[Recommendation]**, gated):

- **Correct under failure.** It behaves correctly when webhooks are missed, retried,
  duplicated, or delivered out of order — because idempotency + reconciliation are
  in place (**[Fact]** basis; O-REL-1).
- **Recoverable.** When it fails, the failure is isolated, named, and retryable
  (auto where safe) with a clear next action (O-LOG-1).
- **Observable & honest.** Its status and data freshness are visible and truthfully
  labelled (O-UX-1).
- **Safe.** Destructive actions require a dry-run/preview or a strong confirmation;
  it never silently loses data (A-CFG-1, A-RET-2; **[Fact]** `productSet`
  delete-on-omit footgun — A-IMP-1).
- **Approachable then powerful.** Sensible defaults with inline help; advanced
  power is opt-in (O-UX-2, O-CFG-2).
- **Evidenced & documented.** It traces to demonstrated need or a Tier-1
  requirement, and ships with honest, screenshot-rich docs (O-DOC-1).
- **Modular & upgrade-safe.** It lives in the right layer, isolated from base code,
  and survives Odoo upgrades (O-MOD-1).

**Anti-definition of premium (what premium is NOT for us):** the largest feature
matrix, "real-time" marketing, or more toggles. Breadth without correctness is
below our bar (**[Inference]**).

## Differentiation strategy

Five differentiation themes, each an **[Inference]/[Recommendation]** on top of
demonstrated or Tier-1 evidence (`gaps-opportunities.md` summary; **not** an MVP or
architecture decision):

1. **Demonstrated correctness** (headline). Idempotency + first-class,
   user-visible reconciliation + rate-limit/GraphQL-cost-aware throttling —
   *demonstrated, not just claimed*. The market's biggest whitespace and
   Tier-1-mandated (O-PREM-1, O-REL-1/2).
2. **The best operator experience.** A unified command center **and** a
   recovery-first error center **together** — combining SH monitoring with VT
   diagnostics, which neither does fully (O-PREM-2, O-DASH-1, O-LOG-1).
3. **Effortless onboarding with real reliability.** OAuth-style guided setup with a
   pre-flight readiness check, *without* the heavy install that excludes Odoo
   Online — the combination no competitor has (O-SET-1; VT has reliability but a
   heavy install, easy-install products lack the reliability).
4. **Honesty & transparency as a feature.** Latency labels, dated changelog
   disclosing fixes, open docs/demo, visible reconciliation/throttle status
   (O-PREM-4, O-DOC-1).
5. **Premium breadth as clean, optional add-ons.** Payout reconciliation (EM-grade,
   **[Demonstrated]**), B2B/VAT (VT), gift cards (SH), Markets/Catalogs (EM/VT),
   metafields — each on the correct, observable core, not bolted on (O-PREM-3).

**Sequencing note (input, not decision):** themes 1–3 are the strongest
differentiation *inputs* for RB-13/RB-14; breadth (theme 5) is **later / optional**.
**No theme is committed to MVP here.**

## UX/UI strategy

Product-level UX intent (screen-level principles live in
[`./setup-ux-principles.md`](./setup-ux-principles.md); **no UI is designed here**).
Grounded in [`../01-research/ux-ui-benchmark.md`](../01-research/ux-ui-benchmark.md):

- **Confidence over speed** — every sync shows *what happened, to what, and what
  failed and why* (stage → inspect → process → verify → log).
- **Glanceable, actionable health** — status encodes the problem **and** the fix
  (VT traffic-light generalised).
- **Recovery-first** — isolated failures, automatic retry where safe, one-click
  manual retry, missed-event reconciliation.
- **Safe by default** — dry-run/preview before destructive apply; irreversible-action
  warnings.
- **Approachable then powerful** — great defaults + progressive disclosure + inline
  help; power features (mappings/transforms) opt-in.
- **Don't leak the platform** — no raw `ir.cron` internals; speak the user's
  language ("every 15 minutes", not `nextcall`) (**[Fact]**-informed; A-UX-2).
- **Two audiences, one product** — an admin surface and a functional-user surface,
  gated by access rights (SH-style), not two apps.

## Reliability and correctness strategy

Reliability is the spine of the product (**[Fact]**-anchored; approaches routed to
AR-003/005/006/007, all open):

- **Idempotency by default.** Persist idempotency handling on writes so retries and
  duplicate webhooks do not double-act — Shopify **requires** `@idempotent` on
  inventory set/adjust and refunds from 2026-04 (**[Fact]**; O-REL-1, A-RET-3,
  A-PAY-2).
- **Reconciliation as a first-class, visible capability.** Because **webhook
  delivery is not guaranteed** (**[Fact]**), the product must reconcile on a
  schedule and on demand, detect drift, and show "last reconciled / drift found" —
  a whitespace no competitor owns (O-REL-1, A-SYNC-2).
- **Webhook integrity.** HMAC verification on the raw body before processing,
  webhook-id dedup, and fast acknowledgement, with heavy work out-of-band
  (**[Fact]** HMAC / 8-retries-then-auto-delete / 5s ack; A-SYNC-4/6, C-SYNC-02/03).
- **Duplicate prevention by design.** A documented Shopify-GID ↔ Odoo binding model
  with explicit dedup keys and safe handling of deleted bindings (O-DUP-1; model
  **not decided** — AR-005).
- **Resilient recovery.** Per-record failure isolation, retry classification
  (auto-safe vs manual-fixable), automatic backoff for safe ops, resumable/chunked
  jobs (O-REL-3, A-RET-1; C-JOB-01…07).
- **Layered sync mechanism.** Webhooks **and** scheduled reconciliation **and**
  manual sync together — never any one alone (A-SYNC-1).

## Modularity and customizability strategy

(**[Recommendation]**/**[Inference]**; boundaries are **not decided** — AR-004.)

- **A layered, isolated addon family** — clear separation of transport / mapping /
  orchestration / domain / UI concerns, isolated from `adams_base` and customer
  code, using link modules for Odoo glue (O-MOD-1; `CLAUDE.md` §9). We favour
  neither one giant module (A-MOD-1) nor over-fragmentation (A-MOD-2) — **exact
  boundaries and module names are deliberately not defined here.**
- **Customizability without forking** — directional, testable field mappings with a
  dry-run and (advanced) safe transforms; documented extension points; feature
  flags so capability groups can be enabled per deployment (O-CFG-1, C-MAP-03,
  C-MULTI-04).
- **Upgrade-safe extension** — in-place model extension over fragile delegation;
  migration-aware; no leaking of platform internals (**[Fact]** Odoo guidance;
  A-MOD-4).
- **Premium breadth as add-ons** — advanced surfaces (payouts, B2B, gift cards,
  Markets, metafields) as optional modules on the core, not baked into it
  (O-PREM-3).

## Performance strategy

(**[Fact]**-anchored; approaches routed to AR-002/003, open.)

- **Rate-limit / GraphQL-cost awareness** — pace off live throttle status, back off
  on 429/`Retry-After`; a total whitespace no competitor addresses (**[Fact]**;
  O-REL-2, A-SYNC-5).
- **Bulk & batch at scale** — route large reads/writes to Bulk Operations; batch
  ORM writes; index binding lookups (**[Fact]** Bulk Operations / Odoo performance;
  O-PERF-1).
- **No long syncs in a request** — chunked, out-of-band processing; respect Odoo
  worker time/memory limits; remember crons are disabled on Odoo.sh staging
  (**[Fact]**; O-PERF-2, A-IMP-3).
- **Honest performance expectations** — surface throttling/backpressure to the user
  rather than failing opaquely (O-UX-1).

## Security and permissions strategy

(**[Fact]**-anchored; details routed to AR-004 / security, open.)

- **Least-privilege and role-aware access** — admin vs functional-user separation,
  connector settings gated behind access rights (SH-demonstrated; C-MULTI-03,
  **[Fact]** Odoo `ir.model.access` deny-by-default).
- **Isolation for multi-tenant use** — per-store config isolation and record-rule
  based multi-company isolation **where in scope** (**[Fact]** Odoo record rules;
  C-MULTI-01/02). **Multi-company stays conditional/later** — a config field is not
  demonstrated support (DP-004); WK multi-company is config-field-only (➖).
- **Credential safety** — OAuth-style connection with credential masking; never
  expose secrets in logs/UI (VT-demonstrated C-CONN-02).
- **Protected-data compliance** — respect Shopify protected customer data rules and
  the 60-day order window / approval gate for historical import (**[Fact]**;
  C-ORD-02, C-CUST-01).
- **Deliberate privilege escalation only** — no casual bypass of ORM access
  controls (**[Fact]** `sudo()` bypasses access rights + record rules; A-IMP-5).

## Documentation, support, and trust strategy

(**[Recommendation]**; O-DOC-1, O-PREM-4, A-DOC-1…4.)

- **Open, screenshot-rich, non-gated docs** — never bot-block or sign-in-gate
  evaluation docs (counter to TQ 403 / EC gated guide).
- **A dated, honest changelog that discloses fixes** (VT-style), citing **current**
  platform figures — never stale ones (counter to SH no-changelog / EM stale figure;
  ties to DP-001).
- **Honest limitation disclosure** (EM/VT-style) — state what the product does not
  do, plainly.
- **Evaluability** — an open demo and a built-in self-test / readiness check so
  buyers can evaluate without a sales gate (O-TEST-1).
- **Documentation mirrors the product** — help is anchored to the screens and jargon
  the user actually sees (setup-ux-principles Principle 12).

## What we will do better than competitors

Each is **[Inference]** on **[Demonstrated]**/**[Fact]** evidence; none is an MVP or
architecture decision:

- **Correctness the market only claims** — demonstrated idempotency + reconciliation
  + rate-limit awareness (vs VT-only idempotency, nobody's reconciliation/throttling).
- **The whole operator loop in one place** — command center + recovery-first errors
  together (vs SH monitoring OR VT diagnostics).
- **Onboarding that is both easy and reliable** — guided OAuth-style setup + readiness
  check, without excluding Odoo Online (vs VT's heavy install; EC's gated guide).
- **Honest status** — accurate latency + freshness + throttle visibility (vs
  "real-time" overstatement).
- **Auto-apply and auto-recovery where safe** — no manual inventory-adjustment step
  (vs EM manual step); automatic retry of safe ops with a clear manual override.
- **Trust & evaluability** — open docs, dated changelog, demo, self-test (vs blocked
  TQ docs / no-screenshot EC / no-changelog SH).
- **Clean modularity & upgrade-safety** — layered, isolated, add-on breadth (vs
  one-giant-module / heavy-dependency friction).

## What we will avoid

The competitor anti-patterns we deliberately steer away from (from
[`../01-research/avoid-list.md`](../01-research/avoid-list.md); these are
**recommendations/inferences, not rejected-approach decisions** — formal rejection
routes through architecture review per `CLAUDE.md` §10):

- Webhook-only **or** cron-only as the sole sync mechanism; no reconciliation
  (A-SYNC-1/2).
- Skipping HMAC verification; heavy work inside the webhook request (A-SYNC-4/6).
- Naive retry without idempotency; manual-only recovery (A-RET-1/3).
- Email-only, reason-less, non-isolated error handling (A-LOG-1/2/3).
- "Real-time" labels on a cron/queue model; opaque/binary status (A-UX-1/4).
- Toggle-dense, jargon-heavy config with no defaults or inline help (A-UX-3, A-CFG-3).
- Blind mappings with no dry-run; long manual scope pastes with silent failure
  (A-CFG-1/2).
- Single-location-only inventory; writing the read-only `committed` quantity;
  manual post-import stock processing (A-INV-1/2/3).
- Legacy order-based fulfilment endpoints (A-FUL-1).
- Non-idempotent refunds; assuming payouts exist for all gateways (A-PAY-1/2).
- No rate-limit/GraphQL-cost handling (A-SYNC-5).
- Bot-blocked / sign-in-gated / stale documentation; no changelog (A-DOC-1/2/3).
- One-giant-module design; fragile `_inherits` delegation; treating a non-core
  queue dependency as turnkey without conscious decision (A-MOD-1/3/4).
- Exposing raw Odoo internals to end users (A-UX-2).

## Product non-negotiables

The things we will not compromise (**[Recommendation]** — the quality contract; the
*how* remains gated):

1. **Never silently lose or corrupt data.** Idempotency + reconciliation + safe
   destructive actions are mandatory, not optional (O-REL-1, A-IMP-1).
2. **Never leave a failure unrecoverable or unexplained.** Isolated, reason-coded,
   retryable failures with a next action (O-LOG-1).
3. **Never overstate reality.** Honest latency, freshness, limitations, and throttle
   status (O-UX-1, O-PREM-4).
4. **Never require developer intervention for normal operation.** A functional user
   can run and recover it (ux-ui-benchmark).
5. **Never couple to or endanger customer/base code.** Isolation from `adams_base`;
   upgrade-safe extension (O-MOD-1; `CLAUDE.md` §9).
6. **Never bypass Shopify/Odoo platform rules.** HMAC, protected-data windows,
   `committed` read-only, FulfillmentOrder, current API figures (**[Fact]** set).
7. **Never gate evaluation behind a wall or ship without tests.** Open docs/demo;
   regression tests for the classic defects at definition-of-done (`CLAUDE.md` §9,
   A-IMP-4).

## MVP inputs, not decisions

> **Candidates for RB-13 review only — not selected, sequenced, or committed**
> (DP-005 guard). Sourced from [`./feature-taxonomy.md`](./feature-taxonomy.md) and
> [`./capability-evidence-map.md`](./capability-evidence-map.md).

- **Candidate core (input):** connect + prove (guided setup, credential masking,
  test connection, readiness check); core object sync (products/variants/pricing/
  inventory/customers/orders/payments/fulfilment/refunds) at the demonstrated
  baseline; the sync + correctness engine (webhooks + reconciliation + scheduled +
  manual, idempotency, dedup/binding, retry/recovery); the operator UX (command
  center + recovery-first error center + honest freshness); role-based access.
- **Explicitly later / not-MVP (input):** advanced breadth (Markets, B2B, POS, gift
  cards, metafields, extended breadth), payouts, financial reporting, per-market
  pricing, custom-Python transforms, multi-company.
- **Open MVP-shaping questions:** single- vs multi-store; single- vs multi-company;
  which capability groups are core vs optional add-ons (feature flags); which
  persona (P1–P4) is the primary MVP target.

**This section decides nothing.** MVP is gated at RB-13 under the
evidence-consistency gate (DP-006).

## Later/advanced inputs, not decisions

> Premium breadth as **optional add-ons** on the core (input for RB-13/RB-14).

- Payout import + bank reconciliation (Shopify-Payments-gated — **[Fact]**;
  EM-demonstrated) (C-POUT-01/02).
- B2B (company accounts, VAT/VIES) — VT-demonstrated only (C-ADV-02).
- Shopify Markets & Catalogs, per-market pricing with dry-run (C-ADV-01, C-PRICE-03).
- POS order import; gift cards; metafields; abandoned-checkout→CRM, recommendations,
  Buy-with-Prime; advanced analytics/financial reporting (C-ADV-03…06, C-RPT-02).
- Returns/RMA lifecycle beyond baseline refunds (C-RET-02).

All are **later/optional inputs**; **none is committed**, and each still carries its
evidence-strength and conditionality (e.g. payouts gated to Shopify Payments).

## Architecture inputs, not decisions

> Routed to **AR-002…AR-008**, all **"Not decided / Evidence pending"**
> ([`../05-qa/architecture-review-log.md`](../05-qa/architecture-review-log.md)).
> This vision **chooses none** of them and re-litigates none (`CLAUDE.md` §10).

- **Distribution model (public App-Store vs custom/private) — OPEN (AR-002).** This
  is unresolved and gates several downstream conditionals. **We do not decide it.**
- **OAuth-first is a strong product/UX/security direction — but conditional.** OAuth
  is a platform *requirement* **only if** public/App-Store distribution is chosen;
  custom/private flows may use token/custom-app access (C-CONN-01, `B / A-if-public`;
  DP-006). **Not phrased as a finalized decision.**
- **Sync orchestration & queue framework — OPEN (AR-003).** `ir.cron` vs OCA
  `queue_job` is **not decided**; both carry trade-offs (**[Fact]** Odoo has no core
  queue). We state the *need* for out-of-band, resumable processing, not the *how*.
- **REST vs GraphQL vs hybrid — OPEN (AR-002).** **Not decided** (GraphQL is the
  Tier-1 convergence, but the custom-app scope is open).
- **Binding / dedup data model — OPEN (AR-005).** `ir.model.data` reuse vs a
  dedicated per-store binding model is **not decided**; no data models are defined.
- **Module boundaries & names — OPEN (AR-004).** A layered family is the direction;
  **no boundaries or names are defined.**
- **Inventory & fulfilment architecture — OPEN (AR-007/008).** Product intent
  (multi-location, write `available`/`on_hand` only, FulfillmentOrder-based) is
  Tier-1-anchored; the design is **not decided**.

## Open questions

Carried forward for RB-13 / RB-14 / ChatGPT (superset of the product-handoff list):

1. **Distribution model** (public App-Store vs custom/private) — decides
   OAuth-mandatory, GraphQL-only, billing/compliance webhooks (AR-002).
2. **Primary MVP persona** (P1 operator vs P2 admin/consultant) and **single- vs
   multi-store / single- vs multi-company** at MVP (RB-13).
3. **Core vs optional add-on grouping** and the feature-flag model (RB-13 / AR-004).
4. **Reconciliation cadence and scope**; per-object vs global freshness (AR-003/006).
5. **Error/retry taxonomy** — which errors auto-retry vs need humans (AR-006).
6. **Binding model** — `ir.model.data` vs dedicated; deleted-binding handling (AR-005).
7. **Queue framework** — `ir.cron` vs `queue_job`; Odoo-Online implications (AR-003).
8. **Payout modelling** for non-Shopify-Payments gateways; **Odoo edition gating**
   disclosure (Enterprise-only reports).
9. **Weak/blocked evidence** — does firming up Teqstars (403), EC/R5, or the 17
   unread VT Confluence articles change any product framing?
10. **Demo/docs hosting** and the built-in self-test scope (O-TEST-1, O-DOC-1).

## Review notes for ChatGPT

Please inspect and confirm:

1. **Positioning & thesis** — is "correct by design, honest by default, prove both
   to the operator" the right premium positioning, and are the five differentiation
   themes correctly prioritised as *inputs* (correctness + operator UX + easy-reliable
   onboarding first; breadth later)?
2. **Evidence discipline (DP-003/DP-004/DP-006)** — confirm no competitor claim is
   promoted to a fact; EM/VT-demonstrated evidence is weighted over SH/WK/EC/TQ
   claims; WK multi-company stays config-field-only, and conditional items (OAuth,
   distribution, queue, REST/GraphQL, multi-company, module boundaries, payouts,
   data models) stay conditional/open.
3. **No premature MVP/architecture** — confirm nothing in "Product principles",
   "Premium quality bar", "Differentiation", or the strategy sections reads as an MVP
   or architecture **decision** (DP-005 guard); flag any wording that hardens a
   candidate into a commitment.
4. **Personas** — are P1–P4 the right target users as **inference-level inputs**, and
   is the "which persona is primary MVP target" question correctly left open?
5. **Non-negotiables** — endorse or amend the seven product non-negotiables (the
   quality contract) without them implying a specific implementation.
6. **Sequencing** — confirm RB-13 (MVP implications) next, then RB-14 (architecture
   prep), both consuming this vision + the setup/UX principles.

> **This document decides nothing.** All principles, strategies, differentiation
> themes, and candidate lists are **inputs** for the gated RB-13 (MVP) and RB-14
> (architecture) reviews, subject to ChatGPT review (`CLAUDE.md` §4–§5, §8–§10).
