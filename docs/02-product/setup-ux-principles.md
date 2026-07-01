# Setup and UX Principles

> The product **UX principles and quality bar** for the Odoo 19 ↔ Shopify
> Connector — setup, configuration, dashboard, sync operations, logs/errors,
> recovery, mappings, permissions, and advanced features. Companion to
> [`./product-vision.md`](./product-vision.md). **This is principles only — it does
> NOT design final screens, menus, or flows** (those are gated UI-design work).

## Status

- **Sprint:** Product Sprint E (RB-11). **Phase:** product strategy / synthesis —
  **no-code gate in force** (`CLAUDE.md` §4–§5). **Decides nothing.**
- **Governance:** every principle is a **product recommendation / inference /
  input**. **No MVP scope, no architecture, no ADRs, no module boundaries, no data
  models, no final UI** are decided here (MVP = RB-13, architecture = RB-14 /
  AR-002…AR-008, both gated).
- **Evidence discipline (DP-003 / DP-004 / DP-006):** competitor UX observations
  stay **claims / demonstrated-on-a-specific-screen**, never elevated to facts;
  improvement ideas are **inference**, not demonstrated competitor capability;
  conditional platform items (OAuth, distribution, queue framework, multi-company)
  stay **conditional**. UX judgements are labelled **[Inference]**; a described
  competitor screen is **[Demonstrated]**; a listing/marketing statement is
  **[Competitor claim]**; Tier-1 platform behaviour is **[Fact]**.
- **Evidence weighting:** demonstrated UX evidence is strongest for **Emipro (EM,
  real screenshots)** and **VentorTech (VT, dated release notes + KB screenshots)**;
  **sh_shopify_connector (SH)** is caption-level; **Webkul (WK)** guide-level; **EC**
  has **no UI screenshots**; **Teqstars (TQ)** docs are 403-blocked → UX
  unverifiable (`../01-research/ux-ui-benchmark.md` evidence base).
- **Dates:** competitor evidence access **2026-06-30**; session **2026-07-01**.

## Purpose

Define the **experience quality bar** so that when UI design and (gated)
implementation happen, they inherit a consistent, evidence-grounded set of UX
principles rather than re-deriving them screen by screen. These principles turn the
Sprint C UX benchmark and the Sprint D capability model into product intent for the
operator experience — the second of our two differentiation whitespaces (a unified
command center + recovery-first errors, which no competitor combines;
[`./product-vision.md`](./product-vision.md) differentiation theme 2).

## Evidence base

Grounded only in already-merged repo evidence (no new research):

- **UX/UI benchmark (Sprint C)** — [`../01-research/ux-ui-benchmark.md`](../01-research/ux-ui-benchmark.md)
  (per-area comparisons, best patterns, gaps, UX principles).
- **Best-in-class observations (Sprint C)** — [`../01-research/best-in-class-observations.md`](../01-research/best-in-class-observations.md).
- **Avoid-list (Sprint C)** — [`../01-research/avoid-list.md`](../01-research/avoid-list.md)
  (UX/config/logs/retry/inventory/docs anti-patterns).
- **Gaps & opportunities (Sprint C)** — [`../01-research/gaps-opportunities.md`](../01-research/gaps-opportunities.md)
  (setup, UX, dashboard, logs/recovery opportunities O-SET/O-UX/O-DASH/O-LOG).
- **Feature taxonomy + evidence map (Sprint D)** — [`./feature-taxonomy.md`](./feature-taxonomy.md),
  [`./capability-evidence-map.md`](./capability-evidence-map.md) (Domains 1–2, 13–17,
  cross-cutting UX groups; capability IDs C-CONN/C-DASH/C-OBS/C-MAP/C-MULTI…).
- **Tier-1 platform facts** — [`../01-research/shopify-official-api-notes.md`](../01-research/shopify-official-api-notes.md),
  [`../01-research/odoo-official-architecture-notes.md`](../01-research/odoo-official-architecture-notes.md)
  (latency reality, webhook/reconciliation, `ir.cron` internals, access rights).

