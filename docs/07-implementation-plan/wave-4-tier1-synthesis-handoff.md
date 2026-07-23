# Wave 4 Tier-1 Synthesis Handoff

> **Status: TIER-1 FINDINGS SYNTHESIZED — CORRECTION NOT YET AUTHORIZED.**
> **Superseded in part (2026-07-23):** see [`wave-4-tier1-decision-lock.md`](wave-4-tier1-decision-lock.md)
> — the four load-bearing decisions this handoff's synthesis left open (Theme D,
> Theme I/F-4, Theme H, Theme A) are now frozen. Current status:
> `WAVE 4 DECISION LOCK COMPLETE — READY FOR CONTROL-ROOM IMPLEMENTATION AUTHORIZATION`.
>
> **Further superseded (2026-07-23):** implementation of all eleven
> authorized themes is now complete — see
> `docs/05-qa/task-014-fulfillment-tracking-validation-results.md` §
> "WAVE 4 CLOSURE CORRECTION CAMPAIGN". Current status: `WAVE 4 CLOSURE
> CANDIDATE IMPLEMENTED AND SELF-VERIFIED — READY FOR ONE CONTROL-ROOM
> REVIEW`. Theme I/F-4 was corrected with the **permanent** architecture,
> per the one-loop control-room ruling (PR #189 review comments
> `4766049839`/`4766053529`), not the interim-only disposition the decision
> lock above had authorized.

## What this session did

