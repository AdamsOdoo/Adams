# Master Blueprint Integrity & Competitor Advantage Audit

> **Documentation-only audit. Not implementation. Not Part E.** This is a
> pre-Part-E quality gate performed after PR #77 (DEC-016 acceptance) merged
> into `Shopify-connector`. It checks whether the accepted foundation
> (DEC-003 through DEC-016, AR-002 through AR-013, Master Blueprint Parts
> A–D) is internally consistent, competitor-aware, and safe to carry into
> Part E. It resolves no open MBQ, changes no accepted decision, and
> authorizes no code.

## 1. Audit basis

- **Date:** 2026-07-04.
- **Branch:** `claude/master-blueprint-audit-ngu1k9`, branched from
  `Shopify-connector`.
- **Merge baseline:** PR #77 ("Accept Master Blueprint Sprint D UI/UX Screen
  Design Blueprint (DEC-016)"), merge commit
  `747bee86b4b1687afbbf1d150c6f808ece411670`. Confirmed via
  `git merge-base --is-ancestor` that this commit is an ancestor of both the
  audit branch and `origin/Shopify-connector` at audit time.
- **Documents reviewed (direct, firsthand read unless noted):** `CLAUDE.md`;
  `docs/01-research/research-methodology.md`; `resource-inventory.md`;
  `docs/00-source-materials/competitor-source-notes.md` (indirect, via
  citations in `common-patterns.md`/`best-in-class-observations.md`/
  `gaps-opportunities.md`/`product-vision.md`); `competitor-screenshot-inventory.md`
  (full); `docs/01-research/ux-ui-benchmark.md` (Sprint D screenshot-audit
  section, full; remainder via citation cross-check); `competitor-feature-matrix.md`
  (indirect, via `common-patterns.md` citations); `competitor-deep-dives.md`
  (indirect, via `common-patterns.md`/`best-in-class-observations.md` citations);
  `avoid-list.md` (full); `best-in-class-observations.md` (full);
  `common-patterns.md` (full); `gaps-opportunities.md` (full);
  `shopify-official-api-notes.md` (full); `odoo-official-architecture-notes.md`
  (full); `docs/02-product/product-vision.md` (full); `setup-ux-principles.md`
  (indirect, via `product-vision.md` citations); `ux-operator-flow.md`
  (indirect, via `DEC-012`/architecture-review-log citations);
  `docs/03-architecture/master-blueprint.md` (full);
  `master-blueprint-core-substrate.md` (targeted read + grep: Status header,
  extension-rule list, guardrail citations); `master-blueprint-product-customer-sale.md`
  (targeted read + grep: Status header); `master-blueprint-inventory-fulfillment.md`
  (targeted read + grep: quantity/location sections, guardrail citations,
  fulfillment-log section); `master-blueprint-ui-ux-screen-design.md`
  (targeted read + grep: header, scope section, claim-label legend, pixel-boundary
  language, sh_shopify_connector chart disposition, status residue throughout);
  `master-blueprint-open-questions.md` (full, verbatim); `docs/04-decisions/DEC-003`
  through `DEC-016` (full README summaries + Status-header grep on all 14 files;
  DEC-016 and DEC-003 read in full); `docs/05-qa/architecture-review-log.md`
  (full, both halves); `rejected-approaches-log.md` (full);
  `quality-feedback-loop.md` (full); `technical-debt-register.md` (full);
  `docs/06-prompts/implementation-task-template.md` (full);
  `docs/06-prompts/session-handoff-template.md` (full);
  `docs/01-research/research-handoff.md` (current top entry and Sprint
  B/C/D checkpoint history, ~750 of 5,570 lines).
- **Method note:** a 7-workstream parallel research fan-out was launched via
  the Workflow tool to independently cross-check each audit dimension: all 7
  agent runs failed on an account-level session usage limit before returning
  results (a resume attempt after the limit reset also did not return usable
  output within this session). This audit therefore rests on **direct,
  firsthand reads and targeted greps** of the primary governance documents
  by the auditing session itself, cross-referenced against each other (e.g.
  every DEC's own Status header checked against `docs/04-decisions/README.md`
  and `architecture-review-log.md`'s narrative; every named MBQ checked
  against the register's own verbatim text; guardrail themes checked with
  direct greps against the four blueprint bodies). No finding below rests on
  an unverified subagent claim.
- **No-code confirmation:** no `*.py`, `*.xml`, `*.csv`, manifest, model,
  view, controller, security, test, migration, CI, or Odoo module file was
  created or modified to produce this audit. Only Read/Grep/Glob were used
  against the existing repository; the two files this session writes are
  both Markdown documentation (this file and a handoff entry).

## 2. Executive verdict

**READY FOR PART E WITH CONDITIONS.**

The accepted foundation (DEC-003–DEC-016, AR-002–AR-013, Master Blueprint
Parts A–D) is internally consistent, does not authorize implementation
anywhere, does not silently resolve any MBQ it shouldn't, and does not
reintroduce any rejected approach. Competitor intelligence is used
strategically (specific, cited advantages and gaps drive specific blueprint
decisions), not just archived. One concrete documentation defect was found
(§7/§9) and a large, honestly-tracked set of open MBQs remains — both are
expected at this stage and neither invalidates the accepted work, but both
should be addressed as conditions before or during the start of Part E.

## 3. Accepted decision consistency

### Contradictions between DEC-003..016

**None found.** All 14 decision records (`DEC-003` through `DEC-016`) carry
self-consistent, unambiguous `## Status` headers reading "Accepted by
ChatGPT" with an acceptance date (verified via a direct grep across every
`docs/04-decisions/DEC-0*.md` file). `docs/04-decisions/README.md` narrates
each acceptance in strict chronological order and every subsequent
acceptance note explicitly reaffirms "DEC-00X through DEC-0YY remain
unchanged," a pattern repeated in `architecture-review-log.md`'s acceptance
notes for AR-002 through AR-013. No DEC record redefines a term, scope
boundary, or technical strategy set by an earlier accepted DEC.

