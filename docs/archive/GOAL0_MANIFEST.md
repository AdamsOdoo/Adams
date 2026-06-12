# Goal 0 Manifest — Governance Cleanup and Documentation Operating System

Date: 2026-06-12  
Scope: Goal 0 only; documentation/governance changes only.  
Branch observed by harness: `work` (requested working branch `claude/codex` was not present locally).  
Base branch requested for understanding: `review/full-audit` (not present locally; no merge attempted).

## Safety Gates

- No production connector code will be edited.
- No Python business logic, controllers, models, sync files, Shopify API files, security files, data files, tests, manifests, or XML views will be edited.
- Documentation moves will be preceded by reference searches.
- If a move requires a manifest, script, import path, test command, module packaging file, or production path update, the move stops and is reported instead of fixed.
- Audit history will be preserved by moving/archiving or append-only notes, not deletion.
- Simulator remains internal QA only and excluded from public app-store packaging.

## Files Planned for Goal 0 Changes

| File | Current purpose | Proposed action | Evidence for action | Rollback note | Documentation scope | Safe for Goal 0? | Packaging / Odoo.sh / App Store risk |
|---|---|---|---|---|---|---|---|
| `docs/archive/GOAL0_MANIFEST.md` | Does not exist. | Create | Task T0 requires a manifest before any other change. | Remove the file or revert the T0 commit. | Internal docs only. | Yes. | None; not loaded by Odoo packaging. |
| `AGENTS.md` | Does not exist at repo root. | Create | Task T1 requires canonical operating file for Codex/future agents. | Revert T1 commit. | Internal governance. | Yes. | None; root Markdown only. |
| `CLAUDE.md` | Long mixed mission, governance, status, branch, and environment guidance. | Rewrite | Task T2 requires short pointer file; environment content moves to `docs/ops/ENVIRONMENT.md`. | Revert T2 commit or restore from prior commit. | Internal governance. | Yes. | None; root Markdown only. |
| `docs/ops/ENVIRONMENT.md` | Does not exist. | Create | Task T3 requires environment/runtime notes moved from old `CLAUDE.md`. | Revert T3 commit. | Internal ops docs. | Yes, if commands are transcribed without changing live green-build commands. | None; docs only. |
| `COVERAGE.md` | Does not exist at repo root. | Create | Task T4 requires scaffold with no fabricated rows. | Revert T4 commit. | Internal QA/governance. | Yes. | None; root Markdown only. |
| `docs/product/BEHAVIOR_CONTRACT.md` | Does not exist. | Create | Task T5 requires behavior skeleton for Goal 1 population. | Revert T5 commit. | Internal product docs. | Yes. | None; docs only. |
| `docs/product/FEATURE_FLAGS.md` | Does not exist. | Create | Task T5 requires feature-flag scaffold. | Revert T5 commit. | Internal product docs. | Yes. | None; docs only. |
| `docs/product/SYNC_OWNERSHIP_MATRIX.md` | Does not exist. | Create | Task T5 requires ownership matrix scaffold. | Revert T5 commit. | Internal product docs. | Yes. | None; docs only. |
| `docs/qa/TEST_MATRIX.md` | Does not exist. | Create | Task T5 requires QA matrix scaffold. | Revert T5 commit. | Internal QA docs. | Yes. | None; docs only. |
| `docs/qa/SIMULATOR_GUIDE.md` | Does not exist. | Create | Task T5 requires simulator guide; existing simulator docs are in `addons/shopify_simulator/doc/`. | Revert T5 commit. | Internal QA docs. | Yes. | Low positive impact; reinforces simulator exclusion. |
| `docs/release/APP_STORE_READINESS.md` | Does not exist. | Create | Task T5 requires later Goal 10 readiness checklist. | Revert T5 commit. | Internal release docs. | Yes. | None; no readiness claim. |
| `docs/release/PACKAGING_RULES.md` | Does not exist. | Create | Task T5 requires packaging rules, including simulator exclusion. | Revert T5 commit. | Internal release docs. | Yes. | Low positive impact; documents exclusion rules. |
| `addons/shopify_connector_pro/doc/COMPETITIVE_ANALYSIS.md` | Shipped addon documentation with commercial/comparison content. | Move | Task T6 requires moving this internal/commercial doc to `docs/product/PRICING_AND_TCO.md` if unreferenced by packaging/module logic. | Revert T6 commit or move back. | Shipped addon doc currently; target internal product doc. | Yes only after reference grep confirms no path dependency. | Potential app-store positive by removing internal sales/TCO content from shipped docs; stop if referenced by packaging/module logic. |
| `docs/product/PRICING_AND_TCO.md` | Does not exist. | Create by move | Target required by T6. | Revert T6 commit or move file back to addon doc path. | Internal product/commercial docs. | Yes after reference grep. | None if unreferenced. |
| `addons/shopify_connector_pro/doc/Shopify_Connector_Pro_Commercial_Documentation.md` | Shipped addon documentation with commercial positioning. | Move | Task T6 requires moving this file to `docs/product/COMMERCIAL_OVERVIEW.md` if unreferenced by packaging/module logic. | Revert T6 commit or move back. | Shipped addon doc currently; target internal product doc. | Yes only after reference grep confirms no path dependency. | Potential app-store positive; stop if referenced by packaging/module logic. |
| `docs/product/COMMERCIAL_OVERVIEW.md` | Does not exist. | Create by move | Target required by T6. | Revert T6 commit or move file back to addon doc path. | Internal product/commercial docs. | Yes after reference grep. | None if unreferenced. |
| `docs/product/COMPETITIVE_ANALYSIS.md` | Existing internal product competitive analysis. | Append | Task T6 requires a note that `PRICING_AND_TCO.md` is the commercial companion if this file exists. | Revert T6 commit or remove appended note. | Internal product docs. | Yes. | None. |
| `addons/shopify_connector_pro/KNOWN_LIMITATIONS.md` | Shipped addon known limitations with internal technical triage/fix sketches. | Split + rewrite shipped version | Task T7 requires merchant-friendly in-addon version and internal architecture version preserving technical content. | Revert T7 commit to restore original; remove internal copy. | Shipped addon documentation. | Yes; explicitly allowed in task. | Positive app-store impact; avoid production path changes. |
| `docs/architecture/KNOWN_LIMITATIONS.md` | Does not exist. | Create by copy/split | Task T7 requires internal architecture version preserving full technical/triage content. | Revert T7 commit or remove file. | Internal architecture docs. | Yes. | None. |
| `LEGACY_NOTES.md` | Root legacy notes with historical evidence and some reusable QA/test guidance. | Move/archive | Task T8 requires moving to `docs/archive/LEGACY_NOTES.md` and adding archive note. | Revert T8 commit or move back. | Internal archive. | Yes after reference grep. | None if unreferenced by packaging/module logic. |
| `docs/archive/LEGACY_NOTES.md` | Does not exist. | Create by move + prepend/append archive note | Target required by T8. | Revert T8 commit or move back. | Internal archive. | Yes. | None. |
| `STAGING_TEST_PLAN.md` | Root staging validation plan. | Move | Task T8 requires moving to `docs/qa/STAGING_TEST_PLAN.md`. | Revert T8 commit or move back. | Internal QA docs. | Yes after reference grep. | None if unreferenced by packaging/module logic. |
| `docs/qa/STAGING_TEST_PLAN.md` | Does not exist. | Create by move | Target required by T8. | Revert T8 commit or move back. | Internal QA docs. | Yes. | None. |
| `docs/qa/TEST_PATTERNS.md` | Does not exist. | Create if active durable test knowledge exists in `LEGACY_NOTES.md` | Task T8 requires extracting active durable test knowledge if present. | Revert T8 commit or remove file. | Internal QA docs. | Yes if only existing content is copied/summarized. | None. |
| `AUDIT.md` | Historical audit evidence. | Append | Task T9 requires dated addendum on historical `MORNING_REVIEW.md` references. | Revert T9 commit or remove appended addendum. | Internal audit docs. | Yes; append-only. | None. |
| `FINALIZE.md` | Historical evidence/backlog and standing approval notes. | Append | Task T9 requires dated note near header about superseded pre-approval wording and preserved history. | Revert T9 commit or remove appended note. | Internal governance/evidence docs. | Yes; append-only in spirit (insert near header requested). | None. |
| `docs/architecture/DECISIONS.md` | Architecture decision record table. | Append | Task T9 requires ADR rows for confirmed product decisions. | Revert T9 commit or remove appended rows. | Internal architecture docs. | Yes; append-only. | None. |
| `README.md` | Minimal placeholder (`# Adams` / `Adams Odoo Addons`). | Rewrite | Task T10 requires useful repo map and pointers. | Revert T10 commit or restore original. | Root repo docs. | Yes. | None; no setup command changes. |

