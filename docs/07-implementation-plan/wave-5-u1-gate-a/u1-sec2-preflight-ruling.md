# Wave 5 U1 — SEC-2 Preflight Ruling

> **Status: Gate A planning artifact — Docs-only. NOT accepted.** Produced
> 2026-07-23; **corrected 2026-07-23** per control-room comment `5056513213`.
> Answers the mandatory SEC-2 preflight (Gate A prompt §7). **The repository
> defines SEC-2 sufficiently → Gate A planning is NOT a HARD STOP — but U1
> production implementation is BLOCKED until SEC-2 merges runtime-green
> (SEC-2-first is binding; D-P0-2 resolved).**

## 1. What SEC-2 specifically means

SEC-2 = **"Two-Role Migration & PII-Masking Simplification."** Governing
documents (all present in-repo):

- `docs/07-implementation-plan/task-sec2-two-role-and-pii-simplification-packet.md`
  (implementation packet — Proposed 2026-07-16; technical method **Decided
  2026-07-17, TA-C5**: Option 1 controlled full removal; retention cron rescoped
  to log/audit redaction only).
- `docs/02-product/connector-roles-and-permissions.md` (§3 no-masking, §4 4→2
  migration, Option M-A).

SEC-2 does exactly two things (packet §A):

1. **Role migration (4 → 2 customer-facing roles).** Collapse the four internal
   groups (`operator`, `reviewer`, `auditor`, `admin`) into two **customer-facing**
   roles — **Connector User** and **Connector Administrator** — where
   Administrator inherits every User capability. Method is **Option M-A**
   (packet §D, roles §6): purely **additive** `implied_ids` — the four legacy
   groups **remain as hidden capability primitives**, **no XML-ID rename**.
   (Packet §H test 14: "admin resolves to all connector groups; user resolves to
   user+operator+reviewer+auditor.")
2. **PII-masking removal.** Remove the masked display field, the manual masking
   action, and the scheduled masking of **customer-binding** snapshot fields from
   the MVP. **Log/audit/credential/header redaction stays mandatory** (redaction ≠
   masking).

## 2. Status of SEC-2

- **Proposed**, with an **accepted technical method** (TA-C5, 2026-07-17). It is
  **not yet a merged implementation** and **not yet its own DEC**; the packet
  "authorizes no implementation."
- **Wave placement (packet §F, wave-5 DoR §1/§3):** SEC-2 is the **first stage of
  Wave 5**, sequenced **before U1** — binding sequence **SEC-2 → PERF-1 → U1 → U2
  → U3**. The DoR §3 explicitly **rejected** "U1-first, SEC-2 flips afterwards."
  This SEC-2-first sequence is now **binding for U1 via control-room comment
  `5056513213`** (D-P0-2 resolved).

## 3. Which security requirements U0 and Wave 4 already cover

- **Four connector groups exist and are enforced server-side**
  (`core/security/shopify_connector_security.xml`): `group_shopify_connector_
  auditor/operator/reviewer/admin`.
- **Wave 4 fulfillment gates on these four groups** — field-level `groups=` on the
  mode fields (admin), `has_group` checks in mode-switch/review/release actions,
  and a four-row ACL matrix (auditor R / operator R,C / reviewer R,W / admin R,W,C).
- **Wave 4 stores no customer PII in the fulfillment domain** — the fulfillment
  binding declares `_pii_snapshot_fields() → []`; the evidence model holds no
  name/email/phone/address field; **tracking data is not PII**. So the
  PII-masking half of SEC-2 has **no surface inside U1**.
- **U0 hardening** (merged): admin-boundary guards on store lifecycle actions;
  redaction on logs; no raw tokens/tracebacks on screens; five-action security
  matrix proven.
- **SEC-1** (Wave 1, merged): protected-field enforcement, sanctioned sudo
  writers, company isolation, credential secrecy, log/audit redaction — all
  in force and unweakened.

## 4. Which SEC-2 requirements remain missing

- The **two customer-facing roles** (`group_shopify_connector_user`,
  `Connector Administrator`) do **not exist yet**; today only the four internal
  groups exist.
- The Wave-1 **masking** artifacts still exist in `shopify_connector_sale` /
  `shopify_connector_core` (masked compute field, manual mask action, masking
  sweep) — SEC-2 removes them. **None of these are in the fulfillment domain.**

## 5. Can U1 safely proceed without implementing SEC-2 first?

**Ruling (control-room comment 5056513213, binding): Gate A *planning* is NOT
blocked by SEC-2 — the repository defines SEC-2 sufficiently. But U1 *production
implementation* is BLOCKED until SEC-2 is accepted, implemented, independently
reviewed, Odoo.sh runtime-green, and MERGED into `mvp/program-integration`
(D-P0-2 resolved SEC-2-FIRST). There is NO parallel four-internal-group path.**
Reasoning:

1. **The PII-masking half does not touch U1 at all.** Fulfillment stores no PII;
   U1 renders no `*_masked` field and introduces no new PII surface. This half is
   a no-op for U1.
2. **U1 must build against the FINAL two-role model, not the four internal groups.**
   SEC-2 introduces the two customer-facing roles via Option-M-A additive
   `implied_ids` — Connector User (the **new** `group_shopify_connector_user`) and
   Connector Administrator (the **existing** `group_shopify_connector_admin`,
   re-purposed — never renamed). U1 **customer-facing view/menu/button visibility
   gates on those two roles**; the four internal capability groups
   (auditor/operator/reviewer/admin) remain the **server-side authorization
   primitives** the two roles resolve to via the implied-group closure
   (Administrator → User → operator/reviewer → auditor). Gating U1 visibility
   directly on the four internal groups (the earlier alternative) is **removed**:
   it would make the customer-facing UI contract depend on hidden legacy groups and
   prove the visibility matrix twice — exactly the rework/UI-vs-ACL-disagreement the
   SEC-2-first sequence exists to prevent (DoR §3 **rejects** "U1 on the old four
   groups, SEC-2 flips afterwards").
3. **The wave-5 DoR §3 binding sequence SEC-2 → PERF-1 → U1** is now reinforced by
   the control-room ruling: SEC-2 lands first; then U1 builds role-gated views
   against the final two-role model.

**Therefore:** the repository **does** define SEC-2 sufficiently to rule on U1;
Gate A planning proceeds now; **U1 implementation waits for SEC-2 to merge
runtime-green.** Tests must prove BOTH layers: (1) customer-facing two-role
visibility (Connector User vs Connector Administrator affordances), and (2)
direct-RPC server authorization/denial through the internal implied groups, with no
privilege escalation and no UI/ACL disagreement. SEC-2 defines the final two-role
group XML IDs (notably the new `group_shopify_connector_user`); U1 must not treat
that XML ID as existing before SEC-2 merges. This is recorded as **resolved P0
decision D-P0-2** in `u1-risks-and-open-questions.md`.

## 6. One genuine SEC-2 scope gap to surface (not a U1 blocker)

SEC-2's **allowed-files list (packet §G) predates Wave 4** and lists only
`core`/`sale` files; its **forbidden** list explicitly excludes "fulfillment …
code." But Wave 4's fulfillment ACLs and `has_group` checks reference the four
legacy groups. Under Option M-A this is harmless (the four groups persist, so the
implied-role model still resolves), **but** if the control room later wants the
two-role model *reflected in* fulfillment security wording/labels, SEC-2's scope
must be extended, or fulfillment continues to rely on the four internal groups by
design. Logged as **open P1 decision D-P1-3**. No change to Wave 4 is proposed by
U1.

## 7. Verdict

**`SEC-2 DEFINED — U1 GATE A (PLANNING) NOT BLOCKED; U1 IMPLEMENTATION BLOCKED
UNTIL SEC-2 MERGES`.** SEC-2 is a Wave-5 implementation obligation, **REQUIRED
before U1 implementation** (binding SEC-2-first via control-room comment
`5056513213`, DoR §3). **D-P0-2 is RESOLVED SEC-2-first** — there is no parallel
four-internal-group path; the only remaining SEC-2-adjacent item is the
**scope-coverage** clarification D-P1-3 (fulfillment continues relying on the four
internal groups as server-side primitives; no Wave 4 backend security is rewritten
by U1). U1 must ship **no** masking surface, gate **customer-facing UI visibility on
the two SEC-2 roles**, and keep the four internal capability groups as the
server-side authorization primitives those roles resolve to.
