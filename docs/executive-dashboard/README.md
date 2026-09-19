# Executive dashboard — ED-001

Status: **G0 in progress; Enterprise database access verified; native source/build access still blocked. Implementation not started.**

Latest update: [authorized Enterprise database inspection](development-environment.md). The user supplied the target, sign-in succeeded, native Accounting was installed and native aging definitions/drill-down were inspected. ED-B01 is resolved; ED-B02 records the remaining Odoo.sh source/build access boundary. The initial observations below are retained as the earlier checkpoint.
Checkpoint: 19 September 2026. This is preparation, not an installed or UAT-ready dashboard.

## Authority and scope

The current user explicitly selected `AdamsOdoo/Adams` and PR #213 for this new development. This overrides the attachment's generic warning not to infer Adams as the target. The dashboard is a separate feature; the old Shopify program is not resumed.

- Baseline: `f2da03cd141f327ec6856cb0e43f384bdfaf56b4`, branch `harness/onboard-work-20260919`.
- Feature branch: `feature/executive-dashboard-report-first`.
- Harness executor: `10ec1d059b5ddc5d422875f68e0726cc500487ce`, unchanged and external/private.
- Governing requirement: [original v4 contract](requirements/Dashboard_Report_First_Contract_v4.md), with [original prompt](requirements/Astra_Dashboard_Implementation_Prompt_v4.md).
- Original ZIP: `Astra_Dashboard_Report_First_Handoff_v4(1).zip`; visual reference remains the attached `Odoo_Executive_Dashboard_UX_v2.html`. Its fixtures are not production rules.
- [Source catalog](source-catalog.md), [acceptance plan](acceptance-plan.md), [input identities](requirements/input-manifest.json).

Allowed development scope is the new dashboard addon(s), their tests and this dossier. Do not modify `adams_base`, connector code, historical PRs, the executor pin or the recorded qualification to implement this feature. Any necessary private runner dependency/contract change must be isolated and tied to the dashboard candidate. No merge, release, production access or real accounting mutation is authorized here.

## Verified environment and access

| Item | Observation |
|---|---|
| Adams connection | AdamsOdoo connection read PR #213 and pinned branch files successfully; PR remains open/draft at the baseline above. |
| Harness connection | MostafaEssamm12 connection read START_HERE, ONBOARDING, CLOSURE at the exact pin and current readiness PR #3. |
| Existing work | Original onboarding checkout is clean at the baseline. A separate worktree was created; no reset, stash, rebase or force-push. |
| External toolkit | Existing separate checkout is clean at the exact pin. `scripts/work-harness.py check` returned `external-resources-verified`, with all eight skills. Its `runtime_verified: false` correctly distinguishes resource loading from a new runtime campaign. |
| Recorded qualification | Reused the 270 harness checks, full runtime qualification and 3 fresh + 3 update Adams smoke results recorded in [onboarding](../harness-onboarding.md). No unchanged test campaign was rerun. |
| Qualified Odoo source | Disposable Community `82f4b92eaf3f2014eb1667e4845e80c377dbfb4f`; not a verified customer/development-database build. |
| Current runner request | Lists only `adams_base`; no dashboard acceptance contract or Enterprise dependency. |
| Target database | Not identified in the selected branch's configuration or onboarding record. Installed modules, localization, report variants, company scope and build are unresolved. |
| Enterprise source | `odoo/enterprise` lookup returned HTTP 404 through both designated connections. This establishes no usable access through these connections; it does not prove the owner lacks a license or other access. |
| Attachment | All seven members listed in its SHA256SUMS verified. Finance/Sales/mobile supplied PNGs visually inspected. |
| Browser | Local prototype launch attempted once. Playwright package is present but its Chromium executable is absent. No interaction or live Odoo browser pass is claimed. |

Skills loaded: solution-design, development, UI and delivery. A compact blueprint is appropriate because this spans financial definitions, department access and report/record handoffs. Private skill contents remain outside Adams.

## Design and first implementation slice

Use a native Owl client action with reusable metric, section, source-detail and table components; keep native Odoo navigation. A small server registry binds approved metrics to verified native sources. Accounting handlers, analytical report models and inventory services remain distinct adapters. There is no generic arbitrary-model RPC endpoint, secondary accounting engine or cross-user result cache.

