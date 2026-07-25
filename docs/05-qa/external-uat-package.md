# External User-Acceptance Testing Package (executable)

> **Status: Executable UAT package. Docs-only — NOT an acceptance, and NOT
> authorisation to begin.** Produced 2026-07-25 on `fable/wave-5-completion`.
> **No session, no case and no sign-off in this package has been executed**, and
> no result in it is claimed.
>
> This package is written to be run by **people who did not build the
> connector** — that is the point of external UAT. It assumes no knowledge of
> the implementation and never asks a participant to inspect code.
>
> Residual alignment (issues are **not** modified by this package): external
> multi-user confirmation → [#197](https://github.com/AdamsOdoo/Adams/issues/197) ·
> live-Shopify prerequisites → [#185](https://github.com/AdamsOdoo/Adams/issues/185),
> [#200](https://github.com/AdamsOdoo/Adams/issues/200) · release/performance
> evidence → [#199](https://github.com/AdamsOdoo/Adams/issues/199).

## 1. Entry criteria — all must hold before session 1

| # | Criterion | Verified by |
| --- | --- | --- |
| U-E1 | The Shopify live-validation campaign ([`shopify-live-validation-package.md`](shopify-live-validation-package.md)) has completed with no open P0/P1 | Campaign run record |
| U-E2 | The exact release-candidate SHA is frozen and deployed to the UAT environment | Deployment record + SHA |
| U-E3 | Exact-SHA Odoo.sh runtime is green for that SHA | Odoo.sh build id |
| U-E4 | A disposable Shopify development store with synthetic data is available | #200 |
| U-E5 | Two named participants exist per role, on **separate** accounts (multi-user is the point — #197) | Participant roster |
| U-E6 | Every participant has read §4 (data handling) | Roster sign-off |
| U-E7 | A triage owner is on point for the whole window | Roster |

**If any entry criterion fails, UAT does not start.** A partial UAT is not UAT.

## 2. Roles, owners and responsibilities

| Role | Who | Responsibility |
| --- | --- | --- |
| **UAT lead** | Product owner or delegate | Runs the window, owns the exit decision recommendation |
| **Connector Administrator** (×2) | Business/ops staff | Setup, store connection, operating-mode decisions, role management |
| **Connector User** (×2) | Day-to-day operators | Sync, review, retry, error handling |
| **Observer / scribe** | Any | Captures evidence per §5; does not solve problems for participants |
| **Triage owner** | Engineering | Classifies findings per §7; does **not** coach participants mid-case |
| **Control room** | ChatGPT / product owner | Accepts or rejects the campaign. **Never the implementing session** |

**Rule:** nobody who implemented a surface may run its case, and no observer may
tell a participant where to click. A participant who cannot find a screen is a
**finding**, not a support call.

## 3. Environment and data

- A dedicated UAT Odoo database at the frozen SHA, with the connector installed
  from scratch (fresh install), plus a second run against a **warm upgrade** of
  a database that predates the release candidate.
- Two Odoo companies, each with its own store, so isolation is exercised by real
  users rather than by a test harness (#197).
- Synthetic fixtures only: `ADAMS-UAT-*` products, `@example.com` customers.
  **No real customer data enters the UAT environment.**

## 4. Data handling (read before session 1)

Participants must not paste real customer names, addresses, emails, phone
numbers or payment details anywhere. Screenshots must be reviewed before
attachment. No participant is ever shown, asked for, or expected to handle a
Shopify access token.

## 5. Evidence template — one per case

```
Case:            UAT-xx-nn
Participant:     <name>            Role: <Connector User | Administrator>
Date/time (UTC): <...>             Build SHA: <...>
Steps actually taken:
  1.
  2.
Expected (from this package):
Observed:
Result:          PASS | FAIL | BLOCKED | NOT EXECUTED
Severity (if not PASS): P0 | P1 | P2 | P3
Evidence:        <screenshot filenames, job ids, sanitized log excerpts>
Participant comment (verbatim, including confusion or hesitation):
```

**"Observed" is what happened, not what should have happened.** Hesitation and
wrong turns are recorded — they are the most valuable output of a UAT.

## 6. Cases

### 6.1 Setup and connection — `UAT-SET-*` (Administrator)

| # | Case | Expected outcome | Acceptance criterion |
| --- | --- | --- | --- |
| UAT-SET-1 | Install the connector on a clean database and find it in the UI | The app is discoverable without developer mode | Reached unaided in < 3 min |
| UAT-SET-2 | Create and connect a store using the guided path | Store reaches Connected | No developer mode, no code |
| UAT-SET-3 | Run Test Connection with a good credential | Clear success with the API version shown | Message understandable without support |
| UAT-SET-4 | Run Test Connection with a bad credential | Clear, non-technical failure reason; **no token shown** | Participant can say what to do next |
| UAT-SET-5 | Read the readiness checks and act on a failing one | Participant identifies and fixes the gap | Unaided |
| UAT-SET-6 | Warm-upgrade a pre-release database | Upgrade completes; existing data intact; screens work | Zero data loss |

### 6.2 Roles and access — `UAT-ROLE-*` (Administrator + User, #197)

| # | Case | Expected outcome | Acceptance criterion |
| --- | --- | --- | --- |
| UAT-ROLE-1 | Administrator assigns the Connector User role to a colleague | Exactly two customer-facing roles are offered | No internal group is exposed on the user form |
| UAT-ROLE-2 | Connector User opens the connector | Sees operational screens; **no** operating-mode control | Confirmed by the User, not by an admin |
| UAT-ROLE-3 | Connector User attempts an Administrator action | Refused with a clear message; nothing changes | Refusal is understandable |
| UAT-ROLE-4 | **Two users in different companies work simultaneously** | Neither sees the other's stores, orders, jobs or fulfilments | Live multi-user, separate sessions (#197) |
| UAT-ROLE-5 | A user outside every connector role logs in | The connector is not visible at all | Confirmed |

### 6.3 Day-to-day operation — `UAT-OPS-*` (Connector User)

| # | Case | Expected outcome | Acceptance criterion |
| --- | --- | --- | --- |
| UAT-OPS-1 | Trigger a manual sync and see it progress | Operator sees state change without refreshing the DB | Unaided |
| UAT-OPS-2 | Find when the next scheduled sync runs | Cadence is visible in the UI | Unaided |
| UAT-OPS-3 | Read a job log and explain what happened | Participant explains it in their own words | No developer mode |
| UAT-OPS-4 | Retry a failed job | Retry succeeds or fails with a clear reason | Unaided |
| UAT-OPS-5 | Cancel a job | Cancellation recorded with a reason | Unaided |
| UAT-OPS-6 | Resolve a manual-review job | Resolution recorded with an audit trail | Unaided |
| UAT-OPS-7 | Encounter a job with mutation evidence | Generic retry is **not** offered; the reason is clear | Participant does not attempt a blind resend |

### 6.4 Fulfillment operator experience (U1) — `UAT-FUL-*`

| # | Case | Expected outcome | Acceptance criterion |
| --- | --- | --- | --- |
| UAT-FUL-1 | Open the Review Workspace and find work needing a decision | Open cases are the default view | Unaided |
| UAT-FUL-2 | Explain what a review case is asking | Participant states the reason in their own words | Reason text is self-explanatory |
| UAT-FUL-3 | Acknowledge an externally-handled fulfilment | Case closes; **no** Odoo stock moves | Participant confirms no stock change |
| UAT-FUL-4 | Import tracking onto the Odoo delivery | Tracking appears on the delivery | Unaided |
| UAT-FUL-5 | Encounter the delivered/Odoo-mismatch case | Participant states that the carrier says delivered **but Odoo is not validated** | **The participant must not conclude the order is complete** |
| UAT-FUL-6 | Encounter an unknown status value | Participant understands it is unrecognised and not a success | Unaided |
| UAT-FUL-7 | Administrator reviews the mode-switch screen and decides | Consequences are understood before confirming | Participant can state what changes |
| UAT-FUL-8 | Administrator switches to Mode 2, then rolls back | Both complete; in-flight work is not lost | Unaided |
| UAT-FUL-9 | Attempt to release a blocked fulfilment whose outcome is uncertain | Refused, reconcile-only, clearly explained | **No blind resend is possible from the UI** |
| UAT-FUL-10 | Look for a "Delivered" status | It is not offered as a supported state anywhere | Participant reports its absence as expected |

### 6.5 Product, order, inventory — `UAT-DOM-*`

| # | Case | Expected outcome | Acceptance criterion |
| --- | --- | --- | --- |
| UAT-DOM-1 | Import products and confirm no duplicates | Counts match; re-run changes nothing | Unaided |
| UAT-DOM-2 | Import orders and reconcile one against Shopify | Totals, currency and lines agree | Unaided |
| UAT-DOM-3 | Change inventory in Odoo and see it in Shopify | Level matches | Unaided |
| UAT-DOM-4 | Introduce drift in Shopify and reconcile | A review case appears; nothing is silently overwritten | Participant confirms |
| UAT-DOM-5 | Configure mappings/settings from a screen | Completed without developer mode | Unaided |

### 6.6 Recovery and resilience — `UAT-REC-*`

| # | Case | Expected outcome | Acceptance criterion |
| --- | --- | --- | --- |
| UAT-REC-1 | Disconnect and reconnect a store | Sync resumes; no duplicates | Unaided |
| UAT-REC-2 | Work while the store is disconnecting | Operations refuse safely with a clear message | Unaided |
| UAT-REC-3 | Uninstall then reinstall the connector | Clean removal and reinstall; no residue | Verified by the triage owner |

### 6.7 Accessibility and presentation — `UAT-A11Y-*`

| # | Case | Expected outcome | Acceptance criterion |
| --- | --- | --- | --- |
| UAT-A11Y-1 | Complete UAT-FUL-1..3 using **keyboard only** | Every control reachable; focus always visible | No mouse |
| UAT-A11Y-2 | Complete a review decision with a screen reader | Dialogs announce; status regions announce | Screen-reader user |
| UAT-A11Y-3 | Use the connector at 390 px width | No horizontal scrolling of the page | Unaided |
| UAT-A11Y-4 | Use an RTL language | Layout mirrors correctly | Unaided |
| UAT-A11Y-5 | Distinguish severities without relying on colour | Severity readable as words | Greyscale check |

## 7. Severity, triage and retest

| Severity | Definition | Handling |
| --- | --- | --- |
| **P0** | Data loss, duplicate remote mutation, credential exposure, cross-company leak, or a participant able to trigger a blind resend | **Stop UAT.** Escalate immediately. Retest the whole affected area after the fix |
| **P1** | A participant cannot complete a core task unaided, or a documented contract is violated | Stop that area; consolidated correction; retest that area in full |
| **P2** | Misleading or confusing operator-visible behaviour | Record; continue; fix in the consolidated batch; retest the case |
| **P3** | Wording/cosmetic | Record; fix in pass; no retest cycle |

**Retest rule:** a fixed P0/P1 is retested **by a different participant** than
the one who found it. A P2 is retested by anyone. No finding is closed on the
implementer's assertion alone.

Findings are consolidated into **one** correction batch (DEC-041 D6), not
fixed one at a time mid-window.

## 8. Exit criteria

UAT is complete only when **all** of the following hold:

1. Every case is executed and recorded as PASS / FAIL / BLOCKED / NOT EXECUTED —
   no case is left blank or inferred.
2. **No P0 and no P1 remains open.**
3. Every P2 is either fixed and retested, or explicitly accepted by the product
   owner with a recorded reason.
4. Multi-user, multi-company isolation (UAT-ROLE-4) passed with **real
   simultaneous sessions** — the #197 external confirmation.
5. Both the fresh-install and warm-upgrade paths were exercised.
6. Accessibility cases §6.7 were executed by people who actually use those
   modalities where possible; any not executed is recorded as **NOT EXECUTED**,
   never as passed.
7. Every piece of evidence is sanitized, durable, and names the exact SHA.
8. The Shopify development store is cleaned up and the credential revoked.

## 9. Sign-off

| Sign-off | Who | Statement |
| --- | --- | --- |
| Functional | UAT lead | Every case executed; exit criteria 1–6 met |
| Evidence | Triage owner | Findings classified, consolidated and retested per §7 |
| Security / privacy | Named reviewer | No credential exposure, no cross-company leak, no real customer data used |
| **Release acceptance** | **Product owner / control room** | Accepts or rejects the release candidate |

**No implementing session may sign any row of this table.** UAT sign-off is not
release acceptance by itself: release acceptance is the product owner's separate
decision, recorded in the program trackers.
