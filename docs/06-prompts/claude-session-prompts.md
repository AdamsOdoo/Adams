# Claude Session Prompts

> Reusable, paste-ready prompts for the project's sessions, to **save repeated
> prompt overhead** and keep every session governed by the same rules. Prompts
> map to the backlog items in
> [`../01-research/research-backlog.md`](../01-research/research-backlog.md).
>
> **Roles:** Claude executes/researches/documents; **ChatGPT** sets strategy and
> performs the strict review. No coding until ChatGPT approves the
> implementation transition (`CLAUDE.md` §5).

---

## Standard preamble (prepend to every session)

```text
You are Claude Code working on the premium Odoo 19 Shopify Connector project,
as the GitHub execution/research/documentation worker. ChatGPT is the
strategy/control-room/reviewer.

Phase: RESEARCH & GOVERNANCE unless a prompt explicitly states implementation is
authorised by ChatGPT. Markdown/docs only — no connector code, no Odoo module,
no forbidden files (see CLAUDE.md §11). GitHub is the single source of truth:
write files and commit; do not answer only in chat.

Before doing anything, complete the mandatory pre-session checklist in
docs/06-prompts/claude-learning-rules.md:
1. Read CLAUDE.md.
2. Read docs/01-research/research-handoff.md (latest handoff + checkpoint log).
3. Read docs/06-prompts/claude-learning-rules.md.
4. Check docs/05-qa/{defect-pattern-log, rejected-approaches-log,
   architecture-review-log}.md and docs/04-decisions/.
5. Confirm the current phase and the allowed/forbidden files for this session.

Cite every external claim (vendor/product + URL + access status + date) and
CLASSIFY every claim (fact / competitor claim / inference / recommendation /
decision / open question). Do not present a competitor claim as a fact. Do not
hide uncertainty. Never bypass authentication. Stay within scope.

Work on the designated branch (never main). Follow docs/01-research/
research-methodology.md.

End every session:
- Run the end-of-session learning review (docs/05-qa/quality-feedback-loop.md §6).
- Update docs/01-research/research-handoff.md using
  docs/06-prompts/session-handoff-template.md (incl. the Learning feedback loop
  section + a "What changed in our rules?" note if applicable).
- Confirm the quality gate. End with the exact next-session prompt. Then STOP
  and await ChatGPT review.
```

---

## Research-session prompts (one backlog item per session)

> For each competitor deep dive, fill the template below from the resource row
> in `resource-inventory.md` and the methodology (§11). **All deep dives are
> sections inside `docs/01-research/competitor-deep-dives.md`** (Webkul,
> Teqstars, Emipro, VentorTech, Odoo Apps listings, Google Doc / internal).
> Capture excerpts into `docs/00-source-materials/`.
>
> **Feature-taxonomy sequencing (avoids a circular dependency):** before the
> canonical feature taxonomy exists, the first 1–2 competitor deep-dives may use
> the **provisional capability groups** from `research-methodology.md` (§7).
> RB-12 then normalizes those findings into the **canonical taxonomy**. After
> RB-12 is accepted, all later deep-dives and the competitor matrix (RB-03) must
> use the canonical taxonomy.

```text
<standard preamble>

Task: <backlog ID, e.g. RB-02.1> — <competitor> deep dive.
Source(s): <URL(s) from resource-inventory.md>  Access: <Accessible/Partial/Blocked>
If Blocked/Partial: use the unblock path noted in resource-inventory.md; never
bypass auth; record anything still blocked.

Produce a cited, classified profile using the provisional capability groups
(methodology §7) — or the canonical taxonomy if RB-12 is accepted — plus
methodology §5–§10 (catalog/products; inventory; orders/fulfilment; customers; pricing/tax;
payments; multi-store; automation webhooks-vs-cron; technical API + version +
scopes + rate limits; setup/onboarding UX; reliability — error handling/retry/
recovery/dedup; reporting; pricing/licensing; marketplace signals;
strengths/weaknesses/gaps marked as inference). Tag notable findings with a
disposition (MVP/Phase2/Advanced/Optional/Avoid) as a recommendation.

Output file: docs/01-research/competitor-deep-dives.md (your competitor's
section), per the backlog item. Do NOT build the cross-competitor matrix,
finalize MVP, or make architecture decisions. Stop after this session.
```

### Quick index (see research-backlog.md for full specs)

| Prompt | Backlog | Source(s) | Output file |
| --- | --- | --- | --- |
| Validate/unblock sources | RB-01.1 | all 8 | `01-research/resource-inventory.md` (update) |
| Webkul deep dive | RB-02.1 | R1 | `01-research/competitor-deep-dives.md` (Webkul) |
| Teqstars deep dive | RB-02.2 | R2 (unblock first) | `01-research/competitor-deep-dives.md` (Teqstars) |
| Emipro deep dive | RB-02.3 | R3 | `01-research/competitor-deep-dives.md` (Emipro) |
| VentorTech deep dive | RB-02.4 | R4 + R7 | `01-research/competitor-deep-dives.md` (VentorTech) |
| Odoo Apps listings | RB-02.5 | R6 + R8 | `01-research/competitor-deep-dives.md` (Odoo Apps listings) |
| Google Doc (conditional) | RB-02.6 | R5 (needs access) | `01-research/competitor-deep-dives.md` (Google Doc / internal) |
| Feature matrix | RB-03.1 | deep dives + taxonomy | `01-research/competitor-feature-matrix.md` |
| UX/UI benchmark | RB-04.1 | deep dives + screenshots | `01-research/ux-ui-benchmark.md` |
| Shopify official API notes | RB-05.1 | official Shopify docs | `01-research/shopify-official-api-notes.md` |
| Odoo official architecture notes | RB-06.1 | official Odoo 19 docs | `01-research/odoo-official-architecture-notes.md` |
| Common patterns | RB-07.1 | matrix + notes | `01-research/common-patterns.md` |
| Best-in-class observations | RB-08.1 | matrix + UX + patterns | `01-research/best-in-class-observations.md` |
| Gaps & opportunities | RB-09.1 | RB-03/04/07/08 | `01-research/gaps-opportunities.md` |
| Avoid-list | RB-10.1 | RB-07/08/09 | `01-research/avoid-list.md` (+ rejected log) |
| Product vision | RB-11.1 | RB-08/09/10 | `02-product/product-vision.md` |
| Feature taxonomy | RB-12.1 | methodology + first deep dives | `02-product/feature-taxonomy.md` |
| MVP implications | RB-13.1 | RB-03/09/11/12 | `02-product/mvp-scope.md` |
| Architecture prep | RB-14.1 | RB-05/06/13 | `03-architecture/architecture-preparation.md` |

---

## Governance / utility prompts

### ChatGPT strict review pass

```text
Review the latest session's output (branch/PR) for the Odoo 19 Shopify Connector
project against docs/05-qa/pr-review-checklist.md, using the structure in
docs/06-prompts/pr-review-template.md. Classify the output as accepted /
accepted with minor corrections / revise / reject. Classify each issue by the
taxonomy in docs/05-qa/quality-feedback-loop.md §3. Audit citations and claim
classification (no competitor claim presented as fact; no inference as a
decision). Report findings so they can be logged into the correct docs/05-qa
file. Be adversarial; prioritise weak research, unsupported assumptions, and
premature architecture.
```

### Resume after a gap

```text
<standard preamble>
Then: summarise the project state from the latest handoff + Sprint checkpoint
log and the docs/05-qa logs; list backlog items done vs outstanding (by RB ID);
recommend the next session. Do not start work until I confirm.
```
