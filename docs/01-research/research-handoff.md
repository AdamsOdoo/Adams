# Research Handoff (rolling)

> Continuity lives in GitHub, not chat. The **current sprint handoff (Sprint C)**
> is immediately below; the **Sprint B** and **Sprint A** handoffs are retained
> underneath as history. The running **Sprint checkpoint log** (one note per
> stage, all sprints) is at the very bottom.

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