### Part A/B/C/D vs accepted DEC alignment

**Consistent**, with one **documentation-residue exception** (not a
substantive contradiction — see §7/§9). `master-blueprint.md` (the index)
correctly lists Part A→DEC-013, Part B→DEC-014, Part C→DEC-015, Part D→DEC-016,
each "Accepted by ChatGPT," and its "Relation to accepted decisions" table
correctly maps every DEC-003 through DEC-012 concept to the blueprint part
that uses it. The Part A (`master-blueprint-core-substrate.md`), Part B
(`master-blueprint-product-customer-sale.md`), and Part C
(`master-blueprint-inventory-fulfillment.md`) documents' own `## Status`
sections all correctly read "Accepted by ChatGPT via DEC-01X" (verified by
direct grep). **Part D's own document does not**: see §7.

### Implementation-authorization risk

**None found.** Every DEC record (003–016), every AR-log acceptance note, and
`master-blueprint.md`'s own "Implementation remains blocked" section
explicitly and repeatedly states that the given acceptance "does not
authorize implementation," lists what it does *not* create (no Odoo module,
model, view, controller, security file, manifest, test, CI workflow, or
dependency change), and reaffirms that the `CLAUDE.md` §4–§5 no-code gate
remains in force. `master-blueprint.md`'s "Criteria for when implementation
may later be opened" section defines five explicit conditions (blueprint
parts accepted; blocking MBQs resolved/accepted-as-risk; a **separate**
explicit ChatGPT gate-opening; every task written to the CLAUDE.md §9
template; no open quality-gate escalation) — none of which reads as
self-satisfying on blueprint acceptance alone. No DEC record or blueprint
part contains language that could be read as satisfying condition 3 (the
explicit gate) by itself.

### Silent MBQ resolution risk