## UX north star

**The operator always knows the answer to three questions: "Is everything OK? What
failed and why? What do I do next?" — and can act on the answer without reading
source code or filing a ticket.** (**[Inference]**, synthesising the
ux-ui-benchmark "UX principles for our product".)

Supporting stance: **confidence over speed** — every operation shows *what happened,
to what, and what failed and why*, following the demonstrated confidence loop
**stage → inspect → process → verify (open the record) → log** (EM/SH
**[Demonstrated]**; ux-ui-benchmark "Sync operation UX").

## Principle 1 — Guided setup, not documentation dependency

Setup is a **guided, in-product flow**, not a doc the user must follow in another
tab. The user should reach a working connection without hand-editing server config
or pasting long scope strings.

- *Evidence:* VT's OAuth-first connect with an up-front scope check + connection
  test is the best onboarding **[Demonstrated]**, but it requires editing
  `odoo.conf` (`server_wide_modules`, `queue_job` channels, ≥2 workers) and is **not
  installable on Odoo Online**; EM requires pasting a full scope string with a
  trailing-slash footgun; EC gates its setup guide behind a sign-in wall (O-SET-1,
  A-CFG-2, A-DOC-1).
- *Principle:* OAuth-style guided connect + credential masking; **minimise/automate
  any server-config prerequisite**; never gate the getting-started guide.
- *Conditional (DP-006):* **OAuth-first is a strong direction but conditional** —
  mandatory only if public/App-Store distribution is chosen; custom/private flows
  may use token/custom-app access. Distribution is **open (AR-002)** and not decided
  here. Whether the queue layer can avoid mandatory `odoo.conf` edits / work on Odoo
  Online is an **[Open question]** (AR-003).

## Principle 2 — Prove readiness before sync

Known failure modes are surfaced **before** the first sync, in one place, as a
pass/fail readiness check — not discovered mid-sync or in a support ticket.

- *Evidence:* EM's trailing-slash warning and VT's scope check show failures are
  predictable, yet still surface late for most; a full readiness check is a partial
  whitespace no competitor fully does (O-SET-2, C-CONN-05).
- *Principle:* a readiness/self-test surface (candidate checks: scopes,
  HTTPS/`web.base.url`, webhook reachability, worker/queue presence, credential
  validity) with an explicit pass/fail before first sync. WK's discrete "Test
  Connection" is the cheap-high-value floor (**[Demonstrated]**).
- *Open:* which checks are essential vs nice-to-have (**[Open question]**).

## Principle 3 — Progressive disclosure

Sensible, opinionated defaults first; advanced power is opt-in behind an "advanced"
tier. Approachable for normal users, powerful for advanced users — **one product,
not two**.