A fresh, dedicated synthesis-reset session read the complete independent Tier-1
review of Wave 4 PR #189 (comment
[`5058257403`](https://github.com/AdamsOdoo/Adams/pull/189#issuecomment-5058257403))
and the binding control-room ruling accepting its `REVISE` verdict (comment
[`5058826143`](https://github.com/AdamsOdoo/Adams/pull/189#issuecomment-5058826143)),
independently re-verified all 24 named findings against the exact reviewed
source (`2d9cff02dd5459f4ec7afee33c84fec5d00b0b8a`), normalized the
inconsistent 24/25/26 headline counts, built one root-cause synthesis with a
recommended correction structure, and produced one locked candidate
implementation prompt. **No production, test, or CI file was touched. No
correction was implemented. No Odoo.sh runtime was executed. No Shopify
request or mutation occurred.**

## Prior head → new docs-only head

- **Prior head (reviewed/rejected):** `2d9cff02dd5459f4ec7afee33c84fec5d00b0b8a`
- **Synthesis docs-only head (this handoff's own commit):** `d3c157c1d4c369c1880fffc69ee6b4801ab9c05c`.
- **Decision-lock docs-only head (2026-07-23, later session):** recorded in
  [`wave-4-tier1-decision-lock.md`](wave-4-tier1-decision-lock.md) and the PR
  #189 timeline — see that document and `research-handoff.md`'s top entry for
  the exact SHA.

## Normalized counts

| | Count |
| --- | --- |
| Distinct reviewer-raised findings | **24** (2 P0 + 9 P1 + 13 material P2) |
| Confirmed (as-is) | 19 |
| Confirmed with reclassification | 5 (`P1-1`, `F-5`, `P1-7`, `F-4`, `F-7` — see ledger §3 for the exact list; `F-11` is CONFIRMED but disposed OUTSIDE ACCEPTED WAVE 4 SCOPE, a separate tag from "with reclassification," and is counted in "Confirmed (as-is)" above, not here) |
| Refuted | 0 |
| Duplicate | 0 |
| Outside this PR's implementable scope (fully) | 2 (`P1-7`, `F-11`) |
| Outside this PR's implementable scope (partially — needs an architecture decision) | 1 (`F-4`) |
| New findings surfaced by this synthesis (not in the reviewer's 24) | 1 (`ADDITIONAL-1`, Theme A) |
| Recoverable non-blocking observation | 1 (`OBS-1`) |
| Count-discrepancy explanation | See `wave-4-tier1-findings-ledger.md` §1 — 24 is authoritative; 25/26 both trace to two findings (`F-2`, `P1-5`) each being mentioned in two dimension write-ups without the review's own headline arithmetic being corrected to match its own stated collapse. |

## P0 findings (both confirmed as binding baselines)

1. **P0-A / `W4-R-P0-001`** — tracking-write transaction poisoning (`stock_picking.py:49-67`, unguarded `_enqueue_once` collision, no savepoint). **Confirmed** exactly as the control room independently found.
2. **P0-B / `W4-R-P0-002`** — Mode-2 partial-fulfillment whole-picking over-validation (`shopify_connector_fulfillment_mode2.py:302-332,422-429`). **Confirmed** exactly as the control room independently found; the single most architecturally significant finding in the review.

## Final root-cause themes (13)

A (P0-A + 4 P1s + 1 new), B (P0-B + 1 P1), C (P1 + material P2), D (P1 — out of scope), E (2 P1 + material P2), F, G, H, I (2 material P2, one out of scope), J, K (2 material P2), L (material P2 — out of scope), M (2 material P2, already applied). Full detail in `wave-4-tier1-correction-synthesis.md` §2.

## Recommended correction structure

**B — one correction campaign with ordered internal stages on the same branch/PR, producing one final candidate before review.** 11 of 13 themes are immediately, narrowly correctable within PR #189's existing allowed-files scope with no destructive migration. Themes D and L (fully) and I's `F-4` sub-finding (partially) are carved out — they require a new control-room decision and, for D/L, touch files outside this PR's authorized scope. Full rationale in the synthesis document §6.

## Affected files (once the correction is authorized)

**Production (10 files, all within `addons/shopify_connector_fulfillment/**`):** `stock_picking.py`, `shopify_connector_fulfillment_admission.py`, `shopify_connector_fulfillment_scans.py`, `shopify_connector_fulfillment_inbound.py`, `shopify_connector_job.py`, `shopify_connector_fulfillment_mode2.py`, `shopify_connector_fulfillment_inbound_evidence.py`, `shopify_connector_fulfillment_reader.py`, `shopify_connector_fulfillment_create_strategy.py`, `shopify_connector_store_settings.py` (conditional).

**Test (14 existing frozen files, no new filename):** see the locked prompt's "Complete allowed test files" section.

**Not to be touched by the future correction (out of scope):** any `shopify_connector_core/**`/`_sale/**`/`_product/**`/`_inventory/**` file (Themes D, L); `shopify.connector.location.mapping` (Theme I's `F-4`).

## Test / runtime plan

See synthesis §5 for the full matrix. Summary: every correctable theme needs new `PY` (TransactionCase) coverage plus a fresh exact-SHA Odoo.sh runtime campaign before independent review (DEC-040's mandatory-evidence rule, full rigor — this is a Tier-1 mutation-safety/concurrency/data-integrity batch). The nine-process external-multiprocessing campaign remains `DEFERRED BY PRODUCT OWNER — NOT PROVEN`, unchanged by anything in this synthesis.

## U1 (PR #194) impact

Highest impact: Theme B (`revalidation_required`) and Theme H (`definitely_changed`, renames/splits a review-reason value PR #194's contract inventory currently counts as one of "20 values, exact"). Theme D also flags a pre-existing, U1-relevant gap (`revalidation_required`) independent of this correction's timing. Full per-theme table and a bounded 15-item post-Wave-4 reconciliation checklist for a *future* U1 session are in synthesis §4. **PR #194 was not touched by this session** and remains frozen at `b38e6874c45559dbf1219cfaec43f05ba5fc959a` per the existing control-room ruling.

## No-`addons/**`-change proof

`git diff --stat <base>..<new-head> -- addons/` is empty for this synthesis commit — every changed path is under `docs/`. Confirmed by static validation before commit (see below).

## No implementation performed

This session created/updated documentation only. No `.py`/`.xml`/`.csv`/manifest/test/CI file was created or modified. No git branch other than the existing `claude/wave-4-fulfillment-gate-b` was used. No new PR was opened.

## No Shopify operation performed

No live Shopify request or mutation occurred in this session.

## Recommendation

`WAVE 4 FINDINGS SYNTHESIS COMPLETE — READY FOR CONTROL-ROOM REVIEW`

**Superseded (2026-07-23):** the control room accepted this synthesis in substance and ordered one narrow decision-lock pass before implementation authorization (PR #189 comment `5059969776`). That pass is complete — see [`wave-4-tier1-decision-lock.md`](wave-4-tier1-decision-lock.md). Current state: `WAVE 4 DECISION LOCK COMPLETE — READY FOR CONTROL-ROOM IMPLEMENTATION AUTHORIZATION`.

## Remaining control-room decisions

1. Accept (or revise) this synthesis and its recommended correction structure (**B**) — **and the four decisions frozen by the decision-lock pass** (`wave-4-tier1-decision-lock.md`).
2. ~~Authorize a new DEC scoping the `shopify_connector_core` multi-company `ir.rule` fix (Theme D) as a separate, later work item.~~ **Disposition frozen (decision-lock Decision A):** does not block PR #189 merge; blocks UAT/RC; owner is a new task (candidate "SEC-3"); target architecture recorded. Control room must still authorize that future task.
3. ~~Authorize a new architecture decision closing DEC-011's open cross-check-mechanism item (Theme I's `F-4`) before that sub-finding can be scheduled.~~ **Disposition frozen (decision-lock Decision B):** permanent core+inventory seam architecture recorded as a separate future task; an interim fail-closed correction to `_c8_location` is now authorized inside PR #189's own correction batch.
4. Route Theme L's dashboard-label fix to the Wave 5/U0 dashboard owner, or grant an explicit scope amendment.
5. If accepted, issue the locked correction prompt (`wave-4-tier1-correction-locked-candidate.md`, now normalized against the decision-lock) to a future implementation session — **not this one, and not the decision-lock session, and not without control-room acceptance first.**
6. The nine-process campaign deferment, issue #185 (CV-013), and issue #193 remain unresolved, carried, and unaffected by this synthesis or the decision-lock pass.