**None found.** The MBQ register (`master-blueprint-open-questions.md`) is
unusually disciplined about this exact risk: its own "Status" section states
"Registering (or accepting the register containing) a question does **not**
decide it and does **not** authorize implementation," and every acceptance
note (DEC-013 through DEC-016) explicitly lists, row by row, which MBQs are
resolved, partially resolved, or explicitly **left open, unchanged** by that
acceptance (e.g. the DEC-016 note: "MBQ-33, MBQ-34, MBQ-41, MBQ-35, and
MBQ-32 remain open recommendations, not decided by this acceptance"). Cross-
checking every DEC-013–016 acceptance note against the register's own rows
found no case where a DEC's acceptance language and the register's row status
diverge.

### Part D scope boundary check

**Confirmed correctly limited to screen-design blueprint level.** Exact quote
from DEC-016's Status section:

> "**Accepted at screen-design blueprint level only** — this acceptance is
> **not implementation-authorizing** under any outcome... and is **not a
> final pixel-level UI approval**; pixel-level visual design / final
> wireframe polish is explicitly **not accepted here**."

And from its "Accepted decision" point (G):

> "**Pixel-level visual design deferred — not accepted here.** This
> acceptance is a **screen-design blueprint** acceptance only. Pixel-level
> visual design and final wireframe polish are explicitly **out of scope**
> and **not accepted** by this record."

`master-blueprint-ui-ux-screen-design.md` itself states the identical
boundary in its own scope section: a screen spec "is **not** a pixel mockup
and **not** Odoo view XML. Pixel/interaction fidelity and the exact XML are
implementation-planning artifacts gated on MBQ-03 and a later, separately-
authorized design pass" (§"What 'screen-level wireframe spec' means here").
A grep of the entire document for pixel/hex/font-size/color-code language
found **zero** instances of concrete visual-design values (colors, fonts,
spacing units) presented as final — only the two hits above, both explicitly
*disclaiming* pixel-level content. **No overstepping into pixel-level
specifics was found.**

## 4. Open MBQ integrity and routing

None of the rows below are resolved by this audit. Status is quoted/paraphrased
directly from `master-blueprint-open-questions.md`.

| MBQ | Status | Blocks what | Owner | Recommended Part E handling | Notes |
| --- | --- | --- | --- | --- | --- |
| MBQ-03 | Open | Any operator-facing screen/view/UI-flow implementation | Implementation planning | Must decide before implementation prompt exists | Exact view/menu/action XML IDs; sibling of MBQ-53 |
| MBQ-04 | Open | Any credential-touching code | ChatGPT + Official-doc verification | Must decide before implementation prompt exists | Credential storage/encryption mechanism; DEC-004 fixed masking/least-privilege but not storage mechanism |
| MBQ-06 | Open | Setup wizard | ChatGPT (or Implementation planning) | Must decide before implementation prompt exists | Readiness-check essential-vs-nice-to-have split; also a Part D sibling row |
| MBQ-08 | Open | Disconnect flow | ChatGPT | Must decide before implementation prompt exists | Store-disconnect data-retention posture |
| MBQ-16 | Open | Retry/backoff code | Implementation planning | Can be decided in the first implementation-planning task | Exact retry-count ceilings and backoff constants |
| MBQ-17 | Open | Reconciliation job | ChatGPT (posture) + Implementation planning (constants) | Must decide before implementation prompt exists (posture); rest in first task | Cadence/scope of the mandatory correctness backstop |
| MBQ-18 | Open | Queue constants (throughput validation blocks release readiness, not code start) | Implementation planning | Can be decided in the first implementation-planning task | Cron cadence/batch sizes under `--max-cron-threads=2` |
| MBQ-19 | Open | Job/log model (every domain depends on it) | Implementation planning | Must decide before implementation prompt exists | Single job model vs job+log split; foundational, decide once early |
| MBQ-20 | Open | Operation-level idempotency code | Implementation planning | Can be decided in the first implementation-planning task | Idempotency key schema (op type, target ID, payload hash) |
| MBQ-21 | Open | Ambiguous-operation guard code | Implementation planning | Can be decided in the first implementation-planning task | Serialization-guard mechanism |
| MBQ-22 | Open | Nothing at code-start (structure already fixed) | Later UI-design pass | Can remain a documented risk (until the copy pass) | Exact user-facing copy/wording |
| MBQ-27 | Open, inconclusive (official-doc check done, mechanism unresolved) | Order import | Official-doc verification + Implementation planning | Requires official Shopify/Odoo verification | Shopify-computed-tax representation on an Odoo sale order without ORM recomputation |
| MBQ-28 | Not triggered by Sprint B | Nothing currently | ChatGPT (only if triggered) | Can remain a documented risk | Domain 9 draft-artifact guard; returns to ChatGPT only if a later sprint triggers it |
| MBQ-32 | Partially resolved by DEC-015 (sources verified, non-equivalent; selection open) | Inventory quantity write-back | Official-doc verification (done) + ChatGPT/Implementation planning (selection) | Must decide before implementation prompt exists | `free_qty` nets out `expired_unreserved_qty`; `available_quantity` does not — not interchangeable |
| MBQ-33 | Open (DEC-015 carries a recommendation, not a decision) | First-push guard | ChatGPT | Must decide before implementation prompt exists | Granularity of "first" (per-store/binding/variant-location) |
| MBQ-34 | Open (DEC-015 carries a recommendation, not a decision) | Post-first-push writes | ChatGPT | Must decide before implementation prompt exists | Auto-apply vs review-then-apply |
| MBQ-35 | Open, unchanged since Sprint A | Only blocks an `on_hand` UI if ever built | ChatGPT | Can remain a documented risk (until `on_hand` UI is proposed) | Whether `on_hand` is ever exposed as a Phase 1 UI choice |
| MBQ-41 | Open (DEC-015 carries a recommendation, not a decision) | Notification UI beyond the per-store default | ChatGPT | Must decide before implementation prompt exists (for the default); rest can be documented risk | Per-order notification-override granularity |
| MBQ-44 | Open | Everything (`ir.model.access` is deny-by-default) | Implementation planning | Must decide before implementation prompt exists | Exact security groups/access CSVs/record rules |
| MBQ-45 | Partially resolved by DEC-013 (hierarchy accepted; mapping open) | Group design before CSVs are written | Implementation planning | Must decide before implementation prompt exists | Roles→groups mapping; admin-vs-functional surface split |
| MBQ-53 | Partially resolved by DEC-016 at screen-design level only; stays open/partial | Any operator-facing screen implementation | ChatGPT (closure depends on MBQ-03/22/44/45/06) | Must decide before implementation prompt exists | Full closure needs all five sibling rows resolved |
| MBQ-54 | Open | Uninstall/disable lifecycle only (not normal MVP sync) | ChatGPT + Implementation planning | Can remain a documented risk if uninstall is guarded/unsupported in Phase 1 | Domain-module uninstall must not silently lose bindings/logs/audit history |
| MBQ-55 | Open | Sprint B binding models | Implementation planning | Must decide before implementation prompt exists | Exact model/field names for product-template/variant/customer/order bindings |
| MBQ-56 | Open | Order import | Implementation planning | Can be decided in the first implementation-planning task | Total-check guard tolerance/comparison mechanism |
| MBQ-57 | Open, current rule stands unless revisited | Nothing now | ChatGPT (future, only if revisited) | Can remain a documented risk | Whether whole-order-hold ever needs a partial-line alternative |
| MBQ-58 | Open, defensive design already stands | Nothing now | Official-doc verification | Can remain a documented risk | Shopify order-identity stability nuances beyond general GID non-permanence |
| MBQ-60 | Open, newly surfaced | Fulfillment tracking write-back | ChatGPT (whether to require it) + Implementation planning | Must decide before implementation prompt exists | Whether `shopify_connector_fulfillment` requires the Odoo `stock_delivery` module |
| MBQ-61 | Open, newly surfaced | Not MVP correctness-core fulfillment creation; yes if hold-aware UX is later required | ChatGPT + Implementation planning | Can remain a documented risk for MVP | FulfillmentOrder lifecycle events beyond creation (holds, merges, splits, moves) |
| MBQ-62 | Open, new (Fable finding C2) | Odoo-event-triggered inventory push and fulfillment creation specifically | ChatGPT + Implementation planning | Must decide before implementation prompt exists | Job-source classification for Odoo-side event triggers; not a Part A §D.2 enum value today |
| MBQ-63 | Open, new (Fable minor finding 4) | Webhook-driven inventory import specifically; not other sync mechanisms | Implementation planning, with official-doc verification | Requires official Shopify/Odoo verification | Inventory-webhook payload shape/subscription mechanics/Phase-1-implementation-scope |

**Additional implementation-blocking MBQs not in the named list** (found by a
full sweep of the register, so none is silently dropped per the register's
own maintenance rule): **MBQ-01/MBQ-02** (exact model/field names — blocks
everything, implementation planning), **MBQ-05** (custom-app creation surface
/ token mechanics — blocks the setup wizard, implementation planning within
DEC-004's fixed model), **MBQ-09** (whether custom apps must implement
Shopify's compliance webhooks — official-doc verification, conservative
posture applies meanwhile), **MBQ-14** (idempotency-key uniqueness scope —
blocks inventory/refund write code, official-doc verification), **MBQ-15**
(Bulk Operation idempotency/resumability — blocks only if/when internal bulk
is used), **MBQ-23/25/29/30** (variant-mutation strategy, draft/publish
mechanism, default-customer fallback, gateway→journal mapping — each
partially resolved by DEC-014, exact detail open), **MBQ-36/38** (inventory
mutation choice per trigger, first-push confirmation record schema — each
partially resolved by DEC-015), **MBQ-40** (backorder-to-picking wizard-UX
residual), **MBQ-42/43** (fulfillment location-confirmation exact detail,
Location-reference cache refresh cadence — each partially resolved),
**MBQ-51/52** (GraphQL cost/throttle pacing parameters; API-version pinning
policy — blocks the transport client).

## 5. Competitor advantage assessment

### Where our blueprint is stronger

- **Unified command center + recovery-first error center, together.** The
  competitor survey found SH has the best monitoring (activity chart,
  failure counts) and VT the best diagnostics (traffic-light health,
  Preview/Report dry-run), but "**neither** has both"
  (`gaps-opportunities.md` O-DASH-1). The accepted DEC-012 ten-flow model +
  Part D's single-shared-surface dashboard/sync-center/error-center combine
  both halves in one accepted design.
- **Idempotency + reconciliation + rate-limit-aware throttling as
  architecture, not an afterthought.** Only VentorTech mechanizes
  idempotency among all six surveyed connectors, and "**no competitor**
  describes" rate-limit/GraphQL-cost handling (`avoid-list.md` A-SYNC-5;
  `gaps-opportunities.md` O-REL-1/O-REL-2) — Sprint C2's TeqStars rebaseline
  reconfirmed this is still true even for the most feature-rich competitor.
  DEC-009 (classified retry + layered idempotency) and DEC-010/DEC-011
  (idempotency applied to inventory/fulfillment writes) make this an
  accepted architectural default, not an optional add-on.
