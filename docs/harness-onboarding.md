# ChatGPT Work harness onboarding — 19 September 2026

Status: private workspace setup and resource smoke checks complete; full onboarding qualification BLOCKED.

## Identity and scope

- Application repository: AdamsOdoo/Adams (public), using the AdamsOdoo connection.
- Separate toolkit: MostafaEssamm12/Odoo (private), using the MostafaEssamm12 connection.
- Pinned setup candidate: `222b7339adc055d4dff619ab105c2712fae1435b`; verified Git tree `c9c31ec1568adabc0a2c259f1f27e040c741b765`.
- Dedicated branch: `harness/onboard-work-20260919`.
- Documentation-only branch base: `a5d45432a9b60f724c1aff700f4b371ea019960e`. Main was inspected, not assumed to be the application baseline. It contains the governance scaffold and adams_base; current connector development remains on separate branches. This base isolates onboarding without adopting an unfinished feature. Select the actual development baseline after the new requirement is supplied.
- No merge, deployment, database access, visibility change or application change is part of onboarding.

## Existing work preserved

All 14 remote branches were inspected. Open PRs [210](https://github.com/AdamsOdoo/Adams/pull/210), [211](https://github.com/AdamsOdoo/Adams/pull/211), and [212](https://github.com/AdamsOdoo/Adams/pull/212) remain unchanged. Observed heads: 210 `f77bfcc25e63615e6226dd9a9329f8f943593cb2`; 211 `3914004e27630b09b211e3d2ee92a8e6d9a0e55e`; 212 `5dbd4504d4ab08998598a5d6cc5933386679ed06`.

Read the [current connector checkpoint](https://github.com/AdamsOdoo/Adams/blob/390f4d9f38604b17fcc290c26a05db330608d96e/docs/v2/13-continuous-execution-handoff.md) only when working on that program; this onboarding does not resume it. Preserved local repositories include connector at `31d597a660e567b815cabb3af27a101da12508ec`, published-check at `30bde525c9d003a9b00eb4175eed012dc65e8c2c`, and adams-v2 at `14be4c0ea94a2ad9fbb5f05322f309deff53c1fb`. No reset, rebase, stash, force-push or overwrite was used.

Existing AGENTS.md and CLAUDE.md bodies remain intact. Their historical research-only/Claude execution rules do not override the user's explicit authorization for this narrowly scoped Work onboarding. They also do not authorize resuming an old feature. On any later application branch, read and reconcile that branch's own instructions and overrides before making changes.

## Load in a future Work session

1. Read this handoff and the selected Adams branch's AGENTS.md / CLAUDE.md. Verify remote head, local status, visibility and account identity again.
2. Through the MostafaEssamm12 connection, read START_HERE.md, ONBOARDING.md and CLOSURE.md at the full pinned commit above. Check [harness PR 2](https://github.com/MostafaEssamm12/Odoo/pull/2) for review state. Do not silently upgrade this pin.
3. Obtain that exact source in a separate private workspace, never inside the public Adams checkout. An authenticated Git checkout is preferred when available. Connector file access is a separate capability from shell Git credentials. In this session, all 151 source blobs, the tree and exact commit were reconstructed from authenticated GitHub objects and verified by their Git hashes.
4. Current transient source location: `/workspace/scratch/2a2ff17b4bfd/private-harness/222b7339adc055d4dff619ab105c2712fae1435b`. Current Adams checkout: `/workspace/scratch/2a2ff17b4bfd/adams-onboarding`. Recreate from GitHub if scratch is absent; do not rely on these paths for durability.
5. Set ODOO_HARNESS_HOME to the separate source location for tools that support it. Read its skill registry and quality guidance, then only the skills relevant to the new task. Skills are manually loaded from the external source; no automatic discovery or isolated target-model evaluation is claimed.
6. From that source, run `python3 -m odoo_harness doctor`. A read-only `onboard --project <Adams path> --repository AdamsOdoo/Adams` preview is supported. Do not use --apply under this private-workspace mode.
7. Select application branch, modules, exact Odoo/edition/dependency pins, authorized runner, acceptance contract and private retention before application testing. Do not copy pilot settings or infer them from this documentation branch.

This is an external-resource arrangement, not a standard installed consumer. No harness-managed lock, copied skill, entrypoint or workflow was installed in Adams. Accordingly, standard check-onboarding is not claimed as passing. It requires the installer-managed resources that privacy constraints presently exclude.

## Verification

| Surface | Observed result |
|---|---|
| Repository file access | Both named account connections can read their respective repositories; permissions report push access. |
| Exact source loading | All 151 tracked blobs and the Git tree/commit verified; private source checkout clean. Eight skill files found; verification and delivery skills loaded for this task. |
| Local tools | Python 3.12.14 and Git available. Docker, PostgreSQL client, Odoo, gh, Codex CLI and Python Playwright unavailable. |
| Static checks | 69 Python, 13 JSON, 2 TOML and 8 skills checked successfully. |
| Focused local smoke | 38 tests passed: tests.unit.test_consumer_hook, tests.unit.test_onboarding_review, tests.unit.test_state_scaffold_cli. These test toolkit behavior with fixtures, not Adams business behavior. |
| Installer preview | Passed at the pinned source; proposed 34 files. Not applied because it copies private resources and adds the unsupported shared-action reference. |
| Exact-source upstream CI | [Quality 35437107658](https://github.com/MostafaEssamm12/Odoo/actions/runs/35437107658) and [runtime 35437107638](https://github.com/MostafaEssamm12/Odoo/actions/runs/35437107638) completed successfully on the pinned commit; job/step results inspected. Separate PR quality run 35437111515 was skipped. |
| Actual Adams Odoo testing | NOT RUN. No selected feature baseline, verified Odoo environment or Docker runner in this session. Upstream fixture qualification is not Adams qualification. |
| GitHub workflow integration | NOT ENABLED. Public Adams / private toolkit / different owners; no private cross-owner uses reference created. |
| Acceptance and retention | Independent acceptance policy, isolated target-model qualification and durable private evidence retention remain unverified. Scratch is not a permanent archive. |

## Remaining gates and publication decision

The pinned candidate has exact-source tests and a review, but an unresolved review finding remains. It is a setup candidate, not an accepted release. See [current review](https://github.com/MostafaEssamm12/Odoo/pull/2#pullrequestreview-5255346527); private review content is not reproduced here. Resolve and qualify a future candidate through the toolkit's own repository, then update this pin in a separate reviewed change.

The standard installer would publish private skills/references and install a private action that is not established as accessible from Adams. User ownership of both accounts does not establish that workflow access. Keep private-workspace mode unless the owner explicitly approves a specific publishable subset or chooses a supported private runner integration. No visibility change or private content publication is authorized by this record.

Full onboarding cannot be marked ready until the review gate and actual consumer configuration/runner/retention gates close. The next business input is the new development requirement; it determines the correct application baseline and required tests.

## Recovery and learning

Revert only this onboarding documentation commit to remove the public pointers. Existing code, instructions and histories remain preserved. No schema/data migration or application screenshot is applicable: no Odoo screen or behavior changed.

Lesson: verify visibility, ownership, exact source review/CI and shell capabilities independently. A connected GitHub account and a historical green run do not establish a runnable, qualified consumer. Public handoffs contain only original setup metadata and links, never copied private toolkit resources.
