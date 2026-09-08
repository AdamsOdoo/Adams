# Adams Shopify connector — execution instructions

## Authority and active work

Follow the user's latest instruction first, this file second, then accepted V2 contracts and ADRs. CLAUDE.md, CHATGPT.md and GPT_SOL.md are compatibility entrypoints/history, not separate authorities. Do not restart from historical prompts.

Read docs/v2/13-continuous-execution-handoff.md and docs/v2/16-delivery-blueprint.md, verify branch/head and worktree, then load only the owning contract and relevant skill. The user authorized continuous V2 development, testing and Astra/Sol orchestration. **UI redesign is parked until the user resumes it; proposals 01/02 are unapproved.** Backend and delivery work continue without routine approval stops.

Work on codex/v2-continuous-implementation. Preserve PR #210/#211 and unrelated changes. Never reset, rebase, stash, force-push or discard preserved work. Commit coherent changes; publish using an authorized write connection. If blocked, preserve local commits and record that they are unpublished. Do not claim GitHub contains them.

Only the authorized development environment and Shopify store testin-lzhbzhtc.myshopify.com may be used. Verify exact build, database/company and shop identity before live work. No staging/production, other stores or public release without separate authority. Use the approved secure credential mechanism; never put secrets, customer payloads or PII in prompts, fixtures, commits or evidence.

## Architecture that must survive repairs

- Odoo 19 modular monolith; preserve addon/model/table/XML IDs, bindings, audit and mutation history. Expand/migrate before switching. Optional modules cannot access another optional owner's schema merely because a shared table exists.
- Typed Shopify gateways own remote I/O, pinned operations and normalized transport/GraphQL/business errors. Webhooks are authenticated, deduplicated hints; scheduled reconciliation repairs missed/out-of-order events.
- Commands enforce actor capabilities, company, exact store, activation and configuration/connection generation at admission and before effects. UI hiding, context booleans and broad sudo are not authorization.
- Durable intent, operation scope, claim fencing and readback prevent duplicate effects. After-send uncertainty remains query-only until resolved; never blindly retry it.
- Preserve global deterministic lock ordering, run/job/handler binding and monotonic scan checkpoints. SQL is justified for migrations, constraints and concurrency correctness as well as measured performance; explain ownership and transaction boundaries.
- Framework transactions own normal RPC commits. Independent cursors need explicit lifecycle. Cron progress APIs are not manual-commit workarounds for ordinary business RPCs.
- Deterministic bindings, explicit inventory first-push approval, protected catalog fields/media, whole-order validation and explicit fulfillment notification remain invariant.
- No speculative broker, external worker, generic repository layer, event bus or framework. Add an abstraction to enforce an actual boundary, isolate a side effect, or remove demonstrated duplication.

## Skills and sources

Repository skills live in .agents/skills/. Read directly if discovery is unavailable; do not install global/personal skills for this project.

| Work | Skill |
| --- | --- |
| Models, APIs/webhooks, schema, runtime, security and domain behavior | connector-backend/SKILL.md |
| Business journeys, native UI, management reporting and usability | connector-journey/SKILL.md |
| Failure triage, native/lifecycle/live qualification and evidence | connector-qualification/SKILL.md |

Official platform/model references are routed from blueprint 16. Refresh version-sensitive facts for the touched operation, not the whole research corpus on every packet. Vendor documentation describes competitor behavior, not platform guarantees. Historical failures/rejected approaches remain regression inputs.

## Astra/Sol coordination and efficiency

One lead owns integration and handoff. Astra handles architecture, cross-domain decisions, mutation/security review and user-facing design when resumed. Sol handles bounded implementation, test repair and evidence extraction. Start Sol medium for straightforward tasks, high for ORM/state/concurrency; use Astra high for difficult integration, raising effort only for unresolved risk. These are initial routing choices, not quota guarantees.

Delegate concrete non-overlapping work beside useful lead work. Usually one implementation agent and one lead suffice. Give objective, exact source, owned paths, constraints, acceptance, tests and return format. Reviewers receive raw evidence and criteria, not instructions to agree. The lead inspects the diff; summaries are not proof. Separate-model review is not human/organizational release independence.

Use incremental searches and batched independent reads. Do not re-audit unchanged code, request maximal effort universally, or run duplicate full campaigns. Measure actual cost/latency when available; do not manufacture usage promises.

## Evidence and continuation

Run focused checks per coherent change, then affected native gates. Full install/upgrade/concurrency/browser/load/live campaigns belong at integration gates and candidate freeze. Skipped, blocked, simulated or failed checks are never passes. Fix causes before cascades; update stale fixtures through sanctioned surfaces, never weaken production safety.

Every advertised feature needs actor → authorization → input → local/remote effect → verified business result → user evidence → recovery. Native backend proof precedes production UI wiring. Prototype approval does not qualify a workflow.

Update the canonical handoff after material checkpoints: source/head, unpublished changes, behavior, exact checks/results, external state, defects, rollback and first next action. Checkpoint atomic work before context pressure. Never claim an exact chat-limit detector, automatic new-chat creation or background execution after the turn ends.

Routine defects, reversible fixes and already-authorized dev tests are work to complete. Escalate significant new scope/architecture, irrecoverable data risk, access outside authority, or final promotion. Preserve the safe checkpoint and continue independent useful work where possible.
