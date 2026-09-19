# Initial dashboard implementation — 19 September 2026

Status: implemented first development slice; full dashboard incomplete.

## Implemented

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

## Verification

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

## Remaining work

Complete Enterprise source/build discovery and native financial mappings, including
dynamic bank/cash directory, historical aging and financial report parity. Complete
Sales/Purchase fixtures, remaining departmental measures and approved charts. Add
export, preference persistence and full interaction/accessibility coverage. Run
source-matched deployment, update tests, English/Arabic desktop/mobile browser
acceptance, performance checks and owner UAT. No main merge or release approval.

Login is deferred at the owner's request. No prototype balance calculations,
production/staging changes or old Shopify development are part of this work.
