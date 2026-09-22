# Dashboard visual polish — owner UAT handoff, 22 September 2026

The technical qualification and staging checks are complete for the source below.
Owner financial and visual acceptance remains pending. PR #214 stays draft; no
merge, main update or production action is authorized or performed.

## Exact qualification and deployment

| Item | Verified identity/result |
|---|---|
| Executable feature commit | `948a006a241603ba8364449cd9dfdaf81b1bb3e4` |
| Executable tree | `7fb2118d46b3730453eb6627ffec9333aaa8d439` |
| Core addon tree / version | `1aaf301bf57fbf5f479d1d013d4c40a625ee3fbc` / 19.0.1.4.2 |
| Finance addon tree / version | `7df8ae98326751406f665a75ed9e938b70156862` / 19.0.1.4.0 |
| Development build | **38418408**, 65 tests, zero failures/errors, 209.40 seconds, 67,411 queries |
| Controller checks | **37 passed**; XML/Python parsing and diff checks passed |
| Staging commit / tree | `9af98d4248090f2be3ceefb5d59bca36258b7c3a` / `2f33a66be48f77bc18f02eff780359a02483bc59` |
| Staging build | **38419464**, dashboard-only source update; explicit two-module upgrade completed |
| Recovery backup | 2026-09-21 18:56:40 UTC, preserving staging `65ccfa9c73effc133b2dfda5d89fe50e78e3ac7a`; reverified before deployment |
| Harness pin | `10ec1d059b5ddc5d422875f68e0726cc500487ce`, unchanged; external-resources-verified check passed during recovery |

The staging commit replaces only the two qualified dashboard addon trees. A Git
diff against its parent contains five paths, all within those addons. All unrelated
staging code is preserved. No test fixture products were introduced into staging.
The upgrade loaded both modules and the registry successfully. Odoo.sh's Warning
includes the pre-existing duplicate Human Resources settings label shared with
Documents HR; it is not a failed upgrade. HR remains disabled.

## Build diagnosis and corrections

Build 38415971 was inspected at its actual source `daf1280`, independently of
build 38415574 at `c17dd27e`. Both had empty install logs and uninitialized
databases; startup failed before dashboard module installation (`ir.http`/missing
module-table symptoms). These were provisioning/platform failures, not browser
assertion failures. One supported rebuild at the same addon trees succeeded as
38417323, with 65 tests passing and 240 retained screenshots.

Independent review closed the RTL stock identity clipping but found a separate
Medium: the Arabic overview's balance-cutoff date split at 390px in both themes.
The final successor applies the shared no-wrap date class to the three applied
summary dates and asserts each occupies one rendered rectangle. It does not change
dates, financial calculations, authoritative reports, mappings, ACLs or business data.

## Rendered evidence and independent review

Build 38418408 retained **240 original PNGs**, ten surfaces per combination of
English/Arabic × native Light/Dark × 320/390/768/1024/1440/1920. The manifest has
24 cases; all 240 sizes and SHA-256 hashes were verified independently. Populated
stock evidence uses 27 rollback-isolated native development fixture products.

Archive: `dashboard-polish-38418408.zip`, SHA-256
`b2871eb41483e93746727f7c101b84e7f7258e0a1877db51f53244c6eebf1070`.
Durable private evidence ID: `libfile_ed8abc8114708191b7838fa03c7b8761`.

The separate reviewer inspected all 40 contact sheets and selected full-resolution
Arabic overview/stock originals at 320/390/768/1024 across both themes. Both Medium
findings are **closed**. No remaining Critical, High or Medium finding was identified
in the final development matrix. This approval is source-bound and is distinct
from owner acceptance. The mobile matrix is actual browser evidence; desktop
staging screenshots are not presented as mobile verification.

## Live staging checks

- Finance, Sales, CRM, Inventory and Purchase load and navigate. HR stays hidden.
- At company Adams For Men, period 2026-09-01–2026-09-21 and balance cutoff
  2026-09-21, all **21 displayed metrics, 21 cash-account rows and the entire
  cash-flow bridge match the retained before-change JSON exactly**.
- Finance source/definition drawer, collapsed technical disclosure, native P&L
  with matching values and visible report warnings, and dashboard return checked.
- Sales recent orders/quotations, distinct invoice/order salesperson rankings,
  product/customer rankings, Top 5/10 and quantity ranking with PCS checked.
  Saving a Top 10 quantity/quotation view, changing it, and restoring it recovered
  the selections. Default Top 5/value/orders selections were saved afterward.
- Inventory populated product/location table, numbered page 2 (25 rows), product
  filtering, historical 2026-09-20 stock, source report and return retaining product
  and date checked. Independent zero/negative toggles were exercised: hiding
  negatives reduced current matches from 345 to 315; allowing zeros while still
  hiding negatives exposed 36,800 matches. Defaults restored.
- Purchase awaiting approval shows a truthful empty state; late receipts shows
  one existing order. CRM's empty pipeline remains explicit. Loading states were
  observed. Error/retry behavior is covered by the controller/native campaign;
  no artificial staging service failure was injected.
- Global search finds existing S00156 and shows empty document groups correctly.
  Source drawers and search close correctly. English and Arabic CSV downloads
  and print previews contain the real scoped values and translated headings.
- English/Arabic and native Light/Dark inspected on staging. Current desktop
  screenshots retained. Expand/collapse and saved-view restoration checked.

Final settled readback confirms English (US), left-to-right, Dark, HR absent,
Top 5 and the saved September 1–21 period/cutoff. Both downloaded summary CSVs
contain 26 data rows after HR is disabled; English and Arabic values agree.

The session crossed midnight: theme/language reloads defaulted to September 22.
Numeric preservation comparison was explicitly performed at the original
September 21 scope. Later theme screenshots document their displayed dates and
are not used for the identical-date comparison.

## Final evidence receipt

`Adams_Dashboard_UAT_Ready_20260922.zip` contains the final native matrix,
eight actual staging captures, bilingual CSVs, before/after JSON comparisons,
qualification record, independent review and handoff snapshot.
SHA-256: `274db43ab193ff542b5c8d5b72d5aae529c1a64369c2bbd717dc9bc0cfd644ca`.
Durable private ID: `libfile_394d1840bc2481919442ac3b711fc9ed`.
This receipt was added after packaging; archived handoff files precede this receipt.
Separate final engineering review found no remaining Critical/High defect and no
new Medium finding; owner acceptance remains separate.

## Owner UAT boundaries

The owner should review the existing accounting warnings, unusual signed balances,
financial meaning, reference-design fit and normal business workflows. Those values
were preserved, not corrected or certified as financially complete. Missing budget
configuration and other unavailable sources remain labelled honestly. Printer-specific
pagination and customer-volume/concurrency qualification are not claimed.

The original HTML and reference PNGs were inspected; its file URL was rejected by
the earlier browser, so no interactive reference-HTML pass or pixel-identical claim
is made. The original checkpoint remains retained with its verified checksum.

The previous local branch history was preserved. After a later runtime cleanup
removed its parent Git metadata, surviving files were left untouched; a separate
checkout at the current remote feature head was used for this documentation.
Both surviving addon directories were compared to it and match exactly. No reset,
rebase, stash, force push or substitution of an older executable baseline occurred.
