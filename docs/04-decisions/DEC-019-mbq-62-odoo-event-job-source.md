# DEC-019 — MBQ-62 Odoo-Side Event Job-Source Classification

> **Accepted decision record** for the premium **Odoo 19 ↔ Shopify
> Connector**, prepared after ChatGPT accepted
> [`DEC-018`](./DEC-018-mbq-decision-batch-1.md) (MBQ Decision Batch 1) on
> **2026-07-04**. DEC-018 accepted Batch 1 **except MBQ-62**, which it
> explicitly split into its own dedicated follow-up decision record rather
> than forcing a same-batch answer (`DEC-018` §4 "strict analysis," §8
> "Recommendation to ChatGPT — accepted"). This record is that dedicated
> follow-up, and is **itself accepted by ChatGPT on 2026-07-04** (at
> decision/semantic-classification level only — see "Status" and
> "Acceptance" below). Companion documents:
> [`../03-architecture/master-blueprint-open-questions.md`](../03-architecture/master-blueprint-open-questions.md)
> (MBQ-62 row),
> [`../03-architecture/master-blueprint-core-substrate.md`](../03-architecture/master-blueprint-core-substrate.md)
> (Part A §D.2, job-source model),
> [`../03-architecture/master-blueprint-inventory-fulfillment.md`](../03-architecture/master-blueprint-inventory-fulfillment.md)
> (Part C §A.7/§A.13/§B.3/§B.12, the two Odoo-side event triggers). Companion
> review-log entry:
> [`../05-qa/architecture-review-log.md`](../05-qa/architecture-review-log.md)
> (**AR-016**, Accepted by ChatGPT via DEC-019).

## Status

- **Accepted by ChatGPT on 2026-07-04.**
- **Documentation-only.**
- **Resolves MBQ-62 at decision/semantic-classification level** — Part A
  §D.2's job-source vocabulary now has a seventh accepted semantic value,
  `odoo_event` (see "Acceptance" below); exact Odoo implementation
  mechanics are **not** decided by this acceptance.
- **Does not authorize implementation.**
- **Does not open the implementation gate.**
- **Does not create implementation tasks.**
- **Implementation remains blocked.**
- **Built after DEC-018 acceptance** (2026-07-04), starting point PR #81
  merge commit `31d6732c9558c04bac49f4c84feba3bd5f90dec8` into
  `Shopify-connector`.
- **This acceptance does not modify DEC-003 through DEC-018 and does not
  modify `../04-decisions/README.md`.** It **does** apply the previously
  drafted MBQ-62 register-impact wording (§6) to
  `master-blueprint-open-questions.md` — **MBQ-62's own row only**; no
  other MBQ row is edited, and MBQ-64/MBQ-65 are untouched.

## Acceptance

**ChatGPT accepted DEC-019 on 2026-07-04.**

**Accepted decision:**

1. Part A §D.2 job-source vocabulary is extended with a seventh accepted
   semantic value: `odoo_event`.
2. `odoo_event` means a job enqueued because an Odoo-side business event
   occurred.
3. `odoo_event` is not a webhook, not manual sync, not scheduled sync, not
   reconciliation, not setup readiness, and not export preview dry run.
4. Every `odoo_event` job must conceptually carry a trigger-origin
   sub-classification.
5. For MBQ-62, the accepted trigger-origin concepts are: **"inventory
   stock-change trigger"** and **"fulfillment picking-validation
   trigger."**
6. An inventory push enqueued by a relevant Odoo stock change is classified
   as `job_source = odoo_event`, trigger-origin = "inventory stock-change
   trigger."
7. A fulfillment creation triggered by a validated `stock.picking` is
   classified as `job_source = odoo_event`, trigger-origin = "fulfillment
   picking-validation trigger."
8. Exact implementation mechanics remain implementation planning.

**Explicitly not accepted / not decided by this acceptance:**

- **MBQ-64** — untouched, reserved for a separate currency/webhook residual
  decision sprint.
- **MBQ-65** — untouched, reserved for a separate currency/webhook residual
  decision sprint.
