# Visual-review report — Fable gap-closure prototypes (2026-07-16 correction)

**Verdict: visual quality PROVEN by rendered evidence** for the twelve gap-closure
surfaces (plus the U0 dashboard and the index). All 28 renders are clean on the
automated checks (0 horizontal overflow, 0 broken links, 0 accessibility flags,
0 page errors); four surfaces were additionally inspected pixel-by-pixel and confirm
premium hierarchy, spacing, and state coverage. This report replaces the earlier
"no rendered PNG evidence yet" self-review gap.

> **Honesty note.** "Inspected in depth" below = the full-page PNG was read and
> reviewed screen-by-screen. "Verified by metrics + shared system" = the surface was
> rendered and passed every automated probe and reuses the same `assets/prototype.css`
> design-system tokens and components as the inspected surfaces, but was not read
> pixel-by-pixel in this pass. No surface is claimed "Apple-grade" without a render.

## Method

Headless Chromium 1194 / Playwright 1.56.1, full-page screenshots at desktop
1440×900 (all 14), tablet 768×1024 and mobile 390×844 (the seven representative
surfaces). Per-render probes: horizontal overflow, internal-link resolution,
static accessibility markup, uncaught page errors. Raw data: `results.json`.

## Checklist result (all surfaces)

| Check | Result |
|---|---|
| Horizontal overflow (desktop/tablet/mobile) | ✅ 0 hits across 28 renders |
| Broken internal links | ✅ 0 / 21 checked |
| `lang`, single `<h1>`, img `alt`, button names | ✅ all pass |
| Decorative-icon `aria-hidden` | ✅ 2 gaps found → fixed → 0 |
| Color-only signalling | ✅ none — badges always icon+label |
| Page errors (JS-free static) | ✅ 0 |

## Per-surface review

| Surface | Depth | Notes |
|---|---|---|
| **settings-permissions** | Inspected in depth (desktop+tablet+mobile) | Five tabs (capabilities/schedules, order policies, fulfillment mode, roles & access, retention & privacy). **PII masking correctly removed:** roles tab shows a "Customer data (PII) access" note ("both roles read the raw customer PII their role permits — no PII masking, no unmask toggle, no separate PII tier"); retention tab is a **documented retention & erasure policy** card (the former "Mask a customer now" action and the masked-sweep rows are gone). Fulfillment-mode tab shows Mode 1 (default) + **Mode 2 (opt-in)** with a consequences drawer. Two role cards, single-dropdown user-form mock, view-only state. Premium hierarchy, generous spacing, consistent badges. |
| **orders** | Inspected in depth (desktop+tablet+mobile) | All 8 financial states as rows; **customer column shows raw name + raw email** (e.g. `Nadia Haddad · nadia.haddad@example.com`) — de-masked. Loaded/loading(skeleton)/empty/error/manual-review/unknown-schema states all present; the unknown-schema banner ("Shopify sent a status this version doesn't recognize — READY_FOR_HANDOFF") demonstrates the fail-closed contract. Filters, review emphasis, danger accents consistent. |
| **external-fulfillment-review** | Inspected in depth (desktop+tablet+mobile) | Mode 1 review cases + Mode 1 proposal detail (proposed Odoo action, line/qty evidence, location-mapping check); **Mode 2 auto-reconciled with the "16 of 16 conditions passed" checklist**, the ambiguous "stopped at condition 7 (quantity_mismatch)" case, and the lot/serial-ambiguity case. Confirms Mode 2 is presented as an **in-scope working backend feature**, not deferred. Empty state included. |
| **cod-reconciliation** | Inspected in depth (mobile 390; desktop+tablet rendered) | Three-dimension state badges, five-value ledger, partial-collection drawer, courier-return discrepancy card, loaded/empty/loading/discrepancy states. **Mobile reflow is clean** — app bar collapses to a Menu button, ledger/timeline/drawer stack to a single column with no clipping; raw customer names shown. |
| **dashboard** (U0) | Verified by metrics + shared system (desktop+tablet+mobile) | Accepted U0 baseline; rendered here for the responsive set; clean at all three viewports. |
| **fulfillment** | Verified by metrics + shared system | Mode chip, layered state badges (four-layer taxonomy), holds, uncertain-outcome rows, carrier-Delivered inconsistency banner. Taxonomy wording corrected ("six concepts" → four-layer). |
| **tracking-timeline** | Verified by metrics + shared system | Carrier-milestone vertical timeline, multi-package tabs, state-taxonomy strip (relabeled from "six-concept"), delayed/failed/unknown-schema variants. |
| **order-review** | Verified by metrics + shared system | Evidence/decision detail; **customer identity de-masked** to raw name+email (bucket-U edit, 0 `•••` remaining). COD approval, duplicate-risk, fail-closed financial mismatch, edit-divergence states. |
| **inventory** | Verified by metrics + shared system | Location mapping, coalesced pushes, CAS status, divergence review, first-push guard, clamp warning. |
| **reconnect-backfill** | Verified by metrics + shared system (desktop+tablet+mobile) | Eight-step reconnect checklist, per-domain catch-up watermarks, honest 60-day backfill preview. |
| **product-export** | Verified by metrics + shared system | Selection → ownership-aware preview → confirm → progress → results with uncertain-reconciliation rows. |
| **stores** | Verified by metrics + shared system | Five lifecycle states, generation chip, **credential card (masked token, no read-back — DEC-004; correctly retained, not PII masking)**, disconnect quiescence, onboarding welcome. |
| **jobs-diagnostics** | Verified by metrics + shared system (desktop+tablet+mobile) | Ten job states, retry/cancel/resolve drawers, cron honesty card, eleven-state global gallery. |
| **prototype-index** | Verified by metrics + shared system | 5 U0 + 12 gap-closure cards; description corrected ("layered state badges"); rendered-evidence pointer added. |

## Visual defects found and fixed this pass

1. `orders.html` — customer column rendered masked emails (`n•••@e•••.com`, 15 cells). **Fixed:** raw names + emails.
2. `tracking-timeline.html` / `prototype-index.html` — "six-concept" strip/label wording. **Fixed:** state-taxonomy / layered-state wording.
3. `orders.html` + `cod-reconciliation.html` — 2 decorative `<use>` icons each lacked `aria-hidden`. **Fixed.**

(The masking removal in `settings-permissions`, `order-review`, `cod-reconciliation`, and the Mode-2/taxonomy wording were applied by the correction's UX bucket and confirmed here by render.)

## Limitations carried to implementation (Wave-5 UI acceptance criteria — not provable in static HTML)

- Real keyboard focus order and dialog/drawer focus-trap behavior under assistive tech.
- Screen-reader announcement of live status transitions and job progress.
- `prefers-reduced-motion` honoring for animated/loading states.
- Full RTL mirroring across all surfaces (only the dashboard demonstrates `dir`).
- WCAG AA/AAA contrast measured against final production token values (tokens are
  design-system-final in `ui-ux-final-design-spec.md`, not re-measured pixel-wise here).
- Production Owl/Odoo rendering parity (these are static HTML/CSS approximations).

No production UI code was created. These prototypes remain **Proposed**, pending
control-room visual acceptance and the Wave-5 UI packets.