- **Per-location inventory identity, not SKU-only or single-location.**
  Webkul's single-default-location design and any SKU-only write path are
  named market anti-patterns (`avoid-list.md` A-INV-2) that risk double-
  decrementing multi-location SKUs. DEC-010 keys inventory identity on
  `(store, inventory_item_id, location_id)` explicitly to avoid this (see
  §7, RA-019).
- **FulfillmentOrder-exclusive, order/line/quantity/location-matched
  fulfillment.** The legacy Order/Fulfillment workflow is unsupported since
  API version 2022-07 (`shopify-official-api-notes.md`); DEC-011 mandates
  FulfillmentOrder-based mutations only, with explicit matching — closing a
  risk area no competitor evidence suggests any of them still carries, but
  that the blueprint proactively guards against (RA-022/RA-023).
- **Honest freshness/latency labelling as a designed-in requirement**, not
  a UX nicety — directly countering the demonstrated market pattern of
  "real-time" mislabelling over cron/queue models (`avoid-list.md` A-UX-1;
  `common-patterns.md` "Common but weakly evidenced patterns").

### Where competitors still lead (not yet adopted)

- **`sh_shopify_connector`'s "Daily Queue Activity Tracking" time-series
  chart** — "the single best monitoring visual in the benchmark," per
  `ux-ui-benchmark.md`'s Sprint D screenshot audit — has **no counterpart**
  in the accepted nine-card dashboard (count cards + a textual timeline
  only, no chart/graph). Explicitly and correctly **deferred**, not
  adopted — see the dedicated callout below.
- **Emipro's CSV/XLSX product-mapping fallback** for non-SKU catalogs is not
  reflected anywhere in the accepted Part B blueprint. Given MVP scope uses
  SKU/barcode-first matching (DEC-006), this is a legitimate, scoped gap —
  worth a deliberate "defer, not silently drop" note rather than leaving it
  unmentioned.
- **VentorTech's automatic retry of safe operations** is the only
  competitor-demonstrated instance of this pattern; DEC-009 accepts the
  *classification* (auto-retry for safe/idempotent classes) but the exact
  backoff constants remain open (MBQ-16) — the blueprint's direction matches
  or exceeds this, but it is not yet a demonstrated implementation.
- **TeqStars' reason-coded Auto/Manual payout reconciliation** is out of MVP
  scope (payouts deferred per `non-mvp-and-later-phases.md`), so this is a
  correctly and explicitly scoped-out gap, not an oversight.

### Patterns to copy / copy-and-improve / avoid / defer

- **Copy:** OAuth-first connect with an up-front scope check + connection
  test (VentorTech) — reflected in DEC-004/DEC-012's setup-wizard readiness
  check.
- **Copy-and-improve:** VentorTech's traffic-light webhook health
  (green/yellow/red, named cause) generalized in Part D's system-wide
  connection/webhook/sync health states, beyond just webhooks.
