# Wave 5 U1 — SEC-2 Preflight Ruling

> **Status: Gate A planning artifact — Docs-only. NOT accepted.** Produced
> 2026-07-23. Answers the mandatory SEC-2 preflight (Gate A prompt §7). **The
> repository defines SEC-2 sufficiently → this is NOT a HARD STOP.**

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

**Ruling: SEC-2 is sufficiently defined; U1 Gate A is NOT blocked; U1
implementation is governed by a control-room sequencing decision — not a missing
definition.** Reasoning:

1. **The PII-masking half does not touch U1 at all.** Fulfillment stores no PII;
   U1 renders no `*_masked` field and introduces no new PII surface. This half is
   a no-op for U1.
2. **The role half is Option-M-A additive.** Because SEC-2 keeps the four internal
   groups as hidden capability primitives (no XML-ID rename), a U1 that gates its
   views/buttons on the **four internal capability groups** — which is exactly
   what Wave 4 enforces server-side — **remains correct after SEC-2** (User ⇒
   operator∪reviewer∪auditor; Administrator ⇒ all). U1 built this way is
   **order-independent** of SEC-2.
3. **However**, the **wave-5 DoR §3 binds the sequence SEC-2 → PERF-1 → U1** and
   rejected U1-first, to avoid proving the visibility matrix twice and to avoid a
   mid-wave window where UI gating and ACLs disagree. That is a **live control-room
   sequencing decision**, not a definitional gap.

**Therefore:** the repository **does** define SEC-2 sufficiently to rule on U1;
**no HARD STOP is required.** U1 *implementation* should either (a) follow the
DoR's binding SEC-2-first sequence, or (b) proceed under an explicit control-room
authorization to gate strictly on the four internal capability groups
(server-mirrored) so it is SEC-2-order-independent. This is recorded as **open P0
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

**`SEC-2 DEFINED — U1 GATE A NOT BLOCKED BY SEC-2`.** SEC-2 is a Wave-5
implementation obligation, recommended before U1 by the DoR; the only open items
are **sequencing** (D-P0-2) and a **scope-coverage** clarification (D-P1-3) — both
control-room decisions, neither a definitional hard stop. U1 must ship **no**
masking surface and gate on capability groups that survive SEC-2.
