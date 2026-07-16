# Connector Roles and Permissions — Two-Role Customer-Facing Model

> **Status: Proposed — Fable gap-closure mission, 2026-07-16.** Product-owner
> binding direction; final acceptance authority: product owner + Claude control
> room. Supersedes, at proposal level, the four-role design in
> [ui-ux-final-design-spec.md §User roles](ui-ux-final-design-spec.md)
> / [screen-inventory-and-navigation-map.md](screen-inventory-and-navigation-map.md)
> role matrix / [ux-operator-flow.md](ux-operator-flow.md) §10 (accepted docs
> are not rewritten; this is the dated proposal layer). **No implementation
> authorized.**

---

## 0. Scope and evidence base

- [Fact — repo, verified 2026-07-16] The codebase currently ships four
  security groups in `shopify_connector_core`:
  `group_shopify_connector_auditor` (base read-only),
  `group_shopify_connector_operator` (implies auditor),
  `group_shopify_connector_reviewer` (implies auditor), and
  `group_shopify_connector_admin` (implies operator + reviewer), under
  category `module_category_shopify_connector` with privilege
  `privilege_shopify_connector`.
- [Fact — repo] Current ACL posture: credentials are admin-only with
  field-level `groups=` on `access_token`; job logs are read-only for all
  roles; bindings — auditor read, operator read+create, reviewer read+write,
  admin read+write+create; customer PII snapshot fields carry field-level
  `groups=reviewer,admin` with a computed masked display for lower roles;
  `action_resolve_manual_review` and `action_override_binding` are
  reviewer/admin; job manual retry/cancel is role-gated.
- [Fact] Odoo 19 security mechanics (implied_ids transitive closure,
  `res.groups.privilege` single-selection rendering, ACL additivity,
  field-level `groups=`, XML ID stability) are captured in
  [odoo19-sale-stock-security-captures-2026-07-16.md §5](../00-source-materials/odoo19-sale-stock-security-captures-2026-07-16.md).
- [Fact] The accepted four-role UX design lives in
  [ui-ux-final-design-spec.md](ui-ux-final-design-spec.md) (DEC-012 §10,
  DEC-013, DEC-018 MBQ-45): one shared role-gated surface, affordance gating,
  Admin ⊇ Operator + Reviewer, everyone ⊇ Auditor visibility.
- [Fact — check performed] No entry in the
  [rejected-approaches log](../05-qa/rejected-approaches-log.md) (RA-001…024)
  rejects a two-role or role-consolidation design; this proposal re-proposes
  nothing rejected.

## 1. The two-role model

**[Proposed product decision — product-owner binding direction, 2026-07-16]**
The final product exposes **exactly two customer-facing roles**:

1. **Connector User**
2. **Connector Administrator**