- **Avoid:** exposing raw `ir.cron` internals (Webkul's "Model, Scheduler
  User, Next Execution Date" fields) — DEC-012/Part D's UX explicitly hides
  cron plumbing behind friendly scheduling language (A-UX-2).
- **Avoid:** toggle-dense configuration with unexplained jargon
  (Emipro/Softhealer/Webkul/TeqStars all demonstrate this) — Part D's
  progressive-disclosure requirement directly counters it (A-UX-3).
- **Defer:** `sh_shopify_connector`'s Daily Queue Activity Tracking chart,
  gift cards, abandoned-checkout→CRM, product recommendations, Buy-with-
  Prime, Markets/Catalogs, B2B/VAT — all correctly logged as later/optional
  add-ons in `product-vision.md` and `non-mvp-and-later-phases.md`, not
  silently dropped.

### Premium differentiators to protect in Part E

Idempotency + reconciliation + rate-limit-aware throttling as a demonstrated
(not just claimed) default; the unified command center + recovery-first
error center combination; effortless-yet-reliable onboarding (OAuth-first +
readiness check, without VentorTech's heavy `odoo.conf`/`queue_job` install
burden); honest status/freshness labelling; premium breadth shipped as
optional add-ons on a correct core, not bolted onto it.

### Overcomplication risks vs competitors

The accepted job/log/error substrate (6 job sources, 10 job states, 16 error
classes, 6 manual-review sub-reasons, 4 roles) is materially richer than any
surveyed competitor's model (the best competitor observability, Emipro's Log
Book, uses a simple Draft/Failed/Cancelled/Done state set). This is a
deliberate, evidence-grounded differentiation (correctness/recovery-first is
the product thesis's headline theme), not an accidental complexity creep —
but it is worth Part E explicitly re-checking the "premium, not bloated"
principle (`product-vision.md` principle 10 and its anti-definition of
premium) at the *operator-facing* surface: the backend taxonomy being rich
does not itself risk overcomplication, but a UI that exposes all 16 error
classes or all 10 job states undifferentiated to an operator would. Part D's
grouped-state screens appear to already guard against this; Part E should
confirm no implementation step flattens that grouping away.

### sh_shopify_connector Daily Queue Activity Tracking chart status

**Explicitly deferred, not adopted.** Direct quote from DEC-016:

> "the `sh_shopify_connector` 'Daily Queue Activity Tracking' chart idea
> surfaced by that audit **remains a deferred premium visualization
> candidate for a later pixel-design pass, not adopted into the accepted
> dashboard card set**."

And from `ux-ui-benchmark.md`'s Sprint D screenshot-audit section: "This
audit does **not** propose adding a tenth card or a chart to the accepted
set... it is logged here as a candidate **premium visualization idea for a
later pixel-design pass** (Part E, or a future implementation-design
revision of Part D), **not decided or adopted now**."

### Screenshot evidence-level limitation

**Confirmed: no pixel-level (rendered image) inspection was ever performed.**
`competitor-screenshot-inventory.md`'s own framing states pages were read
"through the proxy fetcher, which returns **page→markdown / alt-text, not
pixels**," and that for the marketplace listings and marketing pages,
"captions and visible field labels are reliable but whose pixel layout was
not directly inspected." The Sprint D screenshot audit (`ux-ui-benchmark.md`,
2026-07-04) states this explicitly and currently: "No pixel-level (rendered
image) inspection was performed this session... all evidence above is
caption/alt-text/step-text based" — and records that "a same-session attempt
to drive a real headless browser for actual pixel rendering was abandoned
when it could not be made to work through the session's TLS-inspecting proxy
without disabling certificate verification, which is against this
environment's policy." **This audit does not claim pixel-level inspection
occurred anywhere in the project's history to date.**

## 6. Official-doc grounding gaps

| Claim / area | Current evidence | Needed verification | Blocks what | Recommended timing |
| --- | --- | --- | --- | --- |
| Credential encryption/storage-at-rest mechanism (MBQ-04) | DEC-004 fixes masking + least-privilege; storage mechanism unverified | Odoo field-level `groups` protection vs additional encryption — an Odoo capability check | Any credential-touching code | Before Part E's first implementation task |
| `@idempotent` key-uniqueness scope (per-shop/app/global) (MBQ-14) | Shopify docs confirm the directive + 24h server-side dedup TTL, but not key-scope | Official Shopify docs / schema introspection | Inventory/refund write code | Before Part E's inventory/fulfillment task |
| Bulk Operation idempotency/resumability semantics (MBQ-15) | Bulk-op mechanics (JSONL, concurrency, time/size limits) are well-grounded; idempotency-on-resume is not addressed | Official Shopify docs, if/when internal bulk is used | Only bulk-backfill code, if built | Can defer until bulk is actually used |
| Custom-app compliance-webhook obligations (MBQ-09) | Official docs state the 3 mandatory webhooks are App-Store-scoped; whether they bind non-Store custom apps is not stated | Official Shopify docs (compliance/privacy-law-compliance) | Any compliance-relevant code | Before Part E, conservative posture applies meanwhile |
| Odoo.sh/on-prem `server_wide_modules` + Jobrunner support for OCA `queue_job` | Absence of documentation, not a documented denial (`odoo-official-architecture-notes.md`) | Odoo.sh support channel or direct experiment | The AR-003 "queue_job as accelerator" revisit trigger only (not the Phase 1 default, which is the internal cron-queue) | Can defer — only relevant if/when the revisit trigger fires |
| Per-plan GraphQL bucket size (`maximumAvailable` points) | Restore rates are published per plan; bucket capacity is not | Official Shopify docs / live `throttleStatus` observation | Transport-client pacing parameters (MBQ-51) | Before Part E's transport-client task |
| `stock_delivery`/`delivery` module dependency for tracking fields (MBQ-60) | `carrier_tracking_ref`/`carrier_tracking_url`/`carrier_id` are confirmed to live in that module, not core `stock` | ChatGPT decision + manifest-dependency mechanics | Fulfillment tracking write-back | Before Part E's fulfillment task |
| FulfillmentOrder lifecycle events beyond creation (holds, merges, splits, moves) (MBQ-61) | Confirmed as real Shopify webhook topics; not considered by DEC-011 at all | ChatGPT decision on whether/how to react | Not MVP correctness-core; yes if hold-aware UX is later required | Can defer for MVP; document as a known gap |
| Inventory webhook payload shape/subscription mechanics (MBQ-63) | Topic string (`INVENTORY_LEVELS_UPDATE`) verified; payload fields and required scopes beyond `read_inventory` are not | Official Shopify docs | Webhook-driven inventory import specifically (not other sync mechanisms) | Before Part E, only if webhook-driven import is implemented |
| Odoo `free_qty` vs `available_quantity` selection mechanism (MBQ-32 residual) | Both fields' exact formulas verified against official 19.0 source; the two are confirmed **non-equivalent** | A design/selection decision, not further fact-finding | Inventory quantity write-back | Before Part E's inventory task |

