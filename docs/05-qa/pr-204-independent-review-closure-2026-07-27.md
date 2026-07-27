# PR #204 — independent-review closure record

> **This record claims no acceptance.** It is the disposition of the final
> independent review's findings against PR #204, produced by the correction
> session, which is not an independent reviewer of its own work. The
> corrected head still requires a fresh bounded independent re-review before
> any external validation.

| Field | Value |
| --- | --- |
| Branch | `fable/wave-5-completion` |
| Starting head (reviewed SHA) | `9cb7e38a736f04d38684219092fb90c839b45e27` |
| Bound base | `mvp/program-integration@87f1763a1ca699947d665c92bef614bd1fc3168d` (verified ancestor) |
| Review artifact | `Pasted text(94).txt`, SHA-256 `e071f34150c8b715e70c3df1a88e4ab0334b19b252136a598961c7cce2b30ae5` (authoritative digest per the 2026-07-27 continuation ruling; the digest named in the original correction prompt did not match any normalization of the file and was corrected by ruling) |
| Authoritative content | from the heading `PR #204 — Final Independent Review` to end of file |
| Odoo | pinned `30bde9ff758834a4912c5ae55843d3a7dad849f1`, cloned and verified this session |
| `rtlcss` | **4.3.0**, `/opt/node22/bin/rtlcss`, execution verified (`margin-left` → `margin-right`) |
| Shopify | **none** — no store, credential, request, mutation or webhook |

## 1. Evidence classes used in this record

These are kept strictly distinct throughout and must not be conflated:

**source inspection** · **local automated-test evidence** · **local browser
evidence** · **GitHub Actions supporting evidence** · **independent review** ·
**Odoo.sh runtime evidence** · **live-Shopify evidence** · **UAT** ·
**control-room acceptance**

Everything corrected in this session carries at most **source inspection**
and **local automated-test evidence**. **No Odoo.sh runtime, no live-Shopify
contact, no UAT, and no independent review of the corrected head** is
claimed or implied anywhere below.

## 2. Category definitions

| Category | Meaning |
| --- | --- |
| **A** | Confirmed functional/security/reliability defect — corrected, with a binding regression test |
| **B** | Provisional — required a decisive diagnostic before any production change |
| **C** | Evidence or governance defect — a false record, not necessarily a broken product |
| **D** | Live-Shopify validation item — not settleable without an authorized store experiment |
| **E** | Refuted, downgraded, non-material, or out of accepted MVP scope |

## 3. The P0 — Category B, diagnosed, reclassified A, corrected

**Finding.** `operation_scope_key` collision: the export apply handler
enqueues its first child step while the parent is still `running`, with a
byte-identical key against a live `UNIQUE` constraint. Reviewer confidence:
**medium** — "settle it with one 10-minute experiment".

**Diagnostic method.** A dispatcher-driven experiment, not a direct handler
call: `shopify.connector.job.dispatch._dispatch_one(job)` followed by
`env.flush_all()`, so both parent and child keys are materialised at
production's own flush boundary.

**Result — the defect is real.**

```
P0DIAG parent-at-enqueue  state=queued
       key='1|shopify.connector.product.export.preview|1|gid://shopify/Product/111'
P0DIAG outcome=UniqueViolation: duplicate key value violates unique
       constraint "shopify_connector_job_store_operation_scope_key_uniq"
```

The parent (`_enqueue_apply`) and the child (`_enqueue_step`) pass the same
`store_id`, `res_model` (`preview._name`), `res_id` (`preview.id`) and
`shopify_target_gid`; `_compute_operation_scope_key` is built from exactly
those four and excludes `job_type`. **The branch's headline deliverable
could not hand off to its first mutation step.**

Why the suite could not see it: all three apply tests call
`_handle_product_export_apply` directly and never flush, so the child was
created in a transaction where the parent's recomputed key was never
written. The reviewer's characterisation was exact.

**Correction.** The repository's own accepted pattern — the inventory
service already terminalises and `flush_recordset(['state',
'operation_scope_key'])` before creating a child, in five places, with a
comment naming this exact collision. Wrapped in a savepoint so
terminalisation and child creation cannot come apart: without it, a failed
`_enqueue_step` leaves a parent recorded `succeeded` with no step behind it,
and `succeeded -> retry_waiting` is an illegal transition, so the
dispatcher's own failure routing would raise over the top of the real error.

