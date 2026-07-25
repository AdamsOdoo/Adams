# MVP Role Model Addendum — 2026-07-25

- **Status:** Accepted by product-owner instruction, pending merge of the governance PR.
- **Canonical role model:** This addendum and DEC-041 govern MVP-program work on or descending from `mvp/program-integration`.
- **Historical preservation:** Earlier role records remain in place for provenance but are superseded where they conflict with this addendum.

## Canonical roles

| Role | Actor | Authority and boundary |
| --- | --- | --- |
| Strategic control room | **ChatGPT** | Owns program strategy, scope, sequencing, prompts/rulings, evidence adjudication, acceptance recommendations, and governance records. Does not implement connector code in this role. |
| Implementation worker | **GPT-5.6 Sol / Codex** | Implements authorized code/tests/docs in a real coding workspace, self-validates, commits/pushes, and produces the D2 handoff. Never accepts, ready-marks, or merges its own work. |
| Runtime verifier | **Runtime Claude on Odoo.sh** | Executes exact-SHA Odoo 19/PostgreSQL campaigns and controlled probes; produces the D3 report. Does not publish code, change GitHub state, or claim acceptance. |
| Independent reviewer | **Claude in a separate review session** | Independently reviews the exact diff, source, tests, and runtime evidence at the D7 tier. Does not implement the reviewed change and does not self-accept. |
| Final authority | **Product owner** | Decides commercial scope, accepts explicit risk/deferral, authorizes controlled external resources, and retains final promotion/release authority. |

An actor may be reassigned only by a dated product-owner decision. A session has exactly one role. Tool/environment capability must match the assignment under DEC-041 D4.

## Supersession map

| Record | Preserved meaning | Superseded meaning |
| --- | --- | --- |
| `CHATGPT.md` | ChatGPT control-room guide, evidence discipline, environment separation | Any text making Claude or a worker the strategic control room |
| `CLAUDE.md` §13 | No self-acceptance, independent review, branch/gate safeguards | Claude as default builder for this program; Claude as both default builder and default reviewer |
| `GPT_SOL.md` | Sol orientation and implementation safeguards | Reliance on DEC-032’s Claude-control-room assignment or stale trackers as higher authority than live GitHub/DEC-041 |
| DEC-032 | Macro-wave model, checkpoint protection, Sol worker authority, GitHub durability | Claude as MVP control room and sole wave merge gatekeeper |
| DEC-039 | Claude may be explicitly assigned implementation in a different role/session; no self-acceptance | Claude as standing/default implementation worker |
| DEC-040 | Risk tiers, independent review, consolidated corrections, large coherent batches, runtime rigor | Claude as default builder/reviewer; per-session tier negotiation |
| Issue #167 | Master MVP scope, checkpoint, 23-row program, hard stops | Its original role table naming Claude control room and Sol as the only primary worker |

## Operating sequence

1. ChatGPT issues a capability-matched, tiered authorization.
2. Sol implements and posts the exact push record.
3. Runtime Claude verifies exact SHA where required and the report is preserved durably.
4. Claude independently reviews the exact candidate and evidence.
5. ChatGPT adjudicates gate status; the product owner resolves commercial/risk decisions.
6. A separate authorized closure actor ready-marks/merges only after tracker truth is satisfied.

No role change in this addendum removes a gate or permits self-acceptance.
