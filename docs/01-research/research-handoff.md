# Research Handoff (rolling)

> Continuity lives in GitHub, not chat. The **current sprint handoff (Sprint E)**
> is immediately below; the **Sprint D**, **Sprint C**, **Sprint B**, and **Sprint
> A** handoffs are retained underneath as history. The running **Sprint checkpoint
> log** (one note per stage, all sprints) is at the very bottom. The **product-side**
> handoff lives at
> [`../02-product/product-research-handoff.md`](../02-product/product-research-handoff.md).

---

# Product Sprint E Handoff

> **Product Sprint E — Product Vision, Quality Bar, UX Principles, and
> Differentiation Strategy.** Product strategy / synthesis only; **no-code gate in
> force** (`CLAUDE.md` §4–§5). High-power mode **not required** (synthesis of
> already-merged repo evidence — no new competitor crawling, no research fan-out).
> Maps to backlog item **RB-11 (product vision draft)**, feeding RB-13 (MVP
> implications) and RB-14 (architecture prep) — all gated.

## Session summary

Created the **product vision** (`docs/02-product/product-vision.md`) and the
**setup/UX principles** (`docs/02-product/setup-ux-principles.md`) for the Odoo 19 ↔
Shopify Connector, consuming the Sprint C research baseline and the Sprint D
canonical feature taxonomy + capability evidence map. The vision positions the
connector as **correctness-first, UX-first, recovery-first, observable, honest,
modular/customizable, performance-aware, evidence-based, upgrade-safe, and premium
but not bloated** (simple for normal users, powerful for advanced users). It states
the product thesis, target personas (inference-level P1–P4), core customer problems,
ten product principles, a premium quality bar, a five-theme differentiation strategy,
per-domain strategies (UX / reliability / modularity / performance / security /
docs-trust), seven product non-negotiables, and explicit **MVP / later / architecture
inputs (not decisions)**. The UX doc defines a UX north star and 12 principles plus
per-area principle sets. **No connector code, no Odoo module, no MVP finalization, no
architecture decisions, no ADRs, no implementation plan, and no module boundaries**
were produced. Synthesis was **worker-owned** (no fan-out).

## Branch and commits

