# Contrast table — WCAG 2.2 SC 1.4.3 (text) and SC 1.4.11 (non-text)

> **Status: U0 prototype evidence. Proposed. NOT accepted.** Every ratio below
> is **computed**, not asserted. Method: WCAG 2.x relative-luminance formula
> (sRGB → linearized channels → `L = 0.2126R + 0.7152G + 0.0722B`; contrast
> `= (L_light + 0.05) / (L_dark + 0.05)`). Tokens are the accepted design-system
> proposals in `../../03-architecture/premium-ui-ux-design-system.md` §6, with a
> single U0-proposed addition (`--sc-border-strong`) explained in §3 below.
>
> Thresholds: **SC 1.4.3** normal text ≥ 4.5:1, large text (≥ 18.66px bold or
> ≥ 24px) ≥ 3:1; **SC 1.4.11** meaningful UI-component boundaries / graphical
> objects ≥ 3:1.

## 1. Token values used in the prototype

| Token | Hex | Role |
| --- | --- | --- |
| `--sc-text-primary` | `#1F2937` | primary text |
| `--sc-text-secondary` | `#475467` | secondary / meta text |
| `--sc-surface-0` | `#F8FAFC` | page background |
| `--sc-surface-1` | `#FFFFFF` | card / control surface |
| `--sc-border` | `#E4E7EC` | decorative grouping hairline (see §3) |
| `--sc-border-strong` | `#79839B` | **U0 PROPOSED** — interactive control boundary |
| `--sc-accent` / `--sc-focus` | `#175CD3` | links, primary button, focus ring |
| `--sc-success-text` / `--sc-success-bg` | `#067647` / `#ECFDF3` | healthy / succeeded |
| `--sc-warning-text` / `--sc-warning-bg` | `#B54708` / `#FFFAEB` | attention / retry-waiting / overdue |
| `--sc-danger-text` / `--sc-danger-bg` | `#B42318` / `#FEF3F2` | failed / blocked / destructive |
| `--sc-info-text` / `--sc-info-bg` | `#175CD3` / `#EFF8FF` | neutral activity / in-progress |
| `--sc-neutral-text` / `--sc-neutral-bg` | `#475467` / `#F2F4F7` | skipped / cancelled / disabled |

## 2. Computed pairs