- *Evidence:* EM/SH/WK config is toggle-dense with unexplained jargon (10+ toggles
  per screen); VT's per-field mapping with Python transforms is powerful but
  power-user territory (A-UX-3, A-CFG-3, O-UX-2, ux-ui-benchmark "Configuration
  screen comparison").
- *Principle:* defaults that work out of the box; an advanced tier for power
  features; **inline help on every jargon field** ("Forecast vs Free-to-Use", "API
  Record Limit", etc.).

## Principle 4 — Honest sync status and freshness

Status is **truthful**: label each data type's actual sync mode (webhook /
near-real-time vs scheduled) and show "last synced / last reconciled" timestamps.
No "real-time" overstatement.

- *Evidence:* WK/EC/SH overstate "real-time" over cron/queue models
  (**[Competitor claim]** downgraded by Sprint C verification); no connector clearly
  communicates freshness; **[Fact]** Shopify webhook delivery is not guaranteed, so
  "real-time" is misleading (A-UX-1, O-UX-1, C-SYNC-07).
- *Principle:* per-data-type latency labels + visible timestamps; freshness is
  honesty-as-a-feature (cheap, high-trust). *Open:* per-object vs global freshness
  (**[Open question]**).

## Principle 5 — Command center over scattered menus

One place answers "is everything OK, what failed, what do I do" — fusing connection
health, queue/failure status, a recent-activity timeline, reconciliation status, and
quick actions. Not health in one menu and errors three menus away.

- *Evidence:* SH has the best monitoring (Integration Dashboard + daily activity
  chart + failure counts) and VT the best diagnostics (traffic-light health), but
  **neither combines both**; VT lacks a dashboard entirely; EC has none (O-DASH-1,
  C-DASH-01…05, ux-ui-benchmark "Dashboard / command center comparison"). A unified
  command center is a **[Inference]** differentiator built on **[Demonstrated]** halves.
- *Principle:* a single command center as the operator's home; quick actions
  **enqueue** work rather than running heavy sync inline (C-DASH-05 note).
- *Open:* admin vs functional-user dashboard split (**[Open question]**).

## Principle 6 — Recovery-first error handling

Every failure is **isolated, reason-coded, and recoverable** — automatically where
safe, one-click where manual — with a clear next action. Errors are a recovery
surface, never a dead end.

- *Evidence:* EM's reason-coded Log Book + isolated per-line failures and SH's
  failure counts are strong (**[Demonstrated]**); **EC is email-only (a dead end)**;
  retries are mostly manual (only VT auto-retries). No competitor combines
  reason-coded per-record logs + isolated failures + automatic retry + one-click
  manual retry + a named next action (O-LOG-1/2, A-LOG-1, A-RET-1, C-OBS-03).
- *Principle:* an error center where each failure shows record + reason + suggested
  fix + retry; automatic retry/backoff for transient/idempotent-safe operations with
  a clear manual override.
- *Conditional:* the auto-retry-vs-human error taxonomy and the retry mechanism are
  **[Open question]** routed to **AR-006** (not decided here); automatic retry
  **depends on idempotency** to avoid double-acting (**[Fact]**; A-RET-3).

## Principle 7 — Safe-by-default actions

Destructive or irreversible actions require a dry-run/preview or a strong,
explicit confirmation. The product never silently loses data.

- *Evidence:* VT's Preview/Report dry-run before export is the best pre-flight
  pattern (**[Demonstrated]**); most competitors map/apply blind; EM's "Force Done"
  is an irreversible footgun (A-CFG-1, A-RET-2, O-CFG-1). **[Fact]:** Shopify
  `productSet` deletes omitted list entries (delete-on-omit data-loss footgun —
  A-IMP-1).
- *Principle:* dry-run/preview before destructive apply; irreversible-action
  warnings with clear consequences; reversibility where possible; never send partial
  lists to full-state mutations.

## Principle 8 — Human-readable logs

Logs are the in-app source of truth: reason-coded, per-record, human-readable — not
raw stack traces, not email-only, not opaque status.

- *Evidence:* EM's state-coloured queues + per-line Log Lines + reason-coded Log
  Book / Mismatch Log ("SKU not found", "tax not found", "customer missing") is the
  best observability in the survey (**[Demonstrated]**); VT logs "every action" with
  per-line internal info; **EC email-only is the floor** (O-LOG-1, C-OBS-01/02,
  ux-ui-benchmark "Logs, errors, retries").
- *Principle:* reason-coded, per-record, in-app logs with an audit trail and a
  retention policy; failures isolated from successes; completion signals (EM's
  "processed" ribbon). Alerts (email/notification) **complement**, never replace, the
  in-app log (C-OBS-04).

## Principle 9 — Guided mappings

Mappings are **directional, testable, and previewable** — the user never maps blind.
A CSV fallback helps non-SKU catalogs.

- *Evidence:* VT's per-field direction control + custom Python transforms +
  test-against-live-data + Markets Preview/Report is the most advanced mapping UX
  (**[Demonstrated]**); EM's SKU-match-or-CSV/XLSX fallback helps messy catalogs;
  most competitors map blind (O-CFG-1, C-MAP-03, ux-ui-benchmark "Mapping screen
  UX").
- *Principle:* directional field mapping + a dry-run/preview before any destructive
  apply; CSV fallback for non-SKU catalogs; **custom transforms are an advanced,
  opt-in tier** (Principle 3). Documented, explicit dedup/binding keys underpin
  mappings (O-DUP-1; binding model **not decided** — AR-005).

## Principle 10 — Role-aware UX

Two audiences, one product: an **admin** surface (install, credentials, mappings,
permissions) and a **functional-user** surface (run syncs, read logs, fix errors),
separated by access rights.

- *Evidence:* SH gates setup behind an access right (a sound default,
  **[Demonstrated]** via caption); EM separates via user rights; **[Fact]:** Odoo
  `ir.model.access` is deny-by-default and record rules provide isolation
  (C-MULTI-03, ux-ui-benchmark "UX principles" #8).
- *Principle:* connector settings gated to authorised users; a functional user can
  operate day-to-day without admin rights; surface "which store/company does this
  belong to" on records to reduce error (multi-company handling stays conditional —
  see Principle *Multi-store and permissions*).

## Principle 11 — Modular feature visibility

The UI shows what a deployment actually uses. Capability groups (advanced breadth,
premium add-ons) are **feature-flagged** so normal users are not confronted with
surfaces they do not need — premium, not bloated.

- *Evidence:* SH's breadth (gift cards, abandoned-checkout→CRM, recommendations,
  Buy-with-Prime) increases surface area; toggle-dense screens harm onboarding
  (O-PREM-3, A-UX-3; feature-taxonomy cross-cutting "feature flags" group).
- *Principle:* optional/advanced capabilities are hidden until enabled; the default
  surface stays lean. **[Inference]** — the feature-flag model is an input; the
  mechanism is **not decided** (AR-004).

## Principle 12 — Documentation mirrors the product

In-product help and external docs reflect the **actual** screens, jargon, and
limitations the user sees — open, screenshot-rich, honest, and current.

- *Evidence:* EM's rich, screenshot-heavy, honest docs (states limitations plainly)
  and VT's dated release notes lead (**[Demonstrated]**); **TQ docs 403-blocked, EC
  no screenshots + gated setup guide, SH no changelog** are anti-patterns; EM's
  docs also cite a **stale** Shopify figure (O-DOC-1, A-DOC-1/2/3, C-DOCS-01/02).
- *Principle:* open, non-gated, screenshot-rich docs; inline help anchored to real
  fields; a dated changelog that discloses fixes and cites **current** platform
  figures (ties to DP-001); honest limitation disclosure.

---

## Setup flow principles

- Guided, in-product connect (Principle 1); credential masking; **no long manual
  scope paste as the only path**; validate inline (A-CFG-2).
- A readiness/self-test before first sync (Principle 2); WK-style explicit
  pass/fail test connection as the floor.
- Never gate the getting-started guide behind a sign-in wall (A-DOC-1).
- Reconnect / re-authorise / disconnect is a first-class, evidenced need (VT
  store-URL migration fix; C-CONN-06).
- *Conditional:* OAuth-mandatory, GraphQL-only, and billing/compliance-webhook
  setup steps are **conditional on the distribution decision (AR-002, open)** — do
  not present them as universal.

## Configuration screen principles

- Domain-segmented configuration with sensible defaults (WK's tabbed IA is good;
  EM/SH toggle density is the anti-pattern) (ux-ui-benchmark "Configuration screen").
- Inline help on every jargon field; an advanced tier for power options (Principle 3).
- Friendly scheduling language ("every N minutes"), **never raw `ir.cron` internals**
  (Model / Scheduler User / Next Execution Date) (A-UX-2, **[Fact]**-informed).
- Per-instance configuration holding credentials + sync toggles is the common shape
  (common-patterns "configuration"); **the config data model is not decided** (AR-004).

## Dashboard principles

- One command center as the operator home (Principle 5): connection health +
  queue/failure counts + recent-activity timeline + reconciliation status ("last
  synced / last reconciled") + quick actions.
- Health indicators are **glanceable and actionable** — status encodes the cause +
  a fix hint (VT traffic-light generalised; C-DASH-02/04, O-UX-3).
- Quick actions **enqueue** work; heavy sync never runs inline in the request
  (**[Fact]** worker/5s-ack limits; C-DASH-05, A-SYNC-4).
- Empty/first-run states guide the new user (C-DASH-06; **[Inference]** — no
  competitor evidence, UX best-practice only).

## Sync operation principles

- The confidence loop: **stage → inspect → process → verify (open record) → log**
  (EM/SH **[Demonstrated]**).
- Filterable, incremental syncs (all / ID / date-range; "don't update existing";
  "import draft") build confidence (WK/EM; ux-ui-benchmark "Sync operation UX").
- Honest sync-mode + freshness labels per data type (Principle 4).
- Manual/on-demand sync is always available (also the Odoo.sh-staging test path,
  since crons are disabled on staging — **[Fact]**; C-SYNC-05, A-IMP-3).
- Webhooks **and** scheduled reconciliation **and** manual sync coexist — never one
  alone (**[Fact]** delivery not guaranteed; A-SYNC-1/2). *The orchestration
  mechanism is **not decided** (AR-003).*

## Logs, retries, and recovery principles

- Reason-coded, per-record, in-app logs as the source of truth (Principle 8);
  failures isolated (one bad record never blocks the batch — A-LOG-2).
- Recovery-first: automatic retry/backoff for safe ops + one-click manual retry +
  named next action (Principle 6); recovery affordances like a "needs re-export"
  flag (SH) and manual missed-webhook reconciliation (EM).
- Failed-job notifications to the responsible user **complement** the in-app log
  (VT; C-OBS-04) — never email-only recovery (A-LOG-1).
- *Conditional:* the error/retry taxonomy (auto-retry vs human) and mechanism are
  **[Open question]** → **AR-006**; automatic retry depends on idempotency
  (**[Fact]**; A-RET-3).

## Mapping screen principles

- Directional, testable, previewable mappings; dry-run before destructive apply
  (Principle 9, Principle 7).
- CSV/XLSX fallback for non-SKU catalogs (EM **[Demonstrated]**).
- Custom transforms are advanced/opt-in (Principle 3); deterministic routing
  (gateway/location/market) with a clean fallback (EM country→currency→fallback;
  C-MAP-04).
- Documented, explicit dedup/binding keys underpin mappings; **the binding data
  model is not decided** (AR-005; C-MAP-01/02).

## Multi-store and permissions principles

- Per-store config isolation and clear company/warehouse/pricelist routing; surface
  the owning store/company on records (ux-ui-benchmark "Multi-store / multi-company").
- Role-aware access: connector settings gated to authorised users (Principle 10).
- *Conditional (DP-004/DP-006):* **multi-company support/isolation stays conditional
  / later** — a config field is **not** demonstrated support (WK default-Company field
  ➖); record-rule isolation is the **[Fact]**-based mechanism *if in scope*; SH
  multi-company is **not-found**. **Single- vs multi-store / single- vs multi-company
  at MVP is an [Open question] (RB-13).**

## Advanced feature principles

- Advanced/premium surfaces (payouts, B2B/VAT, Markets/Catalogs, POS, gift cards,
  metafields, extended breadth) are **feature-flagged optional add-ons** on the core
  (Principle 11; O-PREM-3), not part of the default surface.
- Each advanced surface still meets the same UX bar (guided, observable,
  recoverable, honest, safe) — premium means *correct and well-run*, not *more
  toggles*.
- *Conditional:* payouts are **Shopify-Payments-gated** (**[Fact]**; A-PAY-1);
  advanced reporting may be Odoo-edition-gated (Enterprise-only; disclose). Evidence
  strength varies (B2B VT-only; gift cards SH-only) and stays labelled — none is an
  MVP decision.

## Anti-patterns to avoid

(From [`../01-research/avoid-list.md`](../01-research/avoid-list.md) — **UX-facing**
anti-patterns; recommendations, not rejected-approach decisions per `CLAUDE.md` §10.)

- "Real-time" labels on a cron/queue model; opaque/binary status with no cause
  (A-UX-1/4).
- Exposing raw Odoo cron internals to end users (A-UX-2).
- Toggle-dense screens with unexplained jargon and no defaults (A-UX-3, A-CFG-3).
- Zero-screenshot / no-proof UX; blocked or sign-in-gated docs (A-UX-5, A-DOC-1).
- Blind mappings with no preview/test (A-CFG-1); long manual scope paste with silent
  failure (A-CFG-2).
- Email-only, reason-less, non-isolated error handling (A-LOG-1/2/3).
- Manual-only recovery; irreversible "Force Done"-style actions without strong
  guards (A-RET-1/2).
- Manual post-import stock processing (auto-apply, optionally with review, instead —
  but **auto-apply is an improvement inference, not demonstrated competitor
  evidence**; DP-006, A-INV-1, C-INV-04).
- Heavy work inside the webhook request (5s ack; **[Fact]**; A-SYNC-4).

## Open questions

1. Which readiness checks are essential vs nice-to-have (Principle 2)?
2. Admin vs functional-user **dashboard** split — one surface with role-gated
   sections, or two (Principle 5/10)?
3. Per-object vs global **freshness** indicators (Principle 4)?
4. The auto-retry-vs-human **error taxonomy** and retry mechanism (Principle 6 →
   AR-006)?
5. Can the setup avoid mandatory `odoo.conf`/queue prerequisites and work on Odoo
   Online (Principle 1 → AR-003)?
6. Single- vs multi-store / single- vs multi-company at MVP, and the **feature-flag**
   model for modular visibility (Principles 10/11 → RB-13 / AR-004)?
7. Do EM/SH/WK config screens actually have inline help/tooltips (not visible in
   Sprint C extraction)? Does firming up TQ (403) / EC (no screenshots) change any UX
   principle?
8. Demo/docs hosting and built-in self-test scope (Principle 12; O-TEST-1)?

## Review notes for ChatGPT

Please inspect and confirm:

1. **Coverage** — do the 12 principles + the per-area principle sets fully capture
   the operator-experience quality bar (setup, config, dashboard, sync, logs/recovery,
   mappings, permissions, advanced), without designing screens?
2. **Evidence discipline (DP-003/DP-004/DP-006)** — confirm competitor UX
   observations stay claims/demonstrated-on-a-screen (EM/VT weighted over SH/WK/EC/TQ),
   improvement ideas (auto-apply, unified command center, freshness) stay
   **inference**, and conditional items (OAuth, distribution, queue, multi-company,
   feature-flag mechanism) stay conditional/open.
3. **No premature design/decision** — confirm nothing reads as a final UI, menu
   structure, MVP scope, or architecture decision (DP-005 guard); flag any principle
   that implies a specific implementation.
4. **Command center + recovery-first** — endorse these as the leading operator-UX
   differentiation inputs (with the differentiation in `product-vision.md`), without
   locking MVP.
5. **Anti-patterns** — confirm the UX anti-patterns are correctly framed as
   recommendations (not rejections) and route to architecture review where flagged.

> **This document decides nothing.** All principles are **inputs** for the gated
> RB-13 (MVP) and RB-14 (architecture) reviews and later UI design, subject to
> ChatGPT review (`CLAUDE.md` §4–§5, §8–§10).
