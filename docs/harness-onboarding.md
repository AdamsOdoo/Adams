> **Superseded on 25 September 2026.** Development now uses odoo-harness 1.2.1 installed in this repository (see the top of AGENTS.md; pin `176f07317e5a6cd8cd9b769d7ebd3d99eca34bd1`). This page and the external-toolkit adapter are kept for provenance only.

# Adams development harness — ready for new development

Verified 19 September 2026. Status: **development-ready for bounded Odoo 19 Community work using the private remote runner**.

## Start the next requirement

Use branch `harness/onboard-work-20260919` as the prepared starting point for a new standalone development. State the business requirement and whether the UI should be standard Odoo or custom. The Work agent will create a feature branch, load the relevant external skills, implement the change, run its contracted tests and preserve documentation/evidence. No main merge or additional onboarding is required to start from this branch.

If the requirement extends an existing feature branch, inspect that branch and reconcile these setup files and instructions first. Do not replace its code or automatically resume the old Shopify program. The prepared baseline contains adams_base, not the unmerged connector program.

## Immutable qualification identities

| Component | Exact revision |
|---|---|
| Tested Adams source | `cb521c07ec2d9b15348cacf1499a8ff5886e6694` |
| Pinned harness executor | `10ec1d059b5ddc5d422875f68e0726cc500487ce` |
| Private runner controller | `8b17239100d6327479c0caea0c731ed7d96bf75f` |
| Prior Adams version used for update | `dec6e6e4046fc4ba4ceec14379551a90f4de5702` |
| Chosen disposable Odoo 19 Community source | `82f4b92eaf3f2014eb1667e4845e80c377dbfb4f` |
| Odoo documentation source | `f827d1229cc09aecf2dc3e79f51cc9a65eb5ea77` |

The later handoff commit changes documentation only; it does not retest or relabel the executable candidate above. This is a deliberate disposable Community test baseline, not a claimed match to an Odoo.sh/customer database.

## What is connected

Adams remains public and owns application code, its original adapter, connection metadata and tests. The harness remains private under MostafaEssamm12 with separate code/history. No private skill/reference content was copied into Adams and no cross-owner private Actions reference was installed.

- `.odoo-harness/connection.json` pins the external toolkit.
- `scripts/work-harness.py` validates its repository, exact commit and clean checkout, lists available skills, checks capabilities and invokes the separate runtime.
- `.github/workflows/harness-metadata.yml` checks public metadata and adapter identity regressions.
- The private harness workflow `adams-consumer.yml` checks out the pinned public Adams commit and pinned private executor, runs disposable Odoo/PostgreSQL tests, and retains execution evidence.
- Native smoke tests under `addons/adams_base/tests/` verify module installation, active English/Arabic languages and a rollback-isolated ORM round trip. They add no business functionality.

Use AdamsOdoo for Adams GitHub operations and MostafaEssamm12 for harness operations. No extra cross-account secret is needed for this tested private-runner/public-consumer arrangement.

## Load resources in Work

