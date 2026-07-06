# UI/UX Design Review Checklist

> Strict review checklist for the UI/UX Final Design Specification package
> ([`../02-product/ui-ux-final-design-spec.md`](../02-product/ui-ux-final-design-spec.md),
> [`../02-product/screen-inventory-and-navigation-map.md`](../02-product/screen-inventory-and-navigation-map.md),
> [`../02-product/mvp-user-flows-and-state-models.md`](../02-product/mvp-user-flows-and-state-models.md),
> [`../07-implementation-plan/ui-ux-implementation-task-map.md`](../07-implementation-plan/ui-ux-implementation-task-map.md))
> — and for **every future operator-facing UI implementation task** once
> the UI gate opens. Complements (does not replace) the accepted Part D
> §19 premium acceptance checklist and
> [`pr-review-checklist.md`](./pr-review-checklist.md). Docs-only;
> authorizes nothing.

## Status

**Accepted by ChatGPT on 2026-07-06** (PR #91 acceptance patch;
[`AR-023`](./architecture-review-log.md)) as the checklist for future
UI/UX design and implementation review. **Does not replace** the
accepted Part D §19 premium acceptance checklist or
[`pr-review-checklist.md`](./pr-review-checklist.md). **Applies once a
UI implementation gate is opened** — this acceptance does not itself
open that gate.

Usage: every item must be checked **Yes / No / N/A with a reason**. A
"No" on any **[Gate]** item blocks acceptance of the design doc (or, later,
the implementation PR).

## A. Architecture alignment

- [ ] **[Gate]** Every screen/flow statement traces to an accepted source
      (DEC-003–020, Parts A–E, MBQ-04 posture) or is explicitly labelled
      **[Design proposal]** / **[Open item]** — nothing unlabelled, nothing
      contradicting an accepted decision.
- [ ] **[Gate]** Fixed vocabularies reused verbatim: 7 job sources (6 +
      `odoo_event`), 10 job states, 16 error classes (no 17th), 6
      manual-review sub-reasons, 4 retry UI cases.
- [ ] **[Gate]** Post-Part-D decisions are reflected, not re-litigated:
      MBQ-06 readiness split, MBQ-08 disconnect retention, MBQ-17
      reconciliation posture (per-store/per-domain, configurable
      conservative cadence), MBQ-33 first-push granularity, MBQ-34
      review-then-apply, MBQ-41 notification default, MBQ-45 one shared
      role-gated surface + 1:1 groups, MBQ-52 API pinning, MBQ-54
      disable-not-uninstall, MBQ-60 tracking dependency, DEC-019
      `odoo_event`, DEC-020 same-currency-only + enqueue-only product
      webhooks; plus the AR-020 closure outcomes screens depend on
      (MBQ-35 `on_hand` excluded; MBQ-32 `free_qty` decided, no
      source-choice UI; MBQ-29 single fallback partner).
- [ ] **[Gate]** No rejected approach reintroduced (RA-006/008/009/013/
      014/015/016/017/018/019/020/021/022/023 checked by name).
- [ ] Order import remains screen-less (MBQ-26): only the two accepted
      error-center extensions are specified.

## B. No unsupported claims

- [ ] **[Gate]** No invented Shopify/Odoo API behaviour — platform claims
      cite already-verified repo research only.
- [ ] **[Gate]** No competitor claim beyond existing repo research
      (ux-ui-benchmark / competitor docs), and none elevated to fact.
- [ ] **[Gate]** No encryption/at-rest security claim anywhere —
      credential copy describes masking + access restriction only (MBQ-04
      posture).
- [ ] All sample copy is labelled illustrative (MBQ-22 open); no string is
      presented as final.

## C. No implementation authorization

- [ ] **[Gate]** The package states, and nothing in it contradicts, that
      it authorizes no code, opens no gate, and starts no Task 002.
- [ ] **[Gate]** No Python/XML/CSV/manifest/test/CI content, no credential
      /API-client/setup-wizard/test-connection implementation, anywhere.
- [ ] **[Gate]** No field/model/group/menu name invented beyond accepted
      docs — only AR-019 accepted planning names or explicitly-marked
      proposed directions; XML IDs everywhere deferred to MBQ-03.

## D. Screen completeness and states

- [ ] **[Gate]** Every specified screen has empty, loading, success,
      warning, error, and (where applicable) manual-review states — no
      happy-path-only screen.
- [ ] Every screen names purpose, users, entry points, fields/regions,
      primary/secondary actions, layout, hierarchy, validations,
      permissions, decision/open-question links, implementation notes,
      what-must-not-be-built-yet, and its clutter failure mode.
- [ ] Every empty state guides a concrete next action; every zero state is
      affirmative ("0 — all clear"), never a bare number.
- [ ] Loading states are honest (no fake real-time; mechanism named).

## E. Errors and recovery