**Regression coverage.** `test_export_apply_handoff.py`, 5 tests, all
dispatcher-driven and all flushing. Commit `89e3101`.

## 4. Disposition of every final-review finding

Final-review inventory: **1 P0 · 11 P1 occurrences (10 distinct) · 14
material P2 · 5 evidence-only · 5 non-material P2 · 7 refuted/downgraded.**

### Corrected this session

| # | Finding | Cat | Correction | Commit | Regression test |
| --- | --- | --- | --- | --- | --- |
| P0 | `operation_scope_key` collision | B→**A** | terminalize-then-flush in a savepoint | `89e3101` | `test_export_apply_handoff.py` (5) |
| P1 | SKU duplicate gate fails open (`sku:%s` unquoted) | **A** | centralized `tools/search_syntax.py`; fails closed before transport | `14ea7a8` | `test_export_search_encoding.py` (19) |
| P1 | Export Settings renders the fulfillment list | **A** | explicit `view_ids`; empty states added | `14ea7a8` | `test_export_action_view_binding.py` (5) |
| P1 | RTL root cause false, recorded as `[Fact]` ×4 | **C** | claim withdrawn in 4 records + 2 shipped source comments | `ac6ffdf` | — (record correction) |
| P1 | U1 "RTL" screenshot byte-identical to LTR, graded PASS | **C** | check withdrawn to neither PASS nor FAIL; headline qualified | `ac6ffdf` | — (record correction) |
| P1 | Three D10 tracker surfaces contradict the head | **C** | 4 present-tense claims corrected; §6a given a superseded banner | `ac6ffdf` | — (record correction) |
| P2 | Runner skip anchoring defeatable (2 skips per line) | **A** | matched per occurrence, not per line | `5fb5062` | 2 new `--self-test` assertions |
| P2 | Subtest skips invisible to the skip check | **A** | pattern now matches `Subtest …` | `5fb5062` | `--self-test` assertion |
| P2 | 3 runner modes claim HOOT evidence they never ran | **A** | modes report `partial`; `hoot_suites_executed` emitted | `5fb5062` | `--self-test` (13 assertions pass) |
| P2 | Tour-bundle guard inspects 1 bundle of 4 | **A** | all 4 bundles; content test, not just path | `5fb5062` | guard verified non-vacuous |

### Refuted or downgraded — deliberately NOT corrected

| Finding | Cat | Basis |
| --- | --- | --- |
| Contrast: connector-owned AA failures | **E** | The final review's own correction stands: 24 connector-owned pairs, **0 failing**; 5 of the 6 disputed rows are `readonly` statusbar buttons Odoo renders `disabled` (WCAG 2.2 exempts inactive components), the 6th is Bootstrap's own `.btn-secondary` border. "0 connector-owned AA failures" is correct. No production change. |
| Scope-quarantine banner unreachable | **E** | The SEC-3 rule filters those rows out of every non-superuser read — stricter than the banner and correct. Explicitly listed as not-to-be-resurrected. |
| `_advance_plan` shares the P0's shape | **E** | Refuted by source: `_apply_validated_consequence` writes the predecessor terminal **before** calling `apply_consequence`, so the successor's key is free. Incidental rather than declared, but real. No change. |
| Overflow instrument unfalsifiable | **E→ open** | `overflow: hidden` on `.o_action_manager` is unconditional at the pin, so a connector surface cannot fail the document-level check; all 15 surfaces recorded exactly `1366 == 1366`. **The instrument is weak, but no connector-owned clipping was demonstrated.** Recorded as outstanding evidence debt below rather than corrected by redesign. |

### Live-Shopify items — Category D, unchanged

`M-EXP-1 … M-EXP-20` **all remain outstanding.** `X-EXPORT-0` remains
**neither PASS nor FAIL**. No live experiment was performed and none is
authorized by this session. The `$app:binding` namespace question
(§9.1) is **Category D**: the implementation omits `namespace` entirely and
is test-pinned to do so; whether Shopify then resolves the app-reserved
namespace, and whether changing it would strand existing remote identity
data, cannot be settled from documentation alone.

## 5. Confirmed but NOT corrected in this session

These were investigated, their factual premises **confirmed**, and they are
**left open**. They are recorded here so no reader mistakes this record for
a clean bill of health.

