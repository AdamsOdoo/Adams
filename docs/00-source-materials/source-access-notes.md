# Source Access Notes

> **Purpose.** A detailed, per-resource access-validation log for the 8 initial
> competitor resources registered in
> [`../01-research/resource-inventory.md`](../01-research/resource-inventory.md).
> This file records **how** each source was reached, **what** is visible, **why**
> a blocked/partial source is gated, the **recommended unblock action**, and
> whether the resource is **ready for a deep dive** (RB-02.*). It captures access
> status only — **not** a deep dive of the content.
>
> **Rules honoured (per `CLAUDE.md` §7 and `research-methodology.md` §2):**
> normal anonymous access only; **no authentication wall was bypassed**; no
> scraping around protected access; gated content is recorded as Blocked/Partial,
> never captured.
>
> - **Validation date (this pass):** 2026-06-30 (Research Sprint B, Stage 2).
> - **Method:** a single normal HTTPS fetch per URL (proxy fetcher), plus — only
>   where the prompt explicitly allowed it (R2) — one search to note an alternate
>   public path. HTTP is upgraded to HTTPS by the fetcher.
> - **Continuity:** results are consistent with the Sprint A check (also dated
>   2026-06-30). No access status changed between Sprint A and Sprint B.

## Access summary (2026-06-30)

> **Superseded for R2 only, 2026-07-01:** see "R2 status correction — Sprint
> C2" below the R2 section. R2 is now **Accessible**; this dated table is
> retained as the original Sprint B snapshot.

| Status | Count | Resources | Deep-dive ready? |
| --- | --- | --- | --- |
| **Accessible** | 5 | R1 Webkul, R3 Emipro, R6 ecommerce_shopify, R7 VentorTech site, R8 sh_shopify_connector | Yes |
| **Partial** | 1 | R4 VentorTech Confluence | Hub yes; some child pages gated |
| **Blocked** | 2 | R2 Teqstars docs (HTTP 403 bot-block), R5 Google Doc (login wall) | No |

---

## R1 — Webkul: Odoo Multichannel Shopify Connector (blog/guide)

- **Date checked:** 2026-06-30
- **URL:** https://webkul.com/blog/odoo-multichannel-shopify-connector/
- **Access result:** **Accessible** (HTTP 200)
- **Visible sections:** Overview; Key Features (states bidirectional sync of
  products/orders/customers/inventory, cron scheduling, duplicate prevention,
  import filters, and use of the Shopify GraphQL API — **vendor/competitor
  claims**, not verified here); Setup Process (create Shopify app, API
  permissions, redirect URLs, OAuth credentials, install module, developer mode,
  establish connection); Configuration; Data Management; Support (UV Desk).
- **Blocked/partial reason:** none.
- **Recommended unblock action:** none needed.
- **Extraction path:** single long page (one continuous user-guide article).
- **Ready for deep dive:** **Yes** (RB-02.1). Note: pricing is gated behind a
  "Buy Now" purchase link, so price is an **open question** until resolved.

## R2 — Teqstars: Shopify Connector for Odoo, docs 19.0 (overview)

- **Date checked:** 2026-06-30
- **URL:** https://docs.teqstars.com/19.0/applications/shopify/overview.html
- **Access result:** **Blocked** (HTTP 403 Forbidden, empty body)
- **Visible sections:** none — the body was never delivered, so no headings or
  content could be read.
- **Blocked/partial reason:** the fetch returns **HTTP 403 Forbidden** with no
  body. This is a **bot-block / WAF rejection of the fetcher's user agent**, not
  a login or sign-in wall — the documentation site is public and indexed by
  search engines, but it refuses the automated fetcher. No authentication is
  required; the obstacle is purely the 403.
- **Recommended unblock action:** retry with an alternate user agent / a real
  browser fetch (or a browser-driven fetch tool that presents a browser-like UA).
  No owner permission or login is needed — only the bot-block must be worked
  around through a different fetch method (never by bypassing authentication,
  because there is none).
- **Alternate public path (noted, not relied upon):** one permitted search
  confirmed the **same canonical URL** is the correct product + version page
  ("Shopify Connector Features — Odoo 19.0 documentation") and surfaced indexed
  summary snippets (GraphQL-based connector, real-time sync, inventory/product/
  order management, refunds & cancellations). A **16.0** mirror exists at
  `docs.teqstars.com/applications/shopify/overview.html`. **These are not treated
  as equivalent** to direct access: indexed snippets are not the full document,
  and the 16.0 mirror is a **different version** of the product. They are noted
  only as fallbacks for ChatGPT to weigh.
- **Extraction path:** documentation hub (overview page + sibling/child doc
  pages such as setup/generate_credentials, product/order/customer management,
  payout report) under `docs.teqstars.com/19.0/applications/shopify/`.
