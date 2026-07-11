# DEC-028 — Credential Storage & Protected-Customer-Data Posture Ladder (MBQ-04 / OP-40 / Q22)

## Status

**Proposed for ChatGPT review. NOT accepted.** Drafted 2026-07-10 by the
MVP planning-completion session (AR-042 candidate); **Rung 1 revised
2026-07-11** by the PR #148 revision session per ChatGPT's
control-room review (comment `4942966937`, item 8): the
hosting-encryption posture for production branch-A deployments that
import protected customer data is upgraded from a
documentation/recommendation statement to **named production-entry
criteria** (point 2 below). Nothing below is
binding until ChatGPT explicitly accepts this record. This proposal does
not authorize any code change, does not modify the merged Task 002
credential model, does not lift RA-003, does not weaken any accepted
no-logging/redaction rule, and does not resolve the MBQ-04 register
row's Partially-resolved→Resolved wording (that upgrade remains
ChatGPT's own register call, exercised by accepting this DEC or
separately).

## Question being decided

MBQ-04/OP-40 left open: how the connector's credential-storage posture
(Task 002's merged plain-`Char` + admin-only ACL + view masking +
mandatory redaction, per AR-022/AR-024/AR-025) reconciles with
Shopify's protected-customer-data (PCD) obligations across the two
accepted distribution branches (DEC-023 branch A custom distribution
now; DEC-026 B-1 public/limited-visibility at Phase 2+), and what the
hosting-neutral packaging story may claim.

## Evidence (all accessed 2026-07-10; captures in `../00-source-materials/shopify-orders-inventory-fulfillment-product-partner-captures-2026-07-10.md` §7; Odoo evidence per AR-022's accepted notes)

