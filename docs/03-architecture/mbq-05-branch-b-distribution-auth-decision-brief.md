# MBQ-05 Branch B — Distribution / Auth Decision Brief (Blocking Analysis for Task 011)

> **Status: [Recommendation] per `CLAUDE.md` §8 — Recommended for ChatGPT
> review, NOT accepted, NOT a distribution decision.** Docs-only. Prepared
> 2026-07-10 by the AR-039 gate-readiness session. This brief answers the
> control-room questions needed **now** — whether MBQ-05 branch B blocks
> Task 011 and whether its research/decision task should run in parallel —
> and refreshes the official-source facts the eventual branch B decision
> will rest on. **It does not decide branch B, does not select a
> distribution method, does not authorize OAuth/wizard/packaging work of
> any kind, and does not reintroduce RA-003** (public App Store
> distribution as a Phase 1 architecture requirement, rejected) — public
> distribution appears below strictly as an *evaluation candidate* under
> RA-003's own stated revisit condition and DEC-023 §3.2's accepted branch
> framing. MBQ-05 remains **Partially routed / Open** in
> [`master-blueprint-open-questions.md`](./master-blueprint-open-questions.md);
> nothing here changes that row.
>
> Official-source refresh: every Shopify distribution/PCD fact below was
> fetched from official pages on **2026-07-10**; excerpts are captured in
> [`../00-source-materials/shopify-customer-odoo19-partner-task-011-captures.md`](../00-source-materials/shopify-customer-odoo19-partner-task-011-captures.md)
> (OP-44 routing).

## 1. What MBQ-05 branch B is (restated from the accepted record)

DEC-023 (Accepted in limited scope, 2026-07-08) split the
token-acquisition/distribution question:

- **Branch A (accepted for narrow use):** Custom Distribution + a
  manually-completed OAuth exchange, **only** for one-store /
  same-Plus-org / private-customer / VAL-B2-evidence purposes.
- **Branch B (open):** the scalable **many-unrelated-customer /
  commercial-product** distribution and auth architecture — "Public
  distribution, or another officially-supported scalable route, must be
  separately evaluated and accepted by ChatGPT before any implementation
  work assumes a specific multi-customer distribution mechanism"
  (DEC-023 §3.2).

## 2. Does branch B block Task 011? — **No** (evidence)

**Answer: No. MBQ-05 branch B is not a Task 011 blocker.**

1. **[Fact]** Task 011's accepted scope performs **no OAuth, no token
   acquisition, no app registration, and no distribution-dependent step
   of any kind**: it consumes an already-established store connection
   through the existing, merged Task 003 API client, with fake-client
   tests and no live-Shopify dependency (accepted gate criteria 8 and 11,
   both **Satisfied** —
   [`../07-implementation-plan/customer-domain-gate-criteria-proposal.md`](../07-implementation-plan/customer-domain-gate-criteria-proposal.md)
   §3; naming proposal §10 step 7).
2. **[Fact]** The accepted Task-011 blocker classification already
   classes MBQ-05 as **B** — "does not block Task 011 but blocks later
   MVP steps" — with the reason "Task 011 would consume an
   already-established store connection; it performs no
   OAuth/token-acquisition"
   ([`../07-implementation-plan/task-011-customer-import-gate-readiness.md`](../07-implementation-plan/task-011-customer-import-gate-readiness.md)
   §5; restated in
   [`../08-release-readiness/open-points-closure-register.md`](../08-release-readiness/open-points-closure-register.md)
   OP-05). This session re-verified that classification against the
   current merged code and the 2026-07-10 official facts below: nothing
   has changed it.
