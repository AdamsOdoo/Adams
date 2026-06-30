# Architecture Review Log

> Tracks architecture discussions **before** they become finalized decision
> records. An entry here is a proposal under review (typically reviewed by
> ChatGPT), not a commitment. Accepted proposals are promoted to an ADR in
> [`../04-decisions/`](../04-decisions/) and linked back here.

## How to use

1. Add a row when an architectural approach is proposed or debated.
2. **Review decision** vocabulary: `accepted` / `accepted with minor
   corrections` / `revise` / `reject`.
   - `reject` → also log in
     [`rejected-approaches-log.md`](./rejected-approaches-log.md).
   - `accepted` → create an ADR (`../04-decisions/`) and put the link in
     **Follow-up action**.
3. **Evidence required** must name concrete proof needed (a Shopify/Odoo
   capability, a competitor behaviour, a benchmark) before acceptance. Do not
   accept while required evidence is missing.
4. **Status** values: `Proposed`, `Under review`, `Evidence pending`,
   `Accepted → ADR`, `Rejected`, `Deferred`.

> Read this log **before finalizing any design** so prior outcomes are not
> re-litigated or contradicted.

---

## Log

| ID | Date | Topic | Proposed approach | Review decision | Reason | Evidence required | Risks | Follow-up action | Status |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| _AR-000_ | _YYYY-MM-DD_ | _e.g. Sync orchestration model_ | _Short description_ | _accepted/revise/reject_ | _Why_ | _Proof needed_ | _Key risks_ | _ADR link / next step_ | _Proposed_ |
| AR-001 | 2026-06-30 | Governance foundation branch | Use the Research Sprint A branch (`docs/research-sprint-a-governance-inventory`) as the canonical governance foundation | Accepted after revision patch | It defers active skills/agents and preserves the no-code, research-first gate | n/a — governance/process decision | Branch divergence if the earlier `claude/odoo-shopify-research-setup-fs4wzi` branch is reused | Do not continue from the old branch; treat it as non-canonical unless ChatGPT explicitly reopens it | Accepted |

_AR-001 is a governance/process decision (not a product-architecture choice);
it is recorded here because it concerns the canonical foundation all later
architecture work builds on. No product-architecture proposals are logged yet —
that work is gated until research is sufficient and ChatGPT approves (see
`CLAUDE.md` §4–§5)._
