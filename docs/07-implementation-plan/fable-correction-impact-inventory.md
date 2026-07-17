# Fable Correction-Impact Inventory — PR #173 consolidated correction

> **Status: control-room correction working artifact — 2026-07-16.** Produced
> before editing, per the consolidated correction ruling (PR #173 comments
> `4993775983` + product-owner superseding `4994990296`). It is the repository-wide
> map of every current-facing statement the correction must change, classified
> historical-keep vs current-replace. Canonical corrective wording lives in the
> per-ruling blocks referenced below; the live status ledger is
> [`fable-gap-closure-status.md`](fable-gap-closure-status.md).

**Scope searched:** every file changed by PR #173 (87 paths, all under `docs/**`),
the canonical decision/SEC-1 records they reference, the Wave 2–6 DoRs, the Task
012/013/014/015/015B packets + `-proposed` addenda, the U0/U1/U2/U3 + twelve
gap-closure prototype artifacts, the QA/UAT matrices, release-readiness, the live
tracker, and the research handoff.

**Classification key:** **STALE-CURRENT** = current-facing, must be replaced.
**HISTORICAL-KEEP** = dated historical record, retained (dated supersession note
added where a reader could mistake it for current state). **CORRECT-ALREADY** =
already matches current truth.

---

## R1 — Stale program state (Wave 1 merged; SRR-03 closed; matrices/spec exist)

| Search term | Affected changed files | Class | Correction |
|---|---|---|---|
| "Wave 1 not yet executed/accepted" | `wave-2-definition-of-ready.md` §5; `wave-3-definition-of-ready.md` §5 | STALE-CURRENT | Wave 1 merged; state Wave 2/3 gating on decision/DoR acceptance, not Wave-1 completion |
| SEC-1 "still open" | `09-ui-prototype/traceability-matrix.md` §4; `09-ui-prototype/README.md`; `implementation-ready-master-plan.md` (unchanged file) | STALE-CURRENT (changed files) / HISTORICAL (unchanged) | SEC-1 merged in Wave 1; "Area 6 + SEC-1 merged" is satisfied |
| "SRR-03 OPEN" | `mvp-completion-program.md` §190; historical validation-results (`task-011b`, `task-core-r2*`, `sync-engine-*`) | STALE-CURRENT (program.md current-facing line) / HISTORICAL-KEEP (validation records pre-merge) | Program.md line → SRR-03 CLOSED; historical records keep their as-of wording |
| "PR #172 … draft/unmerged" | `research-handoff.md` older log entries; `task-sec1-validation-results.md` | HISTORICAL-KEEP | Add dated note: Wave 1 merged 2026-07-16 (merge `d18f9a99`) |
| "master spec forthcoming" / "companion deliverable — pending" | `ui-implementation-phases-packet.md` L203; `wave-5-definition-of-ready.md` L37; `fulfillment-operating-modes.md` §7/§9; `shopify-fulfillment-status-model.md` §10 | STALE-CURRENT | The premium-UX master spec and the QA/UAT matrices now exist — drop "forthcoming/pending" |
| "corrected-head runtime pending" | `task-core-r2-*` (unchanged historical) | HISTORICAL-KEEP | Pre-merge records; corrected-head build 34995642 is green (recorded in the merged tracker) |

## R2 — Fulfillment Mode 2 = mandatory Wave 4 backend (was optional/Wave 5/stretch)

| Search term | Affected changed files | Class | Correction |
|---|---|---|---|
| "Mode 2 … Wave 5 / Wave 4 stretch / optional / if shipped / Mode 1 only" | `fulfillment-operating-modes.md` §10/§11.7; `mvp-capability-map.md` L46/L92–93; `fable-proposed-decision-pack.md` FUL-2/row 5; `release-readiness-gap-list.md` L28; `waves-2-6-dependency-and-gate-map.md` L31/L85; `implementation-readiness-checklist.md` L48/L54/L61; `wave-4-definition-of-ready.md` L29; `wave-5-definition-of-ready.md` L76/L102; `task-014-fulfillment-tracking-implementation-packet.md` L340; `fulfillment-mode-uat-matrix.md` L9; `waves-2-6-cross-domain-test-matrix.md` L98 | STALE-CURRENT | Both Mode 1 & Mode 2 are required MVP **Wave 4 backend**; Wave 5 owns only the mode **UI**. Spec BLOCK 2 |

## R3 — PII masking (no masking in the MVP — supersedes the earlier masked/toggle proposal)

