# V2 Evidence Ledger

This directory holds machine-readable and human-reviewable evidence for the continuous
V2 implementation. Evidence is additive and truthful: an unavailable runtime measure is
`null`/`pending`, never `0`, inferred or promoted to acceptance.

## P00 baseline identity

| Item | Frozen identity |
| --- | --- |
| V1 implementation source | PR #210 head `f77bfcc25e63615e6226dd9a9329f8f943593cb2` |
| V2 approved blueprint source | PR #211 head `3914004e27630b09b211e3d2ee92a8e6d9a0e55e` |
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

## Reproduction

```bash
python3 -m unittest tools.tests.test_v2_repository_baseline -v
python3 tools/v2_repository_baseline.py \
  --source-ref f77bfcc25e63615e6226dd9a9329f8f943593cb2
python3 tools/v2_repository_baseline.py --source-ref HEAD --check
python3 tools/validate_shopify_graphql.py
```

Two consecutive clean generations must have identical SHA-256 digests. `--check` ignores
only provenance ref/SHA fields; any surface drift still fails and requires an intentional
evidence update in the same reviewed change.

## P00 repository-check result

- analyzer unit tests: 4 passed;
- deterministic generation: two consecutive runs produced identical file digests;
- compatibility self-check at the implementation head: passed;
- declared model classes: 156;
- literal Shopify GraphQL operations: 42;
- registered browser tours: 42;
- production addon dependency cycles: 0;
- production cross-addon Python import occurrences: 65, to be classified in P01;
- database/restore/performance acceptance: not yet claimed.

No generated artifact contains credentials, Shopify payloads or merchant PII.
