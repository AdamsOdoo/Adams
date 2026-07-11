# Task 011B — Customer Matching Scalability: Implementation-Ready Planning Packet

> **Status: Proposed for ChatGPT review. NOT accepted. The locked
> prompt in §9 is NOT usable.** Produced 2026-07-11 by the PR #148
> revision session, implementing review item 2 of ChatGPT's
> control-room review (PR #148 comment `4942966937`). Sequenced
> **before Task 012** because order import (guest paths D-012-5)
> reuses this matching mechanism. Evidence: merged
> `shopify_connector_sale` code (re-read 2026-07-11) and the merged
> core substrate.

## 1. The verified current behavior (what is preserved, what is corrected)

**[Fact — merged repository state, `shopify_connector_customer_importer.py`]**
The merged matcher is correctness-safe but not scalable:

- `_find_active_candidates` (lines 313–326) runs
  `Partner.search([('email', '!=', False)])` — **every** active
  partner with an email — then filters in Python with
  `email_normalize(partner.email, strict=False) ==
  normalized_incoming`. `_find_archived_candidates` (lines 328–341)
  repeats this over all archived partners when the active set is
  empty. No index or prefilter narrows the set; no schema change to
  `res.partner` exists anywhere in the connector.
- This preserves recall for wrapped emails (`"Jane Doe"
  <Jane.DOE@Example.COM>`), display-name formats, mixed case, and
  archived contacts, and detects ambiguity (>1 normalized match) —
  the behaviors Task 011's tests prove and which **must not regress**.
- Cost is O(partners with email) **per incoming customer**, in Python,
  once per job. At 100k partners × a 5k-customer import this is
  ~5×10⁸ normalizations plus 5k full-recordset loads —
  the review's scalability finding, confirmed against source.

**Objective:** eliminate the full scan with an indexed, batch-safe
normalized lookup while keeping the match semantics bit-for-bit
identical (same normalizer, same candidate sets, same ambiguity/
archived/blind-create routing).

## 2. Decision closures (D-011B-1 … D-011B-7) — each Proposed

**D-011B-1 — Mechanism: stored normalized-email column on
`res.partner` (connector-owned), chosen over a side table.**
`shopify_connector_sale` adds via `_inherit` one stored computed
field: `shopify_connector_email_normalized` (Char,
`compute='_compute_shopify_connector_email_normalized'`, `store=True`,
`index=True`, `readonly=True`), computed as
`email_normalize(partner.email, strict=False) or False` — **the exact
merged normalizer, applied identically** (`odoo.tools.email_normalize`,
same `strict=False`). Depends on `email` only, so Odoo recomputes it
on every partner email write — no drift.
*Alternative considered (flagged):* a connector-owned side table
(`shopify.connector.partner.email.index`) maintained by
create/write hooks — rejected as primary because it duplicates state,
needs its own consistency repair, and the stored-computed field is
the native Odoo mechanism with automatic maintenance; the side table
remains the fallback if ChatGPT rejects touching `res.partner`
(precedent: Task 012's flagged `sale.order.line` field — one field on
a standard model via `_inherit`, no behavior change to the model).
This is the second (and last) connector field on a standard Odoo
model; both are enumerated in ARCH §3.

**D-011B-2 — Lookup rewrite (semantics-preserving).**
`_find_active_candidates` becomes
`Partner.search([('shopify_connector_email_normalized', '=', normalized_incoming)])`
(btree-indexed equality); `_find_archived_candidates` becomes the same
domain with `active_test=False` + `('active','=',False)`. Ambiguity
(>1), single-match bind, archived-only → `duplicate_risk`,
no-usable-email → blind-create block: **all routing unchanged.**
Guest matching in Task 012 (D-012-5 path 2) uses the same indexed
lookup — its packet is cross-referenced to this one.

**D-011B-3 — Recall-equivalence proof (the safety bar).** A dedicated
test fixture corpus of pathological emails — wrapped/display-name
forms, mixed case, whitespace padding, plus-addressing, unicode
local parts, multi-email strings, empty/garbage values — asserts for
every corpus entry: `old_path_candidates(incoming) ==
new_path_candidates(incoming)` (the old path retained in the test as
a reference implementation, not in production code). The equivalence
test is the acceptance backstop: any divergence fails the build.

**D-011B-4 — Migration/backfill.** The stored computed field is
backfilled by Odoo's standard stored-compute initialization at module
upgrade. For large databases this runs once inside the upgrade
transaction; the packet records the expected cost (single pass over
`res_partner`) and requires the 100k-partner benchmark (§5) to
measure and quote the actual upgrade duration. No custom migration
script (keeps the release plan's "no migration scripts expected"
line true — this is a field addition with compute backfill, the
additive pattern already used for settings fields). If measured
upgrade time on the benchmark exceeds 10 minutes, the packet's named
fallback is a batched post-init hook — a flagged deviation ChatGPT
must approve at gate time with the measured numbers in hand.

**D-011B-5 — Duplicate handling.** Multiple partners sharing one
normalized email remain exactly what they are today: an ambiguity
(`ambiguous_match` → manual review, candidate payload capped at 20,
sorted by id, true total in `candidate_count` — unchanged). The new
column adds no uniqueness constraint on partners (out of scope —
merchant data is not the connector's to constrain).

**D-011B-6 — Concurrency.** Two concurrent imports matching the same
partner are already serialized at the binding layer
(`UNIQUE(store_id, partner_id)` + `UNIQUE(store_id, shopify_gid)`);
the indexed read changes nothing there. Concurrent partner-email
writes during an import recompute the stored field in the writer's
transaction — the read sees committed state (standard MVCC). A test
asserts the second concurrent bind attempt fails cleanly on the
constraint and routes per the existing taxonomy (no new failure
mode). The standing claim/dispatch concurrency caveat (SRR-03/04/09)
is restated, not resolved.

**D-011B-7 — Performance benchmark (binding acceptance numbers).**
A benchmark scenario (documented procedure + a repeatable seeded
script *inside the test suite*, tagged `post_install` + `-standard`
so it runs only when explicitly invoked) creates **100,000 partners**
(≥30% archived, ≥10% wrapped/display-name emails, ≥1% shared
normalized emails) and measures: (a) single-customer match latency —
budget **p95 ≤ 50 ms** (indexed path; the merged path is O(n) and
fails this by construction); (b) sequential 1,000-customer import
matching throughput — budget **≥ 20 customers/s matching cost**
(excluding network); (c) module-upgrade backfill duration — recorded,
budget ≤ 10 min (D-011B-4). Numbers land verbatim in the validation
record (OP-43 rule) and calibrate `performance-budgets.md` §4 rows
(provisional budgets → measured).

## 3. Scope / non-goals

**Scope:** the one `res.partner` field; the two candidate-search
method bodies; the equivalence corpus + benchmark tests; validation
record. **Non-goals:** no matching-policy change of any kind (email
stays the sole automatic key — RA-006 honored); no change to binding
schemas, importer flow, dispatcher, or core; no dedup merge tooling;
no UI; no order-import work (Task 012 consumes this, later).

## 4. Allowed / forbidden files (exhaustive)

**Allowed:**
- `addons/shopify_connector_sale/models/__init__.py` (one import line)
- `addons/shopify_connector_sale/models/shopify_connector_res_partner.py`
  (NEW — the `_inherit` field + compute only)
- `addons/shopify_connector_sale/models/shopify_connector_customer_importer.py`
  (ONLY `_find_active_candidates` + `_find_archived_candidates`
  bodies **plus the class/method docstrings that describe the
  full-scan design** — red-team round-2: the class docstring
  hard-codes the old mechanism outside any method body and would
  otherwise contradict the implementation; every other method's
  logic untouched)
- `addons/shopify_connector_sale/tests/test_customer_matching_scalability.py`
  (NEW — equivalence corpus, routing regression, concurrency,
  benchmark harness)
- `addons/shopify_connector_sale/tests/__init__.py` (one import line)
- `docs/05-qa/task-011b-validation-results.md` (NEW)
- `docs/05-qa/architecture-review-log.md` (append one AR row)
- `docs/01-research/research-handoff.md` (top entry)

**Forbidden:** every core/product file; the customer binding model;
all other importer methods; `adams_base`; views/UI/webhooks/OAuth/CI;
`main`; plain `dev`.

## 5. Tests (exact file: `test_customer_matching_scalability.py`)

1. **Equivalence corpus (D-011B-3)** — old-path vs new-path candidate
   sets identical across the pathological corpus, active and archived.
2. **Routing regression** — re-run the Task 011 matcher outcomes on
   the new path: existing-binding shortcut, single active match binds,
   >1 ambiguous holds with capped candidate payload, archived-only →
   `duplicate_risk`, no-email → blind-create block, binding-conflict
   guard. (Task 011's own suite also stays green — it tests the same
   public behavior.)
3. **Recompute correctness** — partner email create/write/clear
   updates the stored field; archived partners included via
   `active_test=False`.
4. **Concurrency (D-011B-6)** — concurrent bind collision routes
   cleanly on the uniqueness constraint.
5. **Benchmark harness (D-011B-7)** — seeded 100k dataset; latency/
   throughput/backfill measurements emitted for the validation
   record; explicitly excluded from the standard CI pass.
6. **Source guards (red-team-corrected round 2 — AST/domain-pattern,
   not a literal string scan, which multi-line formatting defeats):**
   an AST-level check that neither `_find_active_candidates` nor
   `_find_archived_candidates` builds a search domain containing
   `('email', '!=', False)` and that both search on
   `shopify_connector_email_normalized`; normalizer identity
   (`email_normalize` + `strict=False`) asserted on both compute and
   incoming sides; stale full-scan docstrings updated (no code
   comment may describe the removed mechanism as current).

## 6. Gate criteria (15-pattern, abbreviated)

1 Task 011 merged runtime-green ✅(fact); 2–3 exact names ✅(§2);
4 files ✅(§4); 5 equivalence bar fixed ✅(D-011B-3); 6–8 no
policy/UI/core scope ✅; 9 tests ✅(§5); 10 rollback ✅(§7); 11 no
live-Shopify dependency ✅ (pure Odoo-side change); 12 gate-act
reconfirmation (ChatGPT); 13 the `res.partner` field explicitly
accepted (D-011B-1 — the review call in this packet, mirroring the
Task-012 `sale.order.line` precedent); 14 benchmark budgets stated
✅(D-011B-7); 15 ambiguity/archived semantics provably unchanged
✅(§5.1–.2).

## 7. Acceptance criteria / DoD / rollback

Only §4 files changed; equivalence + regression + concurrency tests
green locally and on Odoo.sh (verbatim quotes); benchmark numbers
recorded; validation record + AR row + handoff; draft PR; gate closes
on draft-open. Rollback: revert the single PR — the stored column is
dropped with the field definition at module upgrade; matching returns
to the merged full-scan path (slow but correct); no data loss.

## 8. Register impacts on acceptance

New row: the review's scalability finding → owned by this packet.
Task 012 packet §D-012-5 note updated (guest matching uses the
indexed path). `performance-budgets.md` §4 customer-matching rows
cite D-011B-7 as their calibration source.

## 9. Locked final implementation prompt (Task 011B)

```text
DO NOT USE UNTIL CHATGPT REVIEWS AND ACCEPTS THIS PLANNING PACKAGE,
EXPLICITLY OPENS THE TASK-011B GATE, VERIFIES THE CURRENT BASE SHA,
AND ISSUES THIS PROMPT.

Implement Task 011B — customer matching scalability — exactly per
docs/07-implementation-plan/task-011b-customer-matching-scalability-packet.md
(D-011B-1..7 binding). Branch from the verified current
Shopify-connector tip (STOP on drift). One session; draft PR; stop.

ALLOWED FILES (exhaustive):
  addons/shopify_connector_sale/models/__init__.py                       (one import line)
  addons/shopify_connector_sale/models/shopify_connector_res_partner.py  (NEW — _inherit res.partner: shopify_connector_email_normalized stored computed indexed field + compute only)
  addons/shopify_connector_sale/models/shopify_connector_customer_importer.py  (ONLY the _find_active_candidates and _find_archived_candidates bodies + the stale full-scan class/method docstrings)
  addons/shopify_connector_sale/tests/test_customer_matching_scalability.py    (NEW)
  addons/shopify_connector_sale/tests/__init__.py                              (one import line)
  docs/05-qa/task-011b-validation-results.md                             (NEW)
  docs/05-qa/architecture-review-log.md                                  (append one AR row)
  docs/01-research/research-handoff.md                                   (top entry)
FORBIDDEN: everything else — core/product modules, the binding model,
every other importer method, matching policy of any kind, adams_base,
views/UI/webhooks/OAuth/CI, main, plain dev.

HARD CONSTRAINTS: email_normalize(strict=False) identically on both
sides (source-guard test); candidate sets provably identical to the
merged path across the pathological corpus (equivalence test is the
acceptance backstop); all Task 011 routing unchanged (ambiguous /
archived-only / blind-create / binding-conflict); no uniqueness
constraint on partners; benchmark per D-011B-7 with numbers quoted
verbatim in the validation record; backfill via stored-compute
initialization (measure and record duration; the batched-hook
fallback needs explicit ChatGPT approval); concurrency caveat
restated, not resolved. Odoo.sh green before merge review (verbatim
quote). Stop condition: draft PR "Task 011B: customer matching
scalability (indexed normalized lookup)"; gate closes on draft-open;
no Task 012 or other work.
```
