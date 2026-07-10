# MBQ-05 Branch B — Next-Implementation Implications

> **Status: [Recommendation] per `CLAUDE.md` §8. Docs-only. Does not
> authorize any implementation, does not open any gate.** Prepared
> 2026-07-10, companion to
> [`../03-architecture/mbq-05-branch-b-final-decision-brief.md`](../03-architecture/mbq-05-branch-b-final-decision-brief.md)
> and
> [`../04-decisions/DEC-026-distribution-auth-branch-b-proposal.md`](../04-decisions/DEC-026-distribution-auth-branch-b-proposal.md).
> This document lists which future implementation tasks become possible
> or remain blocked **depending on which branch B outcome ChatGPT
> eventually accepts** — it does not itself authorize any of them, and it
> does not change any task's current gate status. Every row below is
> conditional on its stated "if accepted" premise; none is triggered by
> this document.
>
> **Status-refresh note (2026-07-10, DEC-026 acceptance session — records
> the already-made acceptance fact only, does not authorize anything
> new):** ChatGPT has accepted DEC-026's hybrid recommendation (see that
> document's "Acceptance note") as the strategic branch-B direction — the
> "**If the hybrid recommendation … is accepted**" / "**If DEC-026's
> hybrid recommendation (B-1 + continued branch A) is accepted**" rows
> below are therefore the now-operative outcome at *strategic-direction*
> level. This does **not** trigger, authorize, or gate-open any row's
> implication — every row still requires its own separate, explicit
> ChatGPT gate-opening act and final implementation prompt, and the five
> prerequisites named in DEC-026's Acceptance note (MBQ-04, OP-23/Q27,
> OP-46, the RA-003 deferral-lift act, and OP-45) remain open.

## 0. Baseline that does not change regardless of outcome

- **Tasks 011–015 (customer, order, inventory, fulfillment, product
  export/update) are distribution-agnostic by construction.** No branch B
  outcome adds, removes, or modifies any file, model, or test in these
  tasks — re-confirmed unchanged by the 2026-07-10 research session. This
  document does not alter that conclusion.
- **DEC-023 branch A (Custom Distribution, one-store/same-Plus-org/
  private-customer/VAL-B2-evidence) keeps working exactly as accepted**
  under every outcome below, including if DEC-026 is rejected outright.
- **No implementation is authorized by this document under any outcome.**
  Every row below requires its own separate, explicit ChatGPT gate-
  opening act and final implementation prompt, per the standard
  two-step pattern (`CLAUDE.md` §9; `research-handoff.md` prior-task
  precedent).

## 1. OAuth / token-acquisition implementation

| Outcome | Implication |
| --- | --- |
| **If DEC-026's hybrid recommendation (B-1 + continued branch A) is accepted** | Two structurally distinct token-acquisition paths become implementation candidates: (1) branch A's existing manually-completed authorization-code-grant exchange against a cross-organization Custom Distribution app (already-accepted mechanics, `token_variant='offline_custom_app'`); (2) a new, separate OAuth implementation for the public app — authorization-code-grant (if standalone) or App-Bridge token exchange (if admin-embedded), requiring a new credential-model extension (a new `token_variant` value or a parallel client-ID/secret/refresh-token shape) that MBQ-04's seam is designed to absorb but has not yet been designed for. **Not authorized by this document** — needs its own dedicated task spec, gated separately, only after ChatGPT lifts RA-003's Phase-1 deferral for this specific surface. |
| **If B-3 alone (per-client custom apps) is accepted for commercial scale** | No new OAuth *mechanism* beyond branch A's existing shape — but a *volume* problem: each new commercial customer requires its own manually-completed exchange, with no self-serve reconnect flow designed yet. A future task would need to scope the per-client onboarding/credential-rotation process at N-customer scale, not just the token mechanics. |
| **If DEC-026 is rejected / MBQ-05 branch B remains undecided** | No OAuth implementation task of any kind may be opened for the many-unrelated-customer use case. Branch A's existing mechanics remain the only implementation-relevant path, for its already-accepted narrow scope only. |

## 2. Setup wizard