| Foreground | Background | Hex fg / bg | Ratio | Threshold | SC | Result | Use |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `--sc-text-primary` | `--sc-surface-1` | #1F2937 / #FFFFFF | **14.68:1** | 4.5:1 | 1.4.3 | ✅ PASS | Body / primary text on card |
| `--sc-text-primary` | `--sc-surface-0` | #1F2937 / #F8FAFC | **14.03:1** | 4.5:1 | 1.4.3 | ✅ PASS | Body / primary text on page |
| `--sc-text-secondary` | `--sc-surface-1` | #475467 / #FFFFFF | **7.69:1** | 4.5:1 | 1.4.3 | ✅ PASS | Secondary & meta text on card |
| `--sc-text-secondary` | `--sc-surface-0` | #475467 / #F8FAFC | **7.35:1** | 4.5:1 | 1.4.3 | ✅ PASS | Secondary & meta text on page |
| `--sc-accent` | `--sc-surface-1` | #175CD3 / #FFFFFF | **5.99:1** | 4.5:1 | 1.4.3 | ✅ PASS | Link / quiet-button label on card |
| `--sc-accent` | `--sc-surface-0` | #175CD3 / #F8FAFC | **5.72:1** | 4.5:1 | 1.4.3 | ✅ PASS | Link on page |
| `--sc-white` | `--sc-accent` | #FFFFFF / #175CD3 | **5.99:1** | 4.5:1 | 1.4.3 | ✅ PASS | Primary-button label (white on accent) |
| `--sc-success-text` | `--sc-success-bg` | #067647 / #ECFDF3 | **5.40:1** | 4.5:1 | 1.4.3 | ✅ PASS | Status word on success tint |
| `--sc-success-text` | `--sc-surface-1` | #067647 / #FFFFFF | **5.69:1** | 4.5:1 | 1.4.3 | ✅ PASS | Success text/icon on white |
| `--sc-warning-text` | `--sc-warning-bg` | #B54708 / #FFFAEB | **5.20:1** | 4.5:1 | 1.4.3 | ✅ PASS | Status word on warning tint |
| `--sc-warning-text` | `--sc-surface-1` | #B54708 / #FFFFFF | **5.43:1** | 4.5:1 | 1.4.3 | ✅ PASS | Warning text/icon on white |
| `--sc-danger-text` | `--sc-danger-bg` | #B42318 / #FEF3F2 | **6.05:1** | 4.5:1 | 1.4.3 | ✅ PASS | Status word on danger tint |
| `--sc-danger-text` | `--sc-surface-1` | #B42318 / #FFFFFF | **6.57:1** | 4.5:1 | 1.4.3 | ✅ PASS | Danger text/icon on white |
| `--sc-info-text` | `--sc-info-bg` | #175CD3 / #EFF8FF | **5.57:1** | 4.5:1 | 1.4.3 | ✅ PASS | Status word on info tint |
| `--sc-info-text` | `--sc-surface-1` | #175CD3 / #FFFFFF | **5.99:1** | 4.5:1 | 1.4.3 | ✅ PASS | Info text/icon on white |
| `--sc-neutral-text` | `--sc-neutral-bg` | #475467 / #F2F4F7 | **6.98:1** | 4.5:1 | 1.4.3 | ✅ PASS | Status word on neutral tint |
| `--sc-neutral-text` | `--sc-surface-1` | #475467 / #FFFFFF | **7.69:1** | 4.5:1 | 1.4.3 | ✅ PASS | Neutral text on white |
| `--sc-text-primary` | `--sc-success-bg` | #1F2937 / #ECFDF3 | **13.92:1** | 4.5:1 | 1.4.3 | ✅ PASS | Lead-band sentence on success tint |
| `--sc-text-primary` | `--sc-warning-bg` | #1F2937 / #FFFAEB | **14.07:1** | 4.5:1 | 1.4.3 | ✅ PASS | Lead-band sentence on warning tint |
| `--sc-text-primary` | `--sc-danger-bg` | #1F2937 / #FEF3F2 | **13.50:1** | 4.5:1 | 1.4.3 | ✅ PASS | Lead-band sentence on danger tint |
| `--sc-text-primary` | `--sc-info-bg` | #1F2937 / #EFF8FF | **13.66:1** | 4.5:1 | 1.4.3 | ✅ PASS | Lead-band sentence on info tint |
| `--sc-text-primary` | `--sc-neutral-bg` | #1F2937 / #F2F4F7 | **13.32:1** | 4.5:1 | 1.4.3 | ✅ PASS | Text on neutral tint |
| `--sc-text-primary` | `--sc-surface-0` | #1F2937 / #F8FAFC | **14.03:1** | 3.0:1 | 1.4.3 (large) | ✅ PASS | 1.75rem/600 dominant answer on page |
| `--sc-danger-text` | `--sc-danger-bg` | #B42318 / #FEF3F2 | **6.05:1** | 3.0:1 | 1.4.3 (large) | ✅ PASS | Large lead answer, danger, on tint |
| `--sc-warning-text` | `--sc-warning-bg` | #B54708 / #FFFAEB | **5.20:1** | 3.0:1 | 1.4.3 (large) | ✅ PASS | Large lead answer, warning, on tint |
| `--sc-border-strong` | `--sc-surface-1` | #79839B / #FFFFFF | **3.80:1** | 3.0:1 | 1.4.11 | ✅ PASS | Input / control boundary on white |
| `--sc-border-strong` | `--sc-surface-0` | #79839B / #F8FAFC | **3.63:1** | 3.0:1 | 1.4.11 | ✅ PASS | Input / control boundary on page |
| `--sc-accent` | `--sc-surface-1` | #175CD3 / #FFFFFF | **5.99:1** | 3.0:1 | 1.4.11 | ✅ PASS | Focus ring & primary-button boundary on white |
| `--sc-success-text` | `--sc-success-bg` | #067647 / #ECFDF3 | **5.40:1** | 3.0:1 | 1.4.11 | ✅ PASS | Status icon (non-text) on success tint |
| `--sc-warning-text` | `--sc-warning-bg` | #B54708 / #FFFAEB | **5.20:1** | 3.0:1 | 1.4.11 | ✅ PASS | Status icon on warning tint |
| `--sc-danger-text` | `--sc-danger-bg` | #B42318 / #FEF3F2 | **6.05:1** | 3.0:1 | 1.4.11 | ✅ PASS | Status icon on danger tint |
| `--sc-info-text` | `--sc-info-bg` | #175CD3 / #EFF8FF | **5.57:1** | 3.0:1 | 1.4.11 | ✅ PASS | Status icon on info tint |

