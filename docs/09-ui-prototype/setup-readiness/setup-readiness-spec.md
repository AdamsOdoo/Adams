# Screen spec — Setup & readiness (S1)

> **Status: Accepted U0 visual baseline** (control-room comment `4951204357`,
> 2026-07-12; merged via **PR #152** into `Shopify-connector` at merge commit
> `65e915aada32930a19a14c94d23dc9bd5e6fb517`). History preserved — gate
> `4948902516` → reviews `4950255482`, `4950432754` → acceptance `4951204357`.
> **Implementation remains separately gated** — UI-U1/U2/U3 stay CLOSED and this
> spec authorizes no code. Inherits S1 / DEC-012
> §1 / Part A §E / the DEC-018 MBQ-06 essential-vs-warning split and the
> MBQ-04 credential posture from
> `../../02-product/ui-ux-final-design-spec.md`. Source: `setup-readiness.html`.
> Copy illustrative (MBQ-22).

## Purpose
Take an admin from a pasted token to a **proven** connection, then to a
readiness result that says exactly what (if anything) still blocks first sync.
Trust is built by proving, not promising.

## Sub-surfaces & states rendered
| Surface / state | File |
| --- | --- |
| Connect — token paste | `setup-connect-1366.png` |
| Test connection — success | `setup-test-success-1366.png` |
| Test connection — failure | `setup-test-fail-1366.png` |
| Readiness — loading | `setup-readiness-loading-1366.png` |
| Readiness — all pass (Continue enabled) | `setup-readiness-pass-1366.png` (+ `-768`, `-375`) |
| Readiness — action required (Continue blocked) | `setup-readiness-action-1366.png` |

The five canonical states map as: **loading** = readiness-loading; **empty** =
the fresh masked credential field; **success** = test-success / readiness-pass;
**error** = test-fail / readiness-action; **manual review** = n/a for setup
(setup has no reviewer queue — stated, not invented).

## Hierarchy
A compressed 6-step indicator (Store · Credentials · Test · Readiness · Domains ·
Review) sits above one centered content column with a single dominant action per
step. Each step closes on an explicit “verified/saved” moment. On the connect
step, **“Step 2 of 6” and “Credentials” are the current step** (verified by the
source-to-render check). At ≤ 900px the app bar uses the **compact Odoo-native
shell** (☰ Menu + current section + persistent health); `setup-readiness-pass`
is rendered at 768px and 375px on that shell.

## Credential honesty rules (binding — MBQ-04)
- One masked field; the value is **never read back** on any surface, for any
  role. The prototype shows masked dots representing the just-entered token.
- Helper copy: *“stored with restricted access and shown only once — never
  displayed again.”* The word **“encrypt” appears nowhere** (grep evidence in
  `../README.md`).
- **OAuth** is shown only as a clearly **deferred future option** (“Available in
  a future release”), never as an available MVP flow (DEC-026).

## Readiness results (DEC-018 MBQ-06)
Rows are grouped into three headed groups:
- **Action required** (must-pass failures) — rendered first;
- **Passed** (must-pass + verified);
- **Not applicable** (capability-aware skips, e.g. inventory location mapping
  when inventory is off, webhook secret when scheduled sync is the trigger —
  matching the merged CORE-R1 capability-aware behavior, not invented).

Every failed check shows **reason + corrective action + responsible owner**
(`.sc-ready__fix` + owner chip). No raw API response, no HTTP code, no stack
trace. **Continue** is `aria-disabled` until all must-pass rows pass — the
disabled reason is stated in words.

## Tokens
Success/warning/danger/neutral families for band and check rows; `--sc-accent`
for the one primary; `--sc-border-strong` for the input and secondary buttons;
step numbers use success tint (done) / accent (current) / neutral (todo).

## Accessibility
Step indicator exposes `aria-current="step"`; the credential input is labelled
with `aria-describedby` helper; failed checks associate reason/fix with the row;
run completion announced via `aria-live`. See
`../accessibility/keyboard-and-focus-notes.md` §2.

## Performance (mapped)
PB-1 test/readiness run is enqueue-then-report (`setup_readiness_check` jobs,
read-only); the screen never blocks on a synchronous network call.

## Proposed vs inherited
- **Inherited:** the 11 accepted steps, the essential-vs-warning split, the
  credential posture, OAuth-deferred, no-raw-error rule.
- **Proposed:** the 6-chip compression of the accepted 11 steps (grouping only —
  no step added/removed/reordered); the three-group readiness layout; the
  “Not applicable” group as a first-class, capability-aware outcome.
