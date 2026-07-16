# Screen spec — Stores (list & detail)

> **Status: Proposed — Fable gap-closure mission, 2026-07-16.** Prototype
> extension of the accepted U0 visual baseline (README §6); design artifact
> only — **no implementation is authorized** and UI-U1/U2/U3 stay CLOSED.
> Source: `stores.html` (+ `../assets/prototype.css`). Copy is illustrative
> (MBQ-22). Uses the **two-role model** (Connector User / Connector
> Administrator) per
> [`../../docs/02-product/connector-roles-and-permissions.md`](../../02-product/connector-roles-and-permissions.md)
> — itself Proposed, not accepted.

## Purpose

One surface answering, per store: *what state is this connection in, is it
healthy, and what lifecycle action (if any) is available to me?* The list is
the fleet overview; the detail is the lifecycle cockpit for one store.

## Primary role

- **Connector Administrator** — sees and performs lifecycle actions
  (reconnect, disconnect, resume setup, replace token). Store lifecycle and
  credentials are Administrator-only capabilities (roles doc §1.2).
- **Connector User** — same surface, read-only: no Reconnect/Disconnect
  buttons; the header shows a "View only" chip; the credential card has no
  Replace action. Gating remains server-side; UI hiding is convenience.

## Data shown

- **Lifecycle state** — exactly the five shipped states
  (`setup_incomplete` / `connected` / `reconnect_needed` / `disconnecting` /
  `disconnected` — [Fact — repo], restated in
  [`reconnect-catchup-backfill-policy.md`](../../02-product/reconnect-catchup-backfill-policy.md)
  PD-RB-3: catch-up adds **no new lifecycle state**). Raw tokens are never
  shown; the badge words are "Setup incomplete", "Connected",
  "Reconnect needed", "Disconnecting", "Disconnected".
- **Health strip** — API health, webhook readiness, last readiness run
  (relative freshness, honest wording).
- **Connection generation** — the monotonic epoch chip (e.g. `#7`), bumped
  on activate / reconnect / disconnect request / credential mutation
  ([Fact — repo], reconnect policy §2 step 5).
- **Capability chips** — enabled domains per store (Products, Customers,
  Orders, Inventory, Fulfillment incl. its operating mode).
- **Quick stats** — bound products/customers, orders this week, open review
  items (counts only, no vanity metrics).
- **Credential card** — masked token (no read-back for any role — DEC-004
  posture), last-verified timestamp, Replace action (Administrator only).
- **Quiescence progress** (disconnecting state) — open-lease count, oldest
  admitted-work timer, and the bounded 15-minute quiescence timeout
  (admission-lease design,
  [`disconnect-quiescence-remediation-analysis.md`](../../03-architecture/disconnect-quiescence-remediation-analysis.md)
  §10: `disconnect_open_lease_count` + `disconnect_oldest_admitted_at`,
  timeout ⇒ `timed_out`, never silent).

## Actions per role

| Action | Connector User | Connector Administrator |
| --- | --- | --- |
| View list / detail / readiness / stats | Yes | Yes |
| Re-run readiness | Yes (permitted verification read) | Yes |
| Resume setup | No | Yes |
| Reconnect | No | Yes (verify → readiness → new generation → fresh scans; no job replay — PD-RB-1/2) |
| Disconnect | No | Yes — always via the confirmation drawer |
| Replace credential | No | Yes (starts fresh verification; stored value never displayed) |

The disconnect drawer states, in plain language, the three quiescence facts:
(1) no new work admitted, (2) in-flight work finishes within the 15-minute
bound while the store shows *Disconnecting*, (3) everything is preserved and
reconnect is always possible. Destructive button is danger-styled and never
primary-positioned.

## States rendered (gallery order)

| State | What it proves |
| --- | --- |
| Store list | All five lifecycle badges across five cards; health strip, generation chip, capability chips, quick stats; only the warning card carries a loud accent. |
| Detail — connected healthy | Success band; Administrator lifecycle actions; readiness panel; masked credential card with Replace; quick stats. |
| Detail — Connector User read-only | Identical data; no lifecycle buttons; "View only" owner chip; credential card without Replace. |
| Detail — reconnect needed | Warning band with cause + reassurance (history preserved) + one primary action (Reconnect…); catch-up behavior stated honestly. |
| Disconnect confirmation drawer | The quiescence explainer; Cancel is secondary, Disconnect is danger. |
| Detail — disconnecting | Info band; open-lease count (2), oldest-admitted timer, 15-minute timeout countdown, new generation `#9`; honest "not instant" line. |
| Detail — disconnected | Neutral band; calm data-preserved notice; single Reconnect CTA; on-reconnect sequence spelled out. |
| Detail — setup incomplete | Onboarding empty state with a **CSS-only welcome illustration** and the 6-chip wizard steps; Resume setup CTA. |

**Illustration policy note.** Decorative/3D illustration is permitted **only**
on education, onboarding, and empty states (the setup-incomplete card here);
operational screens (list, connected/reconnect/disconnecting/disconnected
details) stay illustration-free. The welcome graphic is pure CSS (tinted disc
+ bordered shapes), `aria-hidden`, and severable.

## Tokens used

Semantic families per state: connected → success; reconnect_needed → warning;
disconnecting → info; disconnected → neutral; setup_incomplete → info.
Type: `--sc-fs-lead` band answers, `--sc-fs-cardtitle` card titles,
`--sc-fs-secondary` meta, `--sc-fs-caption` owner chips. Generation and
counters use `.sc-mono` (tabular numerals). Cards: radius 8, 1px
`--sc-border`, no resting shadow; the drawer is the only elevated surface
(`.sc-dialog`). Masked token uses `.sc-input--mask` letter-spacing.

## Accessibility

- Lifecycle state is always a **word** in a `.sc-status` chip; color only
  reinforces (WCAG 1.4.1).
- The confirmation drawer is `role="dialog"` `aria-modal="true"` with a
  labelled heading; destructive action is last in focus order.
- The quiescence spinner respects `prefers-reduced-motion` (stylesheet rule).
- Read-only variant announces itself via the visible "View only" chip, not
  disabled ghost buttons.
- Compact mobile shell (≤ 900px) and logical-property RTL mirroring are
  inherited from the shared stylesheet.

## Traceability

- Lifecycle states + generation + historic-job preservation:
  [Fact — repo] via
  [`reconnect-catchup-backfill-policy.md`](../../02-product/reconnect-catchup-backfill-policy.md)
  §2 (steps 1–8) and PD-RB-1/2/3 [Proposed].
- Quiescence lease counters + bounded timeout:
  [`disconnect-quiescence-remediation-analysis.md`](../../03-architecture/disconnect-quiescence-remediation-analysis.md)
  §10 (committed admission-lease, `disconnect_open_lease_count`,
  `disconnect_oldest_admitted_at`, `DISCONNECT_QUIESCE_TIMEOUT`). The
  15-minute figure is the design bound used illustratively here.
- Role gating (lifecycle/credentials Administrator-only; User read-only):
  [`connector-roles-and-permissions.md`](../../02-product/connector-roles-and-permissions.md)
  §1.1/§1.2 [Proposed product decision].
- Credential posture (masked, no read-back, no "encrypt" wording): accepted
  DEC-004 / U0 baseline.
- Reconnect banner reassurance language: Flow 2/9 skeleton + reconnect
  policy §8 [Recommendation].
- Capability/edition context: [`mvp-capability-map.md`](../../02-product/mvp-capability-map.md).
