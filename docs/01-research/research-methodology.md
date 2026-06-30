# Research Methodology

> How research is conducted for the Odoo 19 Shopify Connector project so that
> findings are **consistent, comparable, cited, and traceable**. Every research
> session follows this method. It operationalises the citation and
> claim-classification rules in `CLAUDE.md` (§7–§8).

---

## 1. Source hierarchy (trust order)

When sources conflict, prefer higher tiers and say which tier a claim rests on:

1. **Tier 1 — Official platform documentation.** Shopify developer docs and
   Odoo 19 developer docs. Highest authority for technical facts.
2. **Tier 2 — Official vendor product documentation.** A connector vendor's own
   docs (Teqstars, Emipro, VentorTech Confluence). Authoritative for *what the
   vendor says their product does* — a **competitor claim**, not an independent
   fact.
3. **Tier 3 — Marketplace listings.** Odoo Apps pages. Good for pricing/license
   (on-page facts) and a feature **claim** list; depth varies.
4. **Tier 4 — Vendor marketing/blog/website.** Promotional; treat all
   capability statements as competitor claims to be verified.
5. **Tier 5 — Third-party/user-provided.** Reviews, forums, user-provided docs
   (e.g. the project Google Doc). Value varies; verify before relying.

> A claim's strength is capped by its source tier. A Tier-4 feature statement
> never becomes a "fact" without Tier 1–2 corroboration.

## 2. Citation rules

Every external claim records: **vendor/product + exact URL + access status
(Accessible / Partial / Blocked) + date accessed** (use the session's provided
date). Mark **direct quote vs paraphrase**. Capture high-value excerpts into
`/docs/00-source-materials/<source>/` with a citation header so research
survives link rot. Never bypass authentication; record gated content as Blocked.

## 3. Competitor evidence rules

- Treat vendor statements as **competitor claims**, not facts, until
  corroborated by Tier 1–2 or independent evidence.
- Distinguish **advertised** capabilities from **demonstrated** ones (docs with
  concrete steps/screenshots are stronger than a marketing bullet).
- Note version/edition context (Odoo version, app version, API version) for
  every capability — capabilities differ across versions.
- Record contradictions between a vendor's marketing page and its own docs.

## 4. Claim classification rules

Label every statement (per `CLAUDE.md` §8): **Fact**, **Competitor claim**,
**Inference**, **Recommendation**, **Decision**, or **Open question**. Never
present a competitor claim as a fact, or an inference/recommendation as a
decision. Decisions live only in `/docs/04-decisions` after review.

## 5. Screenshot analysis method

- Cite where each screenshot appears (source URL) and the date.
- Describe **what the screenshot demonstrates** (a setting, a wizard step, a
  status surface) — distinguish demonstrated behaviour (fact about the UI shown)
  from inferred behaviour.
- Capture/annotate into `/docs/00-source-materials/<source>/`; note any
  ambiguity. Do not fabricate UI that is not shown.

## 6. Pricing & support extraction method

- Record **price, currency, license** (e.g. OPL-1), and the **purchase model**
  (per Odoo version, per store, subscription vs one-off) with the URL + date.
- On-page pricing is a **fact about the listing on that date**; flag that prices
  change and re-date on each visit.
- Capture support/maintenance terms (included updates, support window, SLAs) as
  vendor claims.

## 7. Feature extraction method

For each competitor, extract features into the **fixed taxonomy** so they can be
matrixed later (RB-12 builds the taxonomy; RB-03 builds the matrix). Group by:
catalog/products, variants & media, inventory (multi-location, direction,
real-time vs scheduled), orders & fulfilment (statuses, shipping/tracking
write-back, refunds/returns, partials), customers, pricing/tax/discounts,
payments/payouts, multi-store/channel mapping, automation (webhooks vs cron,
queueing), reliability (error handling, retry/recovery, dedup), reporting, and
configuration/onboarding. Record presence **and depth**, each cited, each
classified (claim vs demonstrated).

## 8. UX extraction method

Capture the **end-to-end flows**: connect/authorise, instance creation, initial
mapping (fields/categories/taxes), scheduling, running/monitoring a sync, and
error recovery. Note step count, jargon, reversibility, guardrails, and
empty/error states. Separate observation (fact about the UI) from UX judgement
(inference). Feed the UX benchmark (RB-04).

## 9. Reliability extraction method

Look specifically for: idempotency/duplicate-prevention mechanisms (external-ID
mapping), partial-failure handling, retry/recovery and backoff, rate-limit
handling, conflict resolution (Odoo↔Shopify wins), and logging/observability.
These are first-class quality concerns for our product; record what each
competitor claims and what is actually demonstrated.

## 10. Technical-risk extraction method

Identify constraints and risks that affect feasibility: Shopify API surface and
version/deprecation, scopes/permissions, rate limits and bulk operations,
webhook delivery guarantees; Odoo 19 extension points, ORM/performance limits,
and module-isolation concerns. Classify each as fact (Tier 1) or open question;
flag anything that could force or forbid a design choice.

## 11. How to produce competitor deep-dives

1. Read `CLAUDE.md`, the latest handoff, `claude-learning-rules.md`, and the
   resource's row in `resource-inventory.md`.
2. Confirm access (and unblock strategy if Blocked/Partial) — never bypass auth.
3. Extract using §5–§10 into a single per-competitor file
   `/docs/01-research/<NN>-<competitor>.md`, every claim cited and classified.
4. Capture excerpts/screenshots into `/docs/00-source-materials/<source>/`.
5. List strengths/weaknesses/gaps **as inference**, plus open questions.
6. Do **not** build the cross-competitor matrix inside a single deep dive (that
   is RB-03) and do **not** draw MVP/architecture conclusions.
7. Close with the learning review + handoff (quality gate).

## 12. How to decide where a finding lands

Tag every notable finding with a **disposition** so product/scope work is
traceable:

| Disposition | Meaning | Rough test |
| --- | --- | --- |
| **MVP** | Needed for a credible first release. | Without it, the connector is not viable for a typical store. |
| **Phase 2** | Important but not first-release-critical. | Adds clear value; can follow MVP safely. |
| **Advanced** | Power/edge capability. | Valuable to a subset; higher complexity. |
| **Optional add-on** | Separable/monetisable extra. | Cleanly optional; not core. |
| **Avoid** | A pattern we deliberately will not copy. | Known to cause harm/risk; record in `../05-qa/rejected-approaches-log.md`. |

Dispositions assigned during research are **recommendations/inferences**, not
decisions; MVP scope is finalized later (RB-13) and only after ChatGPT review.