**Overall grounding health: strong.** Every technical/platform claim
reviewed in the accepted DEC records and blueprint parts traces to a cited
official Shopify (`shopify.dev`) or official Odoo 19.0
(`odoo.com/documentation/19.0` or `github.com/odoo/odoo` 19.0 source) page,
with an access date. No instance was found of a competitor/vendor claim
being promoted to a "Fact" without independent official verification — the
project's own `research-methodology.md` tier system and `CLAUDE.md` §8
labelling discipline are applied consistently throughout every document
this audit read. The gaps above are not undisclosed blind spots: **every one
of them is already tracked as an open MBQ row with "Official-doc
verification" correctly named as an owner** — this audit found no gap that
the project's own MBQ register does not already know about.

## 7. Rejected-approach guardrail check

| RA | Guardrail | Status | Any drift risk | Action |
| --- | --- | --- | --- | --- |
| RA-011 | One giant module | Avoided | None — `master-blueprint-core-substrate.md` §K explicitly cites "No one giant module (RA-011)"; `master-blueprint-inventory-fulfillment.md` §G repeats the same citation | None |
| RA-012 | Per-feature micro-module explosion | Avoided | None — cited alongside RA-011 in the same guardrail lists | None |
| RA-013 | Duplicating queue/job/log/binding abstractions per domain (i.e. per-domain dashboards/queues) | Avoided | None — Part D's screen inventory explicitly states "domains contribute, never fork (RA-013)" | None |
| RA-014 | Retry everything automatically | Avoided | None — DEC-009's classified retry taxonomy (auto only for safe/transient classes) is consistently restated in Parts A/B/C | None |
| RA-015 | Never-retry / manual-only recovery | Avoided | None — same DEC-009 taxonomy provides auto-retry for safe classes | None |
| RA-016 | Raw stack traces as primary UX | Avoided | None — `master-blueprint-inventory-fulfillment.md` §B.13 explicitly states "no raw stack trace as the primary UX"; DEC-009's recovery-first UX spine is restated throughout | None |
| RA-008 | Blind first Odoo→Shopify inventory push | Avoided | None — DEC-007/DEC-010's first-push guard (preview + confirmation + mapped location + recorded source-of-truth) is restated in Part C §A.5 | None |
| RA-009 | Hidden/default-on fulfillment customer notifications | Avoided | None — DEC-007/DEC-011's notification-off-by-default posture (grounded in Shopify's own `notifyCustomer` default) is restated in Part C §B.6 | None |
| RA-022 | Legacy Order/Fulfillment API instead of FulfillmentOrder | Avoided | None — DEC-011's FulfillmentOrder-exclusive mandate is unconditional and restated in Part C | None |
| RA-019 | Single-location-only or SKU-only inventory writes without per-location identity | Avoided | None — DEC-010's `(store, inventory_item_id, location_id)` identity key is restated everywhere inventory is discussed | None |
| RA-021 | Treating Shopify/Odoo inventory quantities as directly equivalent | Avoided | None — DEC-015/Part C explicitly documents `free_qty` and `available_quantity` as verified but **non-equivalent** (Fable finding C1), the exact discipline RA-021 requires | None |
| RA-001 | Thin import-only MVP pilot (Option C) | Avoided | None — DEC-003's accepted MVP scope includes controlled bidirectional product onboarding, webhooks, reconciliation, and write-back | None |
| RA-002 | REST-heavy Shopify API strategy | Avoided | None — DEC-004's GraphQL-first strategy is unconditional | None |
| RA-003 | Public App Store distribution / OAuth public-app flow as Phase 1 | Avoided | None — DEC-004's custom-app/offline-token model is unconditional for Phase 1 | None |
| RA-004 | OCA `queue_job` as the Phase 1 default substrate | Avoided | None — DEC-005's internal cron-queue remains the default; `queue_job` stays an explicit, undecided later option | None |
| RA-005 | `ir.model.data` as the primary binding/dedup mechanism | Avoided | None — DEC-006's dedicated per-store binding model is unconditional | None |
| RA-006 | Name-only automatic product/customer matching | Avoided | None — DEC-006/DEC-014's SKU/barcode-first (products) and email-only (customers) match-key rules are unconditional | None |
| RA-007 | External worker / out-of-Odoo processor as Phase 1 substrate | Avoided | None — DEC-005's internal Odoo-hosted queue is unconditional for Phase 1 | None |
| RA-010 | Automatic full accounting/payment reconciliation as default | Avoided | None — DEC-003's Domain 9 evidence-only (no accounting automation) rule is unconditional | None |
| RA-017 | No connector-designed idempotency key / binding-alone retry strategy | Avoided | None — DEC-009's operation-level idempotency-key concept, layered on top of the binding, is restated in Part A §D | None |
| RA-018 | Writing Shopify's read-only `committed` quantity | Avoided | None — a full-document grep for any "write committed" language returned zero matches; DEC-010's `available`/`on_hand`-only write target is unconditional | None |
| RA-020 | Autonomous bidirectional inventory conflict resolution in Phase 1 | Avoided | None — DEC-010's ambiguous-outcome → manual-review routing (DEC-009) applies to inventory writes; no autonomous conflict engine is proposed anywhere | None |
| RA-023 | Fulfillment creation without FulfillmentOrder/line/quantity/location matching | Avoided | None — DEC-011's explicit matching requirement via `lineItemsByFulfillmentOrder` is unconditional | None |

**No drift toward any of the 23 rejected approaches was found anywhere in
Parts A–D.** All 9 guardrail themes named in the audit task map cleanly to
specific, already-logged RA rows, and every one is correctly cited as a
negative check (not silently assumed) at the point in the blueprint where the
temptation would arise — this is a materially stronger guardrail discipline
than typical, and it held up under direct grep verification, not just a
narrative read.

## 8. Implementation-readiness assessment

