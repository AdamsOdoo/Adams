# SEC-2 — Two-Role Migration & PII-Masking Simplification (implementation packet)

> **Status: Proposed — Fable gap-closure correction, 2026-07-16.** Acceptance
> authority: product owner + Claude control room. **This packet authorizes no
> implementation.** It is the controlled future task that reconciles the existing
> Wave-1 masking implementation with the binding product-owner direction of
> 2026-07-16 (PR #173 ruling `4994990296`): **PII masking is not part of the MVP.**
> Companion product definition: [`../02-product/connector-roles-and-permissions.md`](../02-product/connector-roles-and-permissions.md)
> (§3 no-masking; §4 4→2 migration). Template: [`../06-prompts/implementation-task-template.md`](../06-prompts/implementation-task-template.md).
>
> **Non-retroactive note.** Wave 1 was accepted and merged under the earlier
> SEC-1 decision; its masking implementation and runtime evidence stand and are
> not invalidated. SEC-2 is a **forward** correction to be completed **before MVP
> UAT/release**. Nothing here reopens Wave 1.

---

## A. Objective

1. Migrate the four internal customer-visible groups to **two customer-facing
   roles** — **Connector User** and **Connector Administrator** — with
   Administrator inheriting every User capability (roles doc §4, Option M-A).
2. Make the **raw** connector customer/order PII snapshot fields accessible to
   **both** final roles where their permitted operations require it.
3. **Remove PII masking from the MVP product surface** — the computed masked
   display, the manual masking action, and the scheduled masking of customer
   binding snapshot fields.
4. Preserve all unrelated SEC-1 security: protected-field enforcement, sanctioned
   sudo writers, company isolation, credential secrecy, and **log/audit
   redaction** (redaction is not masking and stays mandatory).

This packet does **not** add any new feature, domain, mutation, or UI beyond the
security/PII simplification above.

## B. Existing implementation inventory (Wave 1 / SEC-1 — [Fact — repo, 2026-07-16])

The preflight must re-extract these exactly before editing; the current known set:

| Item | Location |
|---|---|
| Computed masked display `pii_snapshot_masked` (Char, compute `_compute_pii_snapshot_masked`, e.g. `j***@e***…`) | `addons/shopify_connector_sale/models/shopify_connector_customer_binding.py` (~L57, L87–114) |
| Raw customer snapshot fields `shopify_display_name`, `shopify_email_snapshot`, `shopify_phone_snapshot` (+ any field-level `groups=reviewer,admin` on them) | `addons/shopify_connector_sale/models/shopify_connector_customer_binding.py` (~L36/L43/L50) |
| Manual masking action `action_mask_customer_pii(binding)` | `addons/shopify_connector_core/models/shopify_connector_pii_retention.py` (~L67) |
| Retention/sweep service model `shopify.connector.pii.retention` incl. `_mask_payload(value)`, `run_sweep()` | `addons/shopify_connector_core/models/shopify_connector_pii_retention.py` |
| Retention setting `pii_snapshot_retention_days` (Integer) | `addons/shopify_connector_core/models/shopify_connector_store_settings.py` (~L41) |
| Retention cron `ir_cron_shopify_connector_pii_retention` ("Shopify Connector: PII Retention Sweep") | `addons/shopify_connector_core/data/shopify_connector_pii_retention_cron.xml`; registered `__manifest__.py` |
| Masking/least-privilege tests | `addons/shopify_connector_sale/tests/test_pii_least_privilege.py` (`test_pii_field_and_masked_visibility_for_all_roles`, `test_manual_mask_role_audit_redaction_and_atomicity`); `addons/shopify_connector_core/tests/test_security_hardening.py` (`test_retention_masks_payload_and_one_summary_per_affected_store`); `test_customer_binding.py` references to `pii_snapshot_masked` |
| Views / future UI references to the masked field | to be enumerated in preflight (sale views, any list/form referencing `pii_snapshot_masked`) |
| Audit / log behavior | `_system_append` redaction; job-log `payload_snapshot` redaction — **retained** |
| Sanctioned sudo writers (SEC-1 inventory) | per `../05-qa/task-sec1-validation-results.md` sudo-delta note — **retained; not weakened** |

**Distinction to preserve (critical):** the retention model does two different
things. (a) It **redacts stored job-log `payload_snapshot`** evidence on a
retention schedule (log/evidence hygiene — redaction). (b) It **masks the customer
binding snapshot fields** (`shopify_email_snapshot`/`shopify_phone_snapshot`/
`shopify_display_name`) — this is **business-record masking** and is the forbidden
MVP capability. SEC-2 removes (b); (a) is a Class-C technical decision (keep as
documented log-retention redaction, or re-scope) and must not be conflated with
customer-facing masking.

## C. Target behavior

- **Connector User** and **Connector Administrator** each read the raw customer
  PII snapshot fields their permitted operations require (subject to normal ACL /
  company / role checks).
- **No** masked field on any MVP screen; **no** mask/unmask toggle; **no** manual
  mask action exposed; **no** scheduled masking behavior active or exposed as an
  MVP feature; **no** masking-related setting exposed.
- **No** masked-field requirement on any future binding (Wave 2+ order bindings
  and every later MVP binding introduce no `*_masked` snapshot field).
- Existing log/audit redaction, company isolation, protected-field enforcement,
  and credential secrecy remain in force and unweakened.

## D. Safe code-disposition options (recommend exactly one)

- **Option 1 — full removal via a controlled module upgrade (RECOMMENDED).**
  Remove the `pii_snapshot_masked` computed field and its compute; remove
  `action_mask_customer_pii`; remove the customer-binding masking path from the
  retention model (keep or re-scope the job-log payload redaction per the Class-C
  decision); remove the field-level `groups=reviewer,admin` restriction on the
  snapshot fields so both roles read raw; retire the masking setting and, if the
  retention cron no longer has a business-record job, the cron. Ship as one
  migration (see G). Rationale: the MVP has no masked surface at release; least
  standing debt; a clean, reviewable security diff.
- **Option 2 — deprecate/dormant for one compatibility release, then remove.**
  Hide the masked field from all views, no-op the manual action, disable the
  masking sweep, grant both roles raw read — but leave the columns/methods dormant
  for one release before physical removal. Lower migration blast radius, but
  leaves dormant masking code and a longer window of divergence.

**Recommendation: Option 1.** It best satisfies the priorities — no customer-visible
masking, migration/upgrade/uninstall safety, no irreversible corruption, minimal
debt, clean MVP release behavior. The one Option-2 advantage (staged column drop)
is not needed because the snapshot fields themselves are **kept** (only the masked
*display* and the *masking behavior* are removed), so no PII data column is dropped.

## E. Previously masked stored values (masking is irreversible)

- **Never** pretend masked values can be reconstructed; **never** infer or
  fabricate original PII from a masked string (e.g. `j***@e***`).
- Mark records whose snapshot fields were already masked as **requiring
  refresh/re-import**.
- Where read-only Shopify access is available, **re-import** the customer/order
  snapshot from the authoritative remote record under normal access and retention
  rules; where refresh is unavailable, **show "data unavailable"** rather than a
  fabricated value.
- Audit the remediation (which records refreshed, which left unavailable)
  **without logging raw PII**.

## F. Wave allocation

- The correction must be completed **before MVP UAT/release**.
- **Recommended:** SEC-2 is the **first stage of Wave 5**, executed **before U1**,
  so the premium UI consumes a finished two-role, no-masking security surface.
- **Alternative:** a separately gated **pre-Wave-5** security/product-alignment
  task if the control room determines earlier implementation is safer.
- **Wave 2 must not introduce additional masking** (no `*_masked` fields on the
  order bindings or any Wave 2+ binding).

## G. Allowed and forbidden files

**Allowed (exhaustive intent — exact paths confirmed in preflight):**
- Core security groups & privilege: `addons/shopify_connector_core/security/` group/privilege data (new `group_shopify_connector_user`, `implied_ids`, `privilege_id` re-point, hidden-group name prefixes).
- ACLs: `addons/shopify_connector_core/security/ir.model.access.csv` and the product/sale equivalents (re-key operator∪reviewer → `user`).
- Sale customer binding: `addons/shopify_connector_sale/models/shopify_connector_customer_binding.py` (remove masked field/compute; remove field-level `groups=` restriction on snapshot fields).
- Retention model & cron: `addons/shopify_connector_core/models/shopify_connector_pii_retention.py`, `addons/shopify_connector_core/data/shopify_connector_pii_retention_cron.xml`, `__manifest__.py` (remove business-record masking; keep/rescope log-payload redaction per Class-C).
- Settings: `addons/shopify_connector_core/models/shopify_connector_store_settings.py` (retire the masking setting).
- Views: any sale/core view referencing `pii_snapshot_masked`.
- Migrations: `addons/shopify_connector_core/migrations/<version>/` and `addons/shopify_connector_sale/migrations/<version>/` (two-role membership migration per roles doc §4.7; masked-value remediation per E).
- Tests: the PII/role test modules above, updated to the no-masking target.
- Documentation: this packet's DoD list (§J).

**Forbidden (no-scope-creep):** any job/lease/dispatcher/replay/credential/
inventory/fulfillment/export/Shopify-mutation code; any DEC-031 Layer 2 work; any
new domain, model, webhook, or UI feature beyond the security/PII simplification;
any change to protected references or to modules not listed above.

## H. Tests (must exist and pass)

1. Raw-field read for **Connector User** (permitted snapshot fields readable).
2. Raw-field read for **Connector Administrator**.
3. **Denial** for unrelated Odoo users without a connector role.
4. Company-boundary enforcement on the snapshot fields.
5. **No masked-field UI surface** — no view exposes `pii_snapshot_masked`; the field/compute is gone (Option 1).
6. **No masking action** — `action_mask_customer_pii` is absent/inert and unexposed.
7. **No masking cron behavior** — the sweep performs no business-record masking (customer binding snapshot fields untouched by any schedule).
8. **No masking setting** exposed.
9. **No raw PII in logs/audits** — `_system_append` / `payload_snapshot` redaction still strips email/phone/name/address.
10. Migration **idempotency** (run twice → identical membership; no duplicate effect).
11. **Previously masked-value handling** — masked records flagged for refresh; refreshed where Shopify available, "data unavailable" otherwise; never fabricated.
12. **Upgrade** (prior→SEC-2 clean); **uninstall**; **reinstall**; **rollback**.
13. **Residue** — no orphaned masking columns/records/cron after uninstall.
14. **ACL implication closure** — admin resolves to all connector groups; user resolves to user+operator+reviewer+auditor; no privilege escalation outside the two roles.
15. No SEC-1 protection weakened (protected-field set, sanctioned sudo sites, credential secrecy re-asserted).

## I. Rollback

Revert the module data/code (roles doc §4.10): delete `group_shopify_connector_user`,
re-point `privilege_id` to the legacy groups, restore the prior field definitions.
**Rollback must not pretend to recover PII already irreversibly masked** — records
masked before SEC-2 stay masked/refresh-required; rollback restores the *display*
mechanism, never the lost raw values.

## J. Definition of done

**No customer-facing or active MVP masking capability remains.** Code + tests green
(Odoo.sh exact-head, full regression, uninstall/reinstall/residue, no-PII-leak);
two-role ACL matrix proven; Claude wave review complete; debt logged; rollback
documented. Update all affected records, at minimum:

- `../02-product/connector-roles-and-permissions.md`
- `../04-decisions/fable-proposed-decision-pack.md` (Class A ROLE/PII rulings; Class C SEC-2 option)
- `../02-product/mvp-capability-map.md`
- `../02-product/premium-ux-master-specification.md`
- `../02-product/sales-order-lifecycle-and-confirmation-policy.md` (order PII)
- `task-012-order-import-implementation-packet.md` / `task-012-order-import-proposed.md`
- `wave-2-definition-of-ready.md`, `wave-5-definition-of-ready.md`, `wave-6-definition-of-ready.md`
- `../05-qa/security-pii-matrix-waves-2-6.md`
- `../05-qa/waves-2-6-cross-domain-test-matrix.md`
- `implementation-readiness-checklist.md`
- `../08-release-readiness/release-readiness-gap-list.md`
- `../09-ui-prototype/settings-permissions/` (spec + prototype)
- `../09-ui-prototype/order-review/`, `../09-ui-prototype/cod-reconciliation/`, `../09-ui-prototype/external-fulfillment-review/` (spec + prototype)
- `../09-ui-prototype/traceability-matrix.md`
- `../04-decisions/DEC-028-credential-pcd-posture-ladder-proposal.md` (dated PII-direction note; credential posture unchanged)
- `../05-qa/task-sec1-validation-results.md`, `task-sec1-security-hardening-packet.md` (dated non-retroactive product-direction notes)
- `../01-research/research-handoff.md`, `fable-gap-closure-status.md`, PR #173 body.

## K. Hard stops

No implementation is authorized by this packet. SEC-2 does not start until the
product owner + Claude control room accept it and its wave placement. It never
touches protected references, never performs a Shopify mutation, and never
weakens SEC-1.
