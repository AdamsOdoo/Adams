# Decisions needed to finish the full v4 scope

Status: Decision 1 approved below; all other proposals remain unapproved. This records the material business choices required
by sections 2.2 and 2.5 of the supplied v4 contract. It does not narrow acceptance.
Developer configuration/testing and owner acceptance remain separate.

## Decision 1 — approved UAT company and environment

The owner selected **Adams for Men**, using a test copy of the actual business
company for UAT, and explicitly authorized deployment to **staging**.
**No production actions are authorized.** This supersedes the earlier
development-only / staging-excluded boundary for this dashboard's UAT work.
It does not authorize a main/production merge or approve financial definitions.

Staging deployment is authorized but has not yet been performed. Preserve existing
staging work and verify the selected company's identity, native currency,
localization, reports and permissions before treating its figures as UAT evidence.
The US/USD demo company is not the chosen business UAT company.
The owner requested the remaining decisions one at a time.

## Financial report policy

The current development build is a disposable US demo company, in USD. It is not
the customer's approved reporting setup. Full Accounting was activated and native
report access verified on build 38345613; the mapping list is empty. No definition
has been approved on the owner's behalf.

Recommended policy to review: one authorized company at a time; posted entries;
its native reporting currency; the exact installed/localized P&L and Balance Sheet
variants approved by Finance; native aging by maturity date at the selected cutoff;
native CFS and General Ledger for cash detail; native Executive Summary ratios and
short-term forecast only when their report dependencies align with the approved
statements. Budgets remain unavailable until a specific company budget is selected.
Never infer financial close/completeness from a successful report calculation.

The finance owner must identify the UAT company, confirm these policies, and select
and approve each native definition in Accounting → Configuration → Dashboard
Financial Definitions. Every approval fingerprints the selected native definitions;
subsequent definition changes invalidate it. Developers can prepare draft mappings,
but must not click approval as a substitute for that decision.

## Additional measures

| Requested outcome | Current native source and gap | Proposed decision for owner review |
|---|---|---|
| Daily cash outlook / minimum cash | Standard Executive Summary short-term forecast is available; it is not a dated receipt/payment schedule | Use the standard forecast for the initial scope, or approve a separate dated plan with explicit receipts, obligations, installment/currency rules and deduplication of PO/bill/payment. A daily plan requires additional development and testing. |
| Payments due in 7 / 30 days | Native aging has maturity buckets but the requested exact forward windows have not been qualified | Use native open maturity amounts, not invoice-header dates/current residuals. Define whether windows overlap (1–7 and 1–30), overdue is separate, due-today handling, credits and which non-supplier obligations are included. |
| Remaining backlog value | Native ordered/delivered/remaining quantities are implemented; there is no approved value/history rule | Define goods-only versus services/kits, returns/overdelivery/cancellations, discounted untaxed price, native currency and current versus historical cutoff. Native quantity views remain available. |
| On-time completion | Native first-delivery date is not final completion; original-promise coverage is unverified | Choose transfer/order/line denominator, dispatch versus customer receipt, original deadline and timezone/grace period, partials/returns and missing-history treatment. Show coverage and N/A for no denominator. |
| Management attention | Native purchase approval/late-receipt worklists are implemented; executive materiality/owner rules are undefined | Identify thresholds, responsible role and actionable native route per alert. Do not invent red/green risk badges from sample data. |
| Stock aging / shortage exposure | Native dated valuation and current forecast routes are implemented; aging/nonmovement and exposure definitions are not equivalent | Choose receipt age versus last movement; owned versus consigned stock; product/warehouse scope; physical versus projected shortage and forecast horizon. Reuse the native report where the definition matches. |
| Targets and historical comparisons | Native financial budgets and signed monthly trends are implemented | Select approved budgets and explicit comparable dates. Missing commercial targets or original historical events remain unavailable, never inferred from actuals. |

The owner may approve explicit definitions or defer named extra measures from the
first UAT scope. Until that decision is recorded, the full v4 requirement remains
open. A deferral must be explicit; an unavailable widget is not completed scope.
