# Technical Debt Register

> **No technical debt should be silently accepted.** Every shortcut, compromise,
> deferred hardening, or "good enough for now" decision is recorded here with
> its risk and a target resolution phase.

## How to use

1. Add a row whenever a compromise is knowingly accepted.
2. **Severity** values: `Low`, `Medium`, `High`, `Critical`.
3. **Reason accepted temporarily** must be honest (deadline, missing evidence,
   scope boundary) — not a justification that hides risk.
4. **Target resolution phase** ties the debt to a phase in
   [`../07-implementation-plan/`](../07-implementation-plan/) or a future
   session, so it cannot be forgotten.
5. **Status** values: `Open`, `Scheduled`, `In progress`, `Resolved`,
   `Accepted (won't fix)` — the last requires a linked decision record.

---

## Register

| ID | Date added | Area | Description | Severity | Reason accepted temporarily | Risk | Owner | Target resolution phase | Status |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| _TD-000_ | _YYYY-MM-DD_ | _e.g. Sync engine_ | _What the debt is_ | _Low/Med/High_ | _Why now_ | _What could go wrong_ | _Who owns it_ | _Phase / session_ | _Open_ |

_No technical debt recorded yet (Research Sprints A–C — no code written). This
register becomes active as design and implementation introduce trade-offs._

_**Research Sprint C note (2026-06-30):** none. Sprint C was research-only
(competitor deep dives, matrix, UX benchmark, patterns, gaps, avoid-list) — no
code, no module, no shortcuts. The blocked sources (R2 Teqstars docs 403, R5
Google Doc) are **research gaps**, tracked in
[`../01-research/resource-inventory.md`](../01-research/resource-inventory.md) and
the handoff, **not** technical debt._
