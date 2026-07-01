# Resource Inventory — Research Sprint A

> **Purpose:** register the initial research resources, classify them, capture
> **initial** access status, define **what must be extracted later**, and mark
> open questions. **This is registration/triage only — not a deep dive.** No
> detailed feature claims are made here unless directly verified.
>
> - **Date of access check:** 2026-06-30
> - **Access policy:** no authentication wall was bypassed; gated sources are
>   marked **Blocked** / **Partial**.
> - **"Initial value" and "Evidence strength" are inferences** (our triage
>   judgement), not vendor facts. Evidence strength reflects how authoritative a
>   source is for *its own product* — vendor docs/blogs/listings are
>   **competitor claims**, not independently verified facts (see
>   `research-methodology.md` and `CLAUDE.md` §8).

## Access summary (as of 2026-06-30)

| Status | Count | Resources |
| --- | --- | --- |
| Accessible | 5 | R1 Webkul, R3 Emipro, R6 ecommerce_shopify, R7 VentorTech site, R8 sh_shopify_connector |
| Partial | 1 | R4 VentorTech Confluence (anonymous-access banner) |
| Blocked | 2 | R2 Teqstars docs (HTTP 403 bot-block), R5 Google Doc (login wall) |

## Inventory

| ID | Resource name | URL | Source type | Competitor / category | Initial value (inferred) | Evidence strength (inferred) | Current access status (2026-06-30) | What to extract later | Open questions | Notes |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| **R1** | Webkul — Odoo Multichannel Shopify Connector (blog/guide) | https://webkul.com/blog/odoo-multichannel-shopify-connector/ | Vendor blog that reads as a user guide | Competitor (Webkul) | High | Medium — vendor self-published (competitor claims); rich but promotional | **Accessible** | Feature scope; setup/config flow; sync model (real-time vs cron); API used; pricing (follow "Buy Now"); screenshots for UX benchmark | Actual pricing? Real-time vs scheduled specifics? Which Shopify API/version? | Self-states Odoo V19/V18/V17, version 1.0.0; pricing appears gated behind a purchase link |
| **R2** | Teqstars — Shopify Connector for Odoo, docs 19.0 (overview/features) | https://docs.teqstars.com/19.0/applications/shopify/overview.html | Official product documentation | Competitor (Teqstars) | High | Medium–High — official vendor docs (still competitor claims) | **Blocked** (HTTP 403 on direct fetch — likely UA/bot block, **not** a login wall; page is publicly indexed) | Full doc-tree: setup/create_instance, product/order/customer mgmt, sync model, multichannel, reporting | Will an alternate fetch (different UA / browser fetch / cache) work? Is the 16.0 doc a valid fallback? | No auth bypass attempted; deep dive needs an alternate fetch path |
| **R3** | Emipro — Shopify Odoo Connector docs (v19 install) | https://docs.emiprotechnologies.com/shopify-odoo-connector/v19/installation.html | Official product documentation | Competitor (Emipro) | Medium | Medium–High — official vendor docs | **Accessible** | Crawl nav hub: product/order/customer mgmt, webhooks, metafields, payouts; sync flow; config | Where do sync-flow specifics live in the tree? Screenshots on sub-pages? | Install page is a navigation hub; feature/sync detail is on linked sub-pages |
| **R4** | VentorTech — Shopify documentation (Confluence) | https://ventortech.atlassian.net/wiki/spaces/pd/pages/482639953/Shopify | Confluence wiki (vendor product/R&D docs) | Competitor (VentorTech) | High | Medium–High — vendor docs incl. troubleshooting | **Partial** (anonymous-access banner: "some content might be blocked") | Setup/permission guides; sync workflows incl. metafields; troubleshooting/error/scope guidance; child pages | Which child pages require Atlassian login? Do screenshots render only when authed? | Index/hub linking to many how-to children; do not bypass auth |
| **R5** | Project Google Doc ("E-commerce user documentation") | https://docs.google.com/document/d/1zIwRxp7cvLYeyjl8P_mvsjC-v8Tsd_ugC1JbfTznHC8/edit | Private Google Doc (user-provided) | Project-provided / internal (access-dependent) | Unknown (potentially Medium) | Unknown — cannot assess while gated | **Blocked** (Google sign-in wall; only the title leaked) | TBD — likely user-facing/setup content; confirm after access is granted | What is the actual content? Is it our own connector spec or general e-commerce docs? | **Private / user-provided / access-dependent.** No public mirror found; needs owner-granted view access or an export. No bypass attempted |
| **R6** | Odoo Apps — ecommerce_shopify (19.0) | https://apps.odoo.com/apps/modules/19.0/ecommerce_shopify | Odoo marketplace listing | Competitor (listed author "Odoo IN Pvt Ltd" — official-vs-partner unconfirmed) | High | Medium for features (vendor claims); **pricing/license are on-page facts** | **Accessible** (reading; purchase needs login) | Feature scope; sync cadence; setup flow (out-links); release notes; user comments; **verify provenance** | Is this Odoo S.A. official or a partner module? Exact rating/version history? | On-page: price **$195.56**, license **OPL-1**; no connector-UI screenshots on the listing |
| **R7** | VentorTech — Odoo Shopify Connector (product website) | https://ventor.tech/solutions/odoo-shopify-connector/ | Vendor product/solution page | Competitor (VentorTech) | Medium | Low–Medium — marketing page | **Accessible** | Feature/sync-direction positioning; workflow diagrams; pricing/licensing model | Is sync "instant" real-time or scheduled? How does it map to the Confluence docs? | On-page: **EUR 499**, per-version purchase note; pair with R4 for technical depth |
| **R8** | Odoo Apps — sh_shopify_connector (19.0, features) | https://apps.odoo.com/apps/modules/19.0/sh_shopify_connector#features | Odoo marketplace listing | Competitor (Softhealer) | High | Medium for features (vendor claims); **pricing/license are on-page facts** | **Accessible** | Full feature enumeration; sync/webhook specifics; setup sections; screenshots; verify ratings/downloads | Exact rating/review/download counts? Real-time vs scheduled boundaries? | On-page: price **$168.81**, license **OPL-1**; supports v12.0–19.0; self-described "top seller" |

