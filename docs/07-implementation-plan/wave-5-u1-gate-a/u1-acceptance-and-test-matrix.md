# Wave 5 U1 — Acceptance & Test Matrix

> **Status: Gate A planning artifact — Docs-only. NOT accepted. Authorizes no
> implementation.** Produced 2026-07-23; **reconciled 2026-07-25** against the final
> integrated backend at `2583081f`. Defines the U1 acceptance criteria and the
> evidence classes required to accept the future U1 **code** batch. Grounded in the
> current integrated backend (`u1-backend-ui-contract-inventory.md`), the
> fulfillment mode/COD UAT matrices, and DEC-040's runtime-evidence rules.
>
> **This document defines acceptance for a future code batch. Nothing in it is
> satisfied by the docs-only Gate-A package, and none of its browser/render or
> runtime evidence is claimed by it.**

## 1. Evidence classes (DEC-040) — how each criterion must be proven

| Class | Meaning | Notes |
|---|---|---|
| **PY** | Python/server test (unit/integration) | Runs in Odoo.sh |
| **XMLG** | View/XML **source guard** (AST/source assertion) | e.g. no raw-payload field in any template; groups= present |
| **HOOT** | Owl unit test | Only if any Owl surface exists — U1 has **none** (PD-7); likely N/A |
| **TOUR** | `HttpCase.start_tour` browser tour | Primary operator flows |
| **WALK** | Driven browser walkthrough (app run + clicked) | DEC-040 requires UI batches include a real driven walkthrough |
| **SHOT** | Screenshot set (5 states × required widths, incl. RTL) | From Odoo.sh runtime |
| **RUN** | Genuine Odoo.sh runtime evidence (build id, fresh-install, focused suite) | Mandatory for any code batch |
| **UAT** | Dev-store UAT | Fulfillment dev-store; gated on Shopify access + CV-013 |