- **Ready for deep dive:** **No / blocked** (RB-02.2 stays Blocked). The deep
  dive needs an alternate fetch path for the 19.0 docs, or an explicit ChatGPT
  decision to accept the 16.0 mirror as a non-equivalent fallback.

### R2 status correction — Sprint C2 (2026-07-01, current)

**The Blocked snapshot above is retained as audit trail and is not rewritten.**
Research Sprint C2 (2026-07-01) re-checked R2 and found it **Accessible**: the
recommended unblock action above (an alternate/browser user-agent fetch) was
executed and returned **HTTP 200** — confirming the 403 was a **bot/UA filter,
not a login wall** (no authentication bypassed). **31 Odoo 19.0 Shopify doc
pages** were read in full (setup, product/customer/order management,
collections/catalogs, metafields, payouts, FAQ, support policy; ~98 embedded
screenshots). **Ready for deep dive: Yes** (RB-02.2 is now **Done**, not
Blocked) — see `../01-research/competitor-deep-dives.md` (Teqstars section)
and `competitor-source-notes.md` (R2 "Sprint C2" subsections) for the
page-classified evidence. Full detail:
`../01-research/resource-inventory.md` ("Sprint C2 access change" section).

## R3 — Emipro: Shopify Odoo Connector docs v19 (installation)

- **Date checked:** 2026-06-30
- **URL:** https://docs.emiprotechnologies.com/shopify-odoo-connector/v19/installation.html
- **Access result:** **Accessible** (HTTP 200)
- **Visible sections:** Installation (current page) plus a left-nav doc tree:
  Setup; Shopify Configurations in Odoo; Product Management; Orders Management;
  Customer Export; Webhooks Configuration; additional features (Markets,
  Metafields, Reports, Payouts); a version selector covering v13–v19.
- **Blocked/partial reason:** none.
- **Recommended unblock action:** none needed.
- **Extraction path:** Just-the-Docs static site — a single page with a left-nav
  hub linking to many sibling sub-pages (feature/sync detail lives on the
  sub-pages, not the installation page).
- **Ready for deep dive:** **Yes** (RB-02.3); crawl the nav-hub sub-pages
  (webhooks, metafields, payouts) for sync-flow specifics.

## R4 — VentorTech: Shopify documentation (Confluence)

- **Date checked:** 2026-06-30
- **URL:** https://ventortech.atlassian.net/wiki/spaces/pd/pages/482639953/Shopify
- **Access result:** **Partial** (HTTP 200 with an anonymous-access banner)
- **Visible sections:** the Shopify landing/hub page — title, the parent
  "E-commerce Connectors" section, a Shopify subsection linking to ~27 child
  articles, and the navigation sidebar (other spaces: Direct Print, RabbitMQ
  Connector, ZPL Label Designer, QuickBooks Online Connector, General Questions).
- **Blocked/partial reason:** Confluence loads the hub anonymously but shows the
  banner **"You're viewing this with anonymous access, so some content might be
  blocked."** The detailed bodies of individual child articles are not fully
  rendered in the anonymous view; some content may require Atlassian sign-in.
  Classified **Partial** (not Accessible) because of that banner and the
  unrendered child-article bodies.
- **Recommended unblock action:** for complete article bodies, the owner may
  grant view access or export the space; alternatively, fetch each child article
  link individually to test which specific pages are readable anonymously vs
  gated. The hub level itself needs nothing. **Do not bypass auth.**
- **Extraction path:** navigation hub linking to ~27 child wiki pages; deep-dive
  content lives in those children (some may be gated).
- **Ready for deep dive:** **Partially** (RB-02.4). The hub + article titles can
  be triaged now; per-child anonymous visibility must be tested page-by-page, and
  any gated children recorded as Blocked rather than captured.

## R5 — Project Google Doc ("E-commerce user documentation")

- **Date checked:** 2026-06-30
- **URL:** https://docs.google.com/document/d/1zIwRxp7cvLYeyjl8P_mvsjC-v8Tsd_ugC1JbfTznHC8/edit?tab=t.0#heading=h.8li8a88ebj4s
- **Access result:** **Blocked** (Google sign-in wall; HTTP 200 shell, body
  gated behind authentication)
- **Visible sections:** none of the body. The fetch returns only the Google Docs
  interface shell with a "Sign in" prompt; only the title metadata
  ("E-commerce user documentation") is exposed.
- **Blocked/partial reason:** this is a **private Google Doc**. The document body
  is not served to unauthenticated requests. Per the strict rules, **no
  authentication/bypass was attempted**, and **no content was inferred beyond the
  visible title**.
- **Recommended unblock action:** **requires owner-granted access or an export.**
  The owner could share the doc with view access (e.g. to aysaadab@gmail.com),
  set link-sharing to "Anyone with the link", or export the doc (PDF/DOCX/HTML)
  and provide that file. This is a **ChatGPT decision** before RB-02.6 can run.
