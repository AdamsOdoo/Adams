# Wave 5 U1 — Acceptance & Test Matrix

> **Status: Gate A planning artifact — Docs-only. NOT accepted. Authorizes no
> implementation.** Produced 2026-07-23. Defines the U1 acceptance criteria and
> the evidence classes required to accept the future U1 **code** batch. Grounded in
> the exact Wave 4 backend (`u1-backend-ui-contract-inventory.md`), the fulfillment
> mode/COD UAT matrices, and DEC-040's runtime-evidence rules.

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
| A4 | **Two-role UI visibility** — customer-facing menu/button visibility gates on the two SEC-2 roles: **Connector User** affordances (review, import tracking, acknowledge, validate-proposed, release-review) and **Connector Administrator** affordances (adds mode switching) render/hide correctly; internal implied-group closure (Administrator → User → operator/reviewer → auditor) resolves as expected | PY + XMLG + TOUR |
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
| A18 | **Fulfillment regression** — the accepted Wave 4 fulfillment suite (203) stays green with U1 installed | RUN |
| A19 | **U0 regression** — U0/Test Connection suite (67), sale (194), inventory (247) stay green with U1 installed | RUN |
| A20 | **Package import structure** — addon root `__init__.py` imports `wizards` exactly once (keeps `from . import models`); `wizards/__init__.py` imports the wizard model exactly once; `models/__init__.py` does NOT import the sibling `wizards` package; the wizard TransientModel is registered after install; no circular or duplicate import | PY + XMLG (source guard) + RUN |
| A21 | **Wizard is non-authoritative (display-and-delegate boundary)** — the mode-switch wizard's reads/counts never decide eligibility, never classify blockers, never determine "review required", never choose the target mode, never alter server-action arguments, never suppress a server-legal action, never create a Job/mutation, never write a protected/snapshot field, never contact Shopify; every displayed count is bounded, ACL-safe, and labelled informational/non-authoritative | PY (negative tests) + XMLG (AST source guard) |

## 3. Functional scenarios U1 must support (from the fulfillment-mode + COD UAT matrices)

U1 must render/drive (not re-implement) these existing backend scenarios:

- **Mode 1 review actions** — UAT-FM-1.6/1.7: external-fulfillment detection →
  review case (origin classified); import tracking (non-stock), acknowledge
  ("handled outside Odoo", audited), validate-proposed (exact proposal shown).
- **Mode 2 each condition** — UAT-FM-2.1…2.16: each of the 16 conditions violated
  → the named `review_reason`, zero stock change, workable via Mode 1 actions.
  (Vocabulary: the over-fulfillment case renders as `quantity_overrun` on the
  evidence and persists `ambiguous_match` on the core job — see contract §10.)
- **Mode switch** — UAT-FM-3.1…3.5: confirmation lists unresolved externals;
  scan-gated; rollback any time; idempotent; non-admin refused server-side;
  disconnected-period externals land as review in both modes.
- **Delivered inconsistency** — UAT-FM-4.1: `delivered_inconsistency` critical
  pinned case; never auto-resolves by stock change.
- **Unknown status** — Layer-A unknown value → `schema_warning` badge, never
  silently success.
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
- The nine-process Wave 4 concurrency campaign remains `DEFERRED` (PR #189) — not
  U1's obligation, and not to be represented as passed.

## 5. Definition of done (U1 code batch, when authorised)

SEC-2 merged runtime-green first (D-P0-2). Code + **PY** tests green on Odoo.sh
(**RUN** with build id, fresh-install + warm-upgrade + focused suites + regressions
A18/A19) + **import-structure** tests (A20); **XMLG** source guards green
(A11/A15/A16/A20/A21); two-role visibility matrix (A4/A5) proven with negative
direct-RPC cells; the wizard's display-and-delegate boundary (A6/A21) proven;
**WALK** driven walkthrough + **SHOT** screenshot set + responsive/RTL/a11y
browser-render evidence recorded (a browser class may be deferred only after a
concrete attempt + separate control-room ruling — never recorded as "passed");
independent Claude review (separate session/subagent) posts a verbatim report at
the exact SHA; a separate closure session ready-marks/merges. No self-accept.