| Journey stage | Owner action | Visible response | Server responsibility / supporting source |
|---|---|---|---|
| Select scope | Authorized user chooses company and cut-off | Old-company values disappear immediately; visible sections load independently | Validate user/company and supported filters before evaluation |
| Read receivables | Owner/finance opens Working capital | Native total, aging and approved overdue result with scope/source details | Evaluate actual installed aging engine once per effective option set; retain unformatted values and provenance |
| Investigate | Select total, bucket or partner | Open scoped native aging report | Resolve verified action and effective options; recheck permissions |
| Inspect document | Open report detail/original record | Native Odoo form with permitted information | Native access/rules; no superuser workaround |
| Export and return | Export matching detail; navigate back | All matching authorized rows and restored scope/search/scroll where supported | Revalidate source/access, bound pagination, preserve export provenance and neutralize formula injection |
| Source unavailable | Encounter missing module/mapping/access or request failure | Distinct unavailable/restricted/error state; no invented number | Sanitized diagnostics; never replace missing native results with custom arithmetic |

Then complete Finance and dynamic cash discovery, Sales, and installed supporting departments in contract G2–G4 order. Preserve the approved visual hierarchy, signed values, chart tables, compact mobile attention and English/Arabic RTL. Prototype shell duplication, sample entities, scenario controls and simulated authorization are excluded from the application.

## Concrete blocker and next action

**ED-B01:** Identify the authorized Odoo 19 development database/build for this dashboard, with its licensed reporting modules and source access. The current Community qualification is insufficient evidence for the required native aging, Partner Ledger and statement APIs. The v4 contract G0 requires those APIs and installed mappings to be inspected before calculations are implemented.

The user needs to identify the intended development database/project URL (or an authorized disposable Enterprise target). This is an environment identity question, not a request to reapprove development. Once identified, inspect available connected access before requesting anything further. Do not borrow another project's database authorization or downgrade the requirement to Community-only behavior.

Next: verify actual build, installed modules/localization, native action/variant/expression/column and option contracts; finish each catalog row; select exact feature test IDs; implement and qualify the receivables journey. Any genuine custom metric remains disabled until its material business definition is approved. No custom formula has been proposed as necessary or enabled at this checkpoint.

## Checkpoint / evidence / rollback

Documentation only; no addon, schema or data change and no migration. Feature native/browser/security/performance tests are not run, not passed. Independent implementation review and real English/Arabic screenshots remain pending. The input previews are design evidence only.

The original onboarding checkout and private toolkit remain clean. The new worktree is at `/workspace/scratch/0d625603a72e/adams-dashboard`. Review the commit containing this checkpoint and current Git status when continuing; never infer unchanged remote state from this note. Durable continuation is this feature branch and the original attached archive.

Rollback is removal/reversion of only this feature's documentation commit. No application or runtime rollback is required. Learning: distinguish inherited Community harness qualification from feature-specific licensed report compatibility; verify environment identity before writing financial adapters.

## First implementation slice — login deferred

The owner authorized building before Odoo.sh authentication on 19 September 2026.
`adams_executive_dashboard` is now a separate addon with an Owl client action,
responsive report cards, company/period/cutoff filters, independently loaded sections,
stale-response protection, dashboard membership and native report access checks.
Native analytical adapters cover posted net invoiced sales, confirmed untaxed sales,
distinct orders and confirmed untaxed purchases. Sale/Purchase apps are optional.
Financial mappings, stock/CRM/HR measures, charts, exports, persistent preferences,
Enterprise parity and actual English/Arabic browser acceptance remain incomplete.
This is a development slice, not a completed dashboard or release candidate.

Validation: Python compilation, JavaScript syntax and XML parsing passed locally.
The first native harness campaign passed seven exact contracted tests (zero failures,
errors or skips). See `implementation-status.md` for its exact source and limits. Existing harness qualification is reused.

Install the addon only in a disposable development database. Administrators can
open its menu; other users need the Executive Dashboard group plus their existing
native report permissions. The dashboard group grants no accounting access.
The feature adds no accounting records or scheduled jobs. Enterprise source access
and a source-matched test build are deferred, not waived.

Arabic UI messages are included as an initial translation catalog, checked by GNU
msgfmt. Responsive CSS uses logical inline spacing for RTL. Neither language is
browser-qualified yet. Three Node controller tests pass for overlapping company
refreshes, independent section failure, and component destruction; their stubbed
Owl/services setup does not prove Odoo assets or DOM behavior. Run them with:

```sh
node --test addons/adams_executive_dashboard/tests/frontend.test.mjs
```

Private native campaign: `harness/adams-dashboard-20260919` in the private harness
repository, workflow `adams-dashboard.yml`. It uses the original pinned executor
and a new feature-specific contract. Its screenshots remain required and pending;
a native-test pass is not overall acceptance. The first campaign targets application
commit `96b8501d20ba842dc08df2390ba12f8c8b5382bf`, fresh installation only.
