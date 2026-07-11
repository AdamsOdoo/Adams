# Premium UI/UX Design System and Frontend Architecture

> **Status: Proposed for ChatGPT review. NOT accepted. Docs-only —
> no UI code, asset, token file, or prototype exists or is authorized
> by this document.** Produced 2026-07-11 by the PR #148 revision
> session, implementing review item 4 of ChatGPT's control-room
> review (PR #148 comment `4942966937`). It **revises accepted
> content** and says so explicitly: DEC-016/AR-023's
> standard-views-only posture and the fixed nine-equal-cards
> dashboard (`../02-product/ui-ux-final-design-spec.md`, "Dashboard /
> command center design") are superseded **at proposal level** by
> §3/§9 below, at ChatGPT's own direction in the review — routed
> through the AR-042 revision note, not silently. Everything else in
> the accepted design corpus (`../02-product/ui-ux-final-design-spec.md`
> §Premium Simplicity Standard, the S1–S14 surface inventory in
> `../02-product/screen-inventory-and-navigation-map.md`, DEC-012's
> operator flows, the copy voice rules) **stands and is built upon —
> both files verified present in the repository at those exact paths
> on 2026-07-11.** External grounding: captures 2026-07-11 §3/§4/§13
> (`../00-source-materials/odoo19-shopify-official-captures-2026-07-11.md`).

## 1. Design philosophy — disciplined, not imitative

The bar is **Apple-like discipline, not Apple imitation**: restraint,
one clear answer per screen, generous whitespace, motion that informs
rather than decorates, and zero decoration that does not carry
information. Concretely, five laws every connector surface obeys:

1. **One dominant answer.** Every screen leads with the single thing
   the operator came to learn or do; everything else is visually
   subordinate.
2. **Calm by default, loud only when true.** Color, weight, and
   motion escalate only with real state (an error is loud because it
   is an error, never for emphasis).
3. **Text first, color reinforces.** No state is conveyed by color
   alone (accepted rule, restated; WCAG 1.4.1 posture).
4. **Odoo-native is a feature.** The product must feel like the best
   screen in the user's Odoo, not a foreign app embedded in it —
   premium here means polish and hierarchy inside the platform's
   design language, not a parallel one.
5. **Nothing vanity.** Accepted DEC-012 rule, restated: every element
   informs, reassures, or guides action.

## 2. Frontend architecture (the posture correction)

**[Proposed decision PD-7 — replaces the ordinary-XML-only posture]**

1. **Standard Odoo views remain the default** for lists, records
   (forms), filters/search, settings, and every large data table.
   Large tables are server-paginated Odoo-native lists — binding rule
   PB-9 (`performance-budgets.md`).
2. **Selective Owl client actions/components are permitted** — Owl is
   the official 19.0 component system and registries are the
   sanctioned extension points (captures §4) — **only** where they
   create real premium value, enumerated exhaustively:
   - **Dashboard / command center** (S3) — the §9 hierarchy;
   - **Setup / readiness experience** (S1 wizard chrome + readiness
     results presentation);
   - **Matching centers** (S6 product / S8 customer — candidate
     evidence cards + decision actions);
   - **Product diff/preview** (S7 — field-level diff rendering).
   Anything outside this list requires a new accepted decision.
3. **This is not an SPA.** Each Owl surface is a bounded client
   action inside the standard Odoo web client (menus, breadcrumbs,
   routing, list/form infrastructure all remain Odoo's). No custom
   router, no parallel navigation, no global state store, no
   duplicate list/form implementations.
4. **Data loading:** Owl surfaces call dedicated read-only backend
   endpoints/ORM methods returning **aggregates or bounded pages**
   (PB-10: `read_group`/counts, explicit limits, no unbounded
   recordsets); writes go exclusively through the sanctioned service
   methods (Area-6/SEC-1 doors) — the UI never gains a mutation path
   the backend doesn't already gate.
5. **Assets:** one SCSS token layer (§4–§6) + component styles in the
   owning modules' standard asset bundles; no external fonts, CDNs,
   or JS libraries beyond what Odoo 19 ships (offline-safe,
   review-safe).

## 3. Layout and information hierarchy

- **Page anatomy (every connector screen):** (1) lead answer band /
  title row → (2) primary action or primary exception region → (3)
  content → (4) secondary/metadata. Nothing above the lead answer.
- **Hierarchy budget:** at most **one** dominant element per screen;
  at most two visual emphasis levels below it. If a third feels
  needed, the screen is overloaded — split it (Premium Simplicity
  Standard, restated).
- **Density:** operator screens are information-dense but ranked —
  dense tables live one click below calm summaries, never beside
  them.
- **Grid:** content aligns to an 8 px baseline grid (4 px half-step
  for compact controls); max content width for reading surfaces
  (readiness explanations, error guidance) ~72ch.

## 4. Spacing and typography scales

- **Spacing scale (px):** 4, 8, 12, 16, 24, 32, 48, 64 — token names
  `--sc-space-1 … --sc-space-8`. Rules: siblings ≥ 8; unrelated
  groups ≥ 24; section breaks ≥ 32; card padding 16 (compact) / 24
  (standard). No off-scale values.
- **Typography scale (rem, based on Odoo's platform font stack — no
  custom font):** 0.75 (caption/meta), 0.875 (body-secondary), 1.0
  (body), 1.125 (card title), 1.375 (section/lead), 1.75 (the one
  dominant answer). Weights: 400 body, 500 titles/labels, 600
  dominant answer and critical counts — never heavier; no light
  weights below 400 for text that carries state. Line-height ≥ 1.4
  body, 1.2 headings. Numbers in counts/cards use tabular figures.

## 5. Surfaces, cards, and elevation

- Surfaces: `--sc-surface-0` page background, `--sc-surface-1` card,
  `--sc-surface-2` raised (popover/dialog — platform-managed).
  Exactly one card style: radius 8 px, 1 px border
  (`--sc-border`), **no drop shadows at rest** (elevation change only
  on genuine overlay). No nested cards.
- Cards carry: plain-word title, value/state, one-line qualifier,
  and are clickable to their filtered detail view (accepted card
  anatomy, restated). A zero state reads affirmatively.
- Banners (lead answer band): full-width, tinted per semantic status
  (§6), 1 px border in the darker token, icon + sentence + optional
  single action.

## 6. Light-mode color tokens and semantic status colors

Light mode is the MVP target (dark mode is a named later phase — no
token may hard-code against it). Proposed token set (hex values are
**proposals to be contrast-verified at the prototype gate**; the
checklist in §13 requires recorded ratios for every text/background
pair — WCAG 2.2 SC 1.4.3: ≥ 4.5:1 normal text, ≥ 3:1 large text;
SC 1.4.11: ≥ 3:1 UI component boundaries — captures §13):

| Token | Role | Proposed value |
| --- | --- | --- |
| `--sc-text-primary` | primary text | `#1F2937` |
| `--sc-text-secondary` | secondary/meta text | `#475467` |
| `--sc-surface-0/1` | page / card | `#F8FAFC` / `#FFFFFF` |
| `--sc-border` | hairlines | `#E4E7EC` |
| `--sc-accent` | interactive/brand accent (links, primary buttons — aligns with the Odoo theme primary) | `#175CD3` |
| `--sc-success-text/bg` | healthy, succeeded | `#067647` / `#ECFDF3` |
| `--sc-warning-text/bg` | attention, retry-waiting, overdue | `#B54708` / `#FFFAEB` |
| `--sc-danger-text/bg` | failed, blocked, destructive | `#B42318` / `#FEF3F2` |
| `--sc-info-text/bg` | neutral activity, in-progress | `#175CD3` / `#EFF8FF` |
| `--sc-neutral-text/bg` | skipped, cancelled, disabled | `#475467` / `#F2F4F7` |

Rules: status text tokens are used **for text and icons on their bg
tints or white only**; never white-on-tint; state words always
accompany status color (§1 law 3); the five semantic statuses map
1:1 onto the fixed job-state/error vocabularies (succeeded→success;
retry_waiting/queued→info; blocked_manual_review/failed→danger;
warnings/overdue→warning; skipped/cancelled→neutral) — one mapping
table, no per-screen invention.

## 7. Icon catalogue and icon rules

One icon family only — the platform set Odoo 19 ships (FontAwesome +
`oi` glyphs); outline/regular style; 16 px optical grid (20 px in the
lead band); always paired with text or an `aria-label`; never
multicolor; never emoji. **Catalogue (exhaustive for MVP — additions
require a checklist note):**

| Meaning | Icon (FA name) |
| --- | --- |
| Dashboard / health | `gauge` (fallback `tachometer`) |
| Store / connection | `plug` |
| Sync activity / queue | `arrows-rotate` |
| Scheduled/cron | `clock` |
| Error / needs review | `triangle-exclamation` |
| Blocked manual review | `hand` |
| Retry | `rotate-right` |
| Cancel | `xmark` |
| Success/healthy | `check` |
| Products / catalog | `box` |
| Customers | `user` |
| Orders | `file-invoice` |
| Inventory / locations | `warehouse` |
| Fulfillment / tracking | `truck` |
| Matching / binding | `link` |
| Preview / diff | `code-compare` |
| Settings | `gear` |
| Export evidence / logs | `file-lines` |

## 8. Action hierarchy, motion, reduced motion

- **Action hierarchy per screen:** exactly one primary (filled
  accent) action; secondaries are outlined/quiet; destructive actions
  are danger-styled, never primary-positioned, and always confirm
  with a preview of consequences (accepted guard flows). Buttons ≥
  24×24 CSS px targets (WCAG 2.5.8 — captures §13); enqueue-only
  semantics restated (PB-1).
- **Motion durations:** 100 ms (state/hover feedback), 150 ms
  (reveal/collapse), 250 ms (panel/dialog enter) — ease-out;
  nothing longer; no looping/decorative animation; progress
  indication uses the platform spinner + honest text ("Queued —
  checked every 5 min"), never fake progress bars.
- **Reduced motion:** all non-essential transitions collapse to
  instant state changes under `prefers-reduced-motion: reduce`
  (captures §13); spinners remain (they convey state). This is a
  checklist item with a test (§12).

## 9. Dashboard hierarchy (revision of the accepted nine-card grid)

**[Proposed revision of accepted content — Part A §F.1 / DEC-016's
fixed nine-card set — at ChatGPT's review direction; flagged.]** The
nine cards' *information* is preserved; the nine-equal-tiles *layout*
is replaced by a ranked structure:

1. **Lead answer band** (unchanged, dominant): "All systems normal" /
   "3 items need your attention", 1.75 rem, one optional action.
2. **Primary exception & next-action region:** at most three
   exception entries (needs-review, permanently failed, overdue/
   connection), each a sentence + count + one action routing to the
   filtered S4/S5 view. Empty state: one affirmative line — the
   region collapses, it does not show three zeros.
3. **Quieter secondary metrics row:** compact stat chips (not cards)
   for the remaining accepted metrics — per-domain last-sync state,
   retry-waiting, first-push-pending, inventory/fulfillment/matching
   exceptions — 0.875 rem, neutral styling, loud only when non-zero
   in a danger/warning state.
4. **Recent activity** (human-readable timeline, unchanged) +
   honest-freshness cadence line (unchanged).
5. **Restrained trend (optional, one only):** a single small
   activity/failure sparkline over the last 7 days, rendered only
   when ≥ 7 days of data exist, monochrome with status accents —
   included because failure *trend* is a real operator decision input
   (is recovery working?); if ChatGPT judges it vanity, it is
   severable without touching 1–4 (flagged sub-call).

No nine-equally-loud grid; no metric without an action or a state; no
raw timestamps without context; no vanity numbers (lifetime totals,
API call counts) anywhere.

## 10. Responsive behavior and RTL/localization readiness

- Breakpoints follow the platform's; connector rules: the dashboard
  stacks (band → exceptions → chips → activity) on narrow widths with
  no horizontal scroll; tables rely on Odoo's native responsive list
  behavior (optional-column hiding), and every row's primary answer
  (state + identifier) stays visible at 360 px width; Owl surfaces
  must be usable at 768 px (tablet operator) — UAT scenario covers
  375/768/1366 px.
- **RTL/localization:** all strings translatable (standard Odoo
  terms); no direction-dependent CSS (logical properties: start/end,
  not left/right) in connector SCSS; icons that imply direction
  (arrows) are the platform's RTL-aware glyphs; dates/numbers render
  through Odoo locale formatting; copy deck strings avoid
  concatenation (full sentences with placeholders). RTL smoke check
  (Arabic locale) is a §13 checklist row — layout must mirror without
  breakage.

## 11. States: loading, empty, success, error, manual review

Every surface defines all five (accepted rule, made mechanical):
- **Loading:** skeleton lines (not spinners) for regions ≤ 2 s
  expected; spinner + honest text beyond; never a blank region; never
  fake-instant.
- **Empty:** affirmative or guiding — first-run empties always name
  the one next action ("Connect your store to begin").
- **Success:** quiet confirmation (state chip/toast ≤ 3 s); the
  screen's resting state is the confirmation.
- **Error:** reason + fix + owner, in words (accepted error-entry
  contract); technical detail behind one disclosure; retry only where
  the taxonomy allows it.
- **Manual review:** visually distinct from errors (warning family,
  `hand` icon): "waiting on a decision," with the decision affordance
  inline.

## 12. Accessibility rules (acceptance criteria, not aspirations)

1. Keyboard: every action reachable and operable by keyboard (WCAG
   2.1.1); visible focus indicator on every operable element (2.4.7);
   focus order follows the visual hierarchy; Owl surfaces trap focus
   only in dialogs.
2. Contrast: 1.4.3 / 1.4.11 ratios (§6) recorded per token pair at
   the prototype gate.
3. Targets ≥ 24×24 CSS px (2.5.8).
4. Reduced motion honored (§8); no content flashing; auto-updating
   regions (dashboard refresh) are pausable or ≥ 30 s cadence
   (PB-12; WCAG 2.2.2 posture).
5. Semantics: state chips carry text, not color alone; icons have
   labels; custom Owl widgets follow the W3C ARIA APG pattern for
   their role (tabs, dialog — captures §13); tables keep header
   associations.
6. Evidence: an accessibility section in every UI validation record —
   keyboard walkthrough + contrast table + reduced-motion check —
   and UAT scenario 29 (revised UAT plan) can block release on
   failures (severity rules revised accordingly).

## 13. Visual acceptance checklist (run at the prototype gate and at every UI phase review)

| # | Check |
| --- | --- |
| V-1 | One dominant answer per screen; hierarchy budget respected (§3) |
| V-2 | All spacing/type values on-scale (§4); no ad-hoc values in SCSS |
| V-3 | Token-only colors; contrast table recorded, all pairs pass (§6) |
| V-4 | State never by color alone; all five states designed per surface (§11) |
| V-5 | Icon usage within the §7 catalogue and rules |
| V-6 | One primary action per screen; destructive styling + preview (§8) |
| V-7 | Motion within §8 durations; reduced-motion verified |
| V-8 | Responsive at 375/768/1366 px; no horizontal scroll; RTL smoke check |
| V-9 | Keyboard walkthrough recorded; focus visible everywhere |
| V-10 | No vanity metric, raw token, bare timestamp, or stack trace on any primary surface |
| V-11 | Performance: PB-2/3/4/7/8 measured on the phase's surfaces |
| V-12 | Copy matches the accepted voice rules; no "encrypt"/"real-time" claims |

## 14. Screenshot acceptance requirements

Every UI phase validation record ships: full-page screenshots of
every new/changed surface in **each of the five states** (§11) at
1366 px, plus 375 px and 768 px for the phase's primary surfaces,
plus one RTL screenshot of the dashboard, taken on the Odoo.sh
runtime (not local mockups), filenames
`<surface>-<state>-<width>.png` under the validation record's
evidence folder. The visual-design prototype gate (§15) additionally
requires the prototype screens themselves as reviewable artifacts.

## 15. Gating: visual prototype before UI-U1

UI-U1 implementation **remains blocked** until ChatGPT accepts a
visual prototype produced by a dedicated visual-design session (the
locked prompt lives in the revised
`../07-implementation-plan/ui-implementation-phases-packet.md` §7).
That session produces static, self-contained mockups of the §9
dashboard, setup/readiness, matching, and diff/preview surfaces plus
the §6 contrast table — deliberately **not** Odoo code. Because
static HTML/CSS mockups are not Markdown, that session requires
ChatGPT's explicit allowed-files authorization for
`docs/09-ui-prototype/**` (flagged governance call — CLAUDE.md §11
permits only Markdown today; the alternative is image-only mockups
committed as PNG + a Markdown spec, which the prompt supports as its
default so no governance exception is strictly required).

## 16. Register impacts on acceptance

PD-7 (selective-Owl architecture) and the §9 dashboard revision enter
the master plan §1 review calls; DEC-016/AR-023 remain accepted for
everything not named here (surfaces, flows, copy voice, error
contract); `ui-ux-final-design-spec.md` stays the accepted historical
baseline with this document as the dated proposal layer above it
(append-only convention — the spec file is not rewritten);
UI packet, UAT plan, and performance budgets cross-reference this
document (revised the same session).