| Outcome | Implication |
| --- | --- |
| **If the hybrid recommendation is accepted** | The wizard's OAuth-connect step (UI Group 3 / OP-26) needs a pluggable "connection method" abstraction (per the final decision brief §6) rather than one fixed flow — a design principle a future wizard task spec should adopt, not something this document authorizes building now. The billing-approval interstitial (Shopify's `AppSubscription` confirmation URL) becomes a required step in the public-app connection path specifically. |
| **If B-3 alone is accepted** | The wizard needs to resolve the per-client app-bootstrap question (vendor pre-provisions vs. client self-serve Dev Dashboard app creation) before an OAuth-connect step can be spec'd at commercial scale — currently unresolved. |
| **If undecided** | The wizard's OAuth-connect step remains entirely unspec'd beyond DEC-004's general multi-step credential-flow framing; OP-26 stays blocked on OP-05's outcome, as already recorded. |

## 3. Store-connection UX

| Outcome | Implication |
| --- | --- |
| **If the hybrid recommendation is accepted** | Store-connection UX (readiness checks, test-connection, reconnect/disconnect) must support two coexisting connection *kinds* (custom-app credential vs. public-app OAuth session) permanently, per the final decision brief's finding that the two populations never converge. This is a materially larger UX surface than DEC-012's original single-flow assumption. |
| **If B-3 alone is accepted** | Store-connection UX stays single-kind (custom-app credential only), but must scale its reconnect/rotation flow across many independently-registered per-client apps rather than one shared app. |
| **If undecided** | No change — store-connection UX design work for the many-unrelated-customer case cannot proceed past DEC-004's existing framing. |

## 4. App review / compliance webhooks

| Outcome | Implication |
| --- | --- |
| **If the hybrid recommendation (public-app half) is ever pursued for implementation** | Three mandatory compliance webhooks (`customers/data_request`, `customers/redact`, `shop/redact`, 30-day response) become a required implementation task — currently kept non-MVP under the accepted MBQ-09 posture. This reopens that deferral for a dedicated, separately-gated webhook task; it is **not** reopened by this document or by DEC-026 alone. |
| **If B-3 alone (custom apps only) is accepted** | No Shopify-mandated compliance webhook obligation exists (documented as required "for apps listed on the Shopify App Store" only) — general data-subject-rights duties under applicable privacy law toward each client's end customers may still exist independent of Shopify's own app-review mechanism, but that is a legal question outside Shopify's app-review mechanics and outside this document's scope. |
| **If undecided** | No compliance-webhook implementation task may be opened for the many-unrelated-customer case. |

## 5. Protected Customer Data (PCD) governance