**All 32 evaluated pairs pass their threshold: YES.**

## 3. The one proposed token adjustment — `--sc-border-strong`

The accepted design system (§6) defines a single hairline token
`--sc-border: #E4E7EC`. That value is **1.24:1 on white** — far below the 3:1
required by SC 1.4.11 **for a meaningful component boundary**. Rather than
darken every hairline (which would make the calm, low-contrast grouping style
heavier than the design intends), U0 proposes **splitting the boundary role in
two**:

- **`--sc-border` (`#E4E7EC`, unchanged)** — used **only** for *decorative
  grouping separators*: the resting outline of non-interactive cards, table
  row rules, and section dividers. These are not the sole means of identifying
  a control or its state, so SC 1.4.11 does not require 3:1 for them (1.4.11
  governs "user-interface components" and "graphical objects required to
  understand the content", not decorative boundaries). This is recorded as an
  explicit design position for ChatGPT to accept.
- **`--sc-border-strong` (`#79839B`, PROPOSED NEW)** — used for **interactive
  control boundaries**: text-input borders, unfocused segmented/secondary
  buttons, the candidate radio, and the search field. Computed **3.80:1 on
  white and 3.63:1 on the page** — both clear SC 1.4.11.

**Original value considered and rejected:** a first pass used `#98A2B3`
(2.58:1 on white) — recorded here as failing, replaced by `#79839B`.

Focus is drawn with `--sc-focus` = `--sc-accent` `#175CD3` (**5.99:1** on white),
comfortably above the 3:1 focus-indicator bar, and is applied as a 2px
`:focus-visible` outline with a 2px offset on every operable element.

## 4. Surfaces affected by the proposal

`--sc-border-strong` is applied in `assets/prototype.css` to: `.sc-input`,
`.sc-btn` / `.sc-btn--secondary`, `.sc-search`, `.sc-candidate__radio`,
`.sc-step__num`, `.sc-diff th` bottom rule, `.sc-list th` bottom rule, and the
breadcrumb separator glyph. `--sc-border` remains on `.sc-card`, `.sc-band`,
`.sc-exception`, `.sc-chip`, list/table row rules, and section dividers.

## 5. Decision required from ChatGPT

1. Accept the `--sc-border`/`--sc-border-strong` split, **or** direct a single
   stronger hairline everywhere (heavier look), **or** keep `#E4E7EC`
   everywhere and record the decorative-boundary 1.4.11 exemption as accepted.
2. Accept `#79839B` as the interactive-boundary value (or supply a preferred
   token that also computes ≥ 3:1 on both `#FFFFFF` and `#F8FAFC`).

All other proposed hexes pass unchanged — **no other token adjustment is
required for contrast.**