## Cross-cutting notes (factual triage observations — not conclusions)

- **Two sources need an unblock step before deep dive:** R2 Teqstars (403/bot
  block — try alternate fetch or 16.0 fallback) and R5 Google Doc (needs owner
  access/export). R4 is partially gated.
- **On-page pricing already verified:** R6 $195.56 (OPL-1), R8 $168.81 (OPL-1),
  R7 EUR 499. R1 gates pricing behind a purchase link.
- **No source in this set is deep technical/API documentation.** Authoritative
  Shopify and Odoo 19 facts must come from **official platform docs** (tracked
  as backlog items RB-05 and RB-06), not from these competitor sources.
- **Provenance to verify:** R6 lists author "Odoo IN Pvt Ltd" — confirm whether
  it is Odoo S.A. official or a partner module before treating it as the
  "official" baseline.

## Sprint B re-validation (2026-06-30)

Research Sprint B (Stage 2) re-ran a normal anonymous access check on all 8
resources. **No access status changed from Sprint A** — the table above still
holds. Detailed per-resource access evidence (visible sections, block reasons,
unblock actions, extraction paths, deep-dive readiness) now lives in
[`../00-source-materials/source-access-notes.md`](../00-source-materials/source-access-notes.md).

| ID | Access (2026-06-30) | Deep-dive ready? | Unblock action needed |
| --- | --- | --- | --- |
| R1 Webkul | Accessible | Yes | None (pricing gated → open question) |
| R2 Teqstars 19.0 | **Blocked** (HTTP 403 bot-block) | **No** | Alternate UA / browser fetch; or ChatGPT decision on the 16.0 mirror (non-equivalent) |
| R3 Emipro | Accessible | Yes | None |
| R4 VentorTech Confluence | **Partial** (anonymous-access banner) | Hub yes; children to test | Owner view-access/export, or per-child anonymous test |
| R5 Google Doc | **Blocked** (login wall) | **No** | Owner-granted access or export (ChatGPT decision) |
| R6 ecommerce_shopify | Accessible | Yes | None (confirm official-vs-partner provenance) |
| R7 VentorTech site | Accessible | Yes | None |
| R8 sh_shopify_connector | Accessible | Yes | None |

- **No auth bypass** was attempted on any resource; gated content (R2 body, R5
  body, R4 gated children) was recorded, never captured.
- **Unblock decisions for ChatGPT:** (1) R2 — accept an alternate fetch method
  for the 19.0 docs, or accept the 16.0 mirror as an explicitly non-equivalent
  fallback? (2) R5 — can the owner grant view access or provide an export?

## Sprint C re-validation and access changes (2026-06-30)

Research Sprint C re-ran a controlled anonymous access pass on all 8 resources
(no auth bypassed) and **deep-crawled** the accessible ones. Net access changes
vs Sprint B, with full per-source evidence in
[`../00-source-materials/competitor-source-notes.md`](../00-source-materials/competitor-source-notes.md):

