# PR #204 — Store 360 consolidated blocker correction (2026-08-01)

**Status:** correction implemented on `fable/wave-5-completion`, awaiting bounded
independent correction review. **Not** accepted, ready-marked or merged; no
Odoo.sh qualification and no Shopify UAT were run or claimed by this session.

This record answers the authoritative independent review
[`#issuecomment-5152212340`](https://github.com/AdamsOdoo/Adams/pull/204#issuecomment-5152212340)
(VERDICT: REVISE — CONSOLIDATED BLOCKER). It closes the two verified blockers
(P0-1, P1-1) and the two folded-in findings (P2-1, P2-2). It deliberately does
**not** touch P2-3 (the nondeterministic RTL evidence instrument) or the
recorded P3 wording/guard items, except where a statement would otherwise
become false because of this correction.

Starting head: `53d6a74e584b8b4bc79884739d2233813c40b2a0` (parent
`0e7cba5e283cdcfc34f5edf8a6a485ff5ec41007`, base
`mvp/program-integration@87f1763a1ca699947d665c92bef614bd1fc3168d`). All work
is additive — no rebase, amend, squash, reset or force-push; the PR base is
unchanged.

---

## P0-1 — a client-supplied context key authorised protected projection writes

**Defect (reproduced by the review at the real request boundary).** The eleven
protected `sale.order` projection columns were guarded by a single check —
`not self.env.context.get(PROJECTION_SANCTION_KEY)`. Because
`odoo/service/model.py::call_kw` copies the raw client `context` into the
environment verbatim, any RPC caller could add
`shopify_connector_projection_sanctioned_write: True` to their context and write
every lifecycle mirror, the SEC-3 quarantine mirror, and the store assignment —
and could `create` a fabricated Shopify-looking order — with only ordinary
sale-order write rights.

**Correction — the authorisation is now non-forgeable.**
`addons/shopify_connector_sale/models/shopify_connector_sale_order_projection.py`:

- `PROJECTION_SANCTION_KEY` is removed as an authorisation mechanism. No
  `env.context` value authorises a projection write any more.
- The public `create()` and `write()` refuse **any** of the eleven fields
  **unconditionally** — no context value and no `sudo()` lifts the refusal.
- The one sanctioned writer is a private, non-RPC method,
  `_shopify_connector_write_projection(vals)`:
  - it is name-guarded from RPC — `call_kw` refuses any method whose name starts
    with an underscore, so no request can name it (proven below);
  - it accepts **only** the eleven projection fields and refuses any stray
    field, so it can never be turned into a general back-door write;
  - it reaches the next MRO `write()` directly (`super().write()`), so it
    neither re-enters the refusing public override nor recurses, and it depends
    on no caller-controlled context;
  - it preserves normal ORM constraints, recompute, cache and rollback.
- The binding-synchronisation choke point now calls
  `order.sudo()._shopify_connector_write_projection(changed)` — `sudo()` supplies
  the sale-order-write elevation the acting user may lack; the private helper
  supplies the projection authorisation. No context key is involved anywhere.

The boundary is therefore a Python reference held only by the binding-sync code —
unforgeable over the wire — rather than a value any caller can place in a dict.

## P2-1 — missing sale.order-side store-agreement constraint (folded in)

Added `@api.constrains('shopify_connector_store_id')`
`_check_projection_store_matches_binding` on `sale.order`: an order **with** a
binding must project exactly that binding's store; an order **without** a binding
must carry no projected store. Same-company drift is refused (not only
cross-company, which `check_company` already refuses), so drift introduced by any
path that does not write a binding cannot survive. The existing binding-side
`_check_projection_store_agreement` is left unchanged. Copy/duplicate stays clean
because every projection field is `copy=False`.

## P1-1 — a cancelled current-generation descendant advanced the freshness stamp

**Defect (reproduced by the review through the operator `action_cancel` route).**
Both reconnect-catch-up promotions treated `cancelled` as a non-blocking
terminal state, and both fired promotion on the cancelling write itself. So the
last outstanding descendant transitioning to `cancelled` stamped completion —
before any replacement existed — and the Store 360 bridge then stated
"Complete & current — every discoverable importable order has landed" over an
order that provably never landed.

**Correction — orders**
(`addons/shopify_connector_sale/models/shopify_connector_order_reconnect.py`,
`.../shopify_connector_order_scan.py`):

- `cancelled` is removed from the non-blocking set; a transition to `cancelled`
  no longer triggers promotion (only `succeeded`/`skipped` do), so promotion is
  reconsidered when a replacement succeeds, never when the predecessor is
  cancelled.
- A cancelled current-generation job now blocks promotion **unless its exact
  target is demonstrably covered** (`_order_catchup_cancelled_job_is_covered`):
  a cancelled **scan** never qualifies (an incomplete enumeration is a
  store-wide hole); a cancelled **import** qualifies only when a same-store,
  same-target, current-generation `order_import_sync` has **succeeded**, or when
  authoritative binding evidence for the target GID is already at least as new
  as the version the cancelled job was to import. A different-store,
  different-target or older-generation successor never satisfies coverage.
- The deterministic resume now **links** the cancelled predecessor to its one
  replacement via `superseded_by_job_id`, whether the replacement was just
  enqueued or already existed from a prior scan pass — one-to-one, exactly once.

**Correction — fulfillment**
(`addons/shopify_connector_fulfillment/models/shopify_connector_fulfillment_reconnect.py`):

- There is no accepted fulfillment resume route, so a cancelled
  current-generation fulfillment descendant is **unconditionally blocking**. It
  is cleared only when a later reconnect starts a new generation and fences the
  older cancelled lineage under the existing generation rules — never by
  promoting over the cancel. `cancelled` is removed from the non-blocking set and
  never triggers promotion.

No change was made to `TERMINAL_JOB_STATES`, the legal-transition taxonomy, job
cancellation, migrations, security XML/ACLs/rules, the dashboard
aggregate/UI/CSS, the eleven-field vocabulary, or any file outside the authorised
write set.

## P2-2 — the test-coverage gap that let both blockers ship (folded in)

- `test_sale_order_projection.py` gains a real request-boundary class
  (`HttpCase` + `/web/dataset/call_kw`, an ordinary salesman + connector Auditor
  with no binding-mutation role) that forges the removed sanction key, writes the
  quarantine mirror, reprojects onto another same-company store, creates a sale
  order carrying projection fields, and names the private writer directly — and
  asserts every request is refused with no projection value, binding,
  order/binding population or Store 360 count changing. Unit tests cover the
  private writer's field allowlist and the same-company / no-binding store
  constraint.
- `test_order_reconnect_catchup.py` and `test_fulfillment_reconnect_catchup.py`
  gain cancelled-descendant regressions driven through the real `action_cancel`
  operator route: the stamp does not advance and the bridge does not reach
  `complete_current` on the cancel; a queued/running replacement still blocks;
  promotion happens only after the replacement succeeds; exactly one replacement
  exists; another store/generation/target never covers; a cancelled scan stays
  blocking; a `skipped` policy row stays non-blocking; and on the fulfillment
  side an unrelated later success cannot close the hole while a new reconnect
  generation recovers normally.

## Counterfactual (old head `53d6a74`, new tests overlaid on old production)

The new/changed tests were run against the pre-correction production code to
prove they measure the defects, not fixtures. Results are recorded in
`evidence/store360-blocker-correction-2026-08-01/`.

## Evidence class

Local CI-grade supporting evidence only (pinned odoo/odoo@`30bde9ff`,
PostgreSQL 16, Python 3.12) — **not** Odoo.sh exact-SHA acceptance (DEC-041 D8),
**not** live-Shopify validation, **not** UAT. Zero Shopify requests,
credentials or mutations occurred.

## Explicitly out of scope this session

- **P2-3** (nondeterministic RTL overflow instrument, `u2-inventory-workspace`)
  is retained as recorded; no touched path owns that surface or instrument.
- The recorded **P3** wording/guard-tightening items are not addressed unless a
  statement became directly false because of this correction.