- **Any other MBQ not named above** — unchanged, exactly as open as before
  this acceptance.
- **MBQ-16 retry-count/backoff constants** — remain implementation
  planning.
- **Exact Odoo model names, field names, Python constant names, XML IDs (if
  any), storage/Selection-field implementation mechanics, and
  trigger-origin field/model/identifier implementation** — all remain
  implementation planning.
- **Implementation-task creation** — none is created by this acceptance.
- **Implementation-gate opening** — remains a separate, explicit ChatGPT
  act; not performed here.

**What this acceptance does NOT authorize:** no implementation; no code; no
Odoo modules; no implementation-gate opening (a separate, explicit ChatGPT
act per
[`../05-qa/quality-feedback-loop.md`](../05-qa/quality-feedback-loop.md)
§10, not performed here); no implementation-task creation; no change to
DEC-003 through DEC-018; no weakening of accepted Master Blueprint Parts
A–E; no resolution of MBQ-64/MBQ-65 or any other MBQ.

**Sources reviewed for this record** (existing repository documentation
only; no external Shopify/Odoo research performed, per this session's scope
instruction):
[`master-blueprint-core-substrate.md`](../03-architecture/master-blueprint-core-substrate.md)
§D.2 (job-source model), §F.1/§F.2 (dashboard "last successful sync per
domain with mechanism label"), §G.1 (sync-center trigger/source filter),
§D.5/§D.13 (retry eligibility and retry safety rules — governed by error
class, not job source);
[`master-blueprint-inventory-fulfillment.md`](../03-architecture/master-blueprint-inventory-fulfillment.md)
§A.7/§A.13 (inventory Odoo-side event trigger, "sync-trigger layer") and
§B.3/§B.12 (fulfillment's validated-`stock.picking` trigger);
[`DEC-018`](./DEC-018-mbq-decision-batch-1.md) §4 (MBQ-62 strict analysis
against all six existing job-source values) and §8 (accepted split
recommendation);
[`master-blueprint-open-questions.md`](../03-architecture/master-blueprint-open-questions.md)
MBQ-62 row;
[`architecture-review-log.md`](../05-qa/architecture-review-log.md) AR-012
(Fable finding C2 — the original correction that "event-driven enqueue" is
not a Part A job-source value) and AR-015 (DEC-018 acceptance);
[`rejected-approaches-log.md`](../05-qa/rejected-approaches-log.md) (checked
in full — no row addresses job-source vocabulary; confirmed nothing here
reintroduces a binding rejected approach).

## 1. Purpose

**MBQ-62** asks: what **Part A §D.2 job-source value** should be recorded on
a job when its trigger is an **Odoo-side business event** rather than a
Shopify webhook, an operator action, a timer, a drift-detection pass, or a
read-only preview? Concretely, two use cases:

1. An **inventory push** enqueued by a relevant Odoo stock change (Part C
   §A.7's "sync-trigger layer").
2. A **fulfillment creation** triggered by a validated `stock.picking` (Part
   C §B.3, DEC-011's sole accepted fulfillment trigger).

Every job must record a Part A job source for two accepted, load-bearing
purposes: the **dashboard's "last successful sync per domain with mechanism
label"** card (Part A §F.1.2, "never one global timestamp hiding a stalled
domain; honest freshness") and the **sync-center trigger/source filter**
(Part A §G.1). An undecided or silently-invented source value leaves these
two genuinely common triggers without a defined, accepted classification —
and would corrupt both surfaces the moment implementation writes a job of
this kind.

**Why MBQ-62 was split out of DEC-018 rather than decided there:** Part C's
first draft momentarily treated "event-driven enqueue" as if it were a Part
A job-source value; Fable caught this as **finding C2** during DEC-015's
review (`architecture-review-log.md` AR-012), and the sprint corrected it by
routing the question to MBQ-62 instead of asserting an answer. When DEC-018
later checked MBQ-62 against all six existing values (§4 below restates that
analysis), it found **none a defensible fit** — recommending a same-batch
answer anyway would have repeated the exact unauthorized-vocabulary-
extension failure mode Fable already caught once, one level removed
(a weak mapping instead of an invented value, but still an unexamined
answer under review-batch time pressure). ChatGPT accepted DEC-018's
recommendation to give MBQ-62 its own dedicated session instead. This record
is that session.

## 2. Current accepted model

**The six accepted Part A §D.2 job-source values** — `webhook`,
`manual_sync`, `scheduled_sync`, `reconciliation`, `setup_readiness_check`,
`export_preview_dry_run` — are **[Accepted — DEC-009]**, restated and relied
upon throughout Parts A–E. `setup_readiness_check` and
`export_preview_dry_run` are structurally read-only/preview-only and are
**not business sync runs** (Part A §D.2, citing DEC-012).

**Why this vocabulary is fixed unless ChatGPT accepts a change:** the six
values are not a blueprint-level naming convenience like a proposed model or
field name (Part A/§B–§D's "naming discipline," MBQ-01/02) — they are an
**accepted semantic taxonomy** DEC-009 fixed, load-bearing for the dashboard
and sync-center surfaces cited in §1. Widening it is a genuine architecture
decision, not a formality, exactly as DEC-018 §4 already stated when it
declined to force a same-batch answer ("a real vocabulary widening, not a
formality"). Per `CLAUDE.md` §10, this record does not silently invent a
new value — every candidate below is evaluated, not asserted.

**Why Odoo-side event triggers do not fit cleanly today** — restating
DEC-018 §4's strict per-value analysis, which this record adopts rather than
re-deriving weakly:

- **`webhook`** — describes an **incoming, external, Shopify-originated**
  event. Wrong direction entirely; an Odoo-side trigger is not a webhook.
- **`manual_sync`** — describes an **explicit operator "sync now" action**.
  A routine stock adjustment or picking validation is a warehouse operation,
  not an operator invoking sync; mapping it here would mislabel the trigger
  and corrupt the dashboard/sync-center "how did this job start" filter into
  showing false operator-initiated activity.
- **`scheduled_sync`** — describes a **timer/cron-driven periodic** run. The
  Odoo-side event is immediate and one-off, not periodic; mapping it here
  would key retry/backoff-constant lookups (MBQ-16) on the wrong bucket once
  those constants are decided.
- **`reconciliation`** — describes the **drift-detection backstop** that
  compares full state. A single event-triggered push is not a reconciliation
  pass; conflating them risks letting reconciliation-cadence tuning (MBQ-17,
  now decided by DEC-018 at posture level) inadvertently throttle or skip
  genuinely immediate event-triggered pushes.
- **`setup_readiness_check` / `export_preview_dry_run`** — both structurally
  **read-only/preview-only** **[Accepted — DEC-012]**. Both use cases here
  are real writes (an inventory push; a fulfillment creation). Clearly
  inapplicable.

**None of the six existing values is a defensible fit** — this is DEC-018's
own finding, confirmed again by this record's independent review of the same
evidence; no new evidence contradicts it.

Two more things the current model already establishes, both **accepted** and
neither reopened by this record:

- **Retry eligibility itself is governed by error class, not job source**
  (Part A §D.5) — a 7th job-source value would not change which classes
  auto-retry, are manual-fix-only, or require confirmation. What job source
  *does* affect is which **retry-count-ceiling/backoff-constant** bucket
  (MBQ-16, still `[Implementation-planning default]`) a job's retries draw
  from, and which **dashboard/sync-center mechanism label** a job displays
  under.
- **DEC-010 and DEC-011 already accept the existence of both Odoo-side event
  triggers** as architecture, distinct from the job-source vocabulary
  question: DEC-010 accepts the Odoo-side stock-change trigger as a
  "sync-trigger layer" (Part C §A.7), and DEC-011 accepts a validated
  `stock.picking` as fulfillment's **sole** trigger (Part C §B.3). MBQ-62
  is purely a **classification/labelling** question on top of already-
  accepted triggers — it is not a re-litigation of whether these triggers
  exist.

## 3. Use cases in scope

**In scope (exactly these two, per MBQ-62's own text):**

1. **Inventory push enqueued by a relevant Odoo stock change** — Part C
   §A.7's "sync-trigger layer," §A.13's `inventory_push` job type when
   triggered this way (as opposed to manually, on schedule, by
   reconciliation, or by the `INVENTORY_LEVELS_UPDATE` webhook-drift
   candidate — all four of those already have an accepted Part A source).
2. **Fulfillment creation triggered by a validated `stock.picking`** — Part
   C §B.3/§B.12, DEC-011's sole accepted fulfillment-creation trigger; there
   is no accepted alternative trigger for fulfillment creation in Phase 1.

**Out of scope (explicitly not reopened or touched by this record):**

- Shopify webhooks (`webhook` source, unchanged).
- Manual sync (`manual_sync` source, unchanged).
- Scheduled sync (`scheduled_sync` source, unchanged).
- Reconciliation (`reconciliation` source, unchanged).
- Setup readiness checks (`setup_readiness_check` source, unchanged).
- Export preview dry runs (`export_preview_dry_run` source, unchanged).
- **MBQ-64/MBQ-65** (currency/webhook residual sprint) — untouched,
  unrelated to job-source classification.
- **Implementation field/model mechanics** — `odoo_event` **is** the
  accepted semantic Part A §D.2 job-source value, not a placeholder, and
  the requirement that every `odoo_event` job carries a trigger-origin
  sub-classification is accepted conceptually. What remains implementation
  planning is the exact Odoo model/field placement, Python constant naming,
  XML IDs if any, storage/Selection-field mechanics, trigger-origin
  field/model implementation, and MBQ-16 retry constants (**[Open question
  — MBQ-01/02]**-adjacent).

## 4. Options considered

| Option | Description | Pros | Cons | Dashboard impact | Retry-policy impact | Recommendation |
| --- | --- | --- | --- | --- | --- | --- |
| **A — Add a seventh job-source value** | Extend Part A §D.2's fixed six-value enum with one new value for Odoo-side business-event triggers, with no further metadata. | Gives Odoo-side event triggers an honest, distinct bucket; no mislabeling; consistent with DEC-010/DEC-011's already-accepted description of these two triggers as a distinct causal category ("sync-trigger layer" / "the trigger"). | A genuine widening of a vocabulary DEC-009 fixed at six values — every surface that enumerates job sources (dashboard filter, sync-center filter, this documentation) must account for a 7th; alone, does not distinguish *which* Odoo event fired (stock change vs. picking validation) for operators/implementation who need that finer signal. | Adds an honest 4th mechanism-label bucket ("event-triggered"), replacing today's forced-mislabel risk; loses per-trigger granularity unless paired with metadata. | Gives MBQ-16 an honest, distinct bucket to size backoff/ceilings for an immediate, single-record push, separately from periodic/batch jobs — without this bucket, that distinction cannot be made at all. | **Necessary but not sufficient alone** — adopt combined with a trigger-origin sub-classification (§5). |
| **B — Existing source + trigger-origin metadata (no new value)** | Keep the six values; record an Odoo-event-triggered job under an existing value (`manual_sync` / `scheduled_sync` / `reconciliation`) plus a new `trigger_origin` metadata field naming the actual Odoo event. | No vocabulary widening; cheapest short-term implementation change (one new field, no enum change). | DEC-018 §4 already checked all three candidate existing values on their own semantic terms and found **none defensible** (§2 above restates why): `manual_sync` falsely implies an explicit operator action, `scheduled_sync` falsely implies a periodic timer, `reconciliation` falsely implies a full drift-detection pass. Recording accurate metadata **alongside** a wrong primary label does not fix the primary label — it documents that it is wrong. | **Actively misleading** — "last scheduled sync" or "last manual sync" would reflect an ad hoc reactive push, hiding whether the real periodic/operator action actually ran; corrupts the Part A §G.1 trigger/source filter exactly as DEC-018 warned. | Keys MBQ-16 backoff/ceiling lookups to the wrong existing bucket, potentially conflating an immediate single-record push's tuning with a large scheduled batch's tuning. | **Reject** — repeats the exact weak-mapping failure DEC-018 already ruled out for all three candidates. |
| **C — Separate trigger-origin dimension, no seventh job-source value (as literally stated)** | Keep `job_source`'s six-value vocabulary untouched; add a new accepted classification dimension (`trigger_origin`/`trigger_layer`/`enqueue_origin`) recording the Odoo event; `job_source` itself takes one of the six existing values "when applicable." | Adds a structured place to record the actual Odoo event — better than Option B's ad hoc field alone; on its face, avoids widening `job_source`. | As literally stated, `job_source` must still take one of the six existing values for a case DEC-018 already found has **no defensible fit** — the added dimension does not solve the primary-bucket mislabeling problem, only supplements it. The option's own wording is internally in tension: "Odoo-side event jobs use a new accepted source value" contradicts "no seventh job-source value," and a "nullable/derived source" is itself an unreviewed, undefined new category — no less novel than a named seventh value, without the benefit of an explicit, documented meaning. | Same mislabeling risk as Option B if `job_source` is forced onto an existing value; a null/derived source would show a blank/undefined mechanism label, which Part A §F.4 ("no metric shown unless it maps to a health signal or a clickable next action") does not contemplate for a business-sync row. | Same bucket-mislabeling risk as Option B if `job_source` is forced onto an existing value. | **Reject in its literal "no seventh value" form**, for the same reason as Option B. The dimension idea is worth keeping — folded into the combined proposal (§5), paired with a genuine seventh `job_source` value rather than instead of one. |
| **D — Defer Odoo-side event triggers from Phase 1** | Do not enqueue jobs from Odoo-side events at all; inventory pushes rely on `manual_sync`/`scheduled_sync`/`reconciliation` only; fulfillment creation would need an alternative trigger. | Avoids the vocabulary question entirely for Phase 1; zero classification/dashboard/retry design cost now. | For **fulfillment**, this is not a narrow deferral: DEC-011 (accepted, AR-008) names a validated `stock.picking` as fulfillment's **sole** accepted trigger — no alternative trigger mechanism is accepted anywhere in Part C. Deferring it means Phase 1 ships **no mechanism to create Shopify fulfillments at all**, contradicting DEC-003's accepted MVP scope (fulfillment/tracking write-back in MVP) and DEC-011's architecture. For **inventory**, DEC-010 (accepted, AR-007) already accepts the Odoo-side event trigger as part of its "layered sync" direction (Part C §A.7); deferring it walks back part of an already-accepted architecture decision, not a naming question — and unevenly, since Option D's own framing proposes deferring "all" Odoo-side event triggers together, which is not achievable for fulfillment without gutting it. | For fulfillment: none — no fulfillment jobs exist to show, which is itself the defect (an accepted MVP domain producing nothing to sync). For inventory: ongoing pushes show only as `scheduled_sync`/`reconciliation`/`manual_sync`, at a real freshness cost between periodic passes. | Moot for fulfillment (no jobs exist). Unaffected for inventory (no new bucket needed), but the underlying capability (timely reactive stock sync) is lost. | **Reject** — incompatible with DEC-011's accepted fulfillment-trigger design, and unevenly incompatible with DEC-010's accepted inventory sync-trigger-layer direction; this is a scope rollback disguised as a classification deferral, not an answer to MBQ-62. |

## 5. Accepted decision

**Part A §D.2's job-source vocabulary is extended** with a **seventh
accepted value**, combining Option A (a genuine new value, so the primary
bucket is never wrong) with the useful part of Option C (a
sub-classification dimension, so the specific Odoo event is not lost) —
because Option A alone loses per-trigger granularity and Option C alone
(without a new value) inherits Option B's rejected mislabeling problem.
Options B, C-as-literally-stated, and D are **not** adopted, for the reasons
in §4. **ChatGPT accepted this decision on 2026-07-04** (see "Acceptance"
above).

**Clarification (what is, and is not, open now that DEC-019 is accepted):**
`odoo_event` **is** the accepted seventh Part A §D.2 job-source value — a
settled semantic label, not a placeholder. What remains implementation
planning is strictly the **mechanics** of encoding it: exact Odoo model
names, exact field names, exact Python constant names, exact XML IDs (if
any), exact storage/Selection-field implementation mechanics, exact
trigger-origin field/model/identifier implementation, and the exact
retry-count/backoff constants under MBQ-16. **The semantic value name
`odoo_event`, its meaning, and the requirement that every `odoo_event` job
carries a trigger-origin sub-classification are settled by this
acceptance** — only how these are implemented in Odoo remains open.

- **Accepted value name:** `odoo_event`. Evaluated against the task's other
  candidate examples and rejected in favor of `odoo_event`:
  - `odoo_side_event` — no clearer than `odoo_event`; the extra word adds
    length without adding disambiguation.
  - `internal_event` — ambiguous: could be read as "internal to the
    connector" (e.g. a supersede/cancel event), not specifically "an Odoo
    business event outside connector control."
  - `business_event` — vague; does not convey that the event originates on
    the **Odoo side** specifically, nor that it is a real-time trigger
    rather than, say, a scheduled business-hours job.
  - `odoo_event` is the most defensible: it names the **origin** (Odoo, as
    opposed to `webhook`'s implicit Shopify origin) without overclaiming a
    mechanism (it is not itself a timer, an operator click, or a drift
    check — those already have their own values).
- **Meaning:** "a job enqueued because an Odoo-side business event occurred
  — not a webhook, not an explicit operator action, not a timer, not a
  reconciliation pass, and not a read-only preview."
- **Required companion sub-classification (conceptual, accepted):** every
  job recorded under `odoo_event` must also carry a specific
  **trigger-origin** naming exactly which Odoo event fired — mirroring the
  already-accepted Part A §D.8 pattern that `blocked_manual_review` always
  carries its specific sub-reason, never a generic label. For the two
  MBQ-62 use cases, the two trigger-origins are conceptually: **"inventory
  stock-change trigger"** and **"fulfillment picking-validation trigger."**
  The requirement itself — that every `odoo_event` job carries a
  trigger-origin sub-classification — is part of what this record asked
  ChatGPT to accept, and **is now accepted**, not an open question. Only
  the exact field name, model shape, or Selection-value identifier used to
  implement it remains **[Open question — MBQ-01/02]**-adjacent
  implementation planning, not decided here.

**How inventory stock-change-triggered pushes are classified:** `job_source
= odoo_event`, trigger-origin = "inventory stock-change trigger" —
consistent with, and does not alter, Part C §A.7's already-accepted
sync-trigger-layer description and §A.13's `inventory_push` job type.

**How picking-validation-triggered fulfillment jobs are classified:**
`job_source = odoo_event`, trigger-origin = "fulfillment picking-validation
trigger" — consistent with, and does not alter, Part C §B.3's already-
accepted validated-`stock.picking` trigger posture.

**What metadata must be recorded conceptually to preserve audit truth**
(extending, not replacing, the existing Part A §D.10 audit shape): the
originating Odoo event's identity (e.g. the specific stock move or picking
that fired the trigger) and the Odoo-side event's own timestamp (distinct
from enqueue time, so a delay between the Odoo event and the job actually
being enqueued/processed is itself auditable) — both are additions to the
existing "what was attempted; what was actually written; who/what
confirmed" audit record (Part A §D.10), not a new audit mechanism.

**What remains implementation planning** (not decided by this acceptance):
the accepted semantic job-source value is `odoo_event`; exact Odoo model
names, exact field names, exact Python constant names, exact XML IDs (if
any), exact storage/Selection-field implementation mechanics, exact
trigger-origin field/model/identifier implementation, whether trigger-origin
is its own field or folded into the existing operator-safe operation
reference (Part A §G.7), and the exact retry-count-ceiling/backoff constants
for the `odoo_event` source (MBQ-16 — this record only establishes that
`odoo_event` gives MBQ-16 an honest bucket to reason about; it does not set
the constants themselves) — all remain open. **What is settled by this
acceptance and does not remain open:** the semantic job-source value name
`odoo_event`, its meaning, and the requirement that every `odoo_event` job
carries a trigger-origin sub-classification.

## 6. Register impact — applied

**Applied by this acceptance patch (2026-07-04).** The wording below has
been applied to MBQ-62's row in `master-blueprint-open-questions.md`,
mirroring the DEC-013 through DEC-018 acceptance-patch pattern:

> **MBQ-62:** *"Accepted by ChatGPT via DEC-019 (accept-a-seventh-value):
> Part A §D.2's job-source vocabulary is extended with a seventh **accepted
> semantic value**, `odoo_event`, for jobs enqueued by an Odoo-side business
> event (not a webhook, not operator-initiated, not a timer, not a
> reconciliation pass, not a preview run). Every `odoo_event` job also
> carries a specific trigger-origin naming the Odoo event that fired it —
> for the two named use cases, 'inventory stock-change trigger' and
> 'fulfillment picking-validation trigger', mirroring the accepted §D.8
> manual-review sub-reason pattern; this trigger-origin requirement is
> itself accepted conceptually, not open. The semantic value `odoo_event`
> and its meaning are settled by this acceptance — exact Odoo model/field
> names, Python constants, XML IDs (if any), storage/Selection-field
> implementation mechanics, trigger-origin field/model implementation, and
> retry-constant values (MBQ-16) remain implementation planning."*

This wording **has been** written into the register by this acceptance
patch, consistent with how DEC-018 §5's own pre-drafted register-impact
wording was applied upon ChatGPT's acceptance.

## 7. Implementation gate impact

- **Even though DEC-019 is now accepted, the implementation gate remains
  closed** unless ChatGPT explicitly opens it via a separate, dedicated act
  per `master-blueprint.md`'s gate criteria and
  [`../05-qa/quality-feedback-loop.md`](../05-qa/quality-feedback-loop.md)
  §10. Accepting this proposal resolves one specific, narrow MBQ row
  (MBQ-62) — it does not by itself satisfy gate criterion 2 in full
  (dozens of other "Blocks implementation: Yes" rows remain per the Part E
  bridge document), and it does not touch criterion 3 (the explicit
  gate-opening act) at all.
- **No implementation task is created by this record**, and none is created
  by this acceptance. No file matching `CLAUDE.md` §9 /
  `../06-prompts/implementation-task-template.md` is written here.
- **No code follows directly from this record**, under any outcome. This
  record creates or modifies no Odoo module, model, view, controller,
  security file, manifest, test, migration, or CI file.

## 8. Recommendation to ChatGPT — accepted

**Accept as proposed.** The evidence supports a seventh job-source value:
DEC-018's own strict, per-value analysis (independently re-confirmed in §2
above) already established that none of the six existing values is a
defensible fit, and DEC-010/DEC-011 already accept the existence of both
Odoo-side event triggers as architecture — the only open question was
labelling, and a weak mapping onto an existing value (Option B/C-literal)
would mislabel the dashboard and misroute retry-constant tuning exactly as
DEC-018 warned. Deferring the triggers from Phase 1 (Option D) is
incompatible with DEC-011's accepted fulfillment design in particular.

If ChatGPT prefers a different literal value name than `odoo_event` (e.g.
one of the other three candidates this record evaluated and rejected, or a
new one), that is a narrow **accept with change** on the name only — the
underlying structure (seventh value + required trigger-origin
sub-classification, no change to the other six values, no implementation
authorization) would be unaffected. **Reject and revise** would be
warranted only if ChatGPT judges that Options B, C-literal, or D are in fact
preferable for a reason this record's analysis has not accounted for; **defer
Odoo-side event triggers from Phase 1** (Option D) is evaluated above and
not recommended, primarily because it is not actually achievable for
fulfillment without contradicting already-accepted MVP scope.

**ChatGPT accepted this recommendation, as proposed, on 2026-07-04** (see
"Acceptance" above).

---

**Change control:** further changes to this record require ChatGPT review,
mirroring the DEC-013 through DEC-018 change-control pattern. This record
does not re-litigate DEC-003 through DEC-018, does not reopen accepted
Master Blueprint Parts A–E, and does not reintroduce any row from
`../05-qa/rejected-approaches-log.md`.