**Readiness level: substantively ready, procedurally not yet opened.** The
blueprint's content (module boundaries, binding/job/log substrate, domain
flows, screen design) is detailed enough to plan implementation against.
What is missing is not blueprint depth but the explicit, separate gate-
opening step and the MBQ resolution pass — both of which `master-blueprint.md`
already names as required and neither of which this audit is authorized to
perform.

**What Part E must produce before any coding is authorized:**

- **Implementation sequence.** Follow the DEC-008 dependency DAG: `core`
  first (it has no upstream dependency and every domain module depends on
  it), then `product` (both `sale` and `inventory` resolve bindings through
  it), then `sale`/`inventory` in parallel (neither depends on the other),
  then `fulfillment` last (depends on `sale`, never on `inventory`).
- **MBQ decision plan.** A structured pass through every "Blocks
  implementation: Yes" row in §4 above, routed by owner: ChatGPT-owned
  recommendations (MBQ-06/08/33/34/41/45/60) decided first and cheaply,
  since they gate the very first implementation task in their domain;
  official-doc-verification rows (MBQ-04 partial, MBQ-14, MBQ-27, MBQ-63)
  scheduled just ahead of the task that needs them; naming rows
  (MBQ-01/02/03/22/44) committed once, early, since every later task
  references them.
- **Module-by-module task order.** Within `core`: store/connection →
  credential posture (blocked on MBQ-04) → job/log/error skeleton (MBQ-19/20/21,
  no ChatGPT-only blocker) → setup wizard (blocked on MBQ-06) → access
  groups (blocked on MBQ-44/45). Within `product`/`sale`/`inventory`/
  `fulfillment`: bindings first, then the domain's read path, then its write
  path (guarded by its first-push/confirmation rules).
- **Allowed/forbidden files per task.** `docs/06-prompts/implementation-task-template.md`
  already defines this field; Part E's job is to fill it per task, not
  redesign it.
- **Test strategy.** Per `CLAUDE.md` §9 and `avoid-list.md` A-IMP-4: mandatory
  regression tests for the classic connector defects — duplicate orders,
  multi-location double-decrement, missed-webhook reconciliation, timezone/
  paging bugs — using `TransactionCase` for ORM/mapping logic and
  `HttpCase`/tours (tagged `post_install`) for webhook controllers and setup
  UX, per the official Odoo 19.0 testing guidance already captured in
  `odoo-official-architecture-notes.md`.
- **Rollback strategy.** Feature-flag-gated enable/disable per DEC-008 §I.3/
  §I.4 ("disabling must not delete history"); per-version `migrations/{pre,
  post,end}-*.py` scripts per the official Odoo upgrade-script convention;
  no module ships without a documented reversal path.
- **Acceptance-criteria template.** Already exists
  (`implementation-task-template.md`, §4 "Acceptance criteria" +
  paste-ready prompt skeleton) and needs no redesign — Part E applies it.
- **First safe implementation slice — a recommendation only, not an
  authorization.** The job/log/error abstraction skeleton (MBQ-19/20/21)
  inside `shopify_connector_core` is the strongest first-slice candidate:
  every domain module depends on it, and unlike the credential/setup-wizard
  slice (blocked on the ChatGPT-owned MBQ-04/MBQ-06) or the access-groups
  slice (blocked on MBQ-44/45), its three open MBQs are all
  "Implementation planning"-owned with no ChatGPT-only or official-doc
  precondition — it could be the very first task written to the
  implementation-task-template once the gate opens.
