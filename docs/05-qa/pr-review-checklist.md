# PR / Review Checklist

> The standard checklist for reviewing any deliverable or PR in this project —
> used for Claude self-review and for ChatGPT's strict review pass. Findings
> feed the [Quality Feedback Loop](./quality-feedback-loop.md).
>
> **This checklist grows.** When an issue type recurs (feedback-loop §4),
> add/sharpen a check here so the same mistake is caught systematically.

## Before reviewing

- [ ] Read the latest handoff (`../01-research/research-handoff.md`).
- [ ] Read [`../06-prompts/claude-learning-rules.md`](../06-prompts/claude-learning-rules.md).
- [ ] Check [`defect-pattern-log.md`](./defect-pattern-log.md),
      [`rejected-approaches-log.md`](./rejected-approaches-log.md), and
      [`architecture-review-log.md`](./architecture-review-log.md) for relevant
      prior findings.

## Review classification (record the outcome)

- [ ] Overall decision recorded: **accepted / accepted with minor corrections /
      revise / reject**.
- [ ] Every issue classified by type (feedback-loop §3) and logged in the
      correct `/docs/05-qa` file.
- [ ] Any issue type now at count ≥ 2 → a rule/checklist was updated.
- [ ] Any issue type at count ≥ 3 → implementation paused; prevention gate added.

---

## A. Research / documentation phase (active now)

- [ ] **Scope respected** — only the sprint's allowed files changed; no code
      files; no forbidden files; no actual Odoo module created.
- [ ] **Branch target is correct** — PR targets `Shopify-connector`, **not**
      `main`, **not** plain `dev`, **not** `dev/Shopify-connector`
      (`CLAUDE.md` → Branch governance).
- [ ] **Capability use is appropriate** — large parallel-agent research is
      allowed when justified by the task, documented in the handoff (plan /
      workstreams / sources / stop condition / synthesis / verification), and
      scoped to the allowed files (not a hard agent/token cap).
- [ ] **Small patch sessions** did not use unnecessary large fan-out.
- [ ] **High-power research outputs** were synthesized, verified, and classified
      as facts / claims / inferences / recommendations / open questions.
- [ ] **Citations present** — every external claim has vendor/product + URL +
      access status + date.
- [ ] **Claims classified** — facts vs competitor claims vs inferences vs
      recommendations vs decisions vs open questions (CLAUDE.md §8).
- [ ] **No competitor claim presented as fact**; no inference presented as a
      decision.
- [ ] **Access issues recorded** — blocked/auth-walled sources noted; no bypass
      attempted.
- [ ] **No premature architecture decision** (AR-002…AR-008 stay "Not decided"
      until ChatGPT accepts a candidate). **No unauthorized MVP scope change**
      beyond the accepted baseline in `../04-decisions/DEC-003-mvp-scope.md`
      (DEC-003 itself is finalized — re-proposing/re-deciding MVP scope from
      scratch is not required or expected).
- [ ] **GitHub updated** — output is committed files, not just chat.
- [ ] **Handoff updated** — including the Learning feedback loop section.
- [ ] **Token discipline** — no redundant re-fetching / re-derivation.

## B. Architecture phase (activate later)

- [ ] Approach checked against `rejected-approaches-log.md` (revisit condition
      met if reintroduced).
- [ ] Required evidence present before acceptance (no premature architecture).
- [ ] Odoo 19 assumptions verified against official docs/source.
- [ ] Shopify API assumptions verified against official docs and stated version.
- [ ] Modularity: clear layering, single responsibility, isolated addon(s).
- [ ] Accepted decisions promoted to an ADR in `../04-decisions/`.

## C. Implementation phase (activate later — gated)

- [ ] **Allowed/forbidden files** honoured exactly; connector remains isolated
      from `adams_base`/customer code and follows the approved modular connector
      addon-family architecture once defined; do not collapse the connector into
      one giant module.
- [ ] **Idempotency / duplicate prevention** — stable external-ID mapping;
      re-running a sync does not double-create/update.
- [ ] **Error handling** — failures caught, surfaced, actionable.
- [ ] **Retry / recovery** — transient failures retried with backoff; partial
      runs resumable; no silent data loss.
- [ ] **Rate-limit awareness** — Shopify limits respected (throttle/backoff/batch).
- [ ] **Security / permissions** — least-privilege scopes; secrets never logged;
      correct Odoo access rules.
- [ ] **Performance** — bulk ops batched; no N+1 sync calls; large
      catalogs/orders considered.
- [ ] **Tests** — unit + integration for new logic, including prior defects and
      edge cases; acceptance criteria covered.
- [ ] **Rollback notes** present; **definition of done** met.
- [ ] **Technical debt logged** in `technical-debt-register.md`.