**Working branch:** `claude/sprint-e-product-strategy-gd2kfs` (the harness-designated
branch; based on `Shopify-connector` @ `9a744f7`, the merged **PR #52** Sprint D
baseline). **Branch-name note for ChatGPT (flagged):** the Sprint E prompt body named
`product/sprint-e-product-vision-quality-bar`, but the session's hard git rule
designated `claude/sprint-e-product-strategy-gd2kfs` ("never push to a different
branch without explicit permission"), so work proceeded on the harness-designated
branch; **the PR still targets `Shopify-connector`**; `main` and plain `dev`
untouched.

| Hash | Message |
| --- | --- |
| `ce36ffc` | docs: start sprint e product vision |
| `d3da053` | docs: add product vision |
| `5561db3` | docs: add setup ux principles |
| _(this commit)_ | docs: finalize sprint e product handoff |

## Files created or updated

**Product (`docs/02-product/`)**
- `product-vision.md` (new — main deliverable), `setup-ux-principles.md` (new),
  `product-research-handoff.md` (updated — Sprint E section).

**Research (`docs/01-research/`)**
- `research-handoff.md` (this file — Sprint E section + checkpoints).

**QA / quality memory (`docs/05-qa/`)**
- `defect-pattern-log.md` (updated — Sprint E note: DP-006 gate applied, not
  re-triggered; no new occurrence), `architecture-review-log.md` (updated — Sprint E
  non-decision note), `rejected-approaches-log.md` (updated — nothing rejected),
  `technical-debt-register.md` (updated — no debt).

**No forbidden files touched** (no `*.py`/`*.xml`/`*.csv`/manifests/modules/CI/
Docker; no `addons/**`; no `docs/03|04|07|08`; no `.claude/skills|agents`).

## Product vision summary

- **What:** a best-in-class, modular, reliable Odoo 19 ↔ Shopify connector — a
  correct, observable sync core wrapped in an operator experience, delivered as an
  isolated, upgrade-safe addon family.
- **Positioning:** *correct by design, honest by default — and can prove both to the
  operator.*
- **Thesis:** breadth is table stakes; win on **demonstrated correctness** and the
  **operator experience**, ship the demonstrated breadth as a clean baseline, and
  offer premium breadth as **optional add-ons** on an honest, modular core.
- **Premium quality bar** = correctness / experience / trust, **not** feature count;
  seven **non-negotiables** form the quality contract.
- **Differentiation (inputs):** (1) demonstrated correctness (idempotency +
  reconciliation + rate-limit awareness), (2) command center + recovery-first errors
  together, (3) easy onboarding with real reliability, (4) honesty/transparency, (5)
  premium breadth as clean add-ons.

## UX principles summary

- **North star:** the operator always knows *is everything OK / what failed and why /
  what do I do next* and can act without reading source or filing a ticket.
- **12 principles:** guided setup; prove readiness before sync; progressive
  disclosure; honest status & freshness; command center over scattered menus;
  recovery-first errors; safe-by-default actions; human-readable logs; guided
  mappings; role-aware UX; modular feature visibility; documentation mirrors the
  product — plus per-area principle sets. **No screens or menus are designed.**

## Evidence discipline

- **DP-003 applied:** competitor UX/product statements stay claims; TQ (docs 403) and
  EC (no screenshots) stay claim-only/weak; SH ✅ rest on captions; EM/VT-demonstrated
  evidence is weighted highest.
- **DP-004 applied:** WK multi-company kept **config-field-only (➖)**; market promises
  not treated as demonstrated bidirectionality.
- **DP-005 applied:** every principle/candidate is an **input**, not a decision;
  MVP=RB-13 and architecture=RB-14/AR-002…AR-008 stay gated.
- **DP-006 evidence-consistency gate applied:** conditional platform items (OAuth,
  distribution, queue framework, REST/GraphQL, multi-company, module boundaries,
  payouts, data models) stay conditional/open; improvement opportunities (auto-apply,
  unified command center, freshness) labelled **inference**, not demonstrated
  competitor capability. **No claim promoted to a fact; no on-page detail invented.**

## MVP inputs, not decisions

Candidate core (input): connect+prove; core object sync at the demonstrated baseline;
the sync+correctness engine (webhooks + reconciliation + scheduled + manual,
idempotency, dedup/binding, retry/recovery); operator UX (command center +
recovery-first errors + honest freshness); role-based access. Explicitly later
(input): advanced breadth, payouts, financial reporting, per-market pricing,
custom-Python transforms, multi-company. **MVP is not finalized** — candidates for
**RB-13** only. Open: single/multi-store; single/multi-company; core vs optional
add-on grouping; **primary MVP persona (P1 vs P2)**.

## Architecture inputs, not decisions

The vision/UX principles supply **product-intent inputs** to **AR-002…AR-008** — all
remain **"Not decided / Evidence pending."** No distribution model, OAuth mandate,
REST/GraphQL choice, queue framework, binding data model, module boundary/name, or
inventory/fulfilment design is decided. A **non-decision note** was added to
`architecture-review-log.md`.

## Open questions

Distribution model (AR-002); primary MVP persona + single/multi-store & company
(RB-13); core vs add-on grouping / feature-flag model (RB-13/AR-004); reconciliation
cadence + per-object vs global freshness (AR-003/006); error/retry taxonomy (AR-006);
binding model + deleted-binding handling (AR-005); queue framework + Odoo-Online
(AR-003); non-Shopify-Payments payout modelling; Odoo edition gating disclosure;
whether firming up weak/blocked evidence (TQ 403, EC/R5, 17 unread VT Confluence)
changes any product framing; demo/docs hosting + self-test scope.

## Learning feedback loop

- **New issues discovered:** none. No new defect pattern emerged. The **DP-006
  evidence-consistency gate** (3rd-occurrence, ESCALATED) was **applied, not
  re-triggered**; DP-003/DP-004/DP-005 prevention rules were applied throughout (no
  claim-as-fact; config field ≠ demonstrated support; classification = input, not
  decision).
- **Repeated issue patterns:** none at threshold; no new occurrence added to any
  category. Escalation gates remain honoured by the no-code gate.
- **Rules/checklists updated:** none required — existing rules were sufficient and
  applied. QA logs received non-decision / no-new-issue notes only.
- **New rejected approaches:** none (nothing evaluated to rejection; noted in
  `rejected-approaches-log.md`).
- **New technical debt:** none (no code; noted in `technical-debt-register.md`).
- **Architecture concerns:** vision/UX principles now supply product-intent inputs to
  AR-002…AR-008 — recorded as a **non-decision note** in `architecture-review-log.md`;
  **all rows stay Not decided / Evidence pending.**
- **Tests or review gates needed:** none active (synthesis). The DP-006
  evidence-consistency gate remains the standing pre-MVP/architecture review gate.
- **Should future prompts change? No** (beyond what Sprint D encoded) — keep every
  principle/candidate an **input** with MVP=RB-13 / architecture=RB-14 gating, keep
  synthesis worker-owned, keep conditional platform items conditional (DP-006). Branch
  reality remains the harness-designated `claude/...` branch while the PR targets
  `Shopify-connector`.

## What ChatGPT should review

1. **Positioning & thesis** — is "correct by design, honest by default, prove both to
   the operator" right, and are the five differentiation themes correctly prioritised
   as inputs?
2. **Evidence discipline (DP-003/004/006)** — no claim-as-fact; EM/VT weighted over
   SH/WK/EC/TQ; conditional items stay conditional/open.
3. **No premature MVP/architecture (DP-005 guard)** — confirm nothing reads as a
   decision or final UI/menus; flag any hardening.
4. **Personas** — are P1–P4 reasonable inference-level inputs, with "primary MVP
   persona" left open?
5. **Non-negotiables** — endorse/amend the seven-item quality contract.
6. **Sequencing** — confirm RB-13 next, then RB-14, consuming this vision + UX
   principles.
7. **Branch-name discrepancy** — confirm working on
   `claude/sprint-e-product-strategy-gd2kfs` (PR → `Shopify-connector`) is acceptable.

## Recommended next session

**RB-13 (MVP scope implications — not finalized)** consuming this vision + UX
principles + the Sprint D taxonomy/evidence map under the DP-006 evidence-consistency
gate, then **RB-14 (architecture preparation)** against AR-002…AR-008 — all gated and
ChatGPT-reviewed. Optionally firm up weak/blocked evidence (TQ 403; EC/R5; 17 unread
VT Confluence). Keep the no-code gate; one scoped objective per session.

## Stop confirmation

Stopped at the Sprint E boundary as instructed: three stage commits on the
harness-designated working branch plus this handoff commit, **one draft PR** targeting
**`Shopify-connector`**, **not merged**. **No** code, **no** Odoo module, **no** MVP
finalization, **no** architecture decisions, **no** ADRs, **no** implementation plan,
**no** module boundaries. `main` and plain `dev` untouched. Awaiting ChatGPT review.

## Quality gate confirmation (Sprint E)

- [x] Session handoff updated (this block + product-research-handoff.md Sprint E).
- [x] Quality feedback loop checked (this file + `../05-qa/` logs).
- [x] New learning captured in the correct file (no new issue; DP-006 gate applied —
  noted in `defect-pattern-log.md`).
- [x] Any rejected approach logged (none — noted in `rejected-approaches-log.md`).
- [x] Any accepted technical debt logged (none — noted in `technical-debt-register.md`).
- [x] Any repeated issue pattern escalated per §4 (none at threshold; DP-006 gate
  applied, not re-triggered).

---

# Research/Product Sprint D Handoff

> **Research/Product Sprint D — Canonical Feature Taxonomy and Evidence-Based
> Capability Model.** Research/synthesis-only; no-code gate in force (`CLAUDE.md`
> §4–§5). High-power mode **not required** (focused synthesis of already-merged
> Sprint C evidence — no new competitor crawling). Maps to backlog item **RB-12
> (canonical feature taxonomy)**, feeding RB-11 (vision), RB-13 (MVP implications),
> and RB-14 (architecture prep) — all gated.

## Session summary

Converted the Sprint C competitor research into a **canonical feature taxonomy**
(`docs/02-product/feature-taxonomy.md`) and a **capability evidence map**
(`docs/02-product/capability-evidence-map.md`) for the Odoo 19 ↔ Shopify Connector,
and wrote the product-side handoff (`docs/02-product/product-research-handoff.md`).
The taxonomy normalizes the messy competitor feature matrix into **20 canonical
domains** and ≈90 **canonical capabilities**, each classified by evidence
status/strength, capability type (product-UX / reliability / configuration /
architecture), candidate class (baseline / premium / advanced-later / optional
add-on / unknown), MVP relevance (candidate / later / unknown), and
architecture-review dependency (AR-002…AR-008). Every classification is an
**input**, not a decision. **No connector code, no Odoo module, no MVP
finalization, no architecture decisions, no ADRs, no implementation plan, and no
module boundaries** were produced. No new competitor sources were crawled — the
sprint synthesises **already-merged repo evidence only**, preserving per-claim
classification and DP-003/DP-004 discipline. Synthesis was **worker-owned** (main
thread), not fanned out, so claim classification stayed centrally governed.

### Sprint D revision (PR #52 review — 2026-07-01)

ChatGPT review returned **REVISE** (small taxonomy precision patch); corrected on
the same branch (`docs: correct sprint d taxonomy precision`), logged as **DP-006**:

- **Removed the `SH` abbreviation collision** — `SH` = **only** sh_shopify_connector
  / Softhealer; Shopify official docs are keyed **SHOPIFY-OFFICIAL** (Odoo official
  = **ODOO-OFFICIAL**).
- **OAuth-first (C-CONN-01) official-platform dependency made conditional** — strong
  UX/security direction, competitor-demonstrated (VT), but a platform *requirement*
  **only if public/App-Store distribution is chosen**; custom/private flows may use
  token/custom-app access. AR-002 open; not a finalized decision. Evidence strength
  `A` → `B / A-if-public`.
- **Stock import (C-INV-04) reframed** as "Stock import with controlled apply/review"
  — auto-apply is an **improvement/inference, not demonstrated**; AR-007 still applies.
- **Webkul import-stock coverage corrected** to **⬜ (not found)** per matrix §3 (was
  ✅); matrix-consistent coverage EM✅ VT✅ SH✅ TQ🟨 EC🟨 WK⬜.
- **Escalation:** unsupported-assumption/weak-research reaches its **3rd occurrence**
  (DP-003, DP-004, DP-006) → an **evidence-consistency gate** was recorded in
  `defect-pattern-log.md` (implementation stays paused by the existing no-code gate;
  no capability may enter MVP/architecture as a decision until its evidence strength,
  conditionality, and competitor coverage are ChatGPT-reviewed). **No implementation
  task is set.**

## Branch and commits

**Working branch:** `claude/feature-taxonomy-sprint-d-t8d2t0` (the
harness-designated branch; based on `Shopify-connector` @ `e18ba8e`, the merged
**PR #51** Sprint C baseline). **Branch-name note for ChatGPT (flagged):** the
Sprint D prompt body named `product/sprint-d-feature-taxonomy`, but the session's
hard git rule designated `claude/feature-taxonomy-sprint-d-t8d2t0` ("never push to
a different branch without explicit permission"), so work proceeded on the
harness-designated branch; **the PR still targets `Shopify-connector`**; `main` and
plain `dev` untouched.

| Hash | Message |
| --- | --- |
| `2e297ba` | docs: start sprint d feature taxonomy |
| `70391b9` | docs: add canonical feature taxonomy |
| `aa5d2c4` | docs: add capability evidence map |
| _(this commit)_ | docs: finalize sprint d taxonomy handoff |

## Files created or updated

**Product (`docs/02-product/`)**
- `feature-taxonomy.md` (new — main deliverable), `capability-evidence-map.md`
  (new), `product-research-handoff.md` (new).

**Research (`docs/01-research/`)**
- `research-handoff.md` (this file — Sprint D section + checkpoints).

**QA / quality memory (`docs/05-qa/`)**
- `defect-pattern-log.md` (updated — DP-005 + counter), `architecture-review-log.md`
  (updated — Sprint D non-decision note), `rejected-approaches-log.md` (updated —
  Sprint D "nothing rejected" note), `technical-debt-register.md` (updated —
  Sprint D "no debt" note).

**No forbidden files touched** (no `*.py`/`*.xml`/`*.csv`/manifests/modules/CI/
Docker; no `addons/**`; no `docs/03|04|07|08`; no `.claude/skills|agents`).

## Taxonomy summary

- **20 domains:** (1) connection/auth/setup, (2) dashboard/command center, (3)
  product catalog, (4) variants/media, (5) pricing, (6) inventory/locations, (7)
  customers/companies/addresses, (8) orders/lifecycle, (9) invoices/payments/
  journals, (10) fulfillment/tracking, (11) refunds/returns/cancellations, (12)
  payouts/reconciliation, (13) webhooks/scheduled/manual/reconciliation, (14)
  queue/jobs/retries, (15) logs/errors/observability, (16) mapping/matching/dedup,
  (17) multi-store/company/permissions, (18) advanced Shopify (Markets/B2B/POS/gift
  cards/metafields), (19) reporting/analytics, (20) docs/support/demo.
- **≈90 canonical capabilities**, each with the required attribute block; **8
  cross-cutting groups** (idempotency-by-default, recovery-first ops, honesty/
  transparency, safe-by-default destructive actions, progressive disclosure,
  feature flags, modularity/extension points, multi-tenancy/permissions).
- **Required canonical capabilities represented:** idempotency, duplicate
  prevention, GID binding, HMAC verification, webhook-id dedup, fast-ack, scheduled
  + manual reconciliation, retry classification, auto-retry, manual retry,
  rate-limit/GraphQL-cost throttling, bulk ops, per-record isolation, resumable
  jobs, reason-coded logs, audit trail, recovery-first error center; setup wizard,
  OAuth-first, credential masking, test connection, scope/readiness check, health
  indicators, named-cause diagnostics, command center, activity timeline, queue
  status, failure counts, quick actions, dry-run/preview, guided mapping,
  progressive disclosure, inline help, empty states, recovery actions, sync
  freshness; feature flags, optional add-ons, domain-isolated/per-store config,
  per-company isolation, role-based access, extension points, mapping/transport
  extensibility (architecture inputs); payouts, advanced refunds, Markets, B2B, POS,
  gift cards, metafields, abandoned-checkout→CRM, recommendations, Buy-with-Prime,
  advanced analytics, app-store packaging, public demo/docs/changelog.

## Evidence discipline

- **DP-003 applied:** competitor claims stay claims; TQ (docs 403) and EC (no
  screenshots) support is marked **claim-only / weak**; SH ✅ marks rest on captions
  (medium-behaviour, low-trust).
- **DP-004 applied:** WK multi-company kept as a **config field only (➖)**; SH
  multi-company kept **not-found**; EC product export kept **not-found**; `✅`/
  "demonstrated" used only with a specific demonstrated workflow/screenshot/dated
  release note/explicit doc.
- **Evidence strength scale (A–E)** in the evidence map: **A** official-platform
  requirement (≈22 caps), **B** strong competitor demonstration (EM/VT-led, ≈45),
  **C** mixed/partial (≈8), **E** whitespace/inference (freshness, empty states,
  plus platform-required-but-undemonstrated items: reconciliation surface,
  rate-limit throttling, webhook-id dedup).
- **No competitor claim promoted to a Tier-1 fact; no on-page detail invented.**

## MVP inputs, not decisions

Capabilities tagged **MVP relevance: candidate** cluster around a **correct,
observable core** (connect+prove; core object sync; sync+correctness engine;
operator command center + recovery-first errors; role-based access). Advanced
breadth (Domain 18), payouts, financial reporting, per-market pricing, custom-Python
transforms, and multi-company are tagged **later**. **MVP is not finalized** — these
are candidates for **RB-13** review only. Open MVP-shaping questions: single- vs
multi-store; single- vs multi-company; core vs optional add-on grouping.

## Architecture inputs, not decisions

The taxonomy maps capabilities to **AR-002…AR-008** (API/distribution; sync
orchestration/queue; module boundaries; binding/dedup; error/retry/idempotency;
inventory; fulfillment) — **all remain "Not decided / Evidence pending."** No
queue framework, REST/GraphQL choice, data model, or module boundary/name is
decided. A **non-decision evidence note** was added to
`architecture-review-log.md`.

## Open questions

Distribution model (public vs custom → AR-002); single/multi-store & single/multi-
company at MVP (RB-13); reconciliation cadence/scope + per-object vs global
freshness; error/retry taxonomy; binding model (`ir.model.data` vs dedicated;
deleted-binding handling — AR-005); queue framework (`ir.cron` vs `queue_job`;
Odoo-Online implications — AR-003); core vs optional add-on grouping; firming up
weak/blocked evidence (Teqstars 403, EC/R5 setup guide, 17 unread VT Confluence);
non-Shopify-Payments payout modelling; Odoo edition gating disclosure.

## Learning feedback loop

- **New issues discovered:** one — **DP-005** (premature-decision risk, category
  #4 premature architecture): a feature taxonomy's *candidate / premium / later*
  labels and *architecture-dependency* tags could be **misread as MVP or
  architecture decisions**. **Prevented/Mitigated** by explicit "inputs, not
  decisions" framing throughout, dedicated "MVP-candidate inputs, not decisions"
  and "Capabilities requiring architecture review" sections, per-field gating
  language, and closing "decides nothing" notes; MVP=RB-13 and architecture=RB-14/
  AR-002…AR-008 remain gated.
- **Repeated issue patterns:** DP-005 is the **1st** occurrence of category #4
  (premature architecture) in the defect-pattern log — no 2×/3× escalation. The
  existing unsupported-assumption/weak-research thread (DP-003, DP-004) was **not**
  re-triggered: DP-004's prevention rule (config field ≠ demonstrated support;
  market promise ≠ demonstrated bidirectionality) was **applied throughout** this
  synthesis (WK multi-company ➖, SH multi-company not-found, EC export not-found,
  TQ claim-only), which is the intended anti-repetition behaviour.
- **Rules/checklists updated:** added **DP-005** + prevention rule to
  `defect-pattern-log.md` (a normalized taxonomy must label every candidate/
  classification as an **input**, not a decision; MVP and architecture stay gated).
- **New rejected approaches:** none (synthesis-only; noted in
  `rejected-approaches-log.md`).
- **New technical debt:** none (no code; noted in `technical-debt-register.md`).
- **Architecture concerns:** the taxonomy now supplies **capability-level inputs**
  to AR-002…AR-008 — recorded as a **non-decision note** in
  `architecture-review-log.md`. **All rows stay "Not decided / Evidence pending."**
- **Tests or review gates needed:** none active (synthesis). For implementation
  (gated), the regression-test set seeded in A-IMP-4 (duplicate orders,
  multi-location double-decrement, missed-webhook reconciliation, idempotent
  refunds, timezone/paging) now maps to specific capability IDs.
- **Should future prompts change? Yes** — product-synthesis prompts should (1)
  require every capability classification to be labelled an **input/candidate** with
  MVP=RB-13 / architecture=RB-14 gating stated (now encoded via DP-005), and (2)
  keep synthesis **worker-owned** (not fanned out) so claim classification stays
  centrally governed. Branch reality remains the harness-designated `claude/...`
  branch while the PR targets `Shopify-connector`.

## What ChatGPT should review

1. **Taxonomy completeness & naming** — are the 20 domains + ≈90 capabilities the
   right canonical decomposition (nothing missing/duplicated/mis-placed)?
2. **Evidence discipline** — spot-check DP-003/DP-004: no claim-as-fact; `✅` only
   where demonstrated; WK multi-company ➖, SH multi-company not-found, EC export
   not-found, TQ claim-only all reflected in both product files.
3. **Classification calibration** — are baseline/premium/advanced-later/optional
   and MVP candidate/later/unknown reasonable **as inputs**? Flag anything reading
   like a premature decision (DP-005 guard).
4. **Architecture routing** — confirm AR-002…AR-008 mapping is correct and that
   **no architecture is decided** (no queue framework, no REST/GraphQL, no module
   boundaries/names, no data models).
5. **Whitespace priorities** — endorse/re-rank the correctness whitespace
   (reconciliation, idempotency, rate-limit throttling, webhook-id dedup) and the
   operator-UX whitespace (command center + recovery-first errors) as leading
   differentiation inputs for RB-13/RB-14 — **without** locking MVP.
6. **Branch-name discrepancy** — confirm working on `claude/feature-taxonomy-sprint-d-t8d2t0`
   (PR → `Shopify-connector`) is acceptable.
7. **Next-sprint sequencing** — confirm RB-11 (vision) / RB-13 (MVP implications) as
   the next gated step, then RB-14 (architecture prep).

## Recommended next session

**RB-11 (product vision draft)** and/or **RB-13 (MVP scope implications — not
finalized)**, consuming this taxonomy + evidence map, then feeding **RB-14
(architecture preparation)** against AR-002…AR-008 — all gated and ChatGPT-reviewed.
Optionally firm up weak/blocked evidence (Teqstars 403; EC/R5 setup guide; 17 unread
VT Confluence) if ChatGPT wants firmer classification. Keep the no-code gate; one
scoped objective per session.

## Stop confirmation

Stopped at the Sprint D boundary as instructed: four stage commits on the
harness-designated working branch, **one draft PR** targeting **`Shopify-connector`**,
**not merged**. **No** code, **no** Odoo module, **no** MVP finalization, **no**
architecture decisions, **no** ADRs, **no** implementation plan, **no** module
boundaries. `main` and plain `dev` untouched. Awaiting ChatGPT review.

## Quality gate confirmation (Sprint D)

- [x] Session handoff updated (this block + product-research-handoff.md).
- [x] Quality feedback loop checked (this file + `../05-qa/` logs).
- [x] New learning captured in the correct file (DP-005 in `defect-pattern-log.md`).
- [x] Any rejected approach logged (none — noted in `rejected-approaches-log.md`).
- [x] Any accepted technical debt logged (none — noted in `technical-debt-register.md`).
- [x] Any repeated issue pattern escalated per §4 (none at threshold; DP-005 1st occurrence of #4; DP-004 prevention applied, not re-triggered).

---

# Research Sprint C Handoff

> **Research Sprint C — High-Power Competitor Deep Dives, Screenshot/UX Evidence,
> and Workflow Extraction.** Research-only; no-code gate in force (`CLAUDE.md`
> §5). High-power research mode **explicitly authorized** for this sprint. Maps to
> backlog items **RB-02.* (competitor deep dives)**, **RB-03.1 (feature matrix)**,
> **RB-04.1 (UX/UI benchmark)**, **RB-07.1 (common patterns)**, **RB-08.1
> (best-in-class)**, **RB-09.1 (gaps/opportunities)**, and **RB-10.1 (avoid-list)**.

## Session summary

Studied the **eight user-provided competitor resources (R1–R8)** from real
evidence and produced the full Sprint C research set: **source notes + an
analysed screenshot/visual inventory**, **six competitor deep dives** (Webkul,
Teqstars, Emipro, VentorTech, ecommerce_shopify, sh_shopify_connector + a
blocked-source record for the Google Doc), a **first cross-competitor feature
matrix**, a **UX/UI benchmark**, and the **common-patterns / best-in-class /
gaps-opportunities / avoid-list** synthesis. Evidence was gathered with a
**controlled high-power capture→verify fan-out** (one capture agent + one
adversarial verifier per source) and synthesised by the worker so claim
classification and the no-code/no-MVP/no-architecture gate stayed owned centrally.
**Every claim is cited and classified**; competitor capability statements remained
**competitor claims** unless a documented workflow/screenshot demonstrated them;
**no competitor claim was promoted to a Tier-1 fact**; blocked sources were
recorded, **never bypassed**. **No connector code, no Odoo module, no MVP scope,
and no architecture decisions** were produced.

## Branch and commits

**Working branch:** `claude/research-sprint-c-competitors-hgoo8t` (the
harness-designated branch; based on `Shopify-connector` @ `d6fbcdb`, the merged
**PR #50** Sprint B baseline). **Branch-name note for ChatGPT (flagged):** the
Sprint C prompt body named `research/sprint-c-competitor-deep-dives-ux-evidence`,
but the session's hard git rule designated `claude/research-sprint-c-competitors-hgoo8t`
("never push to a different branch without explicit permission"), so work proceeded
on the harness-designated branch; **the PR still targets `Shopify-connector`**;
`main` and plain `dev` untouched.

| Hash | Message |
| --- | --- |
| `6b07fad` | docs: start sprint c high-power competitor research |
| `e1c5ec4` | docs: capture competitor source and screenshot evidence |
| `1e027a0` | docs: add competitor deep dives |
| `da93ba9` | docs: add competitor matrix and ux benchmark |
| `890ce0b` | docs: synthesize competitor patterns and opportunities |
| _(this commit)_ | docs: finalize research sprint c handoff |

## High-power research mode used

**Yes — explicitly authorized and documented before launch** (the
**Sprint C high-power research plan** below was committed in `6b07fad` before any
agent ran). **Workstreams:** a `pipeline()` workflow of **one capture agent per
source (R1–R8)** returning structured, cited, claim-classified evidence (access
status, feature claims, reconstructed workflows, visuals, reliability signals,
release notes, quotes, open questions), each followed by **one adversarial
verifier** that re-read the source and **downgraded anything not literally
supported** (16 agents, 137 tool calls). **Synthesis/verification:** the worker
read every source digest and wrote all deliverables, preserving per-claim
classification and citations. **Unsupported-claim prevention:** strict claim
classes on every line; competitor claims never elevated to facts; blocked/unknown
stated as such; no hidden-feature guessing. **Result:** all 8 sources captured;
the verifier produced material corrections (e.g. **R2 Teqstars Partial→Blocked**;
**ecommerce_shopify "real-time"→cron**; **sh_shopify_connector multi-company→
not-found**), logged as **DP-003**.

### Sprint C high-power research plan (as committed pre-launch)

- **Why high-power mode is needed:** eight competitor resources, several
  multi-page (Emipro ~35 sub-pages; VentorTech 28-article Confluence hub) and two
  previously gated (R2 403; R5 login wall), had to be studied from real evidence
  with verification in one controlled pass.
- **Workstreams / agents:** one capture agent per source (R1–R8) + one adversarial
  verifier per source; worker-owned synthesis.
- **Sources:** R1 Webkul · R2 Teqstars docs (+Apps listing) · R3 Emipro tree ·
  R4 VentorTech Confluence · R5 Google Doc · R6 ecommerce_shopify · R7 VentorTech
  site/ecosystem/Apps · R8 sh_shopify_connector. Tier-1 grounding only from the
  existing official baselines.
- **Screenshots / UI evidence:** analysed markdown inventory (proxy fetcher returns
  markdown/alt-text, not pixels); binaries not forced (sprint rule allows the
  fallback); no auth bypass for any visual.
- **Files to update:** the Sprint C allowed-files set only (listed below).
- **Stop condition:** all accessible sources captured+verified; blocked sources
  documented without bypass; nine deliverables + evidence written, cited,
  classified; QA logs + handoff updated; quality gate satisfied — then stop.
- **Verification method:** two-pass capture→verify; downgrade anything not literally
  on the page; reuse the DP-001 verification gate.
- **Unsupported-claim prevention:** strict claim classification; no claim→fact
  elevation; blocked/unknown stated; no hidden-feature guessing.

## Files created or updated

**Source materials (`docs/00-source-materials/`)**
- `competitor-source-notes.md` (new), `competitor-screenshot-inventory.md` (new),
  `screenshots/README.md` + `screenshots/{webkul,teqstars,emipro,ventortech,odoo-apps}/README.md` (new).

**Research (`docs/01-research/`)**
- `competitor-deep-dives.md` (new), `competitor-feature-matrix.md` (new),
  `ux-ui-benchmark.md` (new), `common-patterns.md` (new),
  `best-in-class-observations.md` (new), `gaps-opportunities.md` (new),
  `avoid-list.md` (new), `resource-inventory.md` (updated — Sprint C access
  changes), `research-handoff.md` (this file).

**QA / quality memory (`docs/05-qa/`)**
- `defect-pattern-log.md` (updated — DP-003 + counter), `architecture-review-log.md`
  (updated — non-decision Sprint C evidence note), `rejected-approaches-log.md`
  (updated — avoid-list-is-not-rejection note), `technical-debt-register.md`
  (updated — Sprint C no-debt note).

**No forbidden files touched** (no `*.py`/`*.xml`/`*.csv`/manifests/modules/CI/
Docker; no `addons/**`; no `docs/02|03|04|07|08`; no `.claude/skills|agents`).

## Source access results

No auth was bypassed. **Accessible (5):** R1 Webkul, R3 Emipro, R6
ecommerce_shopify, R7 VentorTech site/ecosystem/Apps, R8 sh_shopify_connector —
**plus the Teqstars Odoo Apps listing** as an accessible R2 surrogate. **Partial
(1):** R4 VentorTech Confluence (anonymous banner; 11 of 28 child articles read).
**Blocked (2):** **R2 Teqstars docs host** (HTTP 403 bot-block on the whole
`docs.teqstars.com`, 19.0 **and** 16.0 — verifier downgraded R2 from Partial to
**Blocked**), **R5 Google Doc** (sign-in wall). **New cross-source findings:**
(a) the Teqstars **Apps Store listing is accessible** ($326.20, OPL-1, 83×5.0) and
supplied the R2 evidence; (b) **R5 is the "Get Started" guide for R6
`ecommerce_shopify`** (R6's CTA 301-redirects to that exact doc). Full evidence:
`docs/00-source-materials/competitor-source-notes.md` and the Sprint C section of
`resource-inventory.md`.

## Screenshots / UI evidence captured

Analysed visual inventory in `competitor-screenshot-inventory.md` (no binary files
saved — proxy fetcher returns markdown/alt-text; sprint rule allows the markdown
fallback). **Most demonstrative:** **Emipro** (~29 **real `.png`** screenshots of
queues/Log Book/config) and **VentorTech R4** (traffic-light webhook health,
External-Location mapping, Preview/Report dry-run). **Caption-only/weak:**
Teqstars (17 captions; **docs screenshots 403-blocked**), VentorTech R7 (alt-text
flows). **None:** **ecommerce_shopify (no UI screenshots at all)**; Google Doc
(blocked). sh_shopify_connector has the broadest caption walkthrough (~29 groups)
but no rendered-image verification.

## Competitor deep dives completed

All six in `competitor-deep-dives.md`: **Webkul, Teqstars, Emipro, VentorTech,
ecommerce_shopify, sh_shopify_connector**, plus a **blocked-source record** for the
Google Doc. Each separates competitor claims from facts and from demonstrated
workflows, with per-area feature classification, workflow reconstruction, UX,
reliability, maintenance, strengths/weaknesses, learn/do-better/avoid, and open
questions.

## Key feature findings

- **GraphQL is the converging API** (VentorTech migrated REST→GraphQL Jan 2026;
  all position on it) — consistent with Tier-1.
- **Webhooks + scheduled + manual** is the table-stakes sync shape; **staging/
  queues** are near-universal — **except ecommerce_shopify (cron-only, no
  webhooks, email-only errors)** and Webkul (no webhooks; Feeds staging).
- **Feature-breadth leaders:** sh_shopify_connector (gift cards, abandoned-
  checkout→CRM, recommendations, Buy-with-Prime), Teqstars-on-paper (Markets/B2B/
  payouts/queue — unverified), Emipro (payouts/Markets/metafields/analytic,
  demonstrated).
- **Whitespace (no competitor demonstrates well):** **named rate-limit/cost-aware
  throttling** (none), **first-class user-visible reconciliation** (none),
  **automatic retry** (only VentorTech), **B2B** (only VentorTech), **payout
  reconciliation** (only Emipro demonstrated).
- **Pricing (on-page 2026-06-30):** WK $170 · TQ $326.20 · EC $195.56 · SH
  $168.81 · VT €499 / $569.16; EM price not in docs.

## Key UX/UI findings

- **Best diagnostics — VentorTech:** traffic-light webhook health with a **named
  cause + fix hint**; Preview/Report dry-run; Failed-Job Notifications;
  irreversible-action warnings; honest PII disclosure.
- **Best observability — Emipro:** state-coloured queues + per-line reason-coded
  Log Lines + Log Book.
- **Best monitoring — sh_shopify_connector:** Integration Dashboard + **daily
  activity chart** + failure counts + re-export recovery flag; access-right-gated
  setup.
- **Frustrations to avoid:** "real-time" mislabelling (WK/EC/SH); raw cron
  internals exposed (WK); manual stock-adjustment (EM); email-only errors (EC);
  technical install (VT odoo.conf/queue_job; not Odoo Online); toggle-dense config;
  gated/blocked docs (EC/TQ).
- **No connector has a unified command center + recovery-first error center
  together** — a clear UX differentiator.

## Key reliability findings

- **VentorTech leads (demonstrated by dated release notes):** GraphQL
  **`@idempotent`** directives (Shopify 2026-04), **automatic retry** of safe
  ops, a real **`queue_job`** async queue, HMAC-SHA256 webhooks, and openly
  disclosed **CRITICAL silent-data-loss fixes** (paging, timezone).
- **Emipro:** strong observability (Log Book), email/SKU dedup, stored-reference
  re-export blocking, manual missed-webhook recovery — **but manual-only retry**
  and a **stale v19 changelog**, and its docs cite the **outdated Shopify
  "19 retries/48h"** figure (Tier-1: 8/4h).
- **Across the field:** idempotency is mostly implicit; **rate-limit handling is
  absent**; reconciliation is implicit; "real-time" is overstated. These map onto
  Tier-1 (webhook delivery not guaranteed → reconcile; `@idempotent` from 2026-04).

## Common patterns

Strongly common (≥2 demonstrate): custom-app connect; bidirectional core sync;
**staging/queue before commit**; scheduled + manual sync; SKU/barcode + email
dedup + Shopify-ID write-back; auto-workflow; fulfillment/tracking write-back;
reason-coded in-app logs; per-record failure isolation; GraphQL. Rare/
differentiating: automatic retry, idempotency directives, real job queue,
traffic-light health, dry-run, payouts, gift cards, B2B, abandoned-checkout→CRM.
**Missing across the field:** rate-limit/cost throttling, first-class
reconciliation, a unified command center, honest latency, documented HMAC.
(`common-patterns.md`.)

## Best-in-class observations

Onboarding (VT OAuth + scope/connection test; WK Test Connection), product sync
(EM incremental + CSV fallback; VT testable directional mapping), order flow (VT
auto-workflow pipeline; EM multi-payment fidelity), inventory (VT quantity-field
choice + multi-company; EM deterministic export), fulfillment (EM Put-in-Pack),
logs/errors (EM Log Book; VT diagnostics; SH monitoring), docs/maintenance (EM
honesty; VT dated changelog), security (SH access groups). (`best-in-class-observations.md`.)

## Gaps and opportunities

Top differentiation themes (recommendations, gated): **demonstrated correctness**
(idempotency + reconciliation + rate-limit throttling — the biggest whitespace and
Tier-1-mandated); **best operator UX** (unified command center + recovery-first
errors + named diagnostics + dry-runs); **effortless install with real
reliability** (the combo nobody has); **honesty/transparency** (latency labels,
dated changelog disclosing fixes, open docs/demo); **premium breadth as clean
add-ons** (payouts, B2B, gift cards, Markets). MVP-relevance is tagged
candidate/later/unknown per item — **not finalized**. (`gaps-opportunities.md`.)

## Avoid-list highlights

Webhook-only/cron-only sync; no reconciliation; `ir.cron`-as-a-queue; heavy work
in the webhook request; no rate-limit handling; skipping HMAC; email-only errors;
manual-only recovery; irreversible "Force Done"; single-location inventory;
writing `committed`; legacy fulfillment endpoints; non-idempotent refunds;
assuming payouts exist for all gateways; bot-blocked/gated/stale docs; one-giant-
module / `_inherits` delegation; `productSet` delete-on-omit as partial update.
Items tagged **"Arch review: YES"** route through AR-002…AR-008. (`avoid-list.md`.)

## What is still blocked

- **R2 Teqstars docs** (`docs.teqstars.com`, 19.0 + 16.0) — HTTP **403**
  bot-block on the whole host; no workflow/screenshot evidence. *(The Apps Store
  listing substituted as accessible vendor-claim evidence.)* **Unblock:** a
  browser-UA fetch of the 19.0 docs (no auth to bypass), **or** ChatGPT accepts the
  Apps-listing evidence as sufficient.
- **R5 Google Doc** — sign-in wall; **owner view-access or export required**; it
  is specifically **R6's setup guide**.
- **R4 VentorTech Confluence** — 17 of 28 child articles unread (not gated, just
  not fetched); optional for fuller coverage.

## Inferences, not decisions

All strengths/weaknesses, "do better", gaps/opportunities, avoid-list items, and
the architecture-evidence note are **inferences/recommendations**. **No MVP scope
and no architecture is decided.** Competitor claims are **claims**, not facts;
on-page price/license/version are **facts about the listing on 2026-06-30**. The
AR-002…AR-008 rows remain **"Not decided / Evidence pending."**

## Open questions

Teqstars: are the idempotency/queue-retry/Markets claims real (docs blocked)?
ecommerce_shopify: official vs partner provenance; does product export exist; what
is in the blocked setup doc (R5)? VentorTech: can install be Odoo-Online-friendly;
payout/POS/gift-card roadmap; connector permission model? sh_shopify_connector:
real adoption (no ratings) and currency (no changelog); multi-company; idempotency/
HMAC details? Field-wide: how do competitors surface rate-limit and reconciliation
to users (none observed)? (Per-source lists in the deep dives.)

## Risks

- **Evidence asymmetry:** TQ (docs blocked) and EC (no screenshots) are
  **vendor-claim-heavy** — their real capabilities may differ from the matrix;
  EM/VT carry the most demonstrated evidence (weight accordingly).
- **Vendor-claim drift:** marketing "real-time"/idempotency/queue claims can
  overstate; mitigated by classification + verification (DP-003).
- **Source volatility:** competitor pricing/pages/changelogs change; re-date on
  re-visit. Teqstars 403 may persist.
- **Synthesis temptation:** keep MVP/architecture gated; do not let
  gaps/opportunities harden into decisions before ChatGPT review.

## Learning feedback loop

- **New issues discovered:** one — **DP-003** (unsupported assumption #3 / weak
  research #1): competitor capability statements, **especially from a blocked docs
  site (Teqstars 403) or a screenshot-free listing (ecommerce_shopify)**, risk
  being recorded as facts; "real-time" marketing risks masking a cron/queue model.
  **Prevented** by the capture→verify two-pass + strict claim classification
  (which produced concrete downgrades: R2 Partial→Blocked, EC "real-time"→cron,
  SH multi-company→not-found).
- **Repeated issue patterns:** none at threshold. DP-003 is the **1st** occurrence
  of category #3/#1. Separately, Sprint C found **external confirmation of the
  DP-001 risk** — Emipro's docs cite the stale Shopify "19 retries/48h" figure
  (Tier-1: 8/4h); **not adopted** (the verification gate held). No 2×/3× escalation.
- **Rules/checklists updated:** added **DP-003** + its prevention rule (classify
  every line; never elevate a competitor claim to a fact; run an adversarial
  verifier that downgrades anything not literally on the page) and the occurrence
  counter in `defect-pattern-log.md`. The **per-cell evidence symbol +
  evidence-note** convention in the feature matrix is now the standard for future
  competitor matrices.
- **New rejected approaches:** none (research-only). The **avoid-list** holds
  competitor anti-patterns as **recommendations**, explicitly **not** rejected
  decisions; `rejected-approaches-log.md` notes they route through architecture
  review before any formal rejection.
- **New technical debt:** none (no code). Blocked sources are research gaps, not
  debt (noted in `technical-debt-register.md`).
- **Architecture concerns:** competitor evidence now **informs** AR-002…AR-008 —
  recorded as a **non-decision note** in `architecture-review-log.md` (GraphQL
  convergence; webhooks+cron+queue with `queue_job` as a real data point; SKU/
  email/ID-write-back binding; `@idempotent`+retry; multi-location; FulfillmentOrder).
  **All rows stay "Not decided / Evidence pending."**
- **Tests or review gates needed:** none active (research). For implementation
  (gated): regression tests for duplicate orders, multi-location double-decrement,
  missed-webhook reconciliation, idempotent refunds, timezone/paging — seeded in
  the avoid-list (A-IMP-4) for the definition-of-done.
- **Should future prompts change? Yes** — (1) for blocked/screenshot-free sources,
  prompts should **mandate the capture→verify two-pass and the claim-class
  symbols** (now encoded via DP-003); (2) competitor-research prompts should state
  that the **branch reality is the harness-designated `claude/...` branch** while
  the **PR targets `Shopify-connector`**, to avoid the Sprint C branch-name
  ambiguity.

### Sprint C revision (PR #51 review — 2026-07-01)

ChatGPT review returned **REVISE** for two evidence-classification overstatements;
corrected on the same branch (`docs: correct sprint c evidence classifications`):

- **Correction 1 — Webkul multi-company.** The Webkul default **Company** field was
  initially classified too strongly as **demonstrated multi-company support** (✅).
  True multi-company support/isolation was **not demonstrated**; a visible config
  field is not evidence of multi-company routing or record-rule handling. Downgraded
  to `⬜/➖` in `competitor-deep-dives.md` and to `➖` in `competitor-feature-matrix.md`
  (with an evidence note; EM/VT remain the demonstrated multi-company evidence).
- **Correction 2 — "bidirectional core sync" common pattern.** The strongly-common
  pattern claiming **bidirectional product/order/inventory/customer sync across all**
  connectors was **narrowed**: broad core-object coverage is a common *market promise*,
  but **directionality varies by object and evidence strength** (EC product export not
  found; WK customer export not found; TQ listing-claim only; EM/VT strongest
  directional evidence). Updated in `common-patterns.md`.
- **Category:** unsupported assumption (#3) / weak research classification (#1) — logged
  as **DP-004** in `defect-pattern-log.md`.
- **Prevention rule:** configuration fields must **not** be treated as demonstrated
  feature support unless the workflow/behaviour is shown; common-pattern wording must
  distinguish a **market promise** from **demonstrated bidirectionality**.

## What ChatGPT should review

1. **Claim discipline** — spot-check that competitor claims are not presented as
   facts, especially TQ (docs blocked) and EC (no screenshots), and that the
   verifier's downgrades (R2→Blocked, EC→cron, SH multi-company→not-found) are
   reflected everywhere.
2. **Matrix evidence** — confirm the per-cell symbols + evidence notes are fair
   and that 🟨/🔒 are used where evidence is listing-only/blocked.
3. **Blocked-source handling** — endorse recording R2 docs as Blocked (with the
   Apps-listing surrogate) and R5 as Blocked (= R6's setup guide); decide the
   unblock path for each.
4. **Gaps/opportunities & avoid-list** — confirm these stay **recommendations**
   (no MVP/architecture lock-in) and which opportunities to prioritise for RB-13/
   RB-14.
5. **Branch-name discrepancy** — confirm working on the harness-designated branch
   `claude/research-sprint-c-competitors-hgoo8t` (PR → `Shopify-connector`) is
   acceptable, or instruct otherwise.
6. **DP-003 + verification gate** — endorse making the capture→verify two-pass the
   standing rule for competitor research.

## Recommended next session

With competitor evidence in place, proceed to **RB-12 (canonical feature
taxonomy)** to normalize the matrix rows, then **RB-11 (product vision draft)** and
**RB-13 (MVP scope implications — not finalized)**, feeding **RB-14 (architecture
preparation)** against AR-002…AR-008 — all gated and ChatGPT-reviewed. In parallel,
resolve the **R2/R5 unblocks** (browser-UA fetch decision for Teqstars 19.0 docs;
owner access/export for the Google Doc) and optionally finish the **17 unread
VentorTech Confluence** articles. Keep the no-code gate; one scoped objective per
session.

## Stop confirmation

Stopped at the Sprint C boundary as instructed: five stage commits on the
harness-designated working branch, **one draft PR** to be opened targeting
**`Shopify-connector`**, **not merged**. **No** code, **no** Odoo module, **no**
MVP scope, **no** architecture decisions, **no** ADRs. `main` and plain `dev`
untouched. Blocked sources documented without bypass. Awaiting ChatGPT review.

## Quality gate confirmation (Sprint C)

- [x] Session handoff updated (this block).
- [x] Quality feedback loop checked (this file + `../05-qa/` logs).
- [x] New learning captured in the correct file (DP-003 in `defect-pattern-log.md`).
- [x] Any rejected approach logged (none — avoid-list is recommendations, noted in `rejected-approaches-log.md`).
- [x] Any accepted technical debt logged (none — noted in `technical-debt-register.md`).
- [x] Any repeated issue pattern escalated per §4 (none at threshold; DP-003 1st occurrence).

## Sprint C high-power research plan

- **Why high-power mode is needed:** Eight user-provided competitor resources
  (R1–R8) must be studied from **real evidence** — full documentation trees,
  on-page screenshots, configuration/setup flows, feature claims, release notes,
  pricing/support, and UX — so the connector is designed from knowledge, not
  guesses. Several sources are multi-page (Emipro doc tree, VentorTech Confluence
  hub with ~27 children) and two were previously gated (R2 Teqstars 403; R5
  Google Doc login wall). Covering this breadth with verification in one pass
  justifies a controlled parallel fan-out (per `CLAUDE.md` → High-power research
  mode; the policy is a capability, not a cap).
- **Workstreams / agents:** One **source-capture agent per resource** (R1 Webkul,
  R2 Teqstars, R3 Emipro + sub-pages, R4 VentorTech Confluence hub + children, R5
  Google Doc, R6 ecommerce_shopify, R7 VentorTech site, R8 sh_shopify_connector),
  each returning **structured, cited, claim-classified evidence** (access status,
  visible sections, feature claims, visuals/screenshots described, workflow steps,
  version context). Then a **verification workstream** that re-checks the
  highest-stakes claims (pricing, sync model, key features, access status) against
  the captured evidence and flags anything unsupported. Synthesis into the
  deliverable docs is performed by the worker (main thread) so governance
  (citation + claim classification + no-MVP/no-architecture gate) is owned
  centrally.
- **Sources to inspect:** R1 https://webkul.com/blog/odoo-multichannel-shopify-connector/ ·
  R2 https://docs.teqstars.com/19.0/applications/shopify/overview.html ·
  R3 https://docs.emiprotechnologies.com/shopify-odoo-connector/v19/installation.html (+ tree) ·
  R4 https://ventortech.atlassian.net/wiki/spaces/pd/pages/482639953/Shopify (+ children) ·
  R5 https://docs.google.com/document/d/1zIwRxp7cvLYeyjl8P_mvsjC-v8Tsd_ugC1JbfTznHC8/edit ·
  R6 https://apps.odoo.com/apps/modules/19.0/ecommerce_shopify ·
  R7 https://ventor.tech/solutions/odoo-shopify-connector/ ·
  R8 https://apps.odoo.com/apps/modules/19.0/sh_shopify_connector#features.
  Tier-1 grounding only from the existing official Shopify/Odoo baselines (these
  competitor sources are Tier 2–5 → **competitor claims**, not facts).
- **Screenshots / UI evidence approach:** Primary evidence is the **screenshot
  inventory markdown** (`competitor-screenshot-inventory.md` + per-vendor
  `screenshots/*/README.md`) analysing what each visual/figure on the source
  pages demonstrates (fields, buttons, tabs, workflow step, status/log surfaces,
  UX). Actual binary image capture is **attempted only where practical and
  high-value**; where impractical (JS-gated, heavy, or auth-gated) it is recorded
  as "no file saved" with the reason — the analysis (not the file's existence) is
  the deliverable. No authentication wall is bypassed to obtain any visual.
- **Files to update:** (research) `competitor-deep-dives.md`,
  `competitor-feature-matrix.md`, `ux-ui-benchmark.md`, `common-patterns.md`,
  `best-in-class-observations.md`, `gaps-opportunities.md`, `avoid-list.md`,
  `resource-inventory.md`, `research-handoff.md`; (source materials)
  `competitor-source-notes.md`, `competitor-screenshot-inventory.md`,
  `screenshots/README.md` + `screenshots/{webkul,teqstars,emipro,ventortech,odoo-apps}/README.md`;
  (QA) `defect-pattern-log.md`, `architecture-review-log.md`,
  `rejected-approaches-log.md`, `technical-debt-register.md`. **No other files.**
- **Stop condition:** All accessible sources captured + verified; blocked sources
  (R2/R5 if still gated, R4 gated children) documented without bypass; the nine
  research deliverables + source/screenshot evidence written with every claim
  cited and classified; QA logs and handoff updated; quality gate satisfied. Then
  **stop** — no MVP scope, no architecture decisions, no code, no merge.
- **Verification method:** Two-pass — topic capture, then an independent
  verification agent (and worker spot-checks) re-reading the canonical source for
  the highest-stakes claims; any figure/feature not literally supported on the
  page is downgraded to **open question / vendor claim**, never asserted as fact
  (reuses the DP-001 verification-pass gate).
- **How unsupported claims will be prevented:** Strict claim classification on
  every line (Fact / Competitor claim / Inference / Open question — `CLAUDE.md`
  §8); vendor capability statements stay **competitor claims** unless a concrete
  documented workflow/screenshot demonstrates them (then **visible demonstrated
  workflow**); blocked/unknown is stated as such; no hidden-feature guessing; no
  competitor claim is promoted to a Tier-1 fact (those come only from the existing
  official baselines).

---

# Research Sprint B Handoff

> **Research Sprint B — Dedicated Branch Setup + Source Access Validation +
> Official Shopify/Odoo Baseline.** Research-only; no-code gate in force
> (`CLAUDE.md` §5). Maps to backlog items **RB-01.1** (source validation),
> **RB-05.1** (official Shopify notes), **RB-06.1** (official Odoo notes), and
> **seeds RB-14** architecture questions.

## Session summary

Established the **dedicated project integration branch** (corrected by ChatGPT to
**`Shopify-connector`** — see Base branch below), then produced a controlled
**Tier-1 research baseline**: re-validated access for the 8 competitor resources;
created the **official Shopify API** and **official Odoo 19 architecture** notes
(every factual claim cited to an exact official URL, accessed 2026-06-30, with
**Fact / Inference / Open question** labels and a clear "constraints are
inferences, not decisions" boundary); captured supporting excerpts under
`docs/00-source-materials/`; and seeded **seven evidence-pending architecture
questions** (AR-002…AR-008, all "Not decided"). **No connector code, no Odoo
module, no competitor deep dives, no MVP scope, and no architecture decisions**
were produced — all gated. Facts were gathered topic-by-topic and then
**independently verified** on the highest-stakes pages (rate limits, versioning,
webhooks, Odoo security/manifest).

## Branch and commits

**Working branch:** `research/sprint-b-source-access-official-baseline` (based on
`Shopify-connector` @ `a5d4543`, the merged PR #49 governance foundation).

| Hash | Message |
| --- | --- |
| `54bd6f1` | docs: sprint b governance checkpoint and branch setup |
| `d05ab49` | docs: validate initial source access |
| `468efb6` | docs: add official shopify api baseline |
| `08b4c75` | docs: add official odoo architecture baseline |
| `21c460b` | docs: seed architecture research questions |
| _(this commit)_ | docs: finalize research sprint b handoff |

## Base branch and PR target

- **Dedicated project integration branch: `Shopify-connector`.** The original
  Sprint B prompt named `dev/Shopify-connector`; that branch **cannot exist on
  the remote** because a plain `dev` branch already exists (Git directory/file
  ref conflict — the push was rejected with `directory file conflict`). The
  blocker was reported, **not** worked around. **ChatGPT corrected the policy** to
  use the existing **`Shopify-connector`** branch; plain `dev` was left untouched.
- Before acting, verified `origin/Shopify-connector` was at the old `68007a9`,
  had **no** unique commits beyond `origin/main`, and was a clean fast-forward; it
  was **fast-forwarded to `origin/main` `a5d4543` and pushed normally (no force)**.
- **PR target: `Shopify-connector`** — **not** `main`, **not** plain `dev`, **not**
  `dev/Shopify-connector`. **`main` was not modified; plain `dev` was not modified.**

## Files created or updated

- `docs/00-source-materials/source-access-notes.md` (new) — per-resource access
  evidence for the 8 sources.
- `docs/01-research/resource-inventory.md` (updated) — Sprint B re-validation
  section + unblock decisions for ChatGPT.
- `docs/01-research/shopify-official-api-notes.md` (new) — Tier-1 Shopify baseline.
- `docs/00-source-materials/shopify-official.md` (new) — captured Shopify excerpts.
- `docs/01-research/odoo-official-architecture-notes.md` (new) — Tier-1 Odoo 19
  baseline.
- `docs/00-source-materials/odoo-official.md` (new) — captured Odoo excerpts.
- `docs/05-qa/architecture-review-log.md` (updated) — seeded AR-002…AR-008
  (evidence-pending only).
- `docs/05-qa/defect-pattern-log.md` (updated) — DP-001 (prevented stale-figure
  issue) + occurrence counter.
- `docs/01-research/research-handoff.md` (this file).

## Source access results

No status changed from Sprint A (both checked 2026-06-30; no auth bypassed).
**Accessible (5):** R1 Webkul, R3 Emipro, R6 ecommerce_shopify, R7 VentorTech
site, R8 sh_shopify_connector. **Partial (1):** R4 VentorTech Confluence
(anonymous-access banner; child pages to test individually). **Blocked (2):** R2
Teqstars 19.0 (HTTP 403 bot-block — needs an alternate fetch UA, or a ChatGPT
decision on the non-equivalent 16.0 mirror), R5 Google Doc (login wall — needs
owner-granted access or export). Full evidence:
`docs/00-source-materials/source-access-notes.md`.

## Shopify official facts captured

GraphQL Admin API is the primary API (REST legacy since 2024-10-01; new public
apps GraphQL-only from 2025-04-01); quarterly date-based versioning (`YYYY-MM`,
min 12-month support, ≥9-month overlap, fall-forward); OAuth + token-exchange,
online/offline/session tokens, least-privilege scopes, protected customer data
(60-day order window / `read_all_orders` approval); rate limits (REST 40/2
standard, 400/20 Plus; GraphQL calculated-cost restore 100/200/1000/2000 pts/s,
1000-point single-query cap) and the query-cost model; bulk operations (async
JSONL, concurrency change at 2026-01); webhooks (HMAC-SHA256 on raw body,
**8 retries/4h**, auto-delete after 8 failures, **delivery not guaranteed →
reconciliation required**, mandatory compliance webhooks); products/variants
(2048-variant model, `productSet` delete-on-omit); inventory (variant→item→level→
location, `committed` read-only, `@idempotent` from 2026-04); orders; fulfillment
(FulfillmentOrder-based, legacy unsupported since 2022-07); refunds/returns;
transactions (gateway-agnostic) vs payouts (Shopify Payments only); App Store /
Built-for-Shopify readiness. Full notes + citations:
`docs/01-research/shopify-official-api-notes.md`.

## Odoo official facts captured

Module/manifest structure (`name` only required key; full key list); modularity
via `depends` + `auto_install` link modules; ORM extension (in-place `_inherit`
preferred; `_inherits` delegation discouraged; `@api.model_create_multi`,
`@api.ondelete`, always `super()`); security (`ir.model.access.csv` deny-by-
default, `ir.rule` global=intersect/group=unify, field `groups`, `sudo()`/
superuser bypass); **`ir.cron` is the only documented background primitive**
(poll-based, `--max-cron-threads` default 2; failure rules 3-consecutive /
5-over-7-days→deactivate); **no official built-in job queue — `queue_job` is
community (Open question)**; external IDs / `ir.model.data` (binding-key
inference); performance (prefetch, N+1 → `_read_group`, batch `create`, selective
indexes); testing (`TransactionCase`, `HttpCase`/tours, tags); upgrade scripts
(`migrations/$version/{pre,post,end}`); logging (`ir.logging`/CLI, **no built-in
metrics — Open question**); Odoo.sh deployment (worker/time/memory limits;
**crons disabled on staging/dev**). Full notes + citations:
`docs/01-research/odoo-official-architecture-notes.md`.

## Inferences and constraints, not decisions

The "Architecture constraints implied by …" sections in both baselines are
**inferences only**, and AR-002…AR-008 are **evidence-pending, not decided**.
Key framing (not choices): a new public-app connector effectively needs GraphQL;
webhooks cannot be the sole source of truth (need reconciliation + idempotency);
background sync on stock Odoo is `ir.cron`-bound (queue_job is an explicit
dependency question); modular addon family over a giant module; external IDs as a
candidate binding key; inventory `committed` is order-driven; fulfillment must use
FulfillmentOrder mutations. **None of these is a decision.**

## Open questions

Carried into the baselines and AR rows: REST sunset / GraphQL-only scope for
custom apps; per-plan GraphQL bucket size & throttle error shape; connection-cost
formula; current max product options; REST product/fulfillment deprecation dates;
payout scope string; Pub/Sub & EventBridge retry semantics. Odoo: whether any
official job queue exists beyond `ir.cron`; `ir.cron`/`ir.model.data`/`ir.logging`
field schemas; manifest defaults; `create`-override signature; `read_group`
deprecation; Odoo.sh per-stage quotas; built-in metrics. **Source unblocks for
ChatGPT:** R2 Teqstars (alternate fetch vs 16.0 mirror) and R5 Google Doc (owner
access/export).

## Risks

Commonly-cited API numbers can be stale (see DP-001); version-independent Shopify
policy can drift without a version bump; `productSet` delete-on-omit is a
data-loss footgun; webhook-only designs risk silent drift; treating `ir.cron` as
a job queue (or assuming `queue_job` is core) is a design trap; some JS-rendered
Odoo pages required RST-source recovery (re-verify load-bearing wording).

## Learning feedback loop

- **New issues discovered:** one — **DP-001** (incorrect Shopify API assumption,
  #6): commonly-cited/training-data API figures were **stale vs current official
  docs** (webhook "19/48h" → actual 8/4h; REST Plus "80" → 400; `/rate-limits`
  moved to `/limits`, now GraphQL-only). **Prevented** by the independent
  verification pass.
- **Repeated issue patterns:** none at threshold — DP-001 is the **1st**
  occurrence of category #6 (counter updated; no 2×/3× escalation).
- **Rules/checklists updated:** added the DP-001 **prevention rule** — for
  high-stakes numeric/policy API facts, re-read and cite the **exact** official
  page; if a figure is not literally on the page, mark it **Open question**, never
  assert a remembered/forum figure. The **independent-verification-pass** gate is
  now the recommended method for future official-API research (RB-05/RB-06-style).
- **New rejected approaches:** none (research-only; no approaches evaluated to
  rejection — `rejected-approaches-log.md` unchanged).
- **New technical debt:** none (no code; blocked sources R2/R5 are research gaps,
  not debt — `technical-debt-register.md` unchanged).
- **Architecture concerns:** captured as **AR-002…AR-008 (evidence-pending)**, not
  decisions; the big ones are sync orchestration (cron vs webhook+reconciliation
  vs queue) and duplicate-prevention/binding.
- **Tests or review gates needed:** none active (research phase). For future API
  research, keep the verification-pass gate. The connector-side test stance
  (`TransactionCase` for mapping, `HttpCase`/tours for webhooks/UI) is recorded in
  the Odoo notes for the implementation phase.
- **Should future prompts change? Yes** — official-API research prompts should
  explicitly require an **independent verification pass** on high-stakes numeric
  facts and the "mark Open question if not literally on the page" rule (now
  encoded via DP-001). Also: the branch-policy reality is **`Shopify-connector`**
  (not `dev/Shopify-connector`), which future Sprint prompts should state.

**Revision patch (ChatGPT REVISE — branch policy + high-power research rules):**

- Branch policy was promoted into permanent governance files: `Shopify-connector`
  is the dedicated integration branch; `main` and plain `dev` remain untouched
  unless explicitly approved.
- New issue discovered: high-power research fan-out needs a persistent governance
  rule so large Claude workflows remain intentional, scoped, synthesized, and
  reviewable.
- Category: token waste (#17) / unclear handoff, first occurrence (logged as
  **DP-002**, Mitigated).
- Prevention rule: high-power research mode is allowed and encouraged for major
  research and architecture work, but the fan-out plan, workstreams, sources,
  stop condition, synthesis method, and verification method must be documented.
- **This rule does not limit Claude's capabilities.** It is a *capability,
  not a cap* — there is **no** fixed agent/token limit. Claude is expected to use
  maximum capability when justified to produce a top-tier, state-of-the-art
  connector; the only requirement is that large research be intentional, scoped
  to allowed files, documented, and reviewable (and that small patch sessions
  stay lightweight).
- Rules/checklists updated in this patch: `CLAUDE.md` (new **Branch governance**
  and **High-power research mode** sections), `README.md` (branch-governance +
  high-power research summary), `docs/06-prompts/claude-learning-rules.md`
  (pre-session checklist item 8 + High-power research mode section),
  `docs/06-prompts/claude-session-prompts.md` (default branch policy + High-power
  research mode in the standard preamble and as a section),
  `docs/05-qa/pr-review-checklist.md` (branch-target + capability-use checks),
  `docs/05-qa/defect-pattern-log.md` (DP-002 reframed + counter), and this
  handoff.

## What ChatGPT should review

1. **Branch governance** — confirm `Shopify-connector` is the intended dedicated
   integration branch and that leaving plain `dev` untouched is correct.
2. **Citation/classification rigor** — spot-check that Shopify/Odoo facts cite
   exact official URLs and that constraints are labelled inference, not decision.
3. **High-stakes facts** — the rate-limit, versioning, and webhook numbers
   (incl. the corrected 8-retries/4-hours and REST-Plus-400), and the Odoo
   "no official job queue" finding.
4. **Open questions / unblocks** — decide R2 (Teqstars alternate fetch vs 16.0
   mirror) and R5 (Google Doc access/export).
5. **AR-002…AR-008** — confirm these are the right architecture questions to
   carry (still evidence-pending), and which to prioritise for RB-14.
6. **DP-001 + verification gate** — endorse making the independent-verification
   pass a standing rule for API research.

## Recommended next session

With Tier-1 baselines in place, proceed to **competitor deep dives**
(`RB-02.1 Webkul`, `RB-02.3 Emipro`, `RB-02.5 Odoo Apps listings` — all
unblocked), running **RB-12 feature taxonomy** early for grounding, and revisit
**R2/R5** once ChatGPT decides the unblock path. Keep the no-code gate; one scoped
session per deep dive; follow `research-methodology.md` §11.

## Stop confirmation

Stopped at the Sprint B boundary as instructed: working branch pushed, **one
draft PR** opened targeting **`Shopify-connector`**, **not merged**. **No** code,
**no** Odoo module, **no** competitor deep dives, **no** MVP scope, **no**
architecture decisions. `main` and plain `dev` untouched. Awaiting ChatGPT review.

---

# Research Sprint A Handoff (history)

> Continuity record for **Research Sprint A — Governance, Research Workspace,
> Source Inventory, and Research Backlog.** Continuity lives in GitHub, not chat.
> The running **Sprint checkpoint log** (one note per stage) is at the bottom.

## ChatGPT review decision (Research Sprint A)

> ChatGPT review decision: Research Sprint A is the canonical governance
> foundation after this revision patch is accepted. The earlier branch
> `claude/odoo-shopify-research-setup-fs4wzi` is non-canonical and must not be
> used unless ChatGPT explicitly reopens it.

The Sprint A review returned **REVISE — small governance patch required before
merge.** This patch addresses those findings (modular addon-family wording,
canonical research output filenames, feature-taxonomy sequencing, the
non-canonical-branch warning, and this learning-loop update). See the
revision-patch entry at the bottom of the checkpoint log and the updated
**Learning feedback loop** section below.

## Session summary

Research Sprint A established the GitHub-based **governance and research
foundation** for the premium Odoo 19 ↔ Shopify Connector project, so ChatGPT
can review the repo directly and direct the next sprint. Work was done in six
documentation-only stages on a clean branch off `main`: workspace setup →
governance contract & templates → learning feedback loop → research workspace
(inventory, methodology, backlog) → placeholder READMEs → finalization. **No
connector code, no Odoo module, and no forbidden files were created.** No
competitor deep dives, MVP finalization, or architecture decisions were made —
those are explicitly out of scope and gated.

## Branch and commits

**Branch:** `docs/research-sprint-a-governance-inventory` (based on `origin/main`
@ `68007a9`).

| Hash | Message |
| --- | --- |
| `2e4c276` | docs: create connector governance workspace |
| `d143086` | docs: add governance and review templates |
| `1aba406` | docs: add quality feedback loop |
| `f4f3e7d` | docs: add research inventory and backlog |
| `8aa536b` | docs: add product architecture and claude placeholders |
| _(final)_ | docs: finalize research sprint a handoff |

## Files created or updated

**Root governance**
- `CLAUDE.md` (new) — governance contract (roles, source-of-truth,
  research-first, no-code-until-approved, scoped sessions, citation rules, claim
  classification, future implementation-task requirements, allowed/forbidden
  files, do-not-repeat-rejected rule, mandatory handoff).
- `AGENTS.md` (new) — six **proposed** future agents, marked proposed only.
- `README.md` (updated) — preserved existing content; added the project
  workspace map.

**Research (`docs/01-research/`)**
- `resource-inventory.md`, `research-methodology.md`, `research-backlog.md`,
  `research-handoff.md` (this file).

**QA / quality memory (`docs/05-qa/`)**
- `quality-feedback-loop.md`, `defect-pattern-log.md`,
  `architecture-review-log.md`, `rejected-approaches-log.md`,
  `technical-debt-register.md`, `pr-review-checklist.md`.

**Prompts/templates (`docs/06-prompts/`)**
- `claude-session-prompts.md`, `claude-learning-rules.md`,
  `implementation-task-template.md`, `pr-review-template.md`,
  `session-handoff-template.md`.

**Decisions** — `docs/04-decisions/decision-record-template.md` + `README.md`.

**Placeholder READMEs** — `docs/00-source-materials/README.md`,
`docs/02-product`, `docs/03-architecture`, `docs/07-implementation-plan`,
`docs/08-release-readiness`, and `.claude`, `.claude/skills`, `.claude/agents`.

## What changed

The repository went from a bare Odoo SH scaffold (`addons/adams_base`,
`README.md`, `.gitignore`) to a full **research/governance workspace**: a
governance contract, a learning feedback loop with four logs, a research
methodology, a registered source inventory of 8 resources, a 14-section research
backlog, and review/handoff/decision templates — all documentation. The Odoo
addon scaffold under `/addons` was left untouched.

## Evidence and citations added

Initial **access status** for the 8 sources was verified on **2026-06-30** (no
auth bypass): **Accessible** — Webkul (R1), Emipro (R3), Odoo Apps
ecommerce_shopify (R6), VentorTech website (R7), Odoo Apps sh_shopify_connector
(R8); **Partial** — VentorTech Confluence (R4, anonymous-access banner);
**Blocked** — Teqstars docs (R2, HTTP 403 bot-block, not a login wall), project
Google Doc (R5, login wall). On-page pricing recorded as facts-on-date: R6
$195.56 (OPL-1), R8 $168.81 (OPL-1), R7 EUR 499. No detailed feature claims were
asserted — only registration/triage. Full detail in `resource-inventory.md`.

## Assumptions

- The connector must be **isolated from `adams_base`/customer code**; its final
  structure may be a **modular connector addon family** under `/addons` — exact
  module boundaries are **not final** and will be validated through research +
  architecture review. `adams_base` is unrelated company/base code (inference
  from repo layout + README).
- "Initial value" / "Evidence strength" in the inventory are **triage
  inferences**, not vendor facts.
- The default research order in the backlog is reasonable but adjustable once
  blocked sources are resolved.

## Open questions

- R2 Teqstars: will an alternate fetch (different UA / browser / cache) work, or
  is the 16.0 doc the fallback?
- R5 Google Doc: can the owner grant view access or provide an export? What is
  its actual content?
- R6 ecommerce_shopify: is the listing Odoo S.A. official or a partner module
  (author shown as "Odoo IN Pvt Ltd")?
- R4 VentorTech Confluence: which child pages/screenshots require login?

## Risks

- **Access risk:** two blocked + one partial source could delay specific deep
  dives (RB-02.2, RB-02.6); the backlog isolates these so they don't stall the
  rest.
- **Source bias:** all 8 sources are vendor-published; technical facts must come
  from official Shopify/Odoo docs (RB-05, RB-06), not competitor claims.
- **Scope creep risk:** strong guardrails (allowed/forbidden files, no-code
  gate) are in place; future sessions must honour them.
- **Pricing/feature drift:** vendor pages change; deep dives must re-date and
  capture excerpts.

## Learning feedback loop

- **New issue discovered:** Governance wording could **bias Claude toward one
  giant connector addon/module** — the "self-contained addon" phrasing in
  `CLAUDE.md` §9 and `README.md`. Surfaced by ChatGPT's Sprint A review (REVISE).
- **Category:** premature architecture / weak modularity (first occurrence;
  count = 1).
- **Repeated issue patterns:** None — this is the first occurrence of this
  category; no escalation threshold reached.
- **Prevention rule:** Use **"modular connector addon family"** language and
  state that exact module boundaries are **not final** until validated through
  research + architecture review; never imply a single giant module. Keep the
  isolation-from-`adams_base`/customer-code rule.
- **Rules/checklists updated:** (1) `CLAUDE.md` §9 and `README.md` reworded to
  the modular-family principle; (2) `research-backlog.md` and
  `claude-session-prompts.md` updated to the canonical research output filenames,
  single-file competitor deep dives (`competitor-deep-dives.md`), and the
  provisional→canonical feature-taxonomy sequencing rule; (3)
  `architecture-review-log.md` row **AR-001** added recording this branch as the
  canonical foundation. (No `defect-pattern-log.md` row: this was a pre-merge
  review finding on governance docs, not a shipped defect — captured here and in
  the architecture-review log.)
- **New rejected approaches:** None logged formally; the "one giant connector
  module" bias is prevented by wording. Revisit/log if it recurs.
- **New technical debt:** None.
- **Architecture concerns:** Module-boundary design is explicitly **deferred**
  to research + architecture review (RB-06, RB-14); do not pre-decide it.
- **Tests or review gates needed:** None active in the research phase; the
  implementation checklist (section C) is staged for later.
- **Should future prompts change? Yes/No:** **Yes** — prompt templates now use
  the canonical research output filenames and the modular-family wording, and
  encode the provisional→canonical taxonomy sequencing.
- **Final cleanup:** removed remaining "self-contained addon" wording from
  implementation-phase governance templates so future implementation prompts
  preserve modular addon-family language. Files updated:
  `docs/05-qa/pr-review-checklist.md` (§C) and
  `docs/06-prompts/implementation-task-template.md`.

## What ChatGPT should review

1. **Governance correctness** — does `CLAUDE.md` capture the intended
   Claude/ChatGPT operating model, gates, and claim-classification scheme?
2. **Learning loop sufficiency** — are the escalation thresholds (2×/3×), issue
   taxonomy, and log schemas adequate to prevent repeated mistakes?
3. **Research methodology** — is the source hierarchy, claim classification, and
   extraction method rigorous enough for trustworthy deep dives?
4. **Resource inventory** — accuracy of access triage; is the
   official-vs-partner provenance flag for R6 handled correctly?
5. **Research backlog** — are sequencing, dependencies, and acceptance criteria
   right? Anything missing before deep dives start?
6. **Proposed agents** — approve/adjust the six proposed agents (still inactive).
7. **Blocked sources** — decide the unblock path for R2 (Teqstars) and R5
   (Google Doc) before their backlog items.

## Recommended next session

**RB-01.1 — Validate and unblock sources** (resolve R2/R5 access), then begin
deep dives with **RB-02.1 — Webkul** (accessible, no blockers). Run
`RB-12` (feature taxonomy) early and `RB-05`/`RB-06` (official Shopify/Odoo
notes) in parallel. Use the prompts in `docs/06-prompts/claude-session-prompts.md`.

## Stop confirmation

Stopped at the Research Sprint A boundary as instructed: branch pushed, one
**draft** PR opened for ChatGPT review, not merged. **No** deep competitor
research, **no** architecture, **no** implementation was started. Awaiting
ChatGPT review.

## Sprint self-review

- **Scope respected:** Yes — governance/research documentation only.
- **No coding performed:** Yes — no `.py`/`.xml`/`.csv`, no module, no manifest.
- **Forbidden files untouched:** Yes — forbidden-pattern scan clean; `addons/`
  untouched (verified via `git diff --name-only origin/main`).
- **Research inventory complete:** Yes — all 8 resources registered with the
  required schema and verified access status.
- **Governance files complete:** Yes — CLAUDE.md, AGENTS.md, README, templates,
  checklist.
- **Learning loop complete:** Yes — feedback-loop doc + four logs + learning
  rules.
- **Handoff updated:** Yes — this file (all required sections + checkpoint log).
- **Ready for ChatGPT review:** Yes — draft PR opened.

---

## Sprint checkpoint log

> One short note per stage (most recent last).

- **Stage 1 — Repo inspection & safe setup (2026-06-30):** Confirmed remote
  default branch is `main` at `68007a9` (clean Odoo scaffold:
  `addons/adams_base`, `README.md`, `.gitignore`; no `docs/`, no `CLAUDE.md`).
  Created the clean branch `docs/research-sprint-a-governance-inventory` from
  `origin/main` (deliberately not from the prior research branch, so this PR
  contains exactly this governance foundation). Created the `/docs/00..08` and
  `/.claude/{skills,agents}` directory structure. No code touched. Next: Stage 2
  governance files.
- **Stage 2 — Governance files (2026-06-30):** Created `CLAUDE.md` (roles:
  Claude=execution/research/docs worker, ChatGPT=strategy/control-room/reviewer;
  GitHub source-of-truth; research-first; no-code-until-approved; small scoped
  sessions; mandatory handoff; citation rules; the fact/competitor-claim/
  inference/recommendation/decision/open-question classification; future
  implementation-task requirements incl. allowed/forbidden files, acceptance
  criteria, tests, rollback, definition of done; and the hard do-not-repeat-
  rejected-approaches rule). Created `AGENTS.md` listing six **proposed** agents
  (competitor-research, shopify-api-research, odoo-architecture-research,
  ux-benchmark, qa-review, prompt-control) — none active. Updated `README.md`
  (preserved existing title/description; added the project workspace map).
  Added `decision-record-template.md`, `pr-review-checklist.md`,
  `implementation-task-template.md`, `pr-review-template.md`, and
  `session-handoff-template.md`. Docs only; no forbidden files. Next: Stage 3
  learning feedback loop.
- **Stage 3 — Learning feedback loop (2026-06-30):** Created
  `quality-feedback-loop.md` (review-decision categories; 17-type issue
  taxonomy; 2×→update-rule / 3×→pause-implementation escalation; concrete-lesson
  rule; end-of-session review; quality + acceptance gates; routing table) and
  the four logs with the exact required columns — `defect-pattern-log.md`,
  `architecture-review-log.md`, `rejected-approaches-log.md`,
  `technical-debt-register.md` (all initialized empty with instructions). Created
  `claude-learning-rules.md` with the mandatory 7-item pre-session checklist
  (previous handoff, defect log, rejected log, architecture-review log, decision
  records, current phase, allowed/forbidden files). Next: Stage 4 research
  workspace + source inventory.
- **Stage 4 — Research workspace + source inventory (2026-06-30):** Created
  `00-source-materials/README.md` (capture rules; empty until deep dives).
  Created `resource-inventory.md` registering all 8 sources with the required
  schema (ID, name, URL, source type, competitor/category, initial value,
  evidence strength, current access status, what-to-extract-later, open
  questions, notes); access verified 2026-06-30 (5 Accessible, 1 Partial — R4
  VentorTech, 2 Blocked — R2 Teqstars 403/bot-block & R5 Google Doc login);
  Google Doc marked private/user-provided/access-dependent; no detailed feature
  claims asserted. Created `research-methodology.md` (source hierarchy; citation;
  competitor-evidence; claim-classification; screenshot/pricing/feature/UX/
  reliability/technical-risk extraction; deep-dive procedure; MVP/Phase2/Advanced/
  Optional/Avoid disposition rules). Created `research-backlog.md` (14 sections,
  RB-01..RB-14, each item with Objective/Inputs/Output file/Acceptance criteria/
  Dependencies/Status + sequencing). Next: Stage 5 placeholder READMEs.
- **Stage 5 — Placeholder READMEs (2026-06-30):** Created concise READMEs for
  `docs/02-product`, `docs/03-architecture`, `docs/04-decisions`,
  `docs/07-implementation-plan`, `docs/08-release-readiness`, and `.claude`,
  `.claude/skills`, `.claude/agents` — each stating purpose, what belongs, what
  does not belong yet, and current status. The `.claude/skills` and
  `.claude/agents` READMEs explicitly recommend **deferring** active skills/
  agents until the research workflow stabilizes (premature automation may encode
  weak assumptions). Next: Stage 6 final self-review, handoff, push, draft PR.
- **Stage 6 — Final self-review, handoff, push, draft PR (2026-06-30):** Added
  `claude-session-prompts.md` to complete the prompt library (whitelisted file;
  goal #7). Ran final checks: `git diff --name-only origin/main` shows only
  allowed docs/governance files; forbidden-pattern scan clean; `addons/`
  untouched. Filled all required handoff sections + the sprint self-review.
  Pushed the branch and opened one **draft** PR for ChatGPT review. Stopped.
- **Revision patch — address Sprint A review findings (2026-06-30):** ChatGPT
  returned **REVISE**. Applied a small governance patch to the same branch /
  PR #49 (no new PR, no merge): (1) replaced "self-contained addon" wording in
  `CLAUDE.md` §9 and `README.md` with the **modular connector addon family**
  principle (kept the isolation rule); (2) aligned future research output
  filenames in `research-backlog.md` and `claude-session-prompts.md` to the
  canonical names and consolidated competitor deep dives into one file
  `competitor-deep-dives.md` with per-competitor sections; (3) added the
  **provisional→canonical** feature-taxonomy sequencing rule (first 1–2 deep
  dives may use provisional groups; RB-12 normalizes); (4) added the
  non-canonical-branch warning + AR-001 in `architecture-review-log.md`; (5)
  updated this Learning feedback loop. Allowed files only; no code touched.
  **Deferred follow-up:** `docs/05-qa/pr-review-checklist.md` (§C) and
  `docs/06-prompts/implementation-task-template.md` still contain the phrase
  "self-contained addon"; both are **outside this patch's allowed-files scope**,
  so the reword to "modular connector addon family" is deferred to a future
  ChatGPT-approved patch rather than edited out of scope here. **(Resolved in the
  final cleanup patch — both files reworded.)**

### Research Sprint B checkpoints

- **Sprint B / Stage 0 — Dedicated branch setup + governance correction
  (2026-06-30):** Started Research Sprint B (research-only; no-code gate
  confirmed via `CLAUDE.md` §5; allowed/forbidden files reconfirmed). The
  original Sprint B prompt named `dev/Shopify-connector` as the dedicated project
  integration branch. **Blocker (fact):** that branch cannot be created on the
  remote — a plain `dev` branch already exists, and Git cannot hold both `dev`
  and `dev/Shopify-connector` (a directory/file ref conflict; the push was
  rejected with `directory file conflict`). The blocker was reported, not
  worked around (no `dev` deletion, no force-push). **ChatGPT branch-policy
  correction (decision, by ChatGPT):** use the existing remote branch
  **`Shopify-connector`** as the dedicated project integration branch; leave
  plain `dev` untouched; do not use `dev/Shopify-connector` or
  `dev-Shopify-connector`. Sprint branches now branch from `Shopify-connector`
  and Sprint PRs target `Shopify-connector` (not `main`, not `dev`). Verified
  before acting: `origin/Shopify-connector` was at the old commit `68007a9`, had
  **no** unique commits beyond `origin/main` (empty `main..Shopify-connector`),
  and `68007a9` is a direct ancestor of `origin/main` (clean fast-forward). Then
  fast-forwarded `Shopify-connector` to `origin/main` `a5d4543` (the merged PR
  #49 Sprint A governance foundation) and pushed normally (`68007a9..a5d4543`,
  no force). All seven governance-foundation files are present on the branch.
- **Sprint B / Stage 1 — Pre-session governance check (2026-06-30):** Read
  `CLAUDE.md`, this handoff, `claude-learning-rules.md`, `quality-feedback-loop.md`,
  `research-methodology.md`, `resource-inventory.md`, `research-backlog.md`.
  Confirmed: current phase is **research only**; the no-code gate applies; the
  Sprint B allowed/forbidden file lists are understood; `Shopify-connector` is
  the dedicated integration branch; the Sprint B working branch
  `research/sprint-b-source-access-official-baseline` is based on
  `Shopify-connector`; the Sprint B PR will target `Shopify-connector`; the old
  branch `claude/odoo-shopify-research-setup-fs4wzi` remains non-canonical.
  Sprint B maps to backlog items RB-01.1 (source validation), RB-05.1 (official
  Shopify notes), RB-06.1 (official Odoo notes), and seeds RB-14 architecture
  questions. Added this checkpoint note. Next: Stage 2 source validation.
- **Sprint B / Stage 2 — Source access validation (2026-06-30):** Re-ran a normal
  anonymous access check on all 8 resources (no auth bypass). No status changed
  from Sprint A: 5 Accessible, 1 Partial (R4), 2 Blocked (R2 403 bot-block, R5
  login wall). Created `docs/00-source-materials/source-access-notes.md`
  (per-resource: date, URL, result, visible sections, block reason, unblock
  action, extraction path, deep-dive readiness) and added a Sprint B
  re-validation section + ChatGPT unblock decisions to `resource-inventory.md`.
  Commit `d05ab49`. Next: Stage 3 Shopify baseline.
- **Sprint B / Stage 3 — Official Shopify API baseline (2026-06-30):** Created
  `docs/01-research/shopify-official-api-notes.md` (all required sections; every
  fact cited to an exact shopify.dev URL + access date; Fact/Inference/Open
  question labelled; "Architecture constraints implied" marked inference, no
  decisions) and `docs/00-source-materials/shopify-official.md` (captured
  quotes/paraphrases). Reconciled the verification pass: REST limits cited to the
  REST-specific page (40/2 std, 400/20 Plus), general `/usage/limits` is now
  GraphQL-only; webhook retry corrected to 8/4h. Commit `468efb6`. Next: Stage 4
  Odoo baseline.
- **Sprint B / Stage 4 — Official Odoo 19 baseline (2026-06-30):** Created
  `docs/01-research/odoo-official-architecture-notes.md` (all required sections;
  every fact cited to an exact odoo.com/19.0 URL; queue/async marked Open question
  — only `ir.cron` is official, `queue_job` is community; constraints marked
  inference, no decisions) and `docs/00-source-materials/odoo-official.md`. Commit
  `08b4c75`. Next: Stage 5 architecture seeds.
- **Sprint B / Stage 5 — Architecture review seeds (2026-06-30):** Added
  AR-002…AR-008 to `architecture-review-log.md` (API strategy, sync orchestration,
  module boundaries, mapping/dedup, error handling/retries, inventory,
  fulfillment) — all Review decision "Not decided", Status "Evidence pending",
  with evidence-required/risks/follow-up; updated the log's explanatory note.
  Commit `21c460b`. Next: Stage 6 handoff + learning loop.
- **Sprint B / Stage 6 — Handoff + quality loop (2026-06-30):** Wrote the full
  Sprint B handoff (above) with the learning feedback loop; logged **DP-001**
  (prevented stale-figure issue, category #6, Mitigated) and updated the
  occurrence counter in `defect-pattern-log.md`; `rejected-approaches-log.md` and
  `technical-debt-register.md` left unchanged (none warranted). Ran the
  end-of-session quality gate (all items satisfied). Next: push branch, open one
  draft PR targeting `Shopify-connector`, then stop.

### Research Sprint C checkpoints

- **Sprint C / Stage 1 — Setup + high-power plan (2026-06-30):** Started Research
  Sprint C (research-only; no-code gate confirmed via `CLAUDE.md` §5; high-power
  mode **explicitly authorized** in the prompt). Fetched remote branches and
  verified preconditions: **PR #50 is merged into `Shopify-connector`** (the
  branch tip `d6fbcdb` *is* the PR #50 merge commit), the working branch is based
  on `Shopify-connector` (identical to it at start), and all seven required files
  are present. **Branch-name note (flagged for ChatGPT):** the harness designated
  the working branch **`claude/research-sprint-c-competitors-hgoo8t`** (already
  checked out, based on `Shopify-connector`), whereas the Sprint C prompt body
  named `research/sprint-c-competitor-deep-dives-ux-evidence`; per the
  session's hard git rule ("never push to a different branch without explicit
  permission") the work proceeds on the harness-designated branch and the **PR
  still targets `Shopify-connector`** — `main`/`dev` untouched. Read the required
  governance/research files (CLAUDE.md, this handoff, learning rules, methodology,
  resource inventory, backlog, both official baselines, all QA logs). Wrote the
  **Sprint C high-power research plan** (above) and committed it. Next: Stage 2
  source + screenshot evidence capture (controlled parallel fan-out).
- **Sprint C / Stage 2 — Source + screenshot evidence (2026-06-30):** Ran the
  documented capture→verify fan-out (16 agents, 137 tool calls) over R1–R8;
  verified each source adversarially. Wrote `competitor-source-notes.md`,
  `competitor-screenshot-inventory.md`, and the `screenshots/` READMEs (root +
  webkul/teqstars/emipro/ventortech/odoo-apps); updated `resource-inventory.md`
  with Sprint C access changes (**R2 docs still 403-blocked but Teqstars Apps
  listing accessible; R5 = R6's setup guide; pricing resolved**). No binaries saved
  (proxy returns markdown/alt-text; sprint rule allows the fallback). No auth
  bypassed. Commit `e1c5ec4`. Next: Stage 3 deep dives.
- **Sprint C / Stage 3 — Competitor deep dives (2026-06-30):** Wrote
  `competitor-deep-dives.md` — six competitors (Webkul, Teqstars, Emipro,
  VentorTech, ecommerce_shopify, sh_shopify_connector) + a blocked-source record
  for the Google Doc; each with feature classification, workflow reconstruction,
  UX, reliability, maintenance, strengths/weaknesses, learn/do-better/avoid, open
  questions; verifier downgrades reflected (R2→Blocked, EC→cron, SH multi-company→
  not-found). Commit `1e027a0`. Next: Stage 4 matrix + UX benchmark.
- **Sprint C / Stage 4 — Matrix + UX benchmark (2026-06-30):** Wrote
  `competitor-feature-matrix.md` (grouped tables, per-cell ✅/🟨/⬜/🚫/🔒 symbols +
  evidence notes + implications) and `ux-ui-benchmark.md` (evidence base, per-area
  comparisons, best patterns, gaps, principles — benchmark only, no UI designed).
  Commit `da93ba9`. Next: Stage 5 synthesis.
- **Sprint C / Stage 5 — Patterns/best-in-class/gaps/avoid (2026-06-30):** Wrote
  `common-patterns.md`, `best-in-class-observations.md`, `gaps-opportunities.md`
  (candidate/later/unknown MVP relevance — not finalized), `avoid-list.md` (each
  item with evidence/risk/prevention/arch-review flag). Updated QA logs:
  **DP-003** + counter (`defect-pattern-log.md`); a non-decision competitor-
  evidence note (`architecture-review-log.md`); avoid-list-is-not-rejection note
  (`rejected-approaches-log.md`); Sprint C no-debt note
  (`technical-debt-register.md`). Commit `890ce0b`. Next: Stage 6 handoff + PR.
- **Sprint C / Stage 6 — Handoff + quality loop (2026-06-30):** Wrote the full
  Sprint C handoff (above) with the learning feedback loop (DP-003; external
  DP-001 confirmation; future-prompt updates) and the quality-gate confirmation
  (all items satisfied). Ran final allowed/forbidden-file checks. Next: push the
  working branch and open one draft PR targeting `Shopify-connector`, then stop.

### Research/Product Sprint D checkpoints

- **Sprint D / Stage 1 — Setup + evidence read (2026-07-01):** Started
  Research/Product Sprint D (canonical feature taxonomy + capability evidence
  map). Research/synthesis-only; **no-code gate confirmed** (`CLAUDE.md` §4–§5);
  high-power mode **not required** for this sprint (focused synthesis of
  already-merged Sprint C evidence — no new competitor crawling). Fetched remote
  branches and verified preconditions: **PR #51 is merged into `Shopify-connector`**
  (branch tip `e18ba8e` *is* the PR #51 merge commit); the working branch is based
  on `Shopify-connector` (identical to it at start); all required Sprint C outputs
  present (`competitor-deep-dives.md`, `competitor-feature-matrix.md`,
  `ux-ui-benchmark.md`, `common-patterns.md`, `best-in-class-observations.md`,
  `gaps-opportunities.md`, `avoid-list.md`, `competitor-source-notes.md`,
  `competitor-screenshot-inventory.md`). **Branch-name note (flagged for ChatGPT):**
  the harness designated the working branch **`claude/feature-taxonomy-sprint-d-t8d2t0`**
  (already checked out, based on `Shopify-connector`), whereas the Sprint D prompt
  body named `product/sprint-d-feature-taxonomy`; per the session's hard git rule
  ("never push to a different branch without explicit permission") the work
  proceeds on the harness-designated branch and the **PR still targets
  `Shopify-connector`** — `main`/plain `dev` untouched. Read the required
  governance/research files (CLAUDE.md, README, this handoff, learning rules,
  methodology, resource inventory, both official baselines, all Sprint C evidence,
  all QA logs). Confirmed DP-003/DP-004 prevention rules (competitor claim ≠ fact;
  configuration field ≠ demonstrated support; market promise ≠ demonstrated
  bidirectionality; ✅ requires demonstrated workflow/explicit evidence). Next:
  Stage 2 — draft the canonical feature taxonomy in `docs/02-product/feature-taxonomy.md`.
- **Sprint D / Stage 2 — Canonical taxonomy (2026-07-01):** Wrote
  `docs/02-product/feature-taxonomy.md` — the main deliverable: 20 canonical
  domains, ≈90 canonical capabilities (each with the required attribute block:
  ID/name/description/user-value/evidence-status/evidence-references/competitor-
  examples/UX/reliability/config implications/architecture-dependency/candidate-
  classification/MVP-relevance/notes), 8 cross-cutting groups, a classification
  summary, MVP-candidate + later-phase inputs (not decisions), a capabilities-
  requiring-architecture-review map to AR-002…AR-008, a weak/blocked-evidence
  register, open questions, and ChatGPT review notes. DP-003/DP-004 discipline
  applied throughout (claims stay claims; WK multi-company ➖; SH multi-company
  not-found; EC export not-found; `✅` only where demonstrated). Synthesis was
  worker-owned (no fan-out). Commit `70391b9`. Next: Stage 3 evidence map.
- **Sprint D / Stage 3 — Capability evidence map (2026-07-01):** Wrote
  `docs/02-product/capability-evidence-map.md` — compact per-capability
  traceability with evidence strength (A official / B strong-competitor / C
  mixed / D single-claim / E open-whitespace), strongest evidence, per-competitor
  coverage (WK/TQ/EM/VT/EC/SH with ✅/🟨/⬜/🚫/🔒/➖), official-platform dependency,
  architecture-review need (AR-002…AR-008), and MVP-review relevance. Grouped by
  domain for readability (no giant unreadable table). Commit `aa5d2c4`. Next:
  Stage 4 handoffs + QA loop.
- **Sprint D / Stage 4 — Product handoff + QA loop (2026-07-01):** Wrote
  `docs/02-product/product-research-handoff.md` (product-side handoff); wrote the
  full Sprint D section of this rolling handoff (above) with the learning feedback
  loop (DP-005 premature-decision risk, Mitigated) and the quality-gate
  confirmation; updated QA logs (**DP-005** + counter in `defect-pattern-log.md`;
  Sprint D non-decision note in `architecture-review-log.md`; nothing-rejected note
  in `rejected-approaches-log.md`; no-debt note in `technical-debt-register.md`).
  Ran final allowed/forbidden-file checks. Next: push the working branch and open
  one draft PR targeting `Shopify-connector`, then stop.

### Product Sprint E checkpoints

- **Sprint E / Stage 1 — Setup + evidence read (2026-07-01):** Started **Product
  Sprint E** (product vision, premium quality bar, differentiation strategy, and
  setup/UX principles). Product strategy / synthesis only; **no-code gate confirmed**
  (`CLAUDE.md` §4–§5); high-power mode **not required** (focused product synthesis of
  already-merged repo evidence — no new competitor crawling, no research fan-out).
  Fetched remote branches and verified preconditions: **PR #52 is merged into
  `Shopify-connector`** (confirmed via GitHub API — `merged: true`, merged 2026-07-01;
  branch tip `9a744f7` *is* the PR #52 merge commit); the working branch is based on
  `Shopify-connector` (identical to it at start); all required Sprint D outputs present
  (`feature-taxonomy.md`, `capability-evidence-map.md`, `product-research-handoff.md`);
  the **DP-006 evidence-consistency gate** is present in `defect-pattern-log.md`.
  **Branch-name note (flagged for ChatGPT):** the harness designated the working branch
  **`claude/sprint-e-product-strategy-gd2kfs`** (already checked out, based on
  `Shopify-connector`), whereas the Sprint E prompt body named
  `product/sprint-e-product-vision-quality-bar`; per the session's hard git rule
  ("never push to a different branch without explicit permission") the work proceeds on
  the harness-designated branch and the **PR still targets `Shopify-connector`** —
  `main`/plain `dev` untouched. Read the required governance/product/research files
  (CLAUDE.md, README, this handoff, research methodology, both official baselines,
  competitor deep dives + matrix, UX/UI benchmark, common patterns, best-in-class,
  gaps/opportunities, avoid-list, feature taxonomy, capability evidence map, product
  handoff, all QA logs, learning rules). Confirmed the phase is still **no-code**, that
  Sprint E is **product vision / strategy only** (no MVP finalization, no architecture
  finalization, no ADRs, no module boundaries), and the **DP-003/DP-004/DP-006**
  prevention + evidence-consistency rules (competitor claim ≠ fact; config field ≠
  demonstrated support; market promise ≠ demonstrated bidirectionality; conditional
  platform requirements stay conditional; improvement opportunities are inference, not
  demonstrated evidence; no capability enters MVP/architecture as a decision until
  ChatGPT-reviewed). Next: Stage 2 — draft `docs/02-product/product-vision.md`.
- **Sprint E / Stage 2 — Product vision (2026-07-01):** Wrote
  `docs/02-product/product-vision.md` — the main deliverable: status/purpose/evidence
  base, what we are building, product thesis, target personas (P1–P4, inference-level),
  core customer problems, ten product principles, premium quality bar, five-theme
  differentiation strategy, per-domain strategies (UX / reliability & correctness /
  modularity & customizability / performance / security & permissions / docs-support-
  trust), what we do better than competitors, what we avoid, seven product
  non-negotiables, and explicit **MVP / later / architecture inputs (not decisions)** +
  open questions + ChatGPT review notes. Claim labels ([Fact]/[Competitor claim]/
  [Demonstrated]/[Inference]/[Recommendation]/[Open question]) applied throughout;
  competitor claims kept as claims (EM/VT-demonstrated weighted over SH/WK/EC/TQ);
  conditional items (OAuth, distribution, queue, REST/GraphQL, multi-company, module
  boundaries, payouts, data models) kept conditional/open (DP-006). Worker-owned (no
  fan-out). Commit `d3da053`. Next: Stage 3 — setup/UX principles.
- **Sprint E / Stage 3 — Setup & UX principles (2026-07-01):** Wrote
  `docs/02-product/setup-ux-principles.md` — a UX north star + 12 principles (guided
  setup; prove readiness; progressive disclosure; honest status & freshness; command
  center over scattered menus; recovery-first errors; safe-by-default actions;
  human-readable logs; guided mappings; role-aware UX; modular feature visibility;
  docs mirror the product) + per-area principle sets (setup flow, config screens,
  dashboard, sync operations, logs/retries/recovery, mapping screens,
  multi-store/permissions, advanced features) + anti-patterns + open questions +
  ChatGPT review notes. Grounded in Sprint C UX benchmark / best-in-class / avoid-list
  + Sprint D taxonomy; DP-003/004/006 discipline applied; **no screens or menus
  designed**. Commit `5561db3`. Next: Stage 4 — handoffs + QA loop.
- **Sprint E / Stage 4 — Handoffs + QA loop (2026-07-01):** Wrote the Sprint E section
  of `docs/02-product/product-research-handoff.md` and of this rolling handoff (above),
  each with the learning feedback loop (no new issue; DP-006 gate applied, not
  re-triggered) and, here, the quality-gate confirmation. Updated QA logs with
  non-decision / no-new-issue notes: `defect-pattern-log.md` (Sprint E note — DP-006
  gate applied, not re-triggered, no counter change), `architecture-review-log.md`
  (Sprint E non-decision note — vision/UX principles supply product-intent inputs to
  AR-002…AR-008, all still Not decided / Evidence pending), `rejected-approaches-log.md`
  (nothing rejected), `technical-debt-register.md` (no debt). Ran final allowed/
  forbidden-file checks. Next: push the working branch and open one draft PR targeting
  `Shopify-connector`, then stop.

### Product Sprint F checkpoints

- **Sprint F / Stage 1 — Setup + evidence read (2026-07-01):** Started **Product
  Sprint F** (MVP scope proposal, non-MVP/later-phase boundaries, and user stories —
  backlog item **RB-13**). MVP-proposal synthesis only; **no-code gate confirmed**
  (`CLAUDE.md` §4–§5); high-power mode **not required** (focused product/MVP synthesis
  of already-merged repo evidence — no new competitor crawling, no research fan-out).
  Fetched remote branches and verified preconditions: **PR #53 is merged into
  `Shopify-connector`** (confirmed via GitHub API — `merged: true`, merged 2026-07-01
  10:17Z; branch tip `6e73f82` *is* the PR #53 merge commit); the working branch
  `claude/mvp-scope-user-stories-dms7s8` is based on `Shopify-connector` (identical to
  it at start, merge-base `6e73f82`). All required inputs present:
  `feature-taxonomy.md`, `capability-evidence-map.md`, `product-vision.md`,
  `setup-ux-principles.md`, `product-research-handoff.md`, and the **DP-006
  evidence-consistency gate** in `defect-pattern-log.md`. **Branch-name note for
  ChatGPT (flagged):** the Sprint F prompt body named
  `product/sprint-f-mvp-scope-proposal`, but the session's hard git rule designated
  the harness branch `claude/mvp-scope-user-stories-dms7s8` ("never push to a
  different branch without explicit permission"), so work proceeds on the
  harness-designated branch; **the PR still targets `Shopify-connector`**; `main` and
  plain `dev` untouched. Read `CLAUDE.md`, the required research/product/QA files, and
  confirmed: current phase is still no-code; Sprint F is MVP **proposal** only;
  architecture stays gated (AR-002…AR-008 all Not decided / Evidence pending);
  implementation stays gated; DP-003/004/005/006 prevention rules understood. Added
  this checkpoint. Next: Stage 2 — draft `docs/02-product/mvp-scope.md`.
