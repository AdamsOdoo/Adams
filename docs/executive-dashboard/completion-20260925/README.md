# Executive dashboard completion pass — 25 September 2026

Status: **development candidate qualified locally; not yet on Adams For Men staging.**
PR #214 stays draft, open and unmerged. No production or `main` change.

## Candidate identity

| Item | Value |
| --- | --- |
| Application | Branch `feature/executive-dashboard-report-first`; the commit that adds this file |
| Modules | `adams_executive_dashboard` 19.0.1.8.0, `adams_dashboard_finance` 19.0.1.8.0 |
| Base of this pass | `5810b092` (19.0.1.7.0 staging record); the first commit on top only adopts shared odoo-harness 1.2.1 tooling |
| Local runtime | Odoo 19.0 Community `8d05257d83f9`, Python 3.12.3, disposable databases with Odoo demo data (no customer data) |
| Harness | odoo-harness 1.2.1 (`MostafaEssamm12/Odoo` `176f0731`), used unchanged |
| Approved design | `Adams_Dashboard_UI_Proposal.html` (SHA-256 `36ec9583…2d7f4a`) plus the HR and company-branding addendum |

## What changed

Fourteen grouped root causes, each fixed once for every department — see [root-causes.md](root-causes.md).
In short: lists reload after Refresh, a period change, a company switch or a return from a native record;
the dashboard has a portable, shareable address (`/odoo/executive-dashboard`) that survives reload and
Back; unavailable states say why and offer Retry only when it can work; HR filters are complete on every
tab; copy, number formats, initials, long company names, Arabic selectors and the More menu match the
approved design; the Odoo 19 field-access API is used without weakening security; the app has an icon;
employee list links open the Employees list instead of a blank form; a company switch keeps the HR tab;
long names no longer run over neighbouring columns or out of the rail; restoring a saved view on Inventory applies its
filters; and the approved right-to-left rules now apply in Arabic (Odoo marks right-to-left pages with a body class,
not a `dir` attribute).

Intentional differences from the approved HTML are listed with their user benefit in
[deviations.md](deviations.md) (D01–D18).

## Results on the final build

| Check | Result |
| --- | --- |
| Frontend controller tests (`node --test`) | 92 of 92 pass; each new test fails on the previous code |
| Native Odoo tests, fresh database | 89 tests, 0 failures, 0 errors; 6 skipped (4 need Enterprise Planning, 2 need optional Manufacturing kits) |
| Full control sweep, 1440 px English | 360 of 360 controls reach a terminal outcome: 181 change the view, 61 open the standard Odoo view or report, 38 open a drawer or dialog, 31 reload data, 22 filter fields take effect with Apply, 17 are disabled with a stated reason (first page, nothing to apply, report not configured), 10 are the link to the department already shown |
| Drawer, dialog, menu and revealed-panel sweep | 112 of 112: 39 change state, 29 close their container, 20 open a further dialog, 10 download, 8 open a standard Odoo view, 5 are disabled with a reason, 1 is a draft field |
| Targeted browser checks (URL, Back, reload, invalid input, menus, company switch, search, breadcrumb return, app icon, Arabic) | 66 of 66 pass |
| Role journeys (dashboard viewer without source rights; internal user without the dashboard) | 12 of 12 pass |
| Data reconciliation | 53 of 53 figures match their native source for 1–25 Sep and 1 Jan–25 Sep 2026, and 17 of 17 stock rows; see [data-reconciliation.md](data-reconciliation.md) |
| Bounds check (no content over a neighbouring column or out of its container) | No spills on any department or HR tab at 390, 768, 1024 and 1440 px in English and at 390 and 1440 px in Arabic |
| Paired captures, approved HTML vs Odoo, all 10 department and HR views | 70 pairs (English light at 1440, 1024, 768 and 390 px; English dark approximation at 1440 px; Arabic at 1440 and 390 px), inspected; the differences are the documented deviations and the local Community states |
| Browser journal during every run | No console errors, page errors, failed RPCs or failed requests from the application |