- **No-code-to-code gate checklist**, restated from `master-blueprint.md`'s
  own "Criteria for when implementation may later be opened":
  1. ☑ Required Master Blueprint parts accepted (Parts A–D all accepted;
     Part D at screen-design level, sufficient for its own scope).
  2. ☐ Every "Blocks implementation: Yes" row resolved or explicitly
     accepted as an open risk by ChatGPT in writing — **not yet done**
     (§4's ~45 blocking rows remain open).
  3. ☐ ChatGPT explicitly opens the implementation gate — **not yet
     done**; this is a separate act from blueprint acceptance.
  4. ☐ Every implementation task written to the CLAUDE.md §9 template —
     **not yet done** (no implementation task exists yet).
  5. ☑ No quality-gate escalation open — confirmed clean;
     `technical-debt-register.md` and `quality-feedback-loop.md` show no
     defect-pattern category at its 3rd-occurrence pause.

**Explicit statement: no implementation is authorized by this audit or by
anything it reviewed.** Conditions 2–4 above remain the responsibility of
Part E and a separate ChatGPT gate-opening act.

## 9. Required pre-Part-E cleanup

One item found:

- **`docs/03-architecture/master-blueprint-ui-ux-screen-design.md`'s own
  `## Status` section (and its claim-label legend and closing section) still
  read "Proposed for ChatGPT review — NOT accepted," dated 2026-07-03** —
  even though its companion `DEC-016` was accepted by ChatGPT on 2026-07-04,
  and every other document in the acceptance chain (`DEC-016` itself,
  `docs/04-decisions/README.md`, `master-blueprint.md`, `master-blueprint-open-questions.md`,
  `architecture-review-log.md`, `research-handoff.md`) was correctly
  updated. Verified directly: line 16 reads "**Proposed for ChatGPT review —
  NOT accepted.**"; line 42's claim-label legend still defines "[Screen
  blueprint proposal]" as "**Not binding** unless/until DEC-016 is accepted";
  line 1134 still reads "MBQ-53 stays open **until DEC-016 is accepted**."
  Cross-checked against `research-handoff.md`'s own "Files changed" list for
  the DEC-016 Acceptance Patch commit — `master-blueprint-ui-ux-screen-design.md`
  is **not** in that list, confirming the acceptance patch never touched the
  file. **This is not a new category of risk**: the identical defect
  occurred for Part C and was caught and fixed via a dedicated follow-up
  commit (see `research-handoff.md`'s "DEC-015 Acceptance Patch — Part C
  blueprint document alignment (2026-07-03)" entry) — that same alignment
  step was simply never performed for Part D. **Recommended fix:** a small,
  documentation-only "Part D blueprint document alignment" patch — mirroring
  the Part C fix exactly (Status header → "Accepted by ChatGPT via DEC-016,
  2026-07-04, at screen-design blueprint level only"; the claim-label legend
  and every "not accepted"/"unless/until DEC-016 is accepted" phrase updated
  to reflect the actual accepted status; no architecture substance changed).
  This file is outside this audit's allowed-files scope, so the fix must be
  a separate, small session — not folded into this audit or into Part E.

No other cleanup item was found. Every other document checked for stale
wording, conflicting status labels, or accepted/proposed label errors was
internally consistent with its own acceptance history.

## 10. Required Part E focus areas

In rough priority order:

1. **MBQ decision plan** — resolve or consciously accept-as-risk the ~45
   "Blocks implementation: Yes" rows in §4, starting with the ChatGPT-owned
   recommendations (MBQ-06/08/33/34/41/45/60) since they are cheap ChatGPT
   decisions that would otherwise stall the very first implementation tasks
   in their domains.
2. **Exact naming pass** (MBQ-01/02/03/22/44) — commit Odoo model, field,
   view/menu/action XML ID, security-group, and copy conventions once, early,
   since every later implementation task references them.
3. **Credential storage/encryption mechanism** (MBQ-04) and **store-
   disconnect data-retention posture** (MBQ-08) — both ChatGPT + official-
   doc-verification items that gate the setup wizard and disconnect flow.
4. **Job/log/error abstraction implementation detail** (MBQ-16/17/18/19/20/21)
   — the recommended first safe implementation slice; no ChatGPT-only
   blocker remains once retry constants and reconciliation posture are set.
5. **Inventory quantity-source selection** (MBQ-32 residual) and **first-
   push guard granularity/apply-mode** (MBQ-33/34) — both substantive design
   choices, not further fact-finding; the underlying Odoo facts are already
   verified and non-equivalent, so this is a selection decision, not a
   research task.
6. **Fulfillment module-dependency decision** (MBQ-60: require
   `stock_delivery`?) and **lifecycle-event posture** (MBQ-61, can remain a
   documented risk for MVP) and **webhook-driven inventory import scope**
   (MBQ-63).
7. **Security groups / access CSV design** (MBQ-44/45) — needs the roles→
   groups mapping and admin-vs-functional surface split before any
   `ir.model.access.csv` can be written.
8. **Test-strategy formalization** referencing the specific classic defects
   in `avoid-list.md` A-IMP-4 (duplicate orders, multi-location double-
   decrement, missed-webhook reconciliation, timezone/paging).
9. **The Part D document-alignment cleanup** from §9 — small, but should not
   be left for Part E to trip over.
10. **A later, separately-scheduled pixel-level visual-design pass** — not a
    Part E blocker, but the natural place to reconsider the deferred
    `sh_shopify_connector` activity-chart idea against the accepted nine-
    card dashboard, per DEC-016's own recommendation.

## 11. Risks / limitations

- **Pixel-level screenshot limitation (see §5).** No competitor UI was ever
  rendered/inspected at the pixel level in this project's history; every
  screenshot-derived claim rests on page→markdown extraction, captions, or
  alt-text. A same-session attempt to use a real headless browser for pixel
  rendering was abandoned because it could not be made to work through this
  environment's TLS-inspecting proxy without disabling certificate
  verification (against environment policy) — this is a durable environment
  constraint, not a one-off gap.
- **Source-access limitations, unresolved.** VentorTech's Confluence hub
  (R4) remains **Partial** access — 17 of 28 child articles have never been
  fetched. The project's own Google Doc (R5, which is `ecommerce_shopify`'s
  setup guide) remains **Blocked** behind a Google sign-in wall and requires
  owner-granted access or an export; neither has been resolved as of this
  audit.
- **This audit's own workflow-based cross-check did not complete.** A
  7-agent parallel research fan-out was launched to independently verify
  each audit dimension; all 7 runs failed on an account-level session usage
  limit, and a resume attempt after the limit reset did not return usable
  results within this session. Every finding in this report instead rests on
  this session's own direct reads and greps of the primary documents — a
  narrower but still firsthand and citable evidence base. A future session
  with the parallel workflow available could re-run it as an independent
  second pass, particularly over the ~1,900 lines of competitor research this
  audit read only via secondary citation (`competitor-source-notes.md`,
  `competitor-feature-matrix.md`, `competitor-deep-dives.md` proper, and the
  bulk of `ux-ui-benchmark.md` outside its Sprint D audit section).
- **A large, honest backlog of open MBQs remains** (~45 implementation-
  blocking rows). This is expected and correctly tracked, not a symptom of
  poor governance — but rushing Part E without first executing the MBQ
  decision plan in §10 would recreate exactly the risk this audit was
  commissioned to catch.
- **Odoo.sh/on-prem `server_wide_modules`/Jobrunner support for OCA
  `queue_job`** remains an absence-of-documentation open question. It does
  not block the Phase 1 default (the internal cron-queue), but it gates
  whether the DEC-005 "queue_job as accelerator" revisit trigger could ever
  be exercised.

## 12. Final recommendation

**Proceed to a small, targeted documentation-only cleanup (§9's Part D
status-header alignment), then proceed to Part E — with Part E's own first
work product being the MBQ decision plan (§10, item 1), not implementation
code.** The accepted foundation is sound: no contradiction, no accidental
implementation authorization, no silent MBQ resolution, no rejected-approach
drift, and no unsupported competitor claim was found anywhere in Parts A–D.
The one confirmed defect is a small, mechanical documentation-residue issue
with a known fix pattern (already executed once for Part C). Do not reopen
Parts A, B, or C — no evidence surfaced here calls any of them into
question.
