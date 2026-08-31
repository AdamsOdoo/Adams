# V2 Evidence Ledger

This directory holds machine-readable and human-reviewable evidence for the continuous
V2 implementation. Evidence is additive and truthful: an unavailable runtime measure is
`null`/`pending`, never `0`, inferred or promoted to acceptance.

## P00 baseline identity

| Item | Frozen identity |
| --- | --- |
| V1 implementation source | PR #210 head `f77bfcc25e63615e6226dd9a9329f8f943593cb2` |
| V2 approved blueprint source | PR #211 head `3914004e27630b09b211e3d2ee92a8e6d9a0e55e` |
| Current exact source checkpoint | `880e70088922eb10dd44426678d578ee4ee7a73a` |
| Implementation branch | `codex/v2-continuous-implementation` |
| Protected branches/PRs modified | none |
| Shopify/Odoo external effects for this checkpoint | none |

The implementation branch starts from the latest V1 release-candidate code, then carries
the approved V2 blueprint as documentation-only commits. This avoids silently rebuilding
from the older `Shopify-connector` integration pointer and losing the V1 safety, domain,
test and migration work that exists in PR #210. PR #210 and PR #211 remain independently
reviewable and unmodified.

## Artifact status

| Artifact | Current evidence | Completion condition |
| --- | --- | --- |
| `compatibility-baseline.json` | Frozen repository surface | deterministic check plus runtime registry comparison |
| `dependency-graph.json` | Frozen manifest, production/test import and XML-reference graph | P01 boundary classifications and enforced allowed graph |
| `shopify-operation-inventory.json` | Frozen literal GraphQL and transport-call inventory | manual/runtime linkage of each mutation to certainty/readback policy |
| `ui-task-baseline.md` | Frozen menus, actions, components and browser tours | rendered reachability/state evidence and U1–U14 completion |
| `database-profile.json` | Repository expectations; runtime fields pending | isolated fresh/warm database, backup/restore and identity proof |
| `performance-baseline.json` | Existing scenarios and V2 budgets; runtime fields pending | Tiny and CI-target measurements with environment provenance |
| `journey-baseline.json` | U1–U14 actors, triggers, fixtures, effects, UI and recovery contract | every assertion axis passes on one exact candidate SHA |
| `setup-compatibility-baseline.json` | Twelve durable keys, V1/V2 presentation projections and legacy numeric bridge | resume/insert/reorder/stale-activation fixtures pass without persisted-state rewrite |
| `official-guideline-refresh-2026-08-30.md` | Current Shopify 2026-07/webhook and Odoo 19 implementation obligations from primary sources | every obligation is traced to a P01–P17 contract/test and refreshed at candidate freeze |
| `odoo-apps-packaging-2026-08-30.md` | Odoo Apps repository-registration, manifest, dependency, archive-root, presentation, and unresolved multi-root-ZIP findings (official sources, access date 2026-08-30) | owner-authorized publisher-flow validation and Odoo confirmation of archive/listing treatment |

## Reproduction

```bash
python3 -m unittest tools.tests.test_v2_repository_baseline -v
python3 tools/v2_repository_baseline.py \
  --source-ref 880e70088922eb10dd44426678d578ee4ee7a73a
python3 tools/v2_repository_baseline.py --check
python3 tools/validate_shopify_graphql.py
```

Two consecutive clean generations must have identical SHA-256 digests. `--check` ignores
only provenance ref/SHA fields; any surface drift still fails and requires an intentional
evidence update in the same reviewed change.

## P00 repository-check result

- complete dependency-free source/policy suite: 448 passed;
- deterministic generation: two consecutive runs produced identical file digests;
- compatibility self-check against the exact source tree at `880e7008`: passed;
- declared model classes: 211;
- literal Shopify GraphQL operation documents: 48, all uniquely named and schema-valid
  against Admin API `2026-07`;
- P01 gate: every named document must be owned by exactly one typed operation spec;
- registered browser tours: 42;
- the frozen combined cross-addon graph catalogs 0 cycles and 128 production import
  occurrences; all seven V2 package-direction policies pass. Odoo registry/runtime proof is
  still required before treating the repository-derived result as full runtime qualification;
- database/restore/performance acceptance: not yet claimed.

No generated artifact contains credentials, Shopify payloads or merchant PII.