## Files Inspected but Planned to Keep Unchanged

| File | Current purpose | Proposed action | Evidence for action | Rollback note | Documentation scope | Safe for Goal 0? | Packaging / Odoo.sh / App Store risk |
|---|---|---|---|---|---|---|---|
| `STATUS.md` | Current project state summary. | Keep | Task asks to inspect and point to it; no rewrite requested. | No change. | Internal status. | Yes. | None. |
| `docs/architecture/ARCHITECTURE.md` | Architecture documentation. | Keep | No task requires editing it. | No change. | Internal architecture docs. | Yes. | None. |
| `docs/product/UX_DESIGN.md` | Product UX documentation. | Keep | No task requires editing it. | No change. | Internal product docs. | Yes. | None. |
| `addons/shopify_connector_pro/doc/API_REFERENCE.md` | Shipped API reference docs. | Keep | No task requires editing; shipped addon docs should be minimally touched. | No change. | Shipped addon docs. | Yes. | Avoids packaging risk. |
| `addons/shopify_connector_pro/doc/README.rst` | Shipped addon documentation index. | Keep | No task requires editing; moving commercial docs will proceed only if no live references require index updates. | No change. | Shipped addon docs. | Yes if no broken required references. | Avoids manifest/package risk. |
| `addons/shopify_connector_pro/doc/STEP_BY_STEP_GUIDE.md` | Shipped setup/user guide. | Keep | No task requires editing. | No change. | Shipped addon docs. | Yes. | Avoids app-store doc churn. |
| `addons/shopify_connector_pro/doc/TROUBLESHOOTING.md` | Shipped troubleshooting guide. | Keep | May be linked from merchant-friendly limitations if appropriate, but not edited. | No change. | Shipped addon docs. | Yes. | None. |
| `addons/shopify_connector_pro/doc/USER_GUIDE.md` | Shipped user guide. | Keep | May be linked from merchant-friendly limitations if appropriate, but not edited. | No change. | Shipped addon docs. | Yes. | None. |
| `addons/shopify_connector_pro/doc/setup_guide.rst` | Shipped setup guide. | Keep | No task requires editing. | No change. | Shipped addon docs. | Yes. | None. |
| `addons/shopify_connector_pro/doc/troubleshooting.rst` | Shipped troubleshooting guide. | Keep | No task requires editing. | No change. | Shipped addon docs. | Yes. | None. |
| `addons/shopify_simulator/doc/DESIGN.md` | Internal simulator design doc inside simulator addon. | Keep | Task requires linking/referencing existing simulator docs but not moving or editing simulator docs. | No change. | Simulator addon docs, internal QA. | Yes. | Reinforce exclusion elsewhere; no code/package change. |
| `addons/shopify_simulator/doc/shopify_simulator_user_guide.md` | Internal simulator guide inside simulator addon. | Keep | Task requires link/reference if present; no edit requested. | No change. | Simulator addon docs, internal QA. | Yes. | Reinforce exclusion elsewhere; no code/package change. |
| `addons/requirements.txt` | Addon dependency notes/requirements. | Keep | Discovered as text file; not a governance Markdown file and no task requests dependency edits. | No change. | Runtime/dependency file. | Yes by not touching. | Avoids runtime/build risk. |