Administrator **automatically inherits every User capability** via group
implication — customers assign exactly one role per person, never both
([Fact] `implied_ids` semantics: "Users of this group are also implicitly
part of those groups", source captures §5). The four internal groups **may
remain temporarily as an implementation detail** (hidden, non-selectable).
One coherent product: **no persona-split apps or dashboards** — the accepted
single-surface, affordance-gated principle
([ui-ux-final-design-spec.md](ui-ux-final-design-spec.md)) is retained
unchanged; only the number of selectable roles changes.

### 1.1 Connector User — capability table

Connector User merges the accepted Operator (daily operations) and Reviewer
(audited resolution) functions.

| Domain | Connector User can |
| --- | --- |
| Dashboard / health | View dashboard, store health, connection status, cron/queue health. |
| Jobs & logs | View jobs, job logs, statuses; run permitted manual syncs; retry/cancel **eligible** jobs (eligibility remains server-side error-class-gated, per DEC-003 retry classification). |
| Mappings / bindings | Resolve ordinary product / customer / order mapping items (manual matching, approve/decline candidates); create bindings via matching flows. |
| Sync exceptions | Review sync exceptions; approve **ordinary operational corrections** (the six accepted manual-review sub-reasons), each recorded who/when/what (DEC-009 audit posture). |
| Orders | Inspect imported orders, discrepancies, error detail; resolve ordinary order-mapping exceptions. |
| COD reconciliation | Perform operational COD reconciliation review per store policy (visibility + confirmation of collected/uncollected state on connector records); **no accounting posting** — payment registration stays behind Administrator configuration ([Recommendation] grounded in captures §4: `action_create_payments` immediately posts and reconciles). |
| Fulfillment (mode 1: Odoo-fulfills) | Inspect fulfillment/tracking write-back state and discrepancies; confirm notification-guard prompts (RA-009 posture unchanged). |
| Fulfillment (mode 2: externally-fulfilled) | Reconcile inbound fulfillment per store policy; review external-fulfillment exceptions (quantity/location/line mismatches). |
| Inventory | Inspect inventory sync state and discrepancies; run permitted inventory verification reads; confirm ordinary preview-based pushes where store policy allows (first-push guard stays confirmation-required, RA-008 unchanged). |
| Product export | Run permitted export/preview flows; resolve export matching exceptions. |
| Reconnect / backfill | View reconnect/backfill progress and gap reports; run permitted backfill verification. **Initiating** reconnect is Administrator (credential-adjacent). |
| Abandoned checkouts | View abandoned-checkout data (subject to §3 PII rules); run permitted recovery-flow operations if the capability is enabled. |
| Diagnostics | Role-appropriate diagnostics: verification reads, log/technical-detail expand, exportable job reports. |
| Settings | Read-only view of settings (credentials masked, as for every role — DEC-004: no credential read-back for anyone). |

Connector User **cannot**: change any configuration, credentials, mappings
of configuration nature (locations/taxes/payments/warehouses), scheduling,
capability enablement, retention, policies; perform destructive or
exceptional overrides; connect/disconnect stores; manage user access.

### 1.2 Connector Administrator — additive capability table

Everything above, **plus**:

| Area | Administrator-only capability |
| --- | --- |
| Store lifecycle | Connect / disconnect / reconnect stores; sensitive lifecycle ops (pause, purge-on-disconnect flows, export-before-uninstall — DEC-030). |
| Credentials & scopes | Credential entry/replacement, scope management, connection verification config (never read-back of stored values). |
| Configuration | Company / warehouse / location / tax / payment-method / mapping configuration; source-of-truth selection. |
| Scheduling | Cron/interval scheduling, queue tuning. |
| Capabilities | Domain/capability enablement (inventory, product export, fulfillment, abandoned checkouts, COD). |
| Access | User access configuration (assigning Connector User / Administrator). |
| Privacy | Retention and privacy controls; PII visibility policy (§3). |
| Fulfillment | Fulfillment-mode selection (mode 1 vs mode 2) per store. |
| Order policy | Order-confirmation policy; COD policy (incl. whether any accounting posting is enabled). |
| Overrides | Destructive / exceptional overrides (binding overrides beyond ordinary resolution, forced re-sync, destructive-write confirmations designated admin-tier). |
| Diagnostics | Full admin diagnostics (raw payload access, connection-level tooling). |

[Inference] This split preserves the accepted safety spine: everything
irreversible-or-configuration-shaped is Administrator; everything
operational-and-audited is User.

## 2. What happens to Auditor and Reviewer semantics

### 2.1 Auditor

**[Open question → Recommendation]** The Auditor's read-only surface has two
candidate futures:

- **Option A2a — fold into ordinary Odoo internal-user visibility:** drop the
  customer-facing read-only role; any internal user a customer chooses to
  give menu visibility sees read-only connector data via global read ACLs.
  Simple, but [Inference] weakens the "explicit audit persona" story and
  makes read access implicit rather than assigned.
- **Option A2b — retain `group_shopify_connector_auditor` as a hidden
  technical group** (recommended): it stays the base of the implication
  chain and the anchor for read ACLs, but is removed from the selectable
  privilege so customers never see it. Read-only access, if a customer
  wants it, is a later optional feature, not a launch role.

**[Recommendation]** Adopt A2b: zero ACL churn (every existing read grant
keyed to auditor keeps working), zero data migration for read rules, and the
option to re-expose it later without re-plumbing.

### 2.2 Reviewer

The Reviewer's exclusive audited resolution acts (`blocked_manual_review`
resolution across the six sub-reasons, ordinary binding corrections) **move
to Connector User**. [Inference — safety justification] Safety is preserved
because the protections were never delivered by role scarcity alone:

1. Every resolution remains **audited** (who/when/what — DEC-009), unchanged.
2. Gating remains **server-side** (methods check groups; UI hiding is
   convenience, not security — captures §5: view `groups` is visibility
   only), unchanged.
3. **Destructive variants stay Administrator-only** (destructive-write
   overrides, exceptional binding overrides, first-connect pushes remain
   behind admin-tier confirmation), so the blast radius of a User mistake is
   bounded to reversible, audited operational acts.
4. RA-006/RA-008/RA-009/RA-010 guardrails (no name-only auto-match, no blind
   first push, no silent notifications, no auto accounting) are process
   guards, not role guards — they apply identically to the User.

## 3. PII visibility

- [Fact — repo] Today, customer PII snapshot fields carry field-level
  `groups=reviewer,admin`; lower roles see a computed masked display.
- **[Proposed product decision]** In the two-role model: **Connector User
  sees masked PII by default; unmasked PII is Administrator-only, with a
  per-store, Administrator-configurable toggle that can grant Connector
  Users unmasked access** where the merchant's operations require it (e.g.
  COD/fulfillment reconciliation needing phone/address confirmation).
- [Inference — justification] Shopify Protected Customer Data Level 2
  requirements (per the accepted PCD evidence in the source-materials
  captures) demand purpose limitation, minimization, and access control for
  name/address/phone/email — a default-masked posture with an explicit,
  logged, merchant-controlled opt-in is the strongest defensible reading;
  a blanket "all Users see PII" default is weaker under minimization.
- [Fact] Field-level `groups=` removes restricted fields from views and
  `fields_get` and blocks read/write at the ORM (captures §5) — so the
  toggle must be implemented as **group membership in a hidden technical
  PII group** (e.g. the retained reviewer group per §4), toggled per user or
  granted store-wide by the Administrator, **not** as a view-only trick.
  Exact mechanism (per-store record rule vs. per-user hidden group) is
  **[Open question OQ-A]** for the implementing packet; per-user hidden
  group is the simpler default recommendation.

## 4. Migration design — 4 internal groups → 2 customer-facing groups

**[Recommendation — design only; NOT implemented here; no code authorized.]**

### 4.1 Group-implication design — chosen option

**Chosen: Option M-A — introduce one new group, re-purpose the rest.**

- New group `shopify_connector_core.group_shopify_connector_user`
  ("Connector User") with
  `implied_ids = [operator, reviewer]` (which transitively imply auditor).
- Existing `group_shopify_connector_admin` gains
  `implied_ids += [group_shopify_connector_user]` (it already implies
  operator+reviewer; adding User keeps the closure consistent and makes the
  customer-visible chain explicit: **Administrator → User → (operator,
  reviewer) → auditor**).
- The four old groups become hidden technical groups (§4.4).

**Alternatives considered:**

- *Option M-B — re-label `group_shopify_connector_operator` as "Connector
  User" and add `implied_ids = [reviewer]` to it.* Fewer records, but
  [Inference] it silently escalates every currently-assigned Operator to
  reviewer powers **at the group-definition level with no migration-script
  decision point**, muddies the XML ID's meaning (an ID named `operator`
  rendering as "User" with reviewer powers is a permanent audit-trail
  confusion), and makes rollback harder (removing the implication cannot
  distinguish pre-existing operators from migrated Users). Rejected for
  this proposal.
- *Option M-C — two brand-new groups (User + new Admin), retire all four.*
  Cleanest naming but forces migrating admin assignments too, doubles the
  ACL-mapping churn, and renaming/retiring the admin XML ID risks breaking
  any record rule, server action, or customer customization referencing it.
  Rejected: M-A achieves the same customer-visible result with the admin
  group untouched.

