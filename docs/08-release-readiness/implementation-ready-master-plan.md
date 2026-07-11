# Implementation-Ready Master Plan — Sequence, Gates, and What Starts After Acceptance

> **Status: Proposed for ChatGPT review. NOT accepted. Docs-only.**
> Produced 2026-07-10 (AR-042 candidate). This is the single sequenced
> roadmap from acceptance of this planning PR to MVP release. Every
> implementation step remains gated by its own distinct ChatGPT act;
> **bold** marks ChatGPT acts. Packets: Task 012/013/014/015, Area 6
> ("Task 016"), UI U1–U3, Webhooks W1–W5 (all in
> `../07-implementation-plan/*-packet*.md`), UAT
> (`final-mvp-uat-plan.md`), release
> (`release-readiness-execution-plan.md`).

## 1. Decisions ChatGPT makes when reviewing this PR (one review, eleven calls: ten binding + one optional)

1. **Accept/revise DEC-027** (branch-A pilot scope).
2. **Accept/revise DEC-028** (credential/PCD posture ladder; also the
   MBQ-04 register-wording upgrade).
3. **Accept/revise DEC-029** (Lite/Full packaging) — carries ARCH
   PD-1 (product_export module) and PD-2 (views in owning modules).
4. **Ratify ARCH PD-3..PD-6** (sale manifest deltas; binding
   names/keys incl. the fulfillment-keying refinement; checkpoint
   ownership; API 2026-07 pin).
5. **Confirm the flagged Task-012 interpretations** (D-012-3
   skipped-by-policy routing incl. its one named additive core seam —
   the `JobPolicySkip` dispatcher exception; D-012-4
   ambiguous-customer pre-creation hold; D-012-6 address children;
   D-012-9 T-B tax mechanism; the `shopify_line_item_gid` field on
   `sale.order.line` — the one MVP field added to a standard Odoo
   model, which Task 014 then depends on).
6. **Confirm D-013-5** (the third named sudo for the location cache)
   and **D-013-8** (baseline import deferred to 013B).
7. **Confirm D-014-2** (TD-002 fix as the one named core edit),
   **D-014-6** (no fulfillmentOrderMove in MVP), and the Task-014
   `trigger_origin='fulfillment_tracking_change'` selection_add — an
   extension of the accepted DEC-019 two-value vocabulary, flagged as
   such in the packet.
8. **Confirm D-015-7** (media deferred to 015B) — this re-scopes
   DEC-003's "basic image/media sync" for the export direction and
   must be an explicit call, not silent.
9. **Confirm D-A6-1/D-A6-5/D-A6-7** (Area-6 split; the additive core
   job-actions file incl. manual retry from `skipped` with
   retry_count reset; the readiness pending-slot closure — the
   red-team BLOCKER fix without which no store can reach `connected`,
   incl. the explicitly flagged webhook_hmac not-applicable
   relaxation).
10. **Confirm the webhook MVP-tail scoping** (W1+W2 in MVP, W3–W5
    out) — or re-scope DEC-003's C-SYNC webhook rows explicitly.
11. Optionally: the OP-42 one-line binding confirmation; the AR-040
    status-cell wording.

Accepting the PR without naming exceptions accepts the ten binding
calls (1–10) as proposed; item 11 is optional and lapses silently if
unaddressed (stated here so the review is one act, not eleven
separate ones).

## 2. Critical path (backend chain — each step: **gate act** → one implementation session → draft PR → **merge review** → runtime-green closure)

| # | Step | Packet | Prereqs | Ready when |
| --- | --- | --- | --- | --- |
| 1 | **Task 012 order import** | task-012 packet §15 prompt | This PR merged | **Immediately after acceptance** — the first implementation session |
| 2 | **Task 016 / Area 6 triggers** | area-6 packet §7 prompt | 012 merged | closes UAT blocker U-4; carries D-A6-7, without which no store reaches `connected` — hard prerequisite for steps 4–6 dev-store validation |
| 3 | **UI Phase U1** | ui packet §6 prompt | Area 6 merged | closes most of U-3 |
| 4 | **Task 013 inventory** | task-013 packet §8 prompt | 010 merged (fact); sequenced here per accepted order | first mutation task — dev-store evidence rule active |
| 5 | **Task 014 fulfillment** | task-014 packet §8 prompt | 012 merged (order bindings + line GIDs) | carries the TD-002 fix |
| 6 | **Task 015 product export** | task-015 packet §8 prompt | 010 merged; DEC-029/PD-1 accepted | completes DEC-003 MVP scope (less 013B/015B deferrals) |
| 7 | **UI U2 (wizard/readiness)** | ui packet §1 (prompt drafted post-U1) | U1 merged; VAL-B2 strongly recommended first | |
| 8 | **UI U3 (domain screens)** | ui packet §1 (prompts per domain post-U1) | U1 + each domain merged | rolling — may interleave with 4–6 |
| 9 | **W1 + W2 webhooks (MVP tail)** | webhook packet §6 (W1 prompt; W2 post-W1) | Area 6 + U1 merged | completes C-SYNC-01/02/03 |
| 10 | **UAT waves 1–3** | final-mvp-uat-plan | per its §2/§6 entry criteria | human reviewer sessions |
| 11 | **Release execution + Go/No-Go** | release-readiness-execution-plan | UAT exit | **the release act** |

## 3. Parallel external tracks (independent of the chain; start any time)

- **P-A VAL-B2 execution** (human, live Shopify) —
  `../05-qa/val-b2-closure-plan.md` incl. its new §12; unblocks U-2,
  wizard honesty, UAT entry.
- **P-B Concurrency plan execution** (runtime) —
  `../05-qa/sync-engine-concurrency-validation-plan.md` incl. §13;
  UAT entry criterion (or explicit waiver).
- **P-C Docs-maintenance micro-patch** (OP-25 residue) — unchanged,
  ChatGPT sets its allowed-files list.
- **P-D Phase-2+ preparation (no implementation):** DEC-028 Rung-2
  evidence gathering; B-1 planning under RA-003's own future lift act.

## 4. Deferred-with-names (not lost)

013B one-time inventory baseline import; 015B media/image export;
W3/W4 webhook accelerations; add-on modules (accounting/refund/
payout/multi-store); OAuth/B-1/App Store/billing/compliance (Phase
2+); entitlement/licensing mechanics (Phase 2 commercial).

## 5. The exact next implementation session after acceptance

**Task 012**, using the locked prompt at
`../07-implementation-plan/task-012-order-import-implementation-packet.md`
§15, issued verbatim by ChatGPT in a new session after: this PR merges,
the order-domain gate act is performed (criterion-12 blocker
reconfirmation included), and the base SHA is stated. No broad
research or architecture exercise is required first — that is this
package's completion claim, audited in
`mvp-planning-completion-audit.md` §6.
