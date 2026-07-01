# UX/UI Benchmark (Research Sprint C)

> Benchmark of the **user experience and screen/workflow quality** of the
> competitor connectors, grounded in the screenshot/visual evidence in
> [`../00-source-materials/competitor-screenshot-inventory.md`](../00-source-materials/competitor-screenshot-inventory.md)
> and the deep dives. **Benchmark and principles only — this does NOT design our
> final UI** (gated, `CLAUDE.md` §4–§5). Observations about a UI shown are facts
> about that screen; UX judgements are labelled **inference**. Access date
> **2026-06-30**.

## Evidence base

| Source | UX evidence quality | Basis |
| --- | --- | --- |
| **Emipro (R3)** | **Strong** | ~29 **real screenshots** of config, queues, logs, Markets, payouts. |
| **VentorTech (R4)** | **Strong** | 9 connector-UI screenshots in the Confluence KB (webhooks, inventory, catalogs, fulfillment, risk, cancel). |
| **sh_shopify_connector (R8)** | **Medium–High** | ~29 **captioned** walkthrough groups (pixels not inspected). |
| **Webkul (R1)** | **Medium** | 21 inline guide screenshots (markdown-extracted captions/labels). |
| **VentorTech (R7)** | **Low** | 4 marketing flow figures (alt-text only). |
| **Teqstars (R2)** | **Medium–High** *(Sprint C2, 2026-07-01)* | **~98 real doc screenshots** inside step-by-step pages (create-instance ×15, product-update ×12, order-status ×10, returns ×6, OAuth ×7); docs no longer 403-blocked. |
| **ecommerce_shopify (R6)** | **None** | **No UI screenshots or video** on the listing. |
| **Google Doc (R5)** | **None** | Sign-in-gated; not bypassed. |

> Caveat: pages were read via the proxy fetcher (markdown/alt-text), so field
> labels/captions are reliable but pixel layout, spacing, and exact status
> styling were not directly inspected (except where Emipro/VT screenshots have
> descriptive alt text).

## Competitor UX summaries

- **Webkul (R1):** guide-driven, **stage-before-commit** ("Feeds") model with an
  error queue; tab-segmented config; **but exposes raw Odoo cron internals**
  (Model, Scheduler User, Next Execution Date) and manual multi-field credential
  entry. *Inference: competent but leaks Odoo plumbing.*
- **Teqstars (R2):** *(now demonstrated, Sprint C2)* **screenshot-rich, step-by-step**
  — OAuth-per-step + **Test Connection**; a **tabbed instance config** (Product/Stock/
  Orders/Payout/Customer/Metafield/Workflow/Webhook/Automatic-Jobs) that is **powerful
  but toggle-dense** (10+ order toggles, several dev-mode-gated); a green/red
  **Allowed/Not-Allowed-Sync** badge on the listing form (clean exclude-from-sync);
  Manage-Sales-Channels publish/unpublish; propagate-to-Shopify checkboxes on refund/
  cancel/return; a two-step click&collect pickup flow; Force-Restock with a divergence
  warning. **But: an Operations launcher + Queues/Logs, not a metrics/chart dashboard**
  (the earlier "two dashboards" caption is not substantiated by the docs).
  *Inference: comprehensive and honest-in-warnings, but config-dense and lacking a
  unified monitoring surface.*
- **Emipro (R3):** **operations-grade** — a consistent "Perform Operation" entry,
  **state-coloured Data Queues** with per-line **Log Lines**, a reason-coded **Log
  Book**, and docs that **state limitations and gotchas plainly**. *Inference:
  powerful but expert-heavy, high surface area, manual steps.*
- **VentorTech (R4+R7):** **best diagnostics** — **traffic-light webhook health
  with a named cause**, **Preview/Report dry-run** before export, **Failed Job
  Notifications**, irreversible-action warnings, honest PII disclosure. *Inference:
  most polished operational UX; install is the friction point.*
- **ecommerce_shopify (R6):** **cannot be assessed** (no screenshots); failure
  surface is **email-only** (no in-app queue/log). *Inference: weakest
  operational UX evidence.*
- **sh_shopify_connector (R8):** **dashboard-centric** — an Integration Dashboard
  with a **daily activity chart**, queue dashboards with **failure counts**,
  audit logs, a **re-export recovery flag**, and **access-rights-gated** setup.
  *Inference: most instrumented monitoring UX; breadth → high surface area;
  "real-time" labels overstate a queue/cron model.*

## Setup and onboarding comparison