[Inference — why M-A] It is purely **additive** (new group + implied_ids
edits), never renames an XML ID (captures §5: renaming is delete+create),
requires a user-assignment migration only for operator/reviewer holders, and
rolls back by deleting one group and two implication links.

### 4.2 Exact implied_ids chain (target state)

```
group_shopify_connector_admin
  └─ implies → group_shopify_connector_user            (new link)
                 ├─ implies → group_shopify_connector_operator   (existing group)
                 │              └─ implies → group_shopify_connector_auditor
                 └─ implies → group_shopify_connector_reviewer   (existing group)
                                └─ implies → group_shopify_connector_auditor
(admin's existing direct implied_ids to operator/reviewer may be kept —
harmless under transitive closure — or pruned to the single user link;
recommendation: keep them for one release, prune in a later cleanup.)
```

[Fact] `all_implied_ids` computes the reflexive transitive closure, so a
user assigned only `group_..._admin` resolves to all five groups; a user
assigned only `group_..._user` resolves to user+operator+reviewer+auditor.

### 4.3 res.groups.privilege — one selection on the user form

- [Fact] Odoo 19 `res.groups.privilege` groups multiple `res.groups` sharing
  one `privilege_id` into **one selection field** on the user form
  (captures §5, incl. `placeholder` help text).
- Design: keep `privilege_shopify_connector` ("Shopify Connector"), set
  `privilege_id = privilege_shopify_connector` on **only**
  `group_shopify_connector_user` and `group_shopify_connector_admin`.
  Result: the user form shows a single "Shopify Connector" dropdown with
  exactly *User* / *Administrator* (plus empty).
- The four old groups get `privilege_id = False` (and, if needed for
  Settings-page hygiene, a dedicated hidden/technical category — §4.4).
- [Open question OQ-1 — carried from captures §5] Verify the exact
  radio/selection rendering rule in `res_users_views.xml` before
  implementation.

### 4.4 Hiding the obsolete technical groups (backward compatibility)

- **Keep all four old XML IDs forever; never rename** ([Fact] XML ID rename
  = delete+create; deletion cascades group membership and breaks any
  referencing record rule/ACL — captures §5).
- Make them non-selectable implementation detail:
  - remove `privilege_id` (they drop out of the privilege dropdown);
  - place them under a technical category (either reuse
    `module_category_shopify_connector` with no privilege linkage, or a
    `.../hidden` `ir.module.category` marked as technical) so they render,
    at worst, only in developer-mode group lists;
  - update their `name` to a `"Technical / …"` prefix so any residual
    listing self-documents.
- Group data records must **not** be `noupdate=1` where implication edits
  are needed ([Fact] noupdate loads only at install; normal data reloads on
  update — captures §5). [Open question OQ-B] Audit current noupdate flags
  on the group records; if noupdate, ship the implied_ids/privilege edits in
  a migration script instead.

### 4.5 ACL and record-rule impact table

Principle: **no ACL rewrite is strictly required** — old groups remain valid
grant anchors and Users/Admins reach them via implication. The table below
is the target-state normalization (recommended in the same packet, since ACL
lines keyed to hidden groups are a maintainability smell). "→" = re-key the
ACL line's `group_id`.

| Model (module) | Current grants | Target grants |
| --- | --- | --- |
| Store / credentials (core) | admin: rwcu; field `access_token` groups=admin | unchanged (admin) |
| Job (core) | auditor r; operator r + retry/cancel actions; admin rwcu | auditor r (hidden) → also `user` r; retry/cancel action gate operator/reviewer → `user`; admin unchanged |
| Job log (core) | all four roles: read-only | read-only for `user` (via implication nothing changes; re-key auditor→user optional) |
| Binding (core) | auditor r; operator r+c; reviewer r+w; admin rwc | `user` r+w+c (union of operator∪reviewer, per binding direction); admin rwc; destructive override action stays admin |
| Manual-review / exception (core) | reviewer/admin resolve actions | resolve action → `user`/admin; destructive variants admin-only |
| Customer PII snapshot fields (core/sale) | field groups=reviewer,admin; masked compute for others | field groups= hidden PII group (default membership: admin; per-store/per-user toggle adds Users — §3) |
| Product templates/bindings (product) | mirror of binding pattern per role | same re-key: operator∪reviewer grants → `user` |
| Sale order / COD records (sale) | operator r, reviewer r+w resolution, admin rwcu | `user` r+w resolution; posting/config admin |
| Record rules (all) | any rule keyed to operator/reviewer | union-keyed to `user` (group rules unify — captures §5); global rules untouched |