3. **[Fact, 2026-07-10]** The protected-customer-data availability table
   states that for **custom apps**, Level 1 and Level 2 protected
   customer data are **"Always available"** — no app review — while
   only **public** apps face "Requires review"
   (https://shopify.dev/docs/apps/launch/protected-customer-data,
   Accessible 2026-07-10). The project's current evidence path (DEC-023
   branch A: custom-distribution app for the one pilot/VAL-B2 store)
   therefore faces **no PCD review gate** for the customer fields Task
   011 imports. Dev-store-only testing needs no review either ("If your
   app is for testing or installed only on a development store … You
   don't need to submit for review." — same page, direct quote).
4. **[Inference]** Task 011's code is distribution-agnostic by
   construction: the credential model (`token_variant =
   'offline_custom_app'`), API client, and job substrate are identical
   under every candidate branch B outcome. No Task 011 file would change
   based on the branch B decision — which is the operational definition
   of "not blocking."

**One boundary this brief adds for the record (carried into the final
prompt):** Task 011 must not bake any distribution/auth assumption into
code, tests, or docs (already a standing prohibition —
`task-011-customer-import-gate-readiness.md` §9 — restated in the final
prompt's hard constraints).

## 3. Should the branch B research/decision task run in parallel now? — **Yes (Recommendation)**

**[Recommendation — for ChatGPT decision, not made here]** Authorize the
dedicated branch B research/decision task now, parallel to the Task 011
chain. Reasons, all evidence-cited:

1. **Non-competing.** Docs-only; zero file overlap with Task 011's
   allowed files; Task 011 performs no OAuth (§2).
2. **On the critical path of everything setup-facing.** The setup
   wizard's OAuth-connect step (UI Group 3), OAuth/token-acquisition
   implementation, commercial packaging (OP-23 interacts), App-Store
   readiness (OP-31), and the release checklist all wait on the branch B
   decision (roadmap P1; readiness map §3).
3. **Compliance costs are cheaper to know before customer/order code
   hardens (OP-40).** If branch B lands on public distribution, the
   **Level 2 PCD review obligations** (encrypted backups, test/prod data
   separation, data-loss-prevention strategy, staff-access limits +
   access log, incident-response policy, retention limits — official
   list, re-verified 2026-07-10) become app-review requirements that
   touch how customer/order data is stored and operated. Knowing the
   posture before Tasks 011/012 merge lets their data handling be
   review-compatible by design rather than retrofitted.
4. **The 2026-07-10 refresh sharpened the option space** (§4) — the
   remaining work is a bounded evaluation + one DEC proposal, not
   open-ended research.

## 4. The distribution/auth choices still open (2026-07-10 evidence refresh)

**[Fact, all re-verified 2026-07-10 against official pages; quotes in the
capture file]**

- Shopify offers exactly **two** partner-selectable distribution methods
  — **Public** ("distribute or sell your app to many merchants through
  the Shopify App Store") and **Custom** ("one store or multiple stores
  on the same Plus organization using a link") — and the choice is
  **permanent** per app ("You can't change the distribution method after
  you select it").
- **No review-free multi-merchant route exists.** "All apps distributed
  through the Shopify App Store must have an app listing page"; the old
  "unlisted app" concept survives only as **limited visibility** (not
  indexed/searchable) on a **reviewed** App Store listing; the legacy
  "unpublished app" type is deprecated. Review applies identically to
  fully-visible and limited-visibility apps.
- **Public-app obligations:** the three mandatory compliance webhooks
  (`customers/data_request`, `customers/redact`, `shop/redact`, 30-day
  response); a Shopify-provided billing solution is required for app
  charges ("Apps that use off-platform billing cannot be distributed
  through the Shopify App store, unless you've been notified otherwise");
  PCD Level 1 + Level 2 review with the full data-protection obligations
  list; Lighthouse-impact ≤10-points listing requirement. (Built for
  Shopify remains an optional recognition tier, not an obligation.)
- **Custom-distribution apps:** no review; PCD Level 1/Level 2 "Always
  available"; but **"Can't use the Billing API to charge merchants"** —
  billing for such customers is entirely off-platform; each app is bound
  at creation to one entered store domain (optionally its Plus org).
- **The per-customer-custom-app model's ceiling is officially
  undocumented [Open question]:** no official page states a limit on how
  many custom-distribution apps one partner organization may register,
  and none endorses per-client registration at scale. Absence of a
  documented limit is not permission; the Partner Program Agreement
  (legal terms, not dev docs) has not been reviewed.

**The candidate set for the branch B decision therefore reduces to:**

| Candidate | What it is | Known costs | Known unknowns |
| --- | --- | --- | --- |
| **B-1: Reviewed public app, limited visibility** | One app, App Store listing not indexed anywhere; installable by any merchant via the listing URL | App review; compliance webhooks; Shopify billing for app charges (business-model consequence); PCD Level 1+2 review + full obligations list | Review SLA; what "must sync certain data with Shopify" concretely requires; whether limited-visibility installs can be further gated |
| **B-2: Reviewed public app, fully visible** | Same as B-1 plus App Store discoverability | Same as B-1 + public marketplace exposure | Same as B-1 |
| **B-3: One custom-distribution app per customer organization** | Vendor registers a separate custom app per client store/Plus org; OAuth per DEC-023 branch A mechanics | Manual per-client app registration/ops; no Billing API (off-platform invoicing); no App Store presence | **Scalability/policy ceiling undocumented** (app-count limits; Partner Program Agreement posture); operational burden at N customers unquantified |
| **B-4: Hybrid** | B-3 for early/pilot customers now; B-1/B-2 later | Sequencing complexity; permanent-per-app choice means each custom app stays custom | Same unknowns as both parents |

**RA-003 compliance note:** B-1/B-2 are *evaluation candidates* under
RA-003's stated revisit condition ("a future, ChatGPT-approved decision
to pursue public App Store distribution for Phase 2+") and DEC-023 §3.2's
accepted framing. This brief routes them for evaluation; it does not
adopt them, so RA-003 is respected, not revisited-by-stealth.

## 5. What PCD Level 2 implies for customer import (Task 011) and order import (Task 012)

- **[Fact, 2026-07-10]** Customer **name, address (incl. billing/shipping
  address lines, geolocation, zips), email, and phone** are Level 2
  protected customer fields; "any data that directly relates to a
  customer or prospective customer" is protected customer data. Task
  011's import fields (name/email/default address/phone snapshot) and
  Task 012's order-customer data sit squarely in Level 2.
- **Under the current evidence path (custom distribution, branch A):**
  access is "Always available" — no review. The general data-protection
  expectations still apply as good practice, and the project's accepted
  conservative posture already matches most of them (minimal-field
  import discipline; PII-minimized operator surfaces; no PII invention;
  ACL-restricted logs; credential redaction).
- **If branch B chooses public distribution (B-1/B-2):** the Level 2
  obligations become **review-enforced requirements** — encrypt data at
  rest/in transit, encrypted backups, retention limits, test/prod data
  separation, data-loss-prevention strategy, staff-access limits and an
  access log for protected data, incident-response policy. Two of these
  (encryption-at-rest posture; retention/erasure mechanics) interact
  with **already-accepted decisions** — MBQ-04/Task 002's accepted
  plain-`Char`-plus-ACL credential posture explicitly makes no
  encryption claim, and no retention/erasure design exists yet — so the
  branch B task must scope what a review-compatible posture would
  require **without weakening the accepted Task 002 record** (a future
  DEC, not a silent change).
- **Design consequence already banked for Task 011 (no action needed):**
  Task 011's D2 payload/PII posture (minimal candidate detail,
  ACL-restricted, never server-logged) and minimal-field query (D7) are
  compatible with either branch outcome — verified against the
  obligations list this session.

## 6. Does Task 011's backend implementation need OAuth/public-app distribution finalized? — **No**

Restating §2 as the direct answer to the control-room question: **No.**
Task 011 needs a store record with a working token (any acquisition
path, including the already-accepted branch A evidence path) only at
*runtime in production* — and not even that for its own merge, since its
tests are fake-client-only and its Odoo.sh validation exercises no live
Shopify call. No Task 011 file, test, or acceptance criterion references
a distribution method.

## 7. Exact later work that depends on the branch B decision

| Dependent work | Dependency |
| --- | --- |
| Setup wizard OAuth-connect step (UI Group 3; OP-26) | Which app definition(s) the wizard connects to; redirect/callback mechanics; DEC-023 §6 security constraints |
| OAuth/token-acquisition implementation (no gate exists yet) | Entire mechanism = branch B outcome |
| Commercial packaging / Lite-Full framing (OP-23, Q27) | Billing route (Shopify billing vs off-platform) differs per candidate |
| App Store / public packaging readiness (OP-31; RA-003 revisit) | Only exists under B-1/B-2 |
| Compliance webhooks (customers/data_request, customers/redact, shop/redact) | Mandatory only under B-1/B-2; would need their own gated implementation |
| PCD review + data-protection posture (OP-40) | Review-enforced only under B-1/B-2 (see §5) |
| Release-readiness checklist execution (OP-30) | Checklist's distribution/packaging items unanswerable until branch B decided |
| VAL-B2 (OP-06) | **Not dependent** — proceeds under the already-accepted branch A path, unchanged |
| Tasks 011–015 backend domain code | **Not dependent** (§2/§6) |

## 8. Recommended next action and allowed scope (for ChatGPT to authorize — not authorized here)

**[Recommendation]** Authorize one dedicated, docs-only **MBQ-05 branch B
research/decision task**, parallel to the Task 011 chain, producing a
DEC-numbered proposal (candidate: DEC-026) that selects among §4's
B-1/B-2/B-3/B-4 (or presents a final split for ChatGPT decision), with:

- **In scope:** the §4 "known unknowns" (Partner Program Agreement review
  for per-client custom apps at scale; app-review SLA; the "must sync
  certain data with Shopify" limitation; limited-visibility gating
  mechanics); the §5 compliance-cost mapping per candidate (incl. the
  MBQ-04-interaction analysis, without weakening any accepted record);
  billing/packaging interaction with OP-23 at framing level only; a
  recommendation with revisit conditions.
- **Allowed files (proposed):** a new
  `docs/04-decisions/DEC-026-distribution-architecture-proposal.md` (or
  ChatGPT's preferred number), updates to
  `docs/01-research/shopify-token-acquisition-notes.md`,
  `docs/03-architecture/master-blueprint-open-questions.md` (MBQ-05 row),
  `docs/00-source-materials/**` captures,
  `docs/01-research/research-handoff.md`,
  `docs/05-qa/architecture-review-log.md` (new AR row) — Markdown only.
- **Out of scope / forbidden:** any code, OAuth implementation, wizard
  design beyond constraint restatement, packaging decisions beyond
  framing, any change to DEC-023's accepted branch A scope, any VAL-B2
  claim.
- **Not blocking:** the Task 011 gate sequence proceeds independently
  whether or not this task is authorized (§2).

## 9. Explicit non-authorizations

This brief does not resolve MBQ-05 (either branch), does not select a
distribution method, does not authorize the §8 task (ChatGPT's call),
does not authorize OAuth/wizard/packaging/webhook/UI code of any kind,
does not modify DEC-023's accepted limited scope, does not pass or
advance VAL-B2, and does not block, delay, or condition the Task 011
gate sequence on anything in it.

## Evidence / references

- [`../04-decisions/DEC-023-token-acquisition-and-val-b2.md`](../04-decisions/DEC-023-token-acquisition-and-val-b2.md)
  §2–§4, §8–§9 (branch A/B framing, accepted limited scope) —
  Accessible, this repository, 2026-07-10.
- [`master-blueprint-open-questions.md`](./master-blueprint-open-questions.md)
  MBQ-05 row (Partially routed / Open) — Accessible, 2026-07-10.
- [`../05-qa/rejected-approaches-log.md`](../05-qa/rejected-approaches-log.md)
  RA-003 (rejection + revisit condition, respected above) — Accessible,
  2026-07-10.
- [`../07-implementation-plan/task-011-customer-import-gate-readiness.md`](../07-implementation-plan/task-011-customer-import-gate-readiness.md)
  §5 (MBQ-05 = class B for Task 011);
  [`../08-release-readiness/open-points-closure-register.md`](../08-release-readiness/open-points-closure-register.md)
  OP-05/OP-40 — Accessible, 2026-07-10.
- Official Shopify pages, all fetched 2026-07-10, all Accessible (full
  excerpt capture:
  [`../00-source-materials/shopify-customer-odoo19-partner-task-011-captures.md`](../00-source-materials/shopify-customer-odoo19-partner-task-011-captures.md)):
  - https://shopify.dev/docs/apps/launch/distribution
  - https://shopify.dev/docs/apps/launch/distribution/select-distribution-method
  - https://shopify.dev/docs/apps/launch/distribution/visibility
  - https://shopify.dev/docs/apps/launch/app-store-review/review-process
  - https://shopify.dev/docs/apps/build/compliance/privacy-law-compliance
  - https://shopify.dev/docs/apps/launch/billing
  - https://shopify.dev/docs/apps/launch/shopify-app-store/app-store-requirements
  - https://shopify.dev/docs/apps/launch/protected-customer-data
  - https://help.shopify.com/en/manual/apps/app-types/custom-apps
  - https://help.shopify.com/en/partners/help-support/faq/unpublished-app-deprecation
  - Dead links recorded (both HTTP 404, 2026-07-10, content moved):
    https://shopify.dev/docs/apps/launch/distribution/distribute-custom-app;
    https://shopify.dev/docs/apps/launch/shopify-app-store/app-review

**Next step:** ChatGPT (a) confirms the §2/§6 non-blocking conclusion for
the Task 011 gate decision, and (b) separately decides whether to
authorize the §8 parallel research/decision task. Neither act is
performed by this brief.