**DEC-040 rule (U1 is a PREMIUM UI gate — control-room comment `5056513213`,
finding 5):** every U1 **code** batch ships **PY + RUN** (fresh-install +
warm-upgrade + focused suites + regressions) + **import-structure tests** before
independent review begins. Because U1 is a premium UI gate, **browser/render
evidence is REQUIRED before U1 merge and is NOT automatically inherited from U0's
deferments**: a driven Odoo-rendered **WALK**-through, the agreed **SHOT**
screenshot set (key roles/states), browser-level visibility/action verification,
accessibility/render checks, responsive-width checks, and RTL checks where
applicable, with no sensitive/credential leakage. **HOOT/TOUR** may be classified
separately based on actual environment support, but their deferment is **not
pre-authorized**: a product-owner deferment of any browser class may be requested
**only after** a concrete execution attempt, exact environment-limitation evidence,
and a **separate control-room ruling** — **never mark a deferred class as passed**,
and server tests + XML/source guards alone are **not sufficient** for U1
acceptance. **UAT** is gated on Shopify dev-store availability and is not a U1-merge
blocker per se, but fulfillment dev-store validation + CV-013 (#185) remain
**release/UAT** blockers.

## 2. Acceptance criteria matrix

| # | Criterion | Required evidence |
|---|---|---|
| A1 | **Install** — `shopify_connector_fulfillment` (with U1 views) installs clean on the Wave-4-containing tip; registry loads; no ParseError/missing-model/duplicate-XML-ID | RUN (fresh install) |
| A2 | **Upgrade** — warm `-u` of the module applies U1 views with no regression to the accepted Wave 4 backend | RUN (warm upgrade) |
| A3 | **Uninstall** — module uninstall removes all U1 views/menus/wizard; no residue; business data intact; LC-1 job-type normalization unaffected | RUN (uninstall/reinstall where supported; else `DEFERRED — NOT PROVEN`) |
| A4 | **Two-role UI visibility** — customer-facing menu/button visibility gates on the two **merged** SEC-2 roles (exact XML IDs `shopify_connector_core.group_shopify_connector_user` / `..._admin`; contract §8.1 — invent none), asserted against the **effective** record-rule set observed at runtime rather than the union of declared rules (OQ-4): **Connector User** affordances (review, import tracking, acknowledge, validate-proposed, release-review) and **Connector Administrator** affordances (adds mode switching) render/hide correctly; internal implied-group closure (Administrator → User → operator/reviewer → auditor) resolves as expected | PY + XMLG + TOUR |
| A5 | **Direct-RPC security** — every sanctioned action refuses unauthorized roles server-side with `AccessError` and **zero side effects** (not merely hidden), enforced through the internal capability groups; **no privilege escalation**; **no UI/ACL disagreement** (a hidden button is never the security control) | PY (negative matrix) |
| A6 | **Mode-switch confirmation (display-and-delegate)** — the wizard shows current/requested mode, STATIC consequences, the switch-in-progress flag, and bounded, ACL-safe, **non-authoritative informational** counts (labelled as such); it states the server reconciliation scan is authoritative; it makes NO eligibility/blocker/**review-required** determination and NO target-mode/argument decision | PY + TOUR + WALK + SHOT |
| A7 | **Legal mode-switch** — admin start→Mode 2 on clean scan; rollback→Mode 1 any time; idempotent re-confirm no-op | PY (delegates to accepted actions) |
| A8 | **Illegal mode-switch** — non-admin refused; start when already Mode 2 = no-op; buttons hidden for non-admin | PY + XMLG |
| A9 | **Review workspace actions** — import tracking / acknowledge / validate-proposed / release-review call only the sanctioned actions; role gates correct | PY + TOUR + WALK |
| A10 | **Lineage correctness** — evidence→order/picking/binding/job/mutation lineage renders; job filters cover the 10 fulfillment job types; states correct | PY + XMLG + SHOT |
| A11 | **No sensitive evidence** — no template/field renders `remote_mutation_intent`, `preconditions_snapshot`, fingerprints, idempotency key, `remote_evidence_refs`, nonce, tokens; raw JSON parsed, never dumped | XMLG (source guard) + PY |
| A12 | **Responsive** — logical-properties-only; `dir="rtl"` mirrors; no horizontal page scroll; ≤900/≤640 breakpoints | SHOT (widths + RTL) — **REQUIRED before merge**; deferment only after a concrete attempt + separate control-room ruling |
| A13 | **Accessibility (source + rendered)** — word+icon (never colour alone), `<th scope>`, `role="dialog"`+`aria-modal`, focus order (destructive last), `:focus-visible`, reduced-motion, one primary/screen | XMLG + WALK + browser-a11y checks — **REQUIRED before merge**; deferment only after a concrete attempt + separate control-room ruling |
| A14 | **Bounded queries** — server-paginated lists, default facets, any aggregate = constant `search_count` + `limit`-ed read (PB-9/10/11) | PY + source review |
| A15 | **No UI-owned business logic** — the wizard/views compute no mode decision, create no job/mutation, write no protected/snapshot field, perform no Shopify call | XMLG (AST guard) + PY |
| A16 | **No controller/webhook/OAuth** — whole-tree AST guard finds none introduced by U1 | XMLG (AST guard) |
| A17 | **No real Shopify request** — U1 tests/runtime perform no live Shopify call or mutation | RUN + secret/leak scan |
| A18 | **Fulfillment regression** — the fulfillment suite stays green with U1 installed, measured against the **connector-suite baseline recorded for the exact integration base the control room binds** (do not carry a stale count forward: the counts quoted at Wave 4 Gate A described the pre-merge `2d9cff0` candidate and no longer describe the integrated tree; the currently documented integrated baseline is the PR #203 record — 1517 fresh-install and 1517 warm-update tests with 0 failures/0 errors, plus 18 non-standard-tag tests) | RUN |
| A19 | **Whole-connector regression** — core/U0, sale, product, inventory and SEC-2/SEC-3 suites stay green with U1 installed, against the same bound-base baseline as A18. Re-derive every count from the base run; never restate a historical count as the current one | RUN |
| A20 | **Package import structure** — addon root `__init__.py` imports `wizards` exactly once (keeps `from . import models`); `wizards/__init__.py` imports the wizard model exactly once; `models/__init__.py` does NOT import the sibling `wizards` package; the wizard TransientModel is registered after install; no circular or duplicate import | PY + XMLG (source guard) + RUN |
| A21 | **Wizard is non-authoritative (display-and-delegate boundary)** — the mode-switch wizard's reads/counts never decide eligibility, never classify blockers, never determine "review required", never choose the target mode, never alter server-action arguments, never suppress a server-legal action, never create a Job/mutation, never write a protected/snapshot field, never contact Shopify; every displayed count is bounded, ACL-safe, and labelled informational/non-authoritative | PY (negative tests) + XMLG (AST source guard) |
| A22 | **Status-badge layer correctness (per the canonical §12 matrix)** — every rendered badge maps to its exact §12 backing field with the correct layer label/icon/severity: **A4** fields (`fulfillment_status_*`) render as A4; **A7** fields (`display_status_*`) render as A7 **display-only** and are **never** labelled/iconized as a carrier milestone; **A5** carrier evidence is drawn **only** from parsed `tracking_snapshot` + the `delivered_inconsistency` case and **never** consumes the A7 fields; a delivered-inconsistency is **visually distinct** (word+icon+severity) and never auto-validates Odoo stock; **no A2 `FulfillmentOrderStatus` badge** is present (deferred — no backing seam); **no layer-merging** and **no colour-only** status meaning; an unknown raw value (`schema_warning`) stays visible and fails closed; every badge has backing source evidence; screenshot coverage spans the key layer combinations across widths + RTL; no sensitive/raw JSON payload is rendered | PY + XMLG (source guard: no A7→A5 mapping, no A2 status field, no layer-merge) + SHOT |
| A23 | **SEC-3 guard closure for any new durable U1 surface** — if the U1 implementation introduces **any** new durable store-scoped model or connector-to-connector relation, it carries a stored related `company_id`, declares its parent scope relations in `_sec3_parent_scope_relations()`, receives a **fail-closed global** company rule (`company_id in company_ids` **and** `sec3_scope_quarantined = False`), is registered in the inventory-driven SEC-3 guard, and is covered by the SEC-3 matrix tests including the owning-company control arm (a model that denies everyone must not produce a vacuous green). **U1's design introduces none** — only a non-store-scoped `TransientModel` wizard — so the expected result is a **proven** "no new SEC-3 entry required", asserted by the completeness guard rather than assumed. Additionally: U1 renders no `sec3_scope_quarantined` control, never calls `action_sec3_release_scope_quarantine`, and every U1 count/facet is labelled non-authoritative because quarantined rows are excluded from every interactive read shape. **Issue #197 stays open — U1 must not mark it complete** | PY (SEC-3 matrix + completeness guard) + XMLG (source guard: no quarantine control, no `action_sec3_release_scope_quarantine` call) |

## 3. Functional scenarios U1 must support (from the fulfillment-mode + COD UAT matrices)

U1 must render/drive (not re-implement) these existing backend scenarios:

- **Mode 1 review actions** — UAT-FM-1.6/1.7: external-fulfillment detection →
  review case (origin classified); import tracking (non-stock), acknowledge
  ("handled outside Odoo", audited), validate-proposed (exact proposal shown).
- **Mode 2 each condition** — UAT-FM-2.1…2.16: each of the 16 conditions violated
  → the named `review_reason`, zero stock change, workable via Mode 1 actions.
  (Vocabulary: the over-fulfillment case renders as `quantity_overrun` on the
  evidence and persists `ambiguous_match` on the core job — see contract §10.)
- **Mode switch** — UAT-FM-3.1…3.5: confirmation shows a **bounded, ACL-safe,
  non-authoritative informational count** of open external review cases (the server
  reconciliation scan, not the wizard, is authoritative); scan-gated; rollback any
  time; idempotent; non-admin refused server-side; disconnected-period externals
  land as review in both modes.
- **Delivered inconsistency (A5, §12)** — UAT-FM-4.1: the `delivered_inconsistency`
  critical pinned case is visually distinct and never auto-resolves by stock change.
  *(The flag is declared but **still data-inert at `2583081f`** — re-grepped 2026-07-25; the acceptance verifies the
  rendering path when the flag is set, and that A5 is never synthesized from the A7
  `display_status_*` fields — §12 / risks.)*
- **Unknown status** — Layer-A unknown value → `schema_warning` badge, never
  silently success.
- **Review-reason coverage (Δ1)** — the copy deck and the review-reason badge cover
  **all 21** `review_reason` values, including `external_fulfillment_observed`; no
  value renders as an unmapped raw string.
- **SEC-3 visibility** — a row belonging to another company, and a quarantined row,
  are **both absent** from every U1 list, facet count, grouped read and direct-id
  read, while the owning company's user sees the same row — proving the denial is
  not vacuous.
- **Status-badge layer correctness** — each of A4 / A7 / A5 / reconciliation /
  origin / review-reason renders as its own §12 layer with the correct label/icon/
  severity; A7 is never shown as a carrier milestone; A2 has no badge (A22).
- **COD interplay (read models)** — U1 surfaces fulfillment/tracking state that
  the COD workspace (Wave 6) consumes; U1 does not build the COD workspace.

## 4. Evidence NOT to claim as passed (honesty guards)

- **Browser/render evidence is REQUIRED before U1 merge, not automatically deferred
  (finding 5).** A browser class (TOUR/HOOT/SHOT/WALK/browser-a11y) may be recorded
  as **`DEFERRED — NOT PROVEN`** — never "passed" — **only after** a concrete
  execution attempt, exact environment-limitation evidence, and a **separate
  control-room ruling**. U1 does **not** inherit U0's browser deferments as a normal
  merge path.
- **Fulfillment dev-store UAT** and **CV-013 (#185)** remain **open/critical**
  release/UAT obligations; U1 must not present live fulfillment mutation as proven.
- **All live-Shopify validation remains DEFERRED** until the Wave 5 implementation
  candidate is complete and frozen. **Gate D, CV-013 (#185), provisioning (#200),
  external UAT and release readiness are open and unclaimed** — the deferral is not
  a waiver, and none of them may be recorded as satisfied.
- The external-multiprocessing / concurrency campaign remains `DEFERRED` — not U1's
  obligation, and not to be represented as passed. `test_real_process_death_harness`
  and the browser navigation tour are **runtime pending** and are never claimed as
  proven.
- **PERF-0 numbers are baseline-only.** Issue **#199 is open**; no PERF-0 measurement
  may be restated as a performance guarantee, budget, threshold or SLA in any U1
  view copy, document or acceptance claim. Wave-5 gate **G5-4** is unchecked.
- **Issue #197 (SEC-3) is open** and must not be marked complete by U1 (A23).

## 5. Definition of done (U1 code batch, when authorised)

SEC-2 merged runtime-green first (D-P0-2) — **satisfied as of 2026-07-25**; and the
control room has opened the U1 gate on an **explicitly bound base SHA** (the locked
prompt's `<U1-IMPLEMENTATION-BASE-SHA>` placeholder resolved). Code + **PY** tests green on Odoo.sh
(**RUN** with build id, fresh-install + warm-upgrade + focused suites + regressions
A18/A19) + **import-structure** tests (A20); **XMLG** source guards green
(A11/A15/A16/A20/A21); two-role visibility matrix (A4/A5) proven with negative
direct-RPC cells; the wizard's display-and-delegate boundary (A6/A21) proven;
**WALK** driven walkthrough + **SHOT** screenshot set + responsive/RTL/a11y
browser-render evidence recorded (a browser class may be deferred only after a
concrete attempt + separate control-room ruling — never recorded as "passed");
**A23** SEC-3 closure proven; independent Claude review (separate session/subagent)
posts a verbatim report at the exact SHA; a separate closure session
ready-marks/merges. No self-accept.