1. **[Fact — updates earlier repo phrasing]** Shopify's PCD page makes
   **"Encrypt data at rest and in transit" a Level 1 requirement** —
   it applies to *any* use of protected customer data, not only
   Level 2. Level 2 (name/address/email/phone) adds encrypted backups,
   test/prod separation, staff-access limits, strong passwords, an
   access log, and an incident response policy. Earlier repo notes tied
   encryption obligations to Level 2; the current official text places
   it at Level 1. (https://shopify.dev/docs/apps/launch/protected-customer-data)
2. **[Fact]** Enforcement differs by app type: **public apps require
   review/approval** (unapproved fields redacted; approval gate =
   data minimization); **custom apps: "Always available"** at both
   levels — the obligations are stated for all apps but are
   review-enforced only on the public path. Shopify "encourages all
   apps to meet protected customer data requirements."
3. **[Fact — AR-022, accepted]** Odoo 19 Community/core has **no
   field-level or ORM encryption-at-rest mechanism**; every official
   core credential example is plain storage + `groups=` access control;
   masking/ACL are not encryption; `sudo()` bypasses field `groups`.
4. **[Fact]** The item Shopify's PCD rules protect is **customer
   data** (names, addresses, emails, phones — i.e. what Tasks 011/012
   import into `res.partner`/`sale.order`), not the shop's own API
   token. The Task 002 credential (`access_token`) is a *shop secret*,
   not protected customer data; its handling is governed by DEC-004
   least-privilege + the accepted redaction contract, not by the PCD
   levels.
5. **[Fact]** The connector's PCD-relevant surface is the Odoo
   database itself (partners, orders, job payload snapshots). Whether
   the database is encrypted at rest is a **hosting-layer property**
   (Odoo.sh/on-premise infrastructure), not an application-code
   property; Odoo's corporate "Odoo Cloud" AES-256 statement remains
   platform-level with unconfirmed per-product mapping (AR-022,
   unchanged).

## Alternatives considered

| Option | Description | Consequences |
| --- | --- | --- |
| A — Application-level field encryption now | Encrypt `access_token` (and imported PII) in Python before storage | No official Odoo mechanism exists (AR-022); home-rolled crypto + in-code keys adds real key-management risk without satisfying PCD by itself (the PCD obligations cover the whole data estate, not one field); breaks searchability; heavy migration burden — the exact reasons Options D/E were deferred, all still true |
| B — Status quo forever, silent | Keep Task 002 posture and never state the PCD position | Leaves the DEC-026 acceptance note's named prerequisite unresolved; risks a future public-app submission discovering the gap late |
| **C — Posture ladder (recommended)** | Explicit, documented two-rung posture: MVP/branch-A rung now; public-app rung as named Phase-2+ entry criteria | Honest, evidence-backed, zero code now; converts the MBQ-04 tension into concrete, dated gate criteria for the B-1 path |

## Proposed decision (Recommendation — becomes binding only on ChatGPT acceptance)

**Rung 1 — current MVP / DEC-023 branch A (custom distribution):**

1. The merged Task 002 posture stands unchanged: `access_token` stored
   plain in the dedicated admin-only model, view-level masking, no
   read-back, the sanctioned single `_get_access_token()` path, and the
   mandatory no-logging/redaction contract (all merged and
   suite-proven). No encryption claim may ever appear in product copy
   (existing accepted rule, reaffirmed).
2. **Production-entry criteria (REVISED 2026-07-11 — binding
   prerequisites, not documentation advice):** any **production**
   branch-A deployment that imports protected customer data (i.e.
   runs Task 011/011B/012 against real customers) requires, **before
   go-live, recorded evidence of each of the following** — a named
   per-deployment checklist row set in the release plan §2.8, each
   row evidenced (platform statement capture, configuration
   screenshot, or signed operator attestation) and reviewed at the
   Go/No-Go gate:
   (a) **database encryption at rest** for the production database —
   satisfied at the hosting/infrastructure layer (e.g. Odoo.sh's
   published AES-256 at-rest statement, captured 2026-07-11
   (`../00-source-materials/odoo19-shopify-official-captures-2026-07-11.md`
   §7) — but evidenced **per deployment**, never assumed);
   (b) **encrypted backups**, or an explicit documented equivalent
   posture for that deployment (named storage, access, and rotation
   controls) — silence is not equivalence;
   (c) **staff/access restrictions** — who holds database/server and
   Odoo-admin access, least-privilege confirmed, the connector's
   four-group model actually assigned (no everyone-is-admin
   deployment);
   (d) **a retention/deletion policy** covering imported PII and
   `payload_snapshot` rows (the SEC-1 D-SEC1-6 retention/masking
   surface is the implementation vehicle);
   (e) **incident/access governance appropriate to the deployment** —
   a named incident contact + response note and an access log or
   documented equivalent.
   A deployment missing any row does not go to production with real
   customer data — a test/staging store is the fallback until the
   row is evidenced. The operator-facing installation guide carries
   the same list (documentation follows the criteria; it no longer
   substitutes for them).
3. Because custom apps have PCD access "Always available" and the
   compliance-webhook mandate is App-Store-scoped, **no PCD review or
   compliance webhook is required for the branch-A MVP** — while the
   Level 1/Level 2 *practices* (data minimization, retention,
   staff-access discipline) are adopted as the project's operating
   standard now: at process level plus the point-2 evidence gate and
   the SEC-1 least-privilege/retention code surface. This decision
   still claims **no Shopify certification of any kind** and invents
   **no Odoo field-level encryption** (point 7 unchanged) — the
   point-2 criteria may be satisfied by verified infrastructure
   encryption.

**Rung 2 — Phase 2+ public app (B-1), entry criteria (each blocks the
future RA-003-lift act, none blocks any MVP task):**

4. Before any public-app (B-1) submission: (a) hosting with verified
   encryption at rest for the production database and backups
   (platform evidence captured, not assumed); (b) the three mandatory
   compliance webhooks implemented (`customers/data_request`,
   `customers/redact`, `shop/redact` — per the webhook packet's
   Phase-2+ slice); (c) a PCD Level 2 access request prepared with
   field-level data-minimization justification; (d) a documented
   retention/deletion policy covering imported PII and
   `payload_snapshot` rows; (e) an access-log + incident-response
   process document; (f) re-evaluation of application-level credential
   encryption (Options D/E) **at that time**, against the then-current
   Odoo Enterprise/third-party landscape — deferred, not rejected,
   exactly as AR-022 left them.
5. These six items become named rows in the release-readiness plan's
   Phase-2+ section and in the MBQ-05 implementation-implications
   register — they are gate criteria, not tasks, until ChatGPT opens
   that gate.

**Cross-cutting:**

6. No new logging/redaction weakening of any kind; Q22's rule (no
   second token read path, never logged) is reaffirmed verbatim.
7. This decision does **not** claim Odoo field-level encryption exists
   (it does not, per AR-022), does not claim the MVP is "PCD Level 2
   certified" (no review exists for custom apps), and does not claim
   hosting encryption is in place anywhere (it must be evidenced per
   deployment).

## What becomes binding if accepted

Points 1–7. MBQ-04 may then be marked **Resolved at posture level**
(register note citing this DEC) with the Rung-2 items tracked as
Phase-2+ gate criteria; OP-40's posture decision closes the same way.

## What remains unauthorized regardless of acceptance

Any credential-model code change; any OAuth/public-app/compliance-
webhook implementation (Phase 2+, RA-003 unchanged); any encryption
implementation work (re-evaluated at the Rung-2 gate).