The coverage ledger, [coverage-inventory.csv](coverage-inventory.csv) with totals in
[coverage-summary.json](coverage-summary.json), gives every operated control and every approved-HTML
element a terminal disposition: 718 rows — 628 pass (all 472 operated controls, 105 approved-HTML controls with an operated counterpart and 51 of 54 components), 77 are blocked on Enterprise-only sources (45 Finance, 31 Planning/Shifts, 1 Procurement supplier-payment link), 12 are not applicable (prototype-only explanation links; the UI20 count cards, owner decision) and 1 is conditional (Time off "Review request" is the operated "View request" action for requests awaiting approval). Record-level labels are reduced to their group, so the ledger
carries no business data.

## Not verified in this pass

- **Finance (Enterprise).** Every Finance figure, the chart, Bank & cash, aging, supplier windows, cash
  forecast and balance sheet use Enterprise `account_reports` through `adams_dashboard_finance`, which cannot
  be installed in the local Community runtime. Locally the Finance area shows its truthful not-installed and
  not-configured states. Check these surfaces on the Odoo.sh development build and on staging.
- **Planning (Enterprise).** Shifts content needs Enterprise Planning. Locally every Shifts view shows
  "Planning is not installed". Adams For Men staging does not have Planning installed either.
- **Dark mode.** Community has no dark scheme, so the local dark captures are an approximation (see the
  caveat in [deviations.md](deviations.md)). Enterprise dark mode on Odoo.sh is the acceptance surface.
  Arabic dark was not rendered locally.

## Owner decisions still open

1. **HR counts for users without HR rights.** Attendances and Time Off follow Odoo's record rules, so such a
   user sees counts of the records they may read (often 0) while the employee snapshot says "Access
   restricted". The addendum requires record rules for aggregates too, so this is the designed behaviour.
   Keep it, or show "Access restricted" on those cards as well?
2. Items carried from the [24 September handoff](../handoff-20260924.md) remain as recorded there: quotation
   badge colours follow the native quotation state; Time off keeps the real Second approval and Cancelled
   statuses; UI20 procurement amounts stay deferred; Bank & cash keeps disclosing unmapped accounts.

## Owner review

The candidate runs on the Odoo.sh **development build** of this branch (Odoo.sh builds every push; open the
branch in the Odoo.sh project and use *Connect*), at `/odoo/executive-dashboard`. The Adams For Men staging
URL, <https://adamsmen-staging-38326320.dev.odoo.com/odoo/executive-dashboard>, still runs 19.0.1.7.0 until
the owner promotes this candidate:

1. On Odoo.sh, confirm the development build of this commit is green, including its Enterprise tests.
2. Take a staging backup, then copy only the two addon trees to staging:

   ```
   git fetch origin staging feature/executive-dashboard-report-first
   git checkout -B stage-dashboard origin/staging
   git checkout <this commit> -- addons/adams_executive_dashboard addons/adams_dashboard_finance
   git commit -m "Stage dashboard 19.0.1.8.0 from <this commit>"
   git push origin HEAD:staging
   ```

3. Confirm both modules show 19.0.1.8.0 on staging, then follow the journey below.

## Owner test journey (about 15 minutes)

1. Open **Executive Dashboard** from the apps menu (new icon). Check the company name and logo, then set
   **Period** to Year to date. Copy the address, open it in a new tab: the same department and period appear.
2. In **Sales**, open a figure, then press the browser Back button: you return to Sales with the same period.
3. Press **Refresh** on Sales, Inventory and Procurement: the delivery table, the stock table and the
   late-receipts worklist reload instead of staying blank.
4. In **CRM**, open an opportunity, then click *Executive Dashboard* in the breadcrumb: the opportunities
   list is shown again.
5. Open **More**: press Escape (focus returns to More), reopen and click outside it (it closes), and use the
   arrow keys.
6. In **HR → Time off**, switch company in the HR period bar: you stay on Time off with the filters reset.
   Switch back.
7. In **HR → Employees**, choose a department right after opening the tab, then use **Open Employees**: the
   Employees list opens (not a blank form). Return with Back.
8. On staging (Enterprise), check Finance: figures, chart, Bank & cash and aging drawers. Report warnings
   must stay visible where the native reports have them.
9. Repeat steps 1–5 in Arabic, in dark mode and on a phone.

## Evidence

Detailed evidence (paired screenshots, sweep journals, browser-check results, test logs, reconciliation
output, the scripts that produced them) is kept privately, outside GitHub, with SHA-256 checksums that were
read back. The repository keeps only these sanitized summaries.