| # | Finding | Cat | Evidence | Why not corrected |
| --- | --- | --- | --- | --- |
| P1 | **Media retry is structurally impossible.** `_enqueue_media_step` overrides the enqueue nonce with a deterministic `'%s:%s' % (step, checksum)`, feeding `idempotency_key`, which — unlike `operation_scope_key` — is **never cleared on a terminal state**. `_ensure_media_row` reuses the row, so a legitimate resume reproduces every key component. | **A** | source, confirmed | Requires a resume-vs-retry design decision (new attempt identity without weakening uniqueness or deleting audit history). Re-introduces the shape TD-001 already catalogued. Not a mechanical fix. |
| P1 | **First-push confirmation is unreachable.** `_enqueue_first_push_preview` has **zero production callers**; the only writer of `first_push_state='previewed'` is its handler. No button, cron, RPC or wizard reaches it. The shipped UI text promises a scheduled trigger that does not exist. | **A** | source, confirmed | Needs a sanctioned production path (§8.3) preserving the role matrix, company isolation and server-side admission. Must not be solved by weakening the guard. |
| P1 | **Preview expiry is never re-checked at any mutation boundary.** `_assert_confirmed_preview_pre_c2` checks `state`/`confirmed_uid`/`confirmed_at` and never calls `_is_expired()`. No mutation family re-checks. The create and update paths re-derive their payload from the **live** template while gating on an older confirmation. | **A** | source, confirmed | Touches every mutation family (§8.4). Needs time-crossing tests per family. |
| P1 | **PERF-1 backpressure can never fire.** One production writer of `api_health_state`, writing `'normal'`; `'throttled'` has never been written by production code in any commit. This PR adds the reader (`de257b2`) and deletes the last `'degraded'` writer (`48ab97c`). The packet specified **throttle head-room** with linear back-off; `throttleStatus` is parsed on every response (`api_client.py:928-940`) and has **zero consumers**. | **A** | source, confirmed | Needs the accepted mechanism rebuilt on real throttle data, or an explicit evidence-backed deviation (§8.5). |
| P1 | **PD-PX-7 reconnect reconciliation does not exist.** Zero `action_reconnect` references in the export module. A manual "Expire Open Export Previews" button shipped; the spec requires an automatic pass re-reading every exported binding by GID, verifying variant GID sets and media checksums, blocking exports until it completes. | **A** | source, confirmed | Substantial new subsystem (§8.6). |
| P2 | Overflow instrument cannot fail for connector surfaces | **C** | source + artifacts | Needs a measurement that survives an ancestor clip (§9.10). |
| — | **Systemic:** three governing specifications silently replaced, each in a document asserting the spec was delivered or unchanged (`$app:binding` → omitted; throttle head-room → `api_health_state`; PD-PX-7 pass → expire-previews) | **C** | source, confirmed | The three substitutions are recorded here; the deviation notices belong with their corrections. |

## 6. Status of this head

The four correction commits are real corrections with passing local tests.
They do **not** constitute a completed correction cycle:

- **5 P1s remain open** (media retry, first-push reachability, mutation-time
  expiry, PERF-1 backpressure, PD-PX-7 reconnect) — all with confirmed
  factual premises.
- **No definitive exact-head validation has been run** against a head
  carrying these corrections, and none should be run until the remaining P1s
  are resolved, because §16 requires the definitive run to be the last thing
  that touches the head.
- **PR #204 remains draft, unaccepted, unapproved and unmerged.**

The corrected head is **not** an external-validation candidate. It is a
better recovery checkpoint than `9cb7e38`, and the next authorized session
should continue from it rather than restart.

## 7. What survived scrutiny

Recorded because a closure record that lists only defects misrepresents the
work: API-version discipline, the ownership boundary (no collection,
merchant metafield or media-delete reachable), `FORBIDDEN_UPDATE_KEYS`,
company rules with no NULL escape, protected-field enforcement, Owl/XML
correctness, the group hierarchy, TD-009's diagnosis against the pinned
source, and TD-010's runner genuinely failing closed on the paths it does
check — all held under deliberate attack. The 185 contrast ratios recompute
exactly, and the Actions run at `9cb7e38` genuinely exercised 14/14 tours
and both HOOT suites.