| Search term | Affected changed files | Class | Correction |
|---|---|---|---|
| "masked by default / unmask toggle / PII visibility toggle" | `connector-roles-and-permissions.md` §3/§4.5/§4.6/§4.9; `security-pii-matrix-waves-2-6.md`; `waves-2-6-cross-domain-test-matrix.md` L123/L126; `premium-ux-master-specification.md` L357/L515/L538; `abandoned-checkout-policy.md` §3.2; `settings-permissions-spec.md`/`.html`; `orders-spec.md`; `order-review-spec.md`/`.html`; `cod-reconciliation.html`; `fable-proposed-decision-pack.md` ROLE-4; `ui-implementation-phases-packet.md` L273 | STALE-CURRENT | Both roles read raw operational PII; remove masking/toggle from MVP surface. Spec BLOCK 3 |
| "manual masking / retention masking / Mask a customer now" | `settings-permissions*`; `abandoned-checkout-policy.md`; `security-pii-matrix-waves-2-6.md` | STALE-CURRENT | Remove from MVP surface; masking is post-MVP (Class E); SEC-2 removes Wave-1 masking |
| `pii_snapshot_masked` / `action_mask_customer_pii` / retention sweep | `task-sec1-validation-results.md`; `task-sec1-security-hardening-packet.md` | HISTORICAL-KEEP | Add dated non-retroactive note: valid Wave-1 fact; SEC-2 corrects before MVP UAT/release |
| credential masking (`•••`, no read-back — DEC-004) | `stores*`, `traceability-matrix.md`, `ui-implementation-phases-packet.md`, DEC-028 | CORRECT-ALREADY | Credential masking is NOT PII masking — retained unchanged |
| log redaction ("stripped/masked from logs", `REDACTION_EXTENSION`) | `task-012-order-import-implementation-packet.md` L1154; `task-012-order-import-decision-closure.md` L2933/L3073 | CORRECT-ALREADY | Redaction ≠ masking — retained as mandatory |

## R4 — Fulfillment-state taxonomy (one four-layer taxonomy; Layer A = 7 enum families, verified 2026-07-16)

| Search term | Affected changed files | Class | Correction |
|---|---|---|---|
| "four families" / "four-family" | `shopify-official-api-notes.md` L1001; `shopify-…-captures-2026-07-16.md` §6; `fable-proposed-decision-pack.md` FUL-5 | STALE-CURRENT | "seven Shopify fulfillment enum families (Layer A)"; add dated re-verification incl. A7 |
| "six concepts" | `shopify-fulfillment-status-model.md` §1/§11 | STALE-CURRENT | Four-layer taxonomy (A enum families / B non-enum / C connector-derived / D user labels) — DONE |
| `FulfillmentDisplayStatus` "unverified / verify before freeze" | `shopify-fulfillment-status-model.md` §11-OQ1; `wave-4-definition-of-ready.md` L52 | STALE-CURRENT | A7 verified 2026-07-16 (18 values, no deprecations); display-only, not an automation input |
| "The six families are:" (skip_reason set) | `task-012-order-import-decision-closure.md` L1322 | CORRECT-ALREADY | Unrelated to fulfillment — it is the closed `skip_reason` set; left as-is |

## R5 — Wave 2 live-evidence rule (read-only Shopify preferred, not a merge blocker)

| Search term | Affected changed files | Class | Correction |
|---|---|---|---|
| "credential hard stop / waiver / cannot merge Wave 2 without dev store / VAL-B2 mandatory in Wave 2" | `wave-2-definition-of-ready.md`; `task-012-order-import-*`; `reconnect-catchup-backfill-policy.md`; `wave-6-e2e-uat-release-packet.md`; `waves-2-6-dependency-and-gate-map.md`; `waves-2-6-cross-domain-test-matrix.md` L140; `reconnect-backfill-uat-matrix.md`; `cod-uat-matrix.md`; `release-readiness-gap-list.md` | STALE-CURRENT | Odoo.sh mandatory; read-only Shopify preferred but deferrable to Wave 6 without waiver; mutation waves 3–5 keep genuine dev-store evidence. Spec BLOCK 5 |
| VAL-B2 (pre-existing acceptance-matrix rows) | `mvp-acceptance-matrix.md` (unchanged) | HISTORICAL-KEEP | Row 22 already routes dev-store UAT to Wave 6; no change |

## R6 — Decision pack restructure (Groups A–H → Classes A–E)

| Search term | Affected changed files | Class | Correction |
|---|---|---|---|
| "Groups A–H" as one undifferentiated acceptance | `fable-proposed-decision-pack.md` | STALE-CURRENT | Restructure into Class A (binding rulings) / B (product decisions) / C (technical/Claude) / D (empirical preflight) / E (post-MVP). Spec BLOCK 6 |

---

## Boundary note

No `addons/**` file is edited by this correction (masking code is only *described*
and routed to SEC-2). No decision is marked Accepted. Wave 2 stays
unauthorized/unstarted. PR #173 stays draft/open/unmerged. Protected references
unchanged. Historical validation/handoff records are preserved with dated notes
rather than rewritten.