- **Extraction path:** a single Google Doc with heading anchors — not readable
  until access is granted.
- **Ready for deep dive:** **No / blocked** (RB-02.6 stays Blocked). Marked
  **"requires owner-granted access or export."**

## R6 — Odoo Apps: ecommerce_shopify (19.0)

- **Date checked:** 2026-06-30
- **URL:** https://apps.odoo.com/apps/modules/19.0/ecommerce_shopify
- **Access result:** **Accessible** (HTTP 200; purchase/checkout requires login)
- **Visible sections:** product title ("Shopify Connector for Odoo 19"); price
  **$195.56**; version 19.0; author **"Odoo IN Pvt Ltd"**; license **OPL-1**;
  description / core features; dependencies; live preview / demo links; release
  notes (e.g. 19.0.2.1, 19.0.2.0, 19.0.1.3); community comments. (Pricing/license
  are **on-page facts as of 2026-06-30**; feature text is a **vendor claim**.)
- **Blocked/partial reason:** none for reading; only the Buy/checkout flow needs
  an Odoo account login.
- **Recommended unblock action:** none needed for research reading.
- **Extraction path:** single long product listing page (description,
  dependencies, release notes, comments inline).
- **Ready for deep dive:** **Yes** (RB-02.5). **Open question to resolve in the
  deep dive:** provenance — is "Odoo IN Pvt Ltd" Odoo S.A. official or a partner
  module? Do **not** treat it as the "official" baseline until confirmed.

## R7 — VentorTech: Odoo Shopify Connector (product website)

- **Date checked:** 2026-06-30
- **URL:** https://ventor.tech/solutions/odoo-shopify-connector/
- **Access result:** **Accessible** (HTTP 200)
- **Visible sections:** product title "Odoo Shopify connector PRO"; key features;
  Initial Import (Shopify→Odoo); Product Export & Stock Sync (Odoo→Shopify);
  Order Import (Shopify→Odoo); Tracking Numbers (Odoo→Shopify); detailed feature
  lists; CTAs (BUY NOW / TRY NOW; **pricing 499 EUR**, per-version note); footer.
  (Pricing is an **on-page fact**; capability/sync-direction text is a **vendor
  marketing claim**.)
- **Blocked/partial reason:** none (a "Cookie Settings" link exists but does not
  gate content).
- **Recommended unblock action:** none needed.
- **Extraction path:** single long product landing page (with nav to related
  sub-pages).
- **Ready for deep dive:** **Yes** (RB-02.4, paired with R4 for technical depth).
  **Open question:** is the advertised sync "instant"/real-time or scheduled?

## R8 — Odoo Apps: sh_shopify_connector (19.0, features)

- **Date checked:** 2026-06-30
- **URL:** https://apps.odoo.com/apps/modules/19.0/sh_shopify_connector#features
- **Access result:** **Accessible** (HTTP 200; purchase requires login)
- **Visible sections:** breadcrumb Apps > Sales > Shopify-Odoo Connector;
  provider **Softhealer Technologies**; price **$168.81**; version 19.0; license
  **OPL-1**; availability (Odoo Online, Odoo.sh, On-Premise); Features
  (import/export products/contacts/orders, inventory sync, webhooks,
  multi-store/location, payment gateway, gift cards — **vendor claims**); Platform
  Walkthrough; company credentials ("10K+ customers"); Technical Details /
  Dependencies (CRM, Contacts, Inventory, Accounting, Sales, eCommerce, Discuss,
  Calendar, Website); version support v12.0–19.0. (Pricing/license are **on-page
  facts**; feature/"top seller" text is a **vendor claim**.)
- **Blocked/partial reason:** none for reading; only Buy/checkout needs login.
- **Recommended unblock action:** none needed.
- **Extraction path:** single long product page with anchored sub-sections
  (#features, walkthrough, technical details), all inline.
- **Ready for deep dive:** **Yes** (RB-02.5). **Open question:** exact
  ratings/downloads and the real-time-vs-scheduled boundary.

---

## Triage observations (factual, not conclusions)

- **Two sources need an unblock step before deep dive:** R2 Teqstars (403
  bot-block on the 19.0 docs) and R5 Google Doc (private login wall). R4 is
  partially gated at the child-page level. These are isolated in the backlog so
  they do not stall the rest (RB-02.1, RB-02.3, RB-02.5 are unblocked).
- **No source in this set is authoritative Shopify/Odoo technical documentation.**
  Every one is a vendor blog, vendor doc, marketplace listing, or user-provided
  doc — i.e. **competitor claims** or **on-page pricing facts**. Tier-1 technical
  facts come from the official Shopify and Odoo baselines produced this sprint
  (`../01-research/shopify-official-api-notes.md`,
  `../01-research/odoo-official-architecture-notes.md`), **not** from these
  sources (see `research-methodology.md` §1).