| ID | Sprint B status | Sprint C status | What changed in Sprint C |
| --- | --- | --- | --- |
| R1 Webkul | Accessible | **Accessible** | Pricing **resolved**: store page shows **$170.00** (was an open question). **Version discrepancy** found: blog "1.0.0" vs store "3.5.1". |
| R2 Teqstars 19.0 docs | Blocked (403) | **Blocked (403)** — unchanged, no bypass | The whole `docs.teqstars.com` host (19.0 **and** 16.0) still 403s. **But a different accessible Teqstars source was found:** the **Odoo Apps Store listing** `apps.odoo.com/apps/modules/19.0/shopify` (price **$326.20**, OPL-1, author **TeqStars**, **83 reviews/5.0**, ~28,630 LOC) — gives on-page facts + rich vendor claims. The deep dive is now possible from the **listing** (vendor claims), while the **docs remain blocked**. |
| R3 Emipro | Accessible | **Accessible** | Deep-crawled ~35 v19 sub-pages (queues, webhooks, Markets, metafields, payouts, analytic mapping, net-profit). **No price/license in docs.** Published changelog stale on the v19 path (only to 17.0.3.2 / Apr 2024). |
| R4 VentorTech Confluence | Partial | **Partial** — unchanged | 11 of 28 child articles read in full anonymously; 17 not fetched (recorded not-read). Hub dated **Nov 2023**; **Odoo version not stated** in docs. No auth bypassed. |
| R5 Google Doc | Blocked | **Blocked** — unchanged, no bypass | **New finding:** R5 is the **"Get Started" guide for R6 `ecommerce_shopify`** (R6's `odoo.com/r/ecommerce-shopify` CTA 301-redirects to this exact doc). Still sign-in-gated; **owner access/export required**; content not inferred. |
| R6 ecommerce_shopify | Accessible | **Accessible** | $195.56 / OPL-1 / "Odoo IN Pvt Ltd" / v19 only / **3824 LOC** / **no ratings yet**. **Cron-based (orders every 10 min), no webhooks, no UI screenshots.** Provenance (official vs partner) **still open** (India-subsidiary inference). |
| R7 VentorTech site | Accessible | **Accessible** | Confirmed + extended via **ecosystem + Apps Store `integration_shopify`** (USD **569.16** / €499, v **2.1.6** updated 2026-06-23, **300+ installs**, 20 reviews) and a **dated release-notes page** (1.13.0 → 2.1.6) — the most transparent maintenance trail of the set. |
| R8 sh_shopify_connector | Accessible | **Accessible** | $168.81 / OPL-1 / Softhealer / Odoo 12–19 / **18,951 LOC**. Broadest feature set (gift cards, abandoned-checkout→CRM, recommendations, Buy-with-Prime). **No ratings and no dated changelog** on the listing. |

- **Access summary (2026-06-30, Sprint C):** Accessible **5** (R1, R3, R6, R7, R8;
  plus the Teqstars **Apps listing** as an accessible R2 surrogate), Partial **1**
  (R4), Blocked **2** (R2 docs host, R5 Google Doc). **No authentication wall was
  bypassed on any resource.**
- **Updated unblock asks for ChatGPT:** (1) **R2** — the Teqstars **docs** remain
  403; decide whether the **Odoo Apps listing** (now captured) is sufficient
  competitor evidence, or whether to pursue a browser-UA fetch of the 19.0 docs
  for workflow/screenshot depth. (2) **R5** — owner view-access or an export;
  note it is specifically **R6's setup guide**. (3) **R4** — optionally fetch the
  remaining 17 Confluence child articles for full coverage.
- **On-page pricing facts captured this sprint (2026-06-30):** R1 **$170**,
  R2 **$326.20**, R6 **$195.56**, R7 **€499 / $569.16**, R8 **$168.81**; R3 price
  not shown in its docs.

## Sprint C2 access change — R2 Teqstars docs now Accessible (2026-07-01)

Research Sprint C2 rebaselined the **R2 Teqstars** source only. **This is a
source-availability correction; the Sprint C blocked snapshot above is retained
as audit trail and is not rewritten.**

| ID | Sprint C status (2026-06-30) | Sprint C2 status (2026-07-01) | What changed |
| --- | --- | --- | --- |
| **R2 Teqstars 19.0 docs** | **Blocked (HTTP 403 bot-block)** | **Accessible (HTTP 200 with a browser UA)** | ChatGPT re-checked and found the Odoo 19.0 Shopify docs accessible. Re-access confirmed the 403 was a **user-agent bot-filter, not a login wall** (no auth bypassed; content is public). **31 Shopify doc pages** read in full (setup, product/customer/order management, collections/catalogs, metafields, payouts, FAQ, support policy) with **~98 embedded screenshots**. Evidence is now **page-classified** (demonstrated vs claim vs implied vs not-found) in `../00-source-materials/competitor-source-notes.md` (R2 "Sprint C2" subsections) and `competitor-deep-dives.md`. |

- **Updated access summary (2026-07-01):** Accessible **6** (R1, R3, R6, R7, R8,
  **and R2 Teqstars docs**), Partial **1** (R4 Confluence — 17 child articles
  still unread), Blocked **1** (R5 Google Doc — login wall, unchanged; still
  R6's setup guide). **No authentication wall was bypassed on any resource.**
- **Method note:** the proxy fetcher's default user-agent is still 403-filtered
  by `docs.teqstars.com`; a standard **browser user-agent** request returns
  **HTTP 200**. This satisfies the Sprint C unblock path ("a browser-UA fetch of
  the 19.0 docs — no auth to bypass"). It is **not** an authentication bypass.
- **Standing lesson (reinforces DP-001 / DP-003 and the Sprint G revision note):**
  *an important source recorded as **Blocked** should be re-checked before any
  final scope/architecture decision depends on it* — access can change (WAF/bot
  rules, vendor doc releases). The Sprint C discipline of **not** treating blocked
  content as fact was correct; Sprint C2 simply consumed the evidence once it
  became available.
- **Remaining unblock asks for ChatGPT (unchanged):** (1) **R5** — owner
  view-access or export for the Google Doc (R6's setup guide). (2) **R4** —
  optionally fetch the remaining 17 Confluence child articles for full coverage.