| Outcome | Implication |
| --- | --- |
| **If the hybrid recommendation (public-app half) is ever pursued for implementation** | PCD Level 1 (9 items) + Level 2 (7 items) become review-enforced requirements — encryption at rest/in transit/backups, retention limits, test/prod data separation, a data-loss-prevention strategy, staff-access limits plus an access log, and an incident-response policy. **Two of these directly interact with the already-accepted MBQ-04/Task 002 credential posture** (plain `Char` + ACL, no encryption claim) and cannot be implemented without a dedicated DEC resolving that tension first — named as a hard prerequisite in the final decision brief §1.1 and DEC-026 §9, not resolved by this document. |
| **If B-3 alone (custom apps only) is accepted** | PCD Level 1/2 remain "Always available" — no review-enforced obligations from Shopify. The project's existing conservative posture (minimal-field import, ACL-restricted logs, no PII invention) already satisfies most Level 1 good-practice items without a Shopify mandate forcing it. |
| **If undecided** | No PCD governance work beyond the current branch-A posture (already sufficient for Tasks 011/012's imported fields) is required or authorized. |

## 6. Billing / commercial packaging

| Outcome | Implication |
| --- | --- |
| **If the hybrid recommendation (public-app half) is ever pursued for implementation** | A Shopify Billing API / `AppSubscription` / `AppPurchaseOneTime` integration becomes a required implementation task, entirely new engineering scope, plus the Shopify revenue-share/fee question (currently unsourced) must be resolved before finalizing pricing. This task cannot start before OP-23/Q27 (Lite/Full mechanism) is answered, since the packaging shape determines the `AppSubscription` line-item design. |
| **If B-3 alone (custom apps only) is accepted** | No Shopify-provided billing mechanism is available at all — a fully off-platform billing/invoicing system (vendor-built or a PSP) becomes required engineering scope instead, scaling linearly with customer count, with no Shopify-native fallback ever. |
| **If the hybrid is accepted** (both halves active) | Both billing systems must be built, operated, and reconciled **permanently in parallel** for their respective customer populations — this is additive cost, not a temporary dual-run during a migration window, since no migration path exists between the two populations. |
| **If undecided** | No billing-integration task of any kind may be opened for the many-unrelated-customer case; the existing off-platform assumption for branch-A pilot customers is unaffected. |

## 7. Lite/Full packaging

| Outcome | Implication |
| --- | --- |
| **If the hybrid recommendation is accepted, and OP-23/Q27 favors a flags-based mechanism** | Lite/Full tiers could map onto Shopify `AppSubscription` line items (recurring and/or usage-based) gating the connector's existing `product_domain_enabled`/`sale_domain_enabled`/etc. settings — a technically well-supported mapping, per the final decision brief §7. This mapping is a **hypothesis for a future OP-23 task to evaluate, not a packaging decision made here.** |
| **If B-3 alone (custom apps only) is accepted** | Lite/Full packaging is fully decoupled from any Shopify billing surface — it would be implemented entirely through the vendor's own off-platform licensing/subscription record, independent of which Shopify app variant a client has installed. |
| **If undecided** | OP-23/Q27 remains blocked at framing level regardless — this document does not resolve it and explicitly sequences the Lite/Full task after (or jointly with) the branch B decision, matching the existing register's own sequencing note. |

## 8. Release readiness

| Outcome | Implication |
| --- | --- |
| **If the hybrid recommendation (public-app half) is ever pursued for implementation** | The release-readiness checklist (OP-30) gains new, currently-unexecuted items: App Store submission and review-pass evidence, the mandatory support-email channel being live and monitored, an emergency developer contact on file, PCD Level 2 review approval, and the three compliance webhooks passing live-scenario tests. No official review-turnaround SLA exists, so this introduces unbounded, undocumented launch-timeline risk that the release roadmap should carry explicitly, not silently assume away. |
| **If B-3 alone (custom apps only) is accepted** | Release readiness for the distribution/auth dimension stays scoped to VAL-B2's existing evidence requirement (already tracked) — no App Store review dependency is introduced. |
| **If undecided** | OP-30's distribution/packaging-dependent items remain unanswerable, as already recorded in the release-readiness map §3. |

## 9. UAT implications

| Outcome | Implication |
| --- | --- |
| **If the hybrid recommendation (public-app half) is ever pursued for implementation** | New UAT scenarios become necessary and currently do not exist: a full public-app OAuth-connect flow (authorization-code-grant or token-exchange), a billing-approval interstitial walkthrough, and at least one live-fired compliance-webhook scenario per mandatory topic (`customers/data_request`, `customers/redact`, `shop/redact`). These would extend the existing UAT gap analysis (currently 0/15 scenarios executable) with additional, distribution-specific scenarios not yet scoped anywhere. |
| **If B-3 alone (custom apps only) is accepted** | UAT scope for connection/auth stays limited to the existing VAL-B2 scenario (custom-app token acquisition and test-connection), already tracked in the UAT gap analysis. |
| **If undecided** | No new UAT scenario planning for the many-unrelated-customer case is authorized or needed yet. |

## 10. Sequencing summary (not authorized — for future roadmap reference only)

Regardless of which outcome ChatGPT eventually accepts, the dependency
order among the above areas is: **branch B decision (this package) →
MBQ-04 encryption-posture DEC + OP-23/Q27 answer → RA-003 Phase-1-
deferral-lift act (public-app half only) → OAuth/wizard implementation
task → billing-integration task (public-app half only) → compliance-
webhook task (public-app half only) → PCD Level 2 review execution
(public-app half only) → release-readiness checklist execution → UAT
execution.** No step in this chain is triggered, started, or shortened
by this document.

## Evidence / references

- [`../03-architecture/mbq-05-branch-b-final-decision-brief.md`](../03-architecture/mbq-05-branch-b-final-decision-brief.md)
- [`../04-decisions/DEC-026-distribution-auth-branch-b-proposal.md`](../04-decisions/DEC-026-distribution-auth-branch-b-proposal.md)
- [`../03-architecture/mbq-05-branch-b-distribution-auth-decision-brief.md`](../03-architecture/mbq-05-branch-b-distribution-auth-decision-brief.md)
  §7 (the original dependent-work table this document supersedes with
  outcome-conditional detail)
- [`../08-release-readiness/open-points-closure-register.md`](../08-release-readiness/open-points-closure-register.md)
  OP-05, OP-23, OP-26, OP-40
- [`../08-release-readiness/implementation-readiness-map.md`](../08-release-readiness/implementation-readiness-map.md)
  §3 (cross-cutting readiness layers)
- [`../08-release-readiness/uat-readiness-gap-analysis.md`](../08-release-readiness/uat-readiness-gap-analysis.md)