- [ ] **[Gate]** Every error type leads with a plain-language reason +
      suggested fix + owner state; technical detail only behind an
      explicit expand (RA-016).
- [ ] **[Gate]** Retry is class-conditional (exactly the 4 cases);
      ambiguous outcomes require a verification read; terminal rows carry
      no retry control; no "force" bypass exists.
- [ ] Errors are actionable and non-catastrophic in tone; every failure
      has a next action; no dead ends under any role (route/assign
      exists).
- [ ] Manual review always shows the specific sub-reason, never generic.

## F. Risky operations

- [ ] **[Gate]** Every risky/destructive/irreversible operation
      (destructive write, first push, disconnect, publish, notification
      opt-in, source-of-truth change) has a preview and/or a
      consequence-stating confirmation, with copy that states what will
      happen.
- [ ] **[Gate]** Guards are unbypassable by any flag/setting/role (Part A
      §I.5) — the design offers no bypass affordance.
- [ ] Destructive actions are last in action order and never default
      focus.

## G. Permissions

- [ ] **[Gate]** The four roles (1:1 groups, one shared surface) are
      applied consistently on every screen; actions gated, surfaces
      shared; Auditor can act on nothing.
- [ ] Reviewer-only resolution for the 6 confirmation-required
      sub-reasons; Admin-only for settings/credentials/mappings.
- [ ] Role capabilities are legible in plain language (S14).

## H. Open items respected

- [ ] **[Gate]** Every MBQ open/residual item that constrains a screen is
      cited on that screen; nothing open is presented as decided; nothing
      decided is presented as open.
- [ ] The "Open items and non-decisions" list is complete against the
      register's current state (spot-check MBQ-03/22/44/04/05/56/61/32/38
      and DEC-020 residuals).

## I. MVP vs later

- [ ] **[Gate]** Every element is marked MVP or Later; nothing deferred by
      DEC-003 (order edits/refunds/returns, multi-store, multi-package
      automation) or by DEC-018 (per-order notification override) appears
      as MVP.
- [ ] Later/premium candidates are explicitly not adopted (no hidden
      stubs, no "coming soon" UI).

## J. Odoo-native feasibility

- [ ] Every surface maps to a standard Odoo 19 pattern (list/form/kanban/
      wizard/statusbar/smart button/chatter/activities) or to one of the
      Part D-justified custom patterns — no exotic UI machinery assumed.
- [ ] Chatter and the structured audit trail remain distinct artifacts.
- [ ] No design relies on `sudo()` crossing record-rule boundaries;
      access is deny-by-default.

## K. Premium differentiation

- [ ] The package delivers the researched differentiators: unified command
      center; recovery-first error center; named diagnostics with fix
      hints; dry-run/preview before destructive apply; honest freshness/
      throttle status; readiness self-test.
- [ ] The named competitor anti-patterns are absent: raw cron internals;
      toggle walls; email-only errors; "real-time" overstatement;
      irreversible footguns; blind mappings; gated guidance.

## L. Premium Simplicity Standard

- [ ] **[Gate]** Smooth guided flows: multi-step work follows stage →
      inspect → process → verify → log, with per-step verified moments and
      safe resume.
- [ ] **[Gate]** Clean visual hierarchy: one purpose per screen; the most
      consequential element first; field/action budgets respected or the
      overflow moved behind progressive disclosure.
- [ ] **[Gate]** Minimal cognitive load: one decision per wizard step;
      pre-filtered default views; one consistent vocabulary everywhere.
- [ ] **[Gate]** Progressive disclosure: defaults → advanced → technical
      detail, uniformly applied.
- [ ] **[Gate]** Business-user-friendly copy: no jargon on any action
      path; internal tokens/API terms never primary labels; status never
      colour/icon alone.
- [ ] **[Gate]** No clutter: dashboards high-signal only (nine cards, no
      vanity metrics); no raw logs as primary experience; no overloaded
      forms.
- [ ] **[Gate]** No generic-connector feel: the product reads as a
      polished, confident, Odoo-native product — not a settings pile with
      a log viewer.
- [ ] **[Gate]** **Does every screen feel clean, premium, modern, and
      human-friendly without adding unnecessary complexity?** (Review each
      screen against the design rule: premium = clarity, confidence,
      polish, guidance, recovery — never more screens/colors/charts/
      complexity.)

## M. Future implementation usefulness

- [ ] The task map groups all future UI work with prerequisites, risk,
      dependencies, must-not-dos, acceptance criteria, and premium
      requirements — sufficient for `CLAUDE.md` §9 task authoring without
      guessing.
- [ ] Every screen's "what must not be implemented yet" is consistent
      with the currently-open (core-only, zero-UI) gate.

---

**Result recording.** Reviews of this package record their outcome in
[`architecture-review-log.md`](./architecture-review-log.md) per the
established AR pattern; implementation-era reviews additionally satisfy
Part D §19 and [`pr-review-checklist.md`](./pr-review-checklist.md).
