# UI restructure implementation evidence — 2026-08-02

> **Evidence discipline.** This record contains only commands and results that
> actually ran. GitHub Actions is supporting evidence, not an Odoo.sh gate.
> No live Shopify mutation is authorized or claimed by this mission.

## Mission identity

| Item | Exact value |
| --- | --- |
| Repository | `AdamsOdoo/Adams` |
| Required base branch | `fable/wave-5-completion` |
| Required base SHA | `49cfffbd5ff0eca85d2b855d9ebd2e414680af8e` |
| Working branch | `codex/ui-restructure-implementation` |
| Signed-contract provenance commits on this branch | `971e6ed` (audit + contract capture); `55ffb6f` (product-owner sign-off + mission prompt) |
| Draft PR | Not opened yet |
| Native Odoo.sh exact-head campaign | Not run in this environment |
| Live Shopify calls or mutations | Not run |

## Batch 0 — signed design delta and implementation wireframes

**Scope.** Align the premium UX specification and prototype notes to C1, C4,
C5, C6, and C7 before production code: four-pillar navigation, distinct Sales
and Connector Health pages, five onboarding phases over twelve durable steps,
recoverable mode-switch panel, export acknowledgement component, shared states,
responsive/RTL/accessibility constraints, and visible-action consequence copy.

**Scope commit.** `bf8d80a08dd62ef18405373dc045bc74dffc8ce9`
(`docs(ui): lock restructure delta and screen wireframes`).

**Commands and results.** All commands ran from the repository root at the
scope commit's worktree state before commit:

| Command | Real result |
| --- | --- |
| `python3 -c '<relative Markdown-link existence checker>'` over the four Batch 0 files | `checked 4 Markdown files; missing local links: 0`; exit 0 |
| `rg -F -q` contract-term loop for the four pillars, both dashboard names, review disclosure, mode fields, stale state, and five onboarding phases | All required terms found; exit 0 |
| `git diff --cached --check` | Exit 0; no whitespace errors |
| `python3 -c '<12-condition C1/C2/C3/C4/C5/C6/C7/UI/action-effect assertion set>'` | `Batch 0 contract-adversarial checks: 12/12 passed`; exit 0 |

**CI.** Not run yet.

**Adversarial pass.** The pass challenged the most likely documentation
regressions: leaving the old seven/eight-peer IA apparently authoritative;
mixing health with sales; hiding Configuration from the contract rather than
making it Administrator-only; dropping a durable onboarding step behind the
five-phase presentation; equating Accepted with Verified; omitting stale-job
mode recovery; combining currencies; and omitting mobile/RTL/action-consequence
states. The 12-condition assertion set passed. The old IA is retained only as
clearly superseded provenance behind a prominent signed-delta link. No rendered
browser run was performed or claimed because this batch contains low-fidelity
Markdown wireframe notes rather than HTML/CSS production or prototype changes.

**Revert boundary.** Revert the single Batch 0 scope commit after the two signed
provenance commits; it contains documentation and wireframe notes only.

**Deviations.** None currently recorded.