1. Read this file, AGENTS.md, CLAUDE.md and any instructions on the selected feature branch.
2. Read the private harness START_HERE.md, ONBOARDING.md and CLOSURE.md at the pinned executor revision, plus the current [readiness PR](https://github.com/MostafaEssamm12/Odoo/pull/3). Their older open-review statements are historical; the exact-source evidence and separate review below close the findings for this development scope. Do not change the executor pin silently.
3. Obtain a separate clean private checkout at that full SHA. Connector file access and shell Git credentials are different: an agent may materialize authenticated Git objects and verify their blob/tree/commit hashes if private shell cloning is unavailable. Preserve existing caches.
4. Set `ODOO_HARNESS_HOME` to that checkout, outside Adams. Run `python3 scripts/work-harness.py check`. The verified current path is `/workspace/scratch/2a2ff17b4bfd/private-harness/10ec1d059b5ddc5d422875f68e0726cc500487ce`; recreate it from the private repository if scratch has expired.
5. Read the external skill registry and quality guidance; load only task-relevant skill files. Verification and delivery were exercised in this onboarding. All eight skills are accessible; automatic global installation and a benchmark of every model/skill combination are not claimed.
6. Python/Git execution works locally. `doctor` reports local capability only; this Work shell has no Docker/Odoo. Use the verified private Actions runner for native tests.

## Run feature tests

For a committed feature candidate, choose the relevant modules, exact expected test IDs, Community/authorized Enterprise dependencies and feature-specific acceptance contract before testing. The present smoke contract is not acceptance of a future feature.

The generic adapter accepts a private runtime configuration and contract:

```bash
python3 scripts/work-harness.py test \
  --project /private/runtime-config.json \
  --contract /approved/feature-contract.json \
  --check-id native --cache /runner/odoo-resources \
  --output /evidence/unique-run
```

The adapter binds candidate path and source SHA itself; it rejects overrides and abbreviations. Odoo databases are newly allocated and disposable.

In this Work environment, use the MostafaEssamm12 GitHub connection to update the private runner's `consumers/adams/request.json` with the exact candidate, prior revision if applicable, modules and expected test IDs. Update its contracted requirement for the actual feature, retaining exact source checks. Publish on the dedicated private runner branch; its push triggers execution. Read raw results before claiming a pass. Do not run the onboarding smoke as a substitute for feature tests. More complex browser/integration checks use the existing runtime's reviewed probe/contract options and must be configured for that feature.

## Verified results

| Check | Result and evidence |
|---|---|
| File access and resource loading | Both account connections verified; exact private executor checkout reconstructed and Git hashes verified; external adapter check passed; original repository instruction bodies preserved. |
| Harness unit/static | **270 passed**, zero failures/errors/skips; clean exact source. [Quality run 35452490995](https://github.com/MostafaEssamm12/Odoo/actions/runs/35452490995). |
| Harness Odoo qualification | Native fresh/update, bilingual browser, shell, recovery, deliberate failure/zero-discovery controls and separate synthetic consumer campaign passed. [Runtime run 35452491048](https://github.com/MostafaEssamm12/Odoo/actions/runs/35452491048). |
| Actual Adams native tests | **3 passed fresh + 3 passed after update**, zero failures/errors/skips, exact Adams and executor identities. [Consumer run 35452924190](https://github.com/MostafaEssamm12/Odoo/actions/runs/35452924190). |
| Public GitHub integration | Connection metadata and two adapter regression tests passed on the tested Adams source. [Run 35452888997](https://github.com/AdamsOdoo/Adams/actions/runs/35452888997). |
| Independent review | Separate read-only review found an abbreviated-argument bypass; it was fixed and regression-tested. Follow-up code and raw-evidence review identified no remaining blocker for bounded Community development. This is not institutional certification. |
| Durable evidence | Raw GitHub job logs, exact source/run metadata and independent review archived, retrieved separately and every member checksum verified. Archive: Adams_Harness_Qualification_Evidence_20260919.zip; SHA-256 `e08a6658e14d725a38bb5a8e9cc698c5868b7b3254ae016946b79253721dc46a`. |

The harness log-publication finding is fixed in the pinned executor: capture stays host-private during execution; forged destination paths are rejected. The separate reviewer checked the correction and regressions. PR #2's unchanged head is not the adopted executor.

The retained archive preserves retrieved job logs; it does not claim read-back of the original Actions artifact ZIP bytes. Full runtime artifacts remain available in the private Actions runs with their retention limits. Retain new feature evidence privately for its supported lifetime, verify retrieval/hashes, and link it from the feature dossier; never rely solely on expiring CI URLs. Owner: repository owner; performing agent completes retention for each delivery.

## Boundaries and preserved work

Development readiness is not acceptance of future business behavior, Enterprise/third-party compatibility, every possible model configuration, protected institutional verification, production access or release approval. Each feature still needs its own tests, relevant English/Arabic screens and independent review. Owner UAT and production/release approval remain separate.

No merge, deployment, visibility change, production action or private resource publication occurred. PRs 210–212 and original local repositories remain untouched. Preserved local heads include `31d597a660e567b815cabb3af27a101da12508ec`, `30bde525c9d003a9b00eb4175eed012dc65e8c2c` and `14be4c0ea94a2ad9fbb5f05322f309deff53c1fb`. The [previous onboarding record](https://github.com/AdamsOdoo/Adams/blob/dec6e6e4046fc4ba4ceec14379551a90f4de5702/docs/harness-onboarding.md) preserves initial findings.

Rollback: revert only the onboarding adapter/config/tests/workflow and instruction additions on the onboarding branch. No data migration is involved. No Odoo screenshots are applicable to this infrastructure-only change.

Next action: receive the new business development requirement and create its feature branch.