| Connector | Connect method | Validation up front | Step count (claimed/shown) | Notable |
| --- | --- | --- | --- | --- |
| Webkul | custom-app, **manual credential paste** | **Test Connection** button ✅ | ~5 Shopify + ~5 Odoo | clear screenshots; SAAS users must move to Odoo.sh |
| Teqstars | **OAuth custom-app** + manual-token + legacy password ✅ | **Test Connection** step ✅ | 6-step credential flow + Confirm | now demonstrated (7 screenshots); full scope list with "enable all" warning |
| Emipro | custom-app token (Path A/B) | warns **trailing-slash mismatch fails** ✅ | multi-step, paste full scope string | honest gotcha; **expert** |
| **VentorTech** | **OAuth (no manual tokens)** ✅ | **auto scope-check + connection test** ✅ | Apps "8-step" / ecosystem "3-step" | **but technical install** (odoo.conf/queue_job/≥2 workers; not Odoo Online) |
| ecommerce_shopify | OAuth/Self access 🟨 | ⬜ | guide is the **blocked Google Doc** | setup steps gated |
| sh_shopify_connector | custom-app → Authenticate → **status Done** ✅ | Sync Logs confirm token | multi-step Shopify + Odoo | **access-right-gated** setup (good default) |

**Inference:** the best onboarding combines **OAuth (no manual tokens)** with an
**explicit, early connection/scope test** (VT's model) — but **VT's heavy
self-hosted install (queue_job/workers) is the single biggest onboarding
friction in the survey**. WK's explicit Test Connection and EM's honest
trailing-slash warning are cheap, high-value guardrails. EC gating its setup
guide behind sign-in is an onboarding anti-pattern.

## Configuration screen comparison

- **Segmentation:** WK tabs config by domain (Basic/Sales/Product) — good IA.
  EM and SH are **toggle-dense** (EM's Order Configuration + Webhook Order
  Configuration carry 10+ toggles each; SH has many per-feature tabs).
- **Jargon:** WK ("Auto-evaluate", "API Record Limit", "Stock Action"), EM
  ("Forecast vs Free-to-Use", "Financial Status Configurations") expose terms
  that need inline help; tooltip presence not visible in extraction.
- **Power vs simplicity:** VT's **per-field directional mapping with custom Python
  transforms + test-against-live-data** is the most powerful config surface, but
  it is **power-user territory**.
- **Inference:** competitors trade **breadth for density**. Opportunity: progressive
  disclosure (sensible defaults + an "advanced" tier) with **inline help on every
  jargon field** and a **dry-run/preview** before any destructive apply.

## Dashboard / command center comparison

- **sh_shopify_connector (R8)** leads: a **Shopify Integration Dashboard** plus a
  **"Daily Queue Activity Tracking" time-series chart** and per-entity queue
  dashboards with **draft/completed/failed counts**.
- **Emipro (R3):** a Shopify Dashboard with a performance graph + a "Perform
  Operation" launcher and a Smart Dashboard for imported orders.
- **Teqstars (R2):** *(Sprint C2)* the docs show an **Operations launcher**
  (Marketplaces ‣ Overview) + **Queues/Logs** + **Smart-Notification** alerts, but
  **no metrics/chart monitoring dashboard** — the earlier "two dashboards" caption is
  **not substantiated** by the accessible docs (a marketing claim, not a demonstrated
  screen).
- **VentorTech (R4/R7):** **no dedicated dashboard**; relies on an auto-workflow
  **"visual pipeline"** status and a status menu/Kanban.
- **ecommerce_shopify (R6):** **none**.
- **Inference:** a **single command center** that fuses connection health, queue
  status (with failure counts), a recent-activity timeline, and quick actions is
  a clear differentiator — SH points the way; VT lacks it despite strong internals.

## Sync operation UX comparison

- **Entry points:** EM offers a **consistent dual entry** (Dashboard "Perform
  Operation" **or** Processes » Operations). SH triggers per-tab "Sync X"
  buttons. WK uses per-object wizards + dashboard buttons.
- **Filtering:** WK and EM expose **import filters** (all / ID / date-range;
  "don't update existing"; "import draft"); SH "Sync Based On". *Inference:*
  filterable, incremental syncs build user confidence.
- **Manual-sync confidence:** EM and SH stage into a **queue you can inspect and
  process manually**, with success ribbons/counts and "Open Record" to verify —
  strong confidence signals. WK stages into **Feeds**. EC offers only a dev-mode
  date-range fetch + email outcome (low confidence).
- **Inference:** the confidence pattern = **stage → inspect → process → verify
  (open the created record) → see it in a log**. EC's email-only outcome is the
  weakest.

## Logs, errors, retries, and recovery UX

- **Best observability — Emipro (R3):** **state-coloured Data Queues**
  (Draft/Failed/Cancelled/Done) + per-line **Log Lines** + a reason-coded **Log
  Book / Mismatch Log** ("SKU not found", "tax not found", "customer missing").
  Failures are **isolated** from successes (partial-failure friendly). *Footgun:
  "Force Done" is irreversible.*
- **Best diagnostics — VentorTech (R4):** **traffic-light webhook health** where
  **yellow = "callback URL mismatch — check `web.base.url`"** turns an opaque
  failure into a self-serve fix; **Failed Job Notifications** on user profiles;
  per-line **"internal info"** for failed fulfillments; **automatic retry** of
  safe operations.
- **Best monitoring — sh_shopify_connector (R8):** queue **failure counts** + a
  **daily activity chart** + Sync/Export **audit logs** + a **"Needs Shopify
  Re-Export" recovery flag**.
- **Weakest — ecommerce_shopify (R6):** **email notifications only**, no in-app
  queue/log/retry surface — a recovery dead-end.
- **Retry:** **only VT demonstrates automatic retry**; EM/SH/WK/EC are
  **manual** (re-run / re-evaluate / re-export). *Inference:* automatic retry +
  a clear manual override is the bar.
- **Inference:** the recovery UX target = **reason-coded, per-record, in-app logs
  + isolated failures + a one-click retry + named, actionable diagnostics** (not
  raw stack traces, not email-only).

## Mapping screen UX

- **VentorTech (R4/R7):** the most advanced — **per-field "Receive field on
  import" direction control**, **custom Python transforms**, **"test field
  mappings against live data before applying"**, and **Markets & Catalogs with a
  Preview/Report dry-run**.
- **Emipro (R3):** **SKU match or CSV/XLSX export-and-map** fallback (named
  columns); metafield mapping with Sync Direction Import/Export/Both.
- **sh_shopify_connector (R8):** directional metafield mapping (Sync Direction +
  Odoo Field Name) + a Payment Gateway Workflow Matrix.
- **Teqstars (R2):** *(now demonstrated)* gateway→journal workflow mapping (per
  payment gateway + financial status), location→warehouse mapping, and a
  **metafield→Odoo-field mapping list** with Ready/Missing/Not-Found/Inactive status
  badges and wipe-on-missing — but **no test-against-live-data / dry-run** (VT still
  leads on testable mappings).
- **Inference:** the strongest mapping UX is **directional + testable + dry-run**;
  a CSV fallback (EM) helps non-SKU catalogs. Avoid forcing users to map blind
  with no preview.

## Multi-store / multi-company UX

- **VentorTech:** "connect as many stores as you want"; multi-company inventory
  with correct company context (release-note demonstrated).
- **Emipro:** multi-company via **Markets** (per-market Company/Warehouse/
  Pricelist), with order routing **country→currency→fallback**.
- **sh_shopify_connector:** multi-store "in one Odoo DB" (multi-company
  **unverified**).
- **Webkul:** a default Company per channel (single-store framing).
- **Inference:** multi-store needs **per-store config isolation** and clear
  **company/warehouse/pricelist routing**; surfacing "which store/company does
  this belong to" on every record reduces errors. Record-rule isolation (Tier-1)
  matters for multi-company.

## Screenshot-driven observations

- **VT traffic-light webhook status** (green/yellow/red with a named cause) is the
  single best **status-indicator** pattern observed — it encodes *health* **and**
  *the fix* in one glance.
- **EM state-coloured queues + Log Lines + processed ribbon** is the best
  **operational error surface** — at-a-glance counts, drill-down reasons,
  completion signal.
- **SH daily activity chart + failure counts** is the best **monitoring** visual.
- **VT Preview/Report dry-run** ("detect issues before sending data") is the best
  **pre-flight validation** pattern.
- **WK Feeds error-feeds** is a good **stage-before-commit** concept (but the
  re-evaluate retry is described, not shown).
- **Counter-examples:** EC has **no screenshots** (no UX proof); *(TQ screenshots
  are now accessible — ~98 real doc screenshots, Sprint C2)*; raw cron internals
  (WK) and a long manual scope paste (EM/TQ) are friction; "Force Done" (EM) is an
  irreversible footgun; TQ's config form is **toggle-dense**.

## Best UX patterns observed (adopt-candidates, inference)

1. **Traffic-light health with a named cause + fix hint** (VT webhooks).
2. **State-coloured queue + per-line reason-coded logs + completion ribbon** (EM).
3. **Monitoring dashboard: activity timeline + failure counts + recent records** (SH).
4. **Dry-run / Preview-Report before any destructive apply** (VT catalogs).
5. **Explicit, early connection + scope test** (WK Test Connection; VT scope-check).
6. **Stage → inspect → process → verify (open record) → log** confidence loop (EM/SH).
7. **OAuth-first connect (no manual tokens)** + **credential masking** (VT).
8. **Honest limitation disclosure** (VT "no PII on Basic plan"; EM gotchas).
9. **Failed-job notifications to the responsible user** (VT).
10. **Access-right-gated setup** so only authorized users see connector config (SH).
11. **Recovery affordances:** a "Needs Re-Export" flag (SH); manual import to
    recover missed webhooks (EM); one-click retry (VT).
12. **Irreversible-action warnings** before destructive steps (VT cancel; EM Force Done — warn *better*).

## UX gaps and frustrations (avoid-candidates, inference)

- **Email-only error handling** with no in-app recovery (EC).
- **Raw Odoo cron internals** exposed to end users (WK).
- **Manual inventory-adjustment processing** required after stock import (EM).
- **Irreversible "Force Done"** without a strong guard (EM).
- **"Real-time" labelling** for cron/queue models (WK, EC, SH).
- **No screenshots / no proof of UX** (EC). *(TQ docs, blocked in Sprint C, are
  now accessible — no longer a UX-evidence gap.)*
- **Toggle-dense config** with jargon and no inline help (EM, SH, WK, **TQ**).
- **Technical install** (hand-edited odoo.conf + queue_job + workers) as the only
  path (VT).
- **Setup guide behind a sign-in wall** (EC → R5).
- **No rate-limit feedback** to users when Shopify throttles (all).

## What our connector should do better (recommendations — gated)

- **One command center** fusing connection health, queue status (failure counts),
  a recent-activity timeline, and quick actions — combining SH's monitoring with
  VT's diagnostics, which neither does fully.
- **Effortless onboarding:** OAuth-first; an early connection + scope test with a
  clear pass/fail; **avoid requiring hand-edited odoo.conf/queue_job for basic
  use**; never gate the setup guide.
- **Latency honesty:** label sync as webhook/near-real-time vs scheduled
  accurately; always pair webhooks with a **reconciliation** job.
- **Recovery-first errors:** reason-coded, per-record, in-app logs; isolated
  failures; **automatic retry + clear manual override**; named diagnostics with
  fix hints (the VT yellow-status model generalized).
- **Safe-by-default destructive actions:** dry-run/preview before apply; strong
  confirmation + reversibility where possible; clear irreversibility warnings.
- **Progressive disclosure:** sensible defaults + an "advanced" tier; inline help
  on every jargon field; testable, directional mappings.
- **Auto-apply** imported stock (no manual Inventory Adjustment).
- **Rate-limit awareness surfaced to the user** when Shopify throttles.

## UX principles for our product (inference — not a UI decision)

1. **Confidence over speed:** every sync shows *what happened, to what, and what
   failed and why* — stage → inspect → process → verify → log.
2. **Health is glanceable and actionable:** status indicators encode the problem
   **and** the fix.
3. **Honest by default:** accurate latency labels; disclosed limitations; no
   "real-time" overstatement.
4. **Recoverable by design:** isolated failures, automatic retry, one-click manual
   retry, and missed-event reconciliation.
5. **Safe by default:** dry-run before destructive apply; warn on irreversible
   actions.
6. **Approachable, then powerful:** great defaults + progressive disclosure;
   inline help; power features (mapping/transforms) opt-in.
7. **Don't leak the platform:** no raw `ir.cron` internals; speak the user's
   language ("every 15 minutes", not "nextcall").
8. **Two audiences:** an **admin** view (install, credentials, mappings,
   permissions) and a **functional-user** view (run syncs, read logs, fix errors)
   — gated by access rights (SH-style).

## Open questions

- Do EM/SH/WK config screens have inline help/tooltips (not visible in
  extraction)? *(TQ's "two dashboards" and "Queue Manager retry" captions are now
  **answered** by the accessible docs — **not** substantiated: an Operations launcher
  + Queues/Logs, and queue re-processing + manual re-run, not a metrics dashboard or
  per-record inline-retry control.)* What does EC's actual UI look like (no screenshots)? How do
  competitors surface Shopify **rate-limit/throttle** events to users (none found)?
  How do they present **reconciliation** runs to users (mostly implicit)?