[Open question OQ-C] The exact per-`ir.model.access` line inventory must be
extracted from the three modules' `security/` files by the implementing
packet (this doc's table is the mapping *rule*, not the line-by-line file —
the control room should require the packet to include the exhaustive CSV
diff in its plan).

### 4.6 PII visibility impact

Covered in §3: re-key field-level `groups=` from `reviewer,admin` to the
hidden PII group; default membership = Administrator; toggle grants Users.
Masked-compute display logic is unchanged for non-members.

### 4.7 Migration of currently-assigned users

`post_init_hook` is wrong here (module already installed); use a
**migration script** `shopify_connector_core/migrations/<version>/post-two-role-groups.py`
([Fact] post scripts run "after the module and its dependencies are loaded
and updated", signature `migrate(cr, version)` — captures §7). Design:

1. Resolve group IDs via `ir_model_data` lookups by the stable XML IDs.
2. **operator ∪ reviewer → add `group_..._user` to `group_ids`** (explicit
   assignment; do not remove the old memberships in the same release —
   harmless under closure, and preserves rollback).
3. **admin → add nothing** (admin implies user after the data update;
   explicit re-add optional and unnecessary).
4. **auditor-only users → per §2.1 decision:** under recommended A2b, leave
   membership as-is (hidden group keeps granting read-only). If A2a is
   chosen instead, remove membership and log the affected logins.
5. Idempotent by construction: membership adds are set-inserts
   (`INSERT … ON CONFLICT DO NOTHING` on the rel table, or ORM `link`).
6. Emit a log line per changed user for the audit trail.

### 4.8 Uninstall / upgrade behavior

- [Fact] Uninstall deletes all module-owned XML-ID records — all six groups
  and their membership links go together; no orphan risk (captures §7).
- Upgrade: group `name`/`implied_ids`/`privilege_id` changes propagate on
  `-u` because group data should be non-noupdate (§4.4 / OQ-B).
- [Open question OQ-3 — carried from captures §5] Verify upgrade-time
  cleanup behavior for XML IDs removed from data files before any future
  group retirement; for this migration nothing is removed, only added.

### 4.9 Tests required (by the implementing packet)

1. **ACL matrix tests:** for each of {user-only, admin-only, auditor-only,
   legacy operator-only, legacy reviewer-only} test users × every connector
   model: assert exact CRUD outcomes match §4.5's target table.
2. **Migration idempotency:** run the migration script twice against a
   fixture DB seeded with operator/reviewer/admin/auditor users; assert
   identical final membership both times.
3. **No-privilege-escalation:** assert a migrated legacy Operator gains
   exactly the reviewer-tier acts and nothing admin-tier (credentials,
   settings write, destructive overrides all still denied); assert a
   Connector User cannot read `access_token` or unmasked PII by default.
4. **Field-level PII:** masked compute for User default; unmasked after the
   Administrator toggle; `fields_get` omission verified for non-members.
5. **UI hiding:** user form shows exactly one "Shopify Connector" selection
   with two options; old groups absent from the form; server-side gates hold
   even when a hidden group is manually assigned in developer mode.
6. **Implication closure:** `all_group_ids` of an admin-assigned user
   contains all five connector groups; of a user-assigned user, four.

### 4.10 Rollout / rollback plan

- **Rollout:** ship as one packet: data records (new group, implied_ids,
  privilege re-pointing, name prefixes) + migration script + ACL re-keys +
  tests. Land on the program integration branch behind the normal wave
  review gate; verify on a staging DB restored from production-like data
  before release ([Fact] Odoo.sh staging neutralizes crons — safe rehearsal
  environment, captures §6).
- **Rollback:** revert the module data (delete
  `group_shopify_connector_user` via removing its record and re-pointing
  privilege_id back to the four groups); because old memberships were never
  removed (§4.7 step 2) and old XML IDs never renamed, users regain exactly
  their pre-migration effective rights. Membership rows added to the new
  group die with the group record. Document as the packet's rollback note
  per [implementation-task-template](../06-prompts/implementation-task-template.md).

## 5. Wave allocation

**[Recommendation]** Accept this design **before Wave 5 (UI)** starts —
the UI wave must build role-gated affordances against the two-role model,
not the four-role model, or it will be reworked. Implementation:

- **Preferred: a dedicated `SEC-2` packet** (groups, privilege, ACL re-key,
  PII group, migration script, tests) executed immediately before or at the
  start of Wave 5, so U1 consumes a finished security surface.
- Acceptable fallback: fold into Wave 5 U1 as its first work item — but
  [Inference] a dedicated packet gives the control room a crisper review
  boundary (pure security diff, exhaustive ACL CSV, migration test run) and
  a cleaner rollback unit. **Recommend SEC-2.**

## 6. Proposed-decision block

- **Statement [Proposed product decision]:** The connector exposes exactly
  two customer-facing roles — Connector User and Connector Administrator —
  implemented per §4 (Option M-A: new `group_shopify_connector_user`,
  admin implies user, four legacy groups retained as hidden technical
  groups, single privilege selection, migration script per §4.7, PII per §3).
- **Evidence:** product-owner binding direction (2026-07-16, this mission);
  Odoo 19 mechanics in
  [captures §5/§7](../00-source-materials/odoo19-sale-stock-security-captures-2026-07-16.md);
  current repo group/ACL facts (§0); accepted single-surface UX
  ([ui-ux-final-design-spec.md](ui-ux-final-design-spec.md)).
- **Alternatives:** M-B (re-label operator), M-C (all-new groups) — §4.1;
  A2a vs A2b for Auditor — §2.1; PII admin-only-hard vs configurable — §3.
- **Consequences:** simpler customer mental model and onboarding; Reviewer's
  acts spread to all Users (mitigated per §2.2); accepted four-role UX docs
  become superseded-at-proposal-level and Wave 5 builds two-role gating;
  ACL surface simplifies to two grant anchors over time.
- **Risks:** silent privilege widening for existing Operators (mitigated:
  explicit migration + no-escalation tests + destructive acts stay admin);
  hidden-group confusion in developer mode (mitigated: "Technical /"
  naming); PII toggle misuse (mitigated: admin-only, logged, default off).
- **Rollback:** §4.10 — delete the new group and re-point privileges;
  legacy memberships intact.
- **Affected waves:** Wave 5 (UI) directly; SEC-2 packet (new); any wave
  adding models must grant against `user`/`admin` from acceptance onward.
- **Acceptance authority:** product owner + Claude control room.
- **Blocks implementation?** **Yes for Wave 5 UI** — Wave 5 role-gating work
  must not start until this decision is accepted or explicitly amended.

## 7. Open questions

| ID | Question |
| --- | --- |
| OQ-1 | Exact `res_users_views.xml` rendering rule for privilege groups (radio vs selection) — verify before SEC-2 (carried from captures §5). |
| OQ-3 | Upgrade-time cleanup semantics for removed XML IDs — relevant only to any *future* retirement of the legacy groups (carried from captures §5). |
| OQ-A | PII toggle mechanism: per-user hidden-group membership vs per-store record-rule/context approach (§3). |
| OQ-B | Are the current group data records `noupdate=1`? Determines whether implied_ids/privilege edits ride the data file or the migration script (§4.4). |
| OQ-C | Exhaustive per-line `ir.model.access` inventory across core/product/sale for the §4.5 re-key CSV — to be produced inside the SEC-2 packet plan. |
| OQ-D | Auditor final disposition (A2a vs A2b) — recommendation is A2b (§2.1); needs product-owner confirmation. |
| OQ-E | Should the per-store PII toggle also unmask abandoned-checkout contact data, or is checkout PII always Administrator-only? |
