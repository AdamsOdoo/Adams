# Traceability matrix — U0 prototype

> Maps every prototype surface and major component to the accepted UI/UX corpus,
> the design-system sections, the state/error contracts it inherits, the new
> proposals that require ChatGPT acceptance, and the future UI phase that would
> implement it. **Proposals are never silently converted into accepted
> requirements** — the “New proposal” column is the list ChatGPT must rule on.
>
> Corpus keys: **DS** = `../03-architecture/premium-ui-ux-design-system.md`;
> **SPEC** = `../02-product/ui-ux-final-design-spec.md`; **NAV** =
> `../02-product/screen-inventory-and-navigation-map.md`; **PB** =
> `../03-architecture/performance-budgets.md`; **PACKET** =
> `../07-implementation-plan/ui-implementation-phases-packet.md`.

## 1. Screens → corpus

| Prototype surface | Accepted surface | Operator flow (NAV §4) | Design-system § | State / error contract | Inherited (accepted) | New proposal (needs acceptance) | Phase |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `dashboard/` command center | **S3** (SPEC §Dashboard; DEC-012 §3; Part A §F.1) | Daily check (flow 2) | DS §9, §3, §11 | 5 states (DS §11); lead answer proportionate | Lead-answer-first; nine cards’ *information*; no-vanity; honest freshness | Ranked §9 layout replacing 9-equal-tile grid; secondary metrics as **chips**; **optional sparkline** (§9.5) | U1 (Owl) |
| `setup-readiness/` connect | **S1** step 3 (SPEC screen 5; DEC-004; MBQ-04) | First run (flow 1) | DS §11 | error = reason+fix+owner; masked, no read-back | Masked entry; no read-back; no “encrypt”; OAuth deferred (DEC-026) | 6-chip compression of the 11 accepted steps | U2 |
| `setup-readiness/` test + readiness | **S1** steps 5–6 (DEC-018 MBQ-06) | First run (flow 1) | DS §11 | must-pass vs good-to-fix; no raw HTTP | Essential-vs-warning split; capability-aware “not applicable”; readiness = read-only jobs | Three-group layout (Action required / Passed / Not applicable) | U2 |
| `matching-center/` | **S6/S8** (DEC-006; DEC-012 §6; Part D §11) | Recovery (flow 3) | DS §2 (selective Owl), §11 | 3 distinct match states; ambiguous ≠ error | Match-key order (email sole auto key); evidence-first; blocking preview; audit | Confidence-in-words; evidence-table layout; 4-decision set; ambiguous-vs-technical-error visual split | U3 (Owl) |
| `product-diff/` | **S7** (DEC-007; Part B §A; Part D §12) | Recovery / catalog | DS §2, §11 | 5-state preview; destructive-write diff | Draft-first; price-SoT gate; protected fields; delete-by-omission highlight | 4-column table layout; ranked-changed/dimmed-unchanged; inline SoT chips | U3 (Owl) |
| `odoo-native-exemplar/` | **S4 + job form** (SPEC screens 8–10; DEC-012 §4) | Daily check / recovery | DS §2 (PD-7) | 5 states; row-level exceptions | S4 list; fixed vocabularies as text; smart buttons; **stays Odoo-native** (PD-7) | Restrained token-layer look on standard views | U1 |

## 2. Components → contracts

| Component | Contract inherited | Design-system § | Notes |
| --- | --- | --- | --- |
| Lead answer band | Part D §7 lead region; text-first (SPEC) | DS §5 (banner), §9.1 | 1.75rem/600; tinted per status; one optional action |
| Exception entry (≤3) | DEC-012 §3 item 10 (one next action) | DS §9.2 | issue + count + why + one action + owner; collapses to affirmative line when empty |
| Secondary metric chip | Part A §F.1 metrics; no-vanity (DEC-012 §3.11) | DS §9.3 | quiet; loud only when non-zero warn/danger |
| Recent-activity timeline + cadence | Part D §7 fused elements; honest freshness (DEC-005) | DS §9.4 | relative time + mechanism; no bare timestamps |
| Sparkline | deferred chart (DEC-016 pt G) reframed as restrained trend | DS §9.5 | **severable proposal** — decision 2 |
| Status chip / owner chip | Part D §17 rules 8–9 (state = word, not color) | DS §6, §1 law 3 | word always present; color reinforces |
| Readiness row (pass/fail/na) | DEC-018 MBQ-06 | DS §11 | fail shows reason+fix+owner |
| Credential field | DEC-004; MBQ-04 posture | SPEC screen 5 | masked; no read-back; never “encrypt” |
| Candidate + evidence table | DEC-006; Part D §11 | DS §11 | confidence in words; ≤1 selected; verdict = word+icon |
| Diff table | Part B §A.16; Part D §12 | DS §11 | Odoo/Shopify/Result + SoT; protected rows; variants |
| Error presentation | Part A §H nine-element contract; 16-class registry | SPEC §Error UX | reason→fix→owner; technical behind one disclosure |
| Design tokens (color/space/type/surface/icon) | DS §4–§8 | DS §4–§8 | token-only; one proposed addition `--sc-border-strong` (decision 3) |

## 3. New proposals requiring ChatGPT acceptance (consolidated)

| # | Proposal | Where | Severability |
| --- | --- | --- | --- |
| P1 | Ranked §9 dashboard layout (replaces 9-equal-tile grid) | dashboard | Core to the prototype |
| P2 | Optional 7-day sparkline | dashboard §9.5 | Severable without touching regions 1–4 |
| P3 | `--sc-border-strong #79839B` + `--sc-border` decorative-hairline exemption | contrast-table §3 | Token-level |
| P4 | 6-chip compression of the 11 accepted wizard steps | setup | Presentation only |
| P5 | Three-group readiness layout (Action required / Passed / Not applicable) | setup | Presentation |
| P6 | Confidence-in-words + evidence-table + 4-decision matching layout | matching | Presentation |
| P7 | 4-column diff layout with inline source-of-truth + protected-field treatment | product-diff | Presentation |
| P8 | Restrained token-layer look on standard Odoo views | native exemplar | Token-level |
| P9 | Inline-SVG icon placeholders standing in for §7 FontAwesome glyphs | all | Implementation detail (U1 uses real FA) |
| P10 | Mobile reflow rules (stacked comparison cards; optional-column hiding) | matching / diff / native | Responsive behavior |

## 4. Phase gating (all CLOSED — this matrix authorizes nothing)

- **U0 (this session):** design artifacts only. Produces the prototype + this
  matrix. No Odoo code.
- **U1:** dashboard (Owl), sync/error centers, logs, settings, roles — standard
  Odoo views + the one dashboard Owl surface. Requires Area 6 + SEC-1 merged
  **and the U0 prototype accepted**. **CLOSED.**
- **U2:** setup wizard + readiness (Owl presentation). **CLOSED.**
- **U3:** matching centers, product diff/preview, domain screens (Owl per PD-7).
  **CLOSED.**

No proposal above is accepted by producing this matrix; each is a ChatGPT
decision (see `README.md`).
