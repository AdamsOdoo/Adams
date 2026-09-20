# Executive dashboard — development and live verification

**Status: development continues; full dashboard is NOT ready for business UAT.**
Access was restored on 20 September 2026. The feature build and dashboard opened
successfully. No main merge, production change or Shopify work was performed.

## Current verified checkpoint — 20 September 2026, 14:21 UTC

Application `ac52010ffb531a027663cbca3f7f92bb67861b29`, tree
`79c04c85809aa5590c29b8fbc4c59249d9528222`, Odoo.sh build **38346414**:
**50 native tests, zero failures/errors**; 16 isolated frontend/controller tests
passed locally. Native browser checks exercise EN/AR at 320/390/768/1024/1440/1920,
source drawer focus/exact values/fit/closing, responsive column counts and one
native financial drilldown. Odoo.sh reports Test: Warning, not a clean release gate.

[Private evidence](https://github.com/MostafaEssamm12/Odoo/tree/87e9320b1fb5c142f9d556e10d6455c2796f6c10/evidence/adams-dashboard/20260920-ac52010)
retains 12 actual native screenshots, hashes/dimensions and the original result
excerpt. EN 1440 is the native report; other images show Finance after drawer
closure. The rolled-back fixture approves only revenue 100. It is not customer
configuration, full visual parity or owner approval.

Implemented: native financial statements/ratios, dated cash, aging/CFS/Partner
Ledger, standard forecast/budgets/monthly trends; native commercial analysis,
recent orders, salesperson/customer rankings, quantity fulfillment; current and
historical stock quantity/valuation, workforce, CRM/leave and purchase worklists.
The source side drawer, four-column recent orders, compact display with exact
values, scope-preserving exports and workspace restoration are implemented.

Native full Accounting activation resolved finance report access on disposable
build 38345613. The mapping list was inspected and is empty. No ACL was weakened
and no owner mapping was approved. Fresh builds need their own app configuration.
Current company reporting policy and additional metric definitions require the
concrete decisions in [owner decisions](owner-decisions.md), per contract §2.2/2.5.

Screenshot review found duplicate unavailable margin text and RTL numeric date
ranges; the following template correction removes the duplicate, isolates dates
LTR and fixes balance-card footer semantics even when unavailable. That correction
requires its own native candidate result; ac52010 images do not qualify it.

Full UAT remains open: full reference fidelity and departmental interaction matrix,
remaining role/field/export cases, representative-volume p95, a current finance
upgrade campaign, approved company definitions and the additional custom measures.
Historical statements below describe their dated candidates only; this section
supersedes old claims that finance is unimplemented or login is wholly blocked.

## Earlier live findings, 20 September

- Odoo.sh build `38327805` runs application `c6586cba771fec8a9c5a0901980486d98dce44ec`.
  Its install log reports **one failure, zero errors, 25 tests**: only
  `TestAdamsOnboarding.test_english_and_arabic_loaded` failed. The 22 dashboard
  tests passed. Settings confirmed just one active language.
- Arabic was installed through the native language wizard in this disposable
  development database. The first Arabic dashboard check exposed untranslated
  dashboard labels despite translated native menus.
- Root cause: browser catalogue entries lacked Odoo 19's `odoo-javascript`
  extraction comment. The catalogue now supplies it. A regression exercises
  Odoo's actual web translation loader instead of checking only PO syntax.
- The disposable native-test addon now installs inactive English/Arabic languages
  via Odoo's language wizard before post-install tests, preserving existing terms.
  Customer addon installation does not change language configuration. The original
  onboarding assertions remain unchanged. Fresh-build verification is pending.
- Odoo.sh's editor can read the authorized Enterprise source. The separate Shell
  page redirects repeatedly and the editor terminal has not connected. Finance
  mapping and parity remain pending; source access alone is not acceptance.

The previous exact-source harness results below remain valid for their recorded
candidate. They are not relabelled as evidence for these new localization changes.

## Latest implementation

- Recent orders and quotations: native paged records, document currency/untaxed
  values, localized states and timezone-labelled dates; scoped native list/form
  actions reject wrong-company, wrong-state and out-of-period records.
- Draft/sent quotation value, grouped dimensions and trends use Sales Analysis.
  Expired quotations remain included while their native state is draft/sent;
  no separate validity rule is silently introduced.
- Fulfillment detail uses native ordered/delivered/to-deliver quantities grouped
  by product/UoM, preserving negative values. Quantities are current for the
  selected order-date cohort, not an as-of backlog valuation. No mixed-unit total.
- Native action-stack restoration retains applied filters, selected analysis and
  pages, collapsed sections and scroll. It stores no business values and refreshes
  data/access on return. Actual breadcrumb/scroll behavior still needs browser QA.
- Finance subheadings now follow Profitability / Liquidity / Working capital;
  Sales separates Commercial performance / Fulfillment. New UI text has Arabic
  translations. Fetched timestamps do not claim source completeness.
- Every public dashboard RPC is covered by the no-dashboard-permission fixture.
  New fixtures cover sales-only records/export denial, company isolation,
  27-row recent lists, 27-group totals/full exports and signed HR values.
- Native source inspection and unresolved definition decisions are recorded in
  [native gaps](native-gaps.md); [UAT preparation](uat-checklist.md) covers the
  first session after build/source access is restored.

## Earlier pinned-harness verification

Previously tested application: `365a0f1056613e3e4e1999bc768595f9235eda67`.
Private controller: `e16a42d03410e2e07d6f86f505e1eee55e2cd896`.
Executor remains `10ec1d059b5ddc5d422875f68e0726cc500487ce` and Community remains
`82f4b92eaf3f2014eb1667e4845e80c377dbfb4f`. The original harness qualification is
reused, not repeated. All new campaigns are dashboard feature checks.

[Final native campaign 35474133751](https://github.com/MostafaEssamm12/Odoo/actions/runs/35474133751)
passed **22/22 fresh-install tests and 12/12 core-addon upgrade tests**, with zero
failures/errors/skips. Upgrade baseline was
`ec53289713ee1ca7550886f127d05e0055521ab7`. Optional-app fixtures run on install;
upgrade covers the core addon, not every optional-app/customer migration.

Private artifact `10594037826` is retained until 2026-12-18. Observation archive
SHA256: `81c66ade62ec1f7d5ab34ad9ace2b8dc347994a5af292827c24c861035826bbf`.
The runner verified archive readback. Structured native job summaries and artifact
metadata were retrieved and bound to the exact source above. The final follow-up
changes documentation only; executable and test source remain unchanged.

Ten isolated controller tests pass on the final source, covering stale company,
section, export, recent-list and analysis responses; unmount; selection-only
navigation snapshots; and changing filters while restoration is pending. They
are not browser/DOM tests. Python/JS/XML and Arabic-catalog checks pass. Native
Sass compilation is included in the contracted Odoo suite.

Preceding exact-source evidence remains valid and retained:

| Application | Private campaign | Result |
|---|---|---|
| `ec53289713ee1ca7550886f127d05e0055521ab7` | [35473705772](https://github.com/MostafaEssamm12/Odoo/actions/runs/35473705772) | 21 install + 12 core upgrade passed; numeric HR, recent records, paging/access fixtures |
| `895e908082fa7da87c83587f0db13f1d324ec555` | [35473961480](https://github.com/MostafaEssamm12/Odoo/actions/runs/35473961480) | 22 install + 12 core upgrade passed; native quotation and signed delivery quantities |

All reported native passes have zero failures/errors/skips. The final correction
adds the product-presence filter to delivery provenance and verifies that its
domain exactly matches native drilldown. It also makes current-versus-cutoff
semantics explicit in both languages. Prior campaign success does not substitute
for that latest-source verification.

## What still needs access or decisions

Enterprise P&L/Balance Sheet/Cash Flow/aging/Partner Ledger results, dated cash
balances and financial comparisons remain unconfigured. The feature branch has
not been verified in the provided Odoo.sh database. Customer report variants,
installed extensions, exact source identities, live exports, bilingual/mobile
rendering, actual return navigation and representative-volume performance still
require the matching development build.

Backlog value, final on-time completion, historical inventory/shortage/valuation,
workforce/attendance/capacity, targets and management alerts remain incomplete.
Native source inspection must precede any new calculations; custom gaps need
approved business definitions. Restoring login alone does not complete these
requirements. No full UAT or release pass is claimed.

## Historical expanded implementation — before the latest pre-login work

Status: **bounded development slice verified; full dashboard NOT ready for UAT**.
The original requirements have not been reduced to the implemented subset.

### Current candidate and evidence

- Tested application: `27817631693a4babb1a9d3434697cd7c3e0363cb`.
- Private controller: `ad341c51f88d27e9cd4dca2e399c18f19c312a7f`.
- Executor remains `10ec1d059b5ddc5d422875f68e0726cc500487ce`.
- Community remains `82f4b92eaf3f2014eb1667e4845e80c377dbfb4f`.
- Prior application for update: `b3b37eacb02890a935cbe992daeae5c400aa65e5`.
- [Native install/update campaign](https://github.com/MostafaEssamm12/Odoo/actions/runs/35471793918):
  **17/17 fresh-install tests and 12/12 core-addon update tests passed**, zero
  skips/errors/failures. Install includes optional app fixtures; update covers the
  prior core addon, not a production migration or every optional-app combination.
- Seven isolated controller tests passed locally on this source. Python/JS/XML,
  Arabic catalog and native Sass compilation checks passed. No DOM/browser pass.
- Private artifact `10593185704`, retained until 2026-12-18. Observation ZIP SHA256:
  `9c04a9b0bdf0d47d5bdfba64b015b17ae5f057cdc64a5234603ca049189db89a`.
  Runner archive readback passed; structured native job logs and artifact metadata
  were retrieved. Final follow-up changes are documentation only; application and
  test files remain exactly at this tested source.

### Expanded behavior

Native analytical totals, dynamic customer/salesperson/product/vendor/buyer/stage/
department groups, monthly trends, scoped group drilldowns and CSV exports are
implemented. Groups paginate independently of headline totals. Export requires
native permission, escapes formula-like labels and refuses silent truncation.
The server discards client-injected report/currency/timezone context and validates
all requested dimensions. Source fingerprints bind the report options, not an
unavailable data-version timestamp.

Current stock uses native per-product quantities/UoMs. CRM uses native weighted
revenue for active pending company-assigned opportunities created in the period.
Time Off preserves native negative hours for approved requests starting in the
period. HR tests currently verify action scope, not a full numeric leave fixture.
The cash directory dynamically discovers visible eligible ledger accounts, linked
journals, unlinked and archived accounts; **financial balances remain unconfigured**.

The interface adds translated breakdown/trend tables, signed magnitude bars,
section-expansion preferences and race protection for analysis, paging and export.
The native fixture tests verify known Sales/Purchase amounts, distinct orders,
CRM expected value, current stock, invoice/refund scope, authorization and exports.
No claim is made for historical inventory, fulfillment, full workforce reporting,
financial totals or actual English/Arabic rendering.

### Failure and correction record

[Expanded first attempt](https://github.com/MostafaEssamm12/Odoo/actions/runs/35471424730)
retains 13 passes, one failure and two errors. Two errors identified missing Sales
roles in the finance test fixture; the purchase fixture returned no report rows.
The latter did not independently identify whether confirmation state or pending
writes caused the empty result. The correction grants only the intended fixture
roles, asserts confirmed purchase state, and flushes fixture changes before report
reads. Application ACLs and expected amounts were not loosened. Existing evidence
was inspected without rerunning tests via the private diagnostic workflow.
The corrected campaign above closes those fixture failures. Stylesheet syntax was
also made compatible with Odoo Sass and tested with the actual compiler.

### Blocking next action and remaining scope

Odoo.sh is still at GitHub device verification. Both designated GitHub connections
return 404 for the licensed Enterprise report source. Complete that authentication
to inspect licensed source/build identities and prepare the feature development
build. Access was already authorized; this is not a permission approval request.

Financial engine adapters, dynamic dated bank/cash balances, historical aging,
ledger/statement/forecast/budget journeys, fulfillment and remaining departmental
scope remain incomplete. Deployed browser/RTL/mobile/navigation acceptance,
representative performance, complete role matrix and independent review remain
pending. See [UAT preparation](uat-checklist.md) and [gate ledger](acceptance-plan.md).
Nothing was merged, released, deployed to production/staging, or added to Shopify.

---

# Historical first implementation checkpoint

Status: implemented first development slice; full dashboard incomplete.

### Implemented

- Separate `adams_executive_dashboard` addon and Owl client action inside Odoo.
- Finance, Sales and Operations cards; responsive layout; company, period and
  balance-cutoff controls; per-section loading/errors; accessible source details.
- Server-owned report/measure allowlist, no sudo, single active authorized company,
  dashboard group plus native report access checks on each RPC and drilldown.
- Native Invoice Analysis adapter: posted customer invoices less refunds, untaxed,
  invoice date. Native Sales/Purchase Analysis adapters are implemented but their
  installed-app runtime parity is not tested yet.
- Same scoped native action for drilldown, without conflicting search defaults.
- Unverified financial and other operational sources return null with explicit
  not-configured states. No guessed financial values or prototype fixtures.
- Initial Arabic catalog and RTL-compatible logical CSS; real browser review pending.

### Verification

Private run: https://github.com/MostafaEssamm12/Odoo/actions/runs/35470273977

| Identity / result | Value |
|---|---|
| Tested application commit | `96b8501d20ba842dc08df2390ba12f8c8b5382bf` |
| Pinned executor | `10ec1d059b5ddc5d422875f68e0726cc500487ce` |
| Feature runner controller | `1b367711ba3c143f7554f0f34cd6c1437f9824d7` |
| Disposable Community source | `82f4b92eaf3f2014eb1667e4845e80c377dbfb4f` |
| Native tests | 7 discovered, 7 passed, 0 skipped/errors/failures |
| Native coverage | RPC authorization; unauthorized company/filter validation; underlying accounting access; explicit unavailable finance; invoice/refund/draft/date scope and native action parity; empty state; permission revocation |
| Private retained artifact | `10592752408`, expires 2026-12-18 |
| Observation bundle SHA256 | `07243f2b5f89584e7550073572a7f3568586e56e2844bfcd7608ccac5b007da2` |

The private runner verified archive readback and source binding. Logs and artifact
metadata were read back through GitHub. The feature contract keeps bilingual
screenshots required; passing native checks does not satisfy those requirements.
The original harness qualification was reused, not rerun.

After that exact tested commit, only the UI initial-loading behavior, initial Arabic
catalog, three frontend controller tests and documentation changed. Backend/native
tests remain byte-identical. The native result is retained for that bounded backend
slice; it is not relabeled as exact-final-candidate installation or UI acceptance.

Local verification: Python compilation, XML parsing, JavaScript syntax, GNU msgfmt
catalog checking and three Node controller tests passed. The controller tests cover
late prior-company responses, immediate old-value clearing with partial failure,
and unmount suppression. Services/Owl lifecycle are stubbed: no DOM or actual
Odoo browser behavior is claimed.

### Remaining work

Complete Enterprise source/build discovery and native financial mappings, including
dynamic bank/cash directory, historical aging and financial report parity. Complete
Sales/Purchase fixtures, remaining departmental measures and approved charts. Add
export, preference persistence and full interaction/accessibility coverage. Run
source-matched deployment, update tests, English/Arabic desktop/mobile browser
acceptance, performance checks and owner UAT. No main merge or release approval.

Login is deferred at the owner's request. No prototype balance calculations,
production/staging changes or old Shopify development are part of this work.

## Native finance expansion — verified 20 September 2026

Source `fd3fd714039f473ab9025351250b9276fe009898`, tree
`2d90751c33a4ff9f27806bbe0a202dc049209297`, Odoo.sh build **38344123**:
**44 tests, zero failures/errors** (Odoo.sh reports Test: Warning).
This supersedes the earlier 35-test finance checkpoint for the implemented code.

Additional verified features: native GL dated cash-account balances (including
unlinked, archived, zero, negative and foreign-currency accounts); due-date aging
buckets; native Cash Flow Statement with unclassified lines; separately scoped
customer/vendor Partner Ledger actions; native Executive Summary short-term cash
forecast; approved native financial budget selection, preserving explicit zero
and distinguishing a period with no budget entries. No customer mappings were
approved automatically. Accounting-authorized browser parity remains open.

### Operational expansion candidate (validation pending)

Adds native Odoo 19 product stock valuation, current/historical inventory modes,
scoped stock forecast/history/location/orderpoint actions, and current HR workforce
counts by department. Historical quantities use the native stock computation with
a timezone-correct cutoff; current reservations and forecasts are not described as
historical. Valuation uses `product.product.total_value`, not journal-entry sums or
an obsolete valuation-layer model. Workforce requires HR officer access; no private
employee fields are returned. EN/Arabic strings and 11 controller tests pass locally.
Native integration results for this candidate must be recorded before qualification.

Full v4 UAT is still not qualified: remaining features, full parity/security/upgrade,
responsive/bilingual browser matrix, representative performance and owner-approved
business definitions/configuration are tracked in the UAT checklist.

## Source 4f50789 native acceptance and visual correction

Odoo.sh build **38344984**, source `4f50789de48d901c3789cb77cde5219464c7df0b`,
completed **48 tests, zero failures/errors**. The corrected native historical stock
fixture confirms quantity 12/value 120 at the August cutoff and current quantity 8;
company/route/archived-product checks and current workforce restrictions pass.
Signed monthly finance results and clipped period drilldown also pass. The native
HttpCase browser fixture passed English and Arabic at widths 320, 390, 768, 1024,
1440 and 1920, including known revenue 100, RTL/LTR direction, page reflow, focus,
and one native report drilldown. This is bounded functional browser acceptance,
not pixel fidelity, full accessibility, performance, upgrade or customer UAT.

The user identified a material visual mismatch with UX v2. This is an implementation
defect, not a permitted consequence of report-first data assurance. The next
candidate restores the reference workspace rail, six department navigation tabs,
four-card profitability hierarchy, chart/context composition, dark cash card,
vector icons, typography/spacing and mobile two-column cards (single-column below
370px). Native data adapters and permission checks remain authoritative. No
fictional prototype amounts, identities, scenario controls or trust badges are
imported. Visual comparison against the supplied Finance/Sales/Mobile references
is now a separate blocking acceptance gate. Do not call the current work UAT-ready.


## UAT closure work — source drawer and Sales details (20 September)

The exact 9a7d137237f88c83f25a69e035ca5e5bab8ac980 candidate passed 50 native
tests with zero failures/errors on Odoo.sh build 38345613. The actual Sales
workspace was inspected: three headline cards and side-by-side orders/ranking.
This is not complete visual acceptance.

The Finance access restriction was traced to native app configuration: only
Invoicing was activated. The full Accounting app was activated in this disposable
development database. Finance now returns Not configured, not Access restricted;
no dashboard access check was weakened and no financial mapping was approved.
The native account security source at Community 7bbce824 documents why the
manager group implies report access only with the full Accounting app.

The next candidate moves source details to a keyboard-accessible native modal
side drawer, retains precise values behind compact large headlines, aligns recent
orders with the reference's four-column hierarchy, shows native salesperson and
delivery status, and adds top customers from Invoice Analysis. Source drawers and
customer rankings clear immediately on filter/company changes. CSV exports now
include retrieval UTC, definition version and scope fingerprint.

Sixteen focused controller tests pass locally. Expanded native browser checks
exercise drawer opening, focus, viewport fit, exact value and closing in EN/AR.
Native candidate execution is pending; do not reuse the prior candidate's result.

The first drawer candidate 63f9823/build 38346314 found a Sass compatibility
error: Odoo's compiler evaluated CSS min(520px,100vw) as incompatible units.
The 390px layout failure followed the failed stylesheet. The correction uses
width plus max-width with identical intended layout. Browser evidence capture
is instrumented after successful assertions using Odoo's native screenshot helper.
No calculation, rendering or pass condition is mocked.
