# Executive dashboard — final staged testing handover

**Staging is available for owner hands-on testing. Formal owner UAT is not yet ready for sign-off.** The implementation, exact native suite and staged technical checks pass. Three source-dependent business decisions (UI07, UI08, UI20) and owner acceptance remain open. This handover does not authorize a PR merge, production upgrade or main-branch change.

## Exact source and deployment

| Identity | Verified value |
|---|---|
| Repository / review | `AdamsOdoo/Adams`, draft PR [#214](https://github.com/AdamsOdoo/Adams/pull/214); feature `feature/executive-dashboard-report-first`. |
| Final application HEAD | `b9461b76f3b1a1e1085fda87d55f6ef66ecca9b9`. |
| Core / finance addon trees | `78710c2fc2334379aedc44939968d9a4e818f8ab` / `a01fdad4fcc866e02093c3c115d4c71432902313`. |
| Development qualification | Odoo.sh build **38514095**; 120/120 native post-tests, zero failures/errors, 403.75s / 118,807 queries; 65/65 focused frontend checks. |
| Staging application | `28b37d90d77571383b37e70212681e9730d5cf40`, running build **38326320**, clean matching addon trees, `adams_executive_dashboard` and `adams_dashboard_finance` both installed **19.0.1.5.0**. Odoo build reports **19.0+e**. |
| Recovery/deployment | Manual staging backup **2026-09-23 05:34:26 UTC**; dashboard-only upgrade successful **06:16:25 UTC**. The optional HR apps were not installed. |
| Approved HTML | SHA-256 `36ec95831f3f1e82e0709594d5c177938e3b3805ccd763b1e59c13933b2d7f4a`; six departments, five HR tabs, UI01–UI38. |

The final translation/test delta left calculation code unchanged from the preceding staged backend candidate. Its **34/34 independent read-only checks** (Finance 9; Procurement/CRM 5; Inventory/HR 5; preservation/performance 12; stock prefilter 3) remain explicitly bound to that preceding backend source. The final frontend/native browser campaign and actual staging interactions are separately bound to the identities above. Do not relabel the 34 raw probe records as a new run on the final tree.

## Technical evidence and scope

- Native development campaign: 120 passing post-tests; English/Arabic × Odoo light/dark × seven actual viewports produced **28 browser cases, 532 PNG screenshots and four actual dashboard PDFs**. Passing assertions and retained captures do not alone prove every pixel matched the reference.
- Real staging: all six departments and five HR views operated. Actual Partner Ledger and other standard report/source links, native Aged Receivable XLSX/PDF signed reconciliation, dashboard exports, desktop Inventory Category plus working Source data, native valuation/forecast links, and permitted employee work-profile source were observed. The previously observed Partner Ledger click interception, missing Category column and populated Employees Owl crash no longer reproduce on the final source.
- Performance: retained matched three-repeat ORM stock current page one **10.818→1.116s / 4,391→694 queries**; page two **11.205→1.068s / 4,404→672**; historical **21.745→1.918s / 4,379→662**. Final staging RPC samples: Inventory median **0.772s / 716 queries (n=3)**; bootstrap median **0.009s / 4 queries (n=6)**. Backend caches were invalidated for ORM repetitions; DB buffers, browser rendering and network time were not controlled by these figures. No after-the-fact acceptance threshold was invented.
- Permissions: native tests exercise dashboard-denied, source-specific, record/field and company boundaries without adding source access through dashboard membership. Staging had only one authorized company. Attendance, Time Off and Planning were uninstalled, and their tabs displayed honest missing-app states; native populated fixtures cover their rules but this staging cannot demonstrate those live workflows or a second-company switch.

Private evidence is retained separately from repository documentation. The exact archive and index are:

| Private artifact | Identity and contents |
|---|---|
| `Adams_Dashboard_Private_Qualification_20260923.zip` | SHA-256 **`59f86fa3908688b1bec4b2e305d495f7bf2cb915f81b9ad0daf09f2a790b4b75`**; Library ID `libfile_58020b0171cc8191acb693c535dac7a6`, **version 1** (corrected finance tree). ZIP integrity and `INDEX.json` source/tree identities were checked. Earlier version/hash is superseded. |
| Development native/browser | Build38514095 four actual dashboard PDFs and native screenshot manifest, plus six selected PNG bytes. The full 532 images and full native test log remain in private development-build artifacts; the compact Library ZIP indexes the complete capture set without duplicating it. |
| Paired screenshots | **15 HTML/Odoo pairs**: all six departments, five HR tabs, employee profile and four Arabic/dark combinations. Every pair's screenshot paths/source are indexed privately. These do not cover every menu, error state or responsive width. |
| Staging and reconciliation | Exact stage source/upgrade metadata, actual summary CSV and native Aged Receivable XLSX/PDF, source-bound signed report comparison, five raw backend-identical probe JSONs totaling 34 checks, controlled performance results and exercised dashboard print preview. A staged dashboard print PDF is **not** included. Customer names, amounts, employee records and Enterprise internals remain private. |

The sanitized task [closure ledger](closure-ledger.md), [UI parity matrix](ui-parity-matrix.md), [qualification checkpoint](qualification-checkpoint.md), [implementation status](../implementation-status.md) and [UAT checklist](../uat-checklist.md) are the public navigational index. The report-first handover ZIP and raw customer/Enterprise files stay private. Historical audits and older successful builds remain source-bound to their own commits.

## Owner entry and decisions

Open the [Adams For Men staging dashboard](https://adamsmen-staging-38326320.dev.odoo.com/odoo/action-1004) with your authorized Odoo account. Start with Finance report values and signed overdue; then Sales rankings and fulfillment, Inventory product/location/cutoff/negative stock, Procurement and CRM source rows, and all five HR tabs. Test saved selections, dates, filters, numbered pages, source return and actual PDF/CSV output. Compare English/Arabic, Odoo light/dark, desktop/narrow widths, scrolling and company identity against the approved HTML. [The detailed walkthrough](../uat-checklist.md) gives the expected report meanings and issue-recording fields. On this staging account, only one company is authorized and the three optional HR applications are absent; observe those capability states rather than creating test business apps or a second company just to fill cards.

The owner still needs to settle three precise points before **READY FOR OWNER UAT** may be declared:

1. **UI07 comparable period:** approve the period and percentage/baseline semantics for custom dates, partial months, YTD and zero/negative prior results, or accept the truthful “comparison not configured” state.
2. **UI08 bank versus cash:** identify an authoritative source/account-journal classification, including ambiguous associations, or explicitly accept the combined signed native cash total and account directory.
3. **UI20 purchase attention:** accept native approval/late-receipt **order counts** as labelled worklists, or approve an exact source-based amount, currency and date rule for the prototype's monetary figures.

These questions concern new business definitions and explicit source-dependent parity dispositions. The approved HTML design itself does not need reapproval. Owner acceptance, draft-PR disposition and production release are separate future decisions. Main and production remain untouched.
