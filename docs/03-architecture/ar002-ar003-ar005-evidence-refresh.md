# AR-002 / AR-003 / AR-005 — Evidence Refresh (2026-07-02)

> **Architecture Decision Sprint — evidence refresh only.** This file is the **dated
> evidence-refresh record** supporting the proposed decisions in
> [`../04-decisions/DEC-004-distribution-api-auth-strategy.md`](../04-decisions/DEC-004-distribution-api-auth-strategy.md),
> [`DEC-005-sync-orchestration-strategy.md`](../04-decisions/DEC-005-sync-orchestration-strategy.md),
> and [`DEC-006-binding-dedup-identity-strategy.md`](../04-decisions/DEC-006-binding-dedup-identity-strategy.md).
> **It verifies facts; it does not decide anything.** AR-002/AR-003/AR-005 move to
> **"Proposed for ChatGPT review"** in
> [`../05-qa/architecture-review-log.md`](../05-qa/architecture-review-log.md) on the
> strength of the DEC files, **not** on this file alone — **no architecture decision is
> self-accepted here**, and **no implementation is authorized**.

## Date and scope

- **Date:** 2026-07-02.
- **Scope:** **only** decision-critical evidence for AR-002 (distribution/API/auth),
  AR-003 (sync orchestration/queue), and AR-005 (binding/dedup/identity) that was **not
  already resolved** by the RB-14 Part 1 refresh (2026-07-01,
  [`rb14-official-source-refresh.md`](./rb14-official-source-refresh.md)) and the RB-14
  Part 2 resolution (2026-07-01,
  [`rb14-part2-open-question-resolution.md`](./rb14-part2-open-question-resolution.md)).
  Those two files remain the dated Tier-1 baseline for the great majority of AR-002/005
  Shopify facts (GraphQL-primary/REST-legacy, webhook delivery/HMAC/dedup-header
  behaviour, the 17-mutation `@idempotent` list + 24-hour dedup TTL, GID non-permanence,
  `ir.model.data` shape, `sudo()` semantics, Odoo Online's custom-module incompatibility)
  — they were re-verified **one day before this sprint** and are not re-fetched here to
  avoid redundant token spend (`claude-learning-rules.md` "token waste" category).
- **What this sprint adds:** the **one genuinely open, decision-blocking gap** the RB-14
  Part 2 resolution explicitly left unresolved for AR-003 — whether **Odoo.sh / on-prem**
  officially support `server_wide_modules` and an external Jobrunner (which gates OCA
  `queue_job`, AR-003 Option 3) — plus a **community-tier** check of OCA `queue_job`
  itself for the Odoo 19.0 line. No Shopify page was re-fetched this sprint (no new
  Shopify open question was in scope); no competitor/vendor/blog/forum source was used.

## Method

Two narrow, single-purpose fetch passes, both restricted to the **official/allowed
tiers** in the sprint prompt:

1. **Official Odoo.sh docs** (`odoo.com/documentation/19.0/administration/odoo_sh/**`,
   with the raw-RST fallback where needed) — checked for `server_wide_modules` support,
   a custom long-running/daemonized worker process, restrictions on custom
   processes/threads, `ir.cron`/scheduled-action limits beyond the already-known
   staging-cron neutralization, and any explicit statement on OCA `queue_job`.
2. **OCA `queue_job` GitHub repo + PyPI** (community/secondary tier per the sprint
   prompt) — checked for a 19.0 release, the Jobrunner's process model, the
   `server_wide_modules` install requirement, and stated production maturity.

**Stop condition:** both passes returned (Odoo.sh docs fetched and read; OCA repo/PyPI
fetched and read); no further pages were needed because the two passes together resolve
what official evidence can resolve and leave what it cannot as open, not guessed.
**No source was used outside these two tiers.**

---

## Official facts verified (Tier 1 — Odoo.sh, `odoo.com/documentation/19.0`)

- **[Official fact]** Odoo.sh runs scheduled actions (`ir.cron`) on a **"best effort"**
  basis, **not** a guaranteed schedule: *"we cannot guarantee an exact running time for
  scheduled actions"*; *"Do not expect any scheduled action to be run more often than
  every 5 min"*; *"Odoo.sh always limits the execution time of scheduled actions (aka
  crons)."* Odoo.sh's own guidance for cron authors is to **work in small batches,
  commit after each batch, and be idempotent**.
  (`odoo.com/documentation/19.0/administration/odoo_sh/advanced/frequent_technical_questions.html`)
  — **this is new, decision-relevant detail beyond the previously-recorded "staging
  crons are disabled" fact**, and it applies to **production**, not just staging.
- **[Official fact]** The only Odoo.sh-managed background services named in the official
  docs are **`http`** and **`cron`** (`odoosh-restart` documentation references
  restarting "Odoo.sh services (http or cron)").
  (`.../odoo_sh/getting_started/branches.html`)
- **[Official limitation]** Odoo.sh does **not** support installing/upgrading system
  (apt) packages, and PostgreSQL extensions are **not** supported.
  (`.../odoo_sh/create_module.html`)
- **[Open question — unresolved by official docs]** `server_wide_modules` support on
  Odoo.sh, and whether a custom module may run its own persistent background
  thread/process (a "Jobrunner") **alongside** the platform's `http`/`cron` services, are
  **not addressed** in any fetched Odoo.sh page (getting-started, create-module,
  settings, advanced/containers, advanced/frequent-technical-questions, branches). This
  is **absence of documentation, not a documented denial** — it must **not** be read as
  either "supported" or "unsupported."
- **[Open question — unresolved]** No fetched Odoo.sh page states anything, positive or
  negative, about **OCA `queue_job`** by name.

## Community evidence verified (Secondary tier — OCA GitHub + PyPI)

> Classified as **community evidence**, per the sprint prompt — **not** an Odoo
> official fact, and not a substitute for the open Odoo.sh question above.

- **[Community evidence]** The OCA module (repository renamed **`OCA/queue`**, module
  `queue_job`) has a published **19.0** release on PyPI —
  **`odoo-addon-queue-job` 19.0.2.0.2.2**, `requires_dist: odoo==19.0.*` — so a
  Shopify-connector-relevant Odoo 19.0 release **exists** as of this check.
  (`github.com/OCA/queue/tree/19.0`; `pypi.org/pypi/odoo-addon-queue-job/json`)
- **[Community evidence]** The 19.0 README states jobs are dispatched by a
  **Jobrunner**, and — per the module's own changelog — the Jobrunner **now runs as an
  Odoo worker process** ("Run jobrunner as a worker process instead of a thread in the
  main process, when running with `--workers` > 0"), **not** as a wholly separate
  external daemon/binary. It still requires **`server_wide_modules = ...,queue_job`**
  in `odoo.conf` (or `--load=web,queue_job`) and **`--workers` > 0** (dev-mode
  `workers=0` is unsupported), and a restart after first install "for the runner to
  detect it." (`raw.githubusercontent.com/OCA/queue/19.0/queue_job/README.rst`)
- **[Community evidence]** The module's OCA development-status badge reports
  **"Mature,"** with a continuous PyPI release history spanning Odoo versions from
  roughly **2021 through the 19.0 line checked here** — i.e. an actively maintained,
  long-lived community project, not a one-off.
- **[Inference, not fact]** Because the Jobrunner can now run **inside** the Odoo
  process (as a worker), the "separate daemon to operate" friction reported by
  competitor evidence (VentorTech's `odoo.conf`-edit pain, `../01-research/avoid-list.md`
  A-MOD-3) is **somewhat reduced** on the *process-model* axis versus older `queue_job`
  releases — but the **`server_wide_modules` config requirement remains**, and whether
  Odoo.sh's managed `odoo.conf`/build pipeline lets a project set
  `server_wide_modules` is **exactly the open question above**, which this community
  evidence cannot answer (OCA docs describe the module's own requirements, not what a
  specific hosting platform permits).

## Below-Tier-1 / not relied upon

- No admin-created-custom-app-auto-grants-`read_all_orders` claim, forum answer,
  unofficial staff statement, or marketplace/vendor claim was used to reach any fact or
  recommendation in this refresh or in DEC-004/005/006. Where the repo's existing
  framing docs already carry such an item (e.g. the `read_all_orders` grant question),
  it remains **`Below-Tier-1 / needs verification`** and is **not** used as a decision
  input — see the AR-002 framing doc's own required-evidence section.

## Open questions (carried forward, not resolved by this refresh)

- **AR-003 (still open):** whether Odoo.sh (and on-prem, where the operator controls
  `odoo.conf` directly) permit `server_wide_modules` + a Jobrunner-as-worker-process for
  OCA `queue_job`. This refresh **narrows the shape** of the question (the Jobrunner
  itself no longer requires a separate external daemon binary on 19.0) but does **not**
  resolve whether Odoo.sh's managed configuration surface exposes
  `server_wide_modules` to a project. **This is why DEC-005 proposes the internal
  cron-queue as the Phase 1 default and keeps `queue_job` optional/deferred, not
  rejected** — see DEC-005 "Rejected/deferred options."
- **AR-003 (reinforced, not new):** Odoo.sh crons are **"best effort," ≥5-minute
  interval, time-limited, and must be idempotent/batched** even in production — this
  reinforces (does not newly discover) the DEC-005 requirement that the connector own
  its own per-record retry/backoff regardless of substrate (RQ-003-3, already sourced
  from the Odoo 19.0 `ir_cron.py` source in RB-14 Part 2).
- **AR-002 (unchanged, carried from RB-14 Part 2):** the blanket custom/private
  GraphQL-mandate scope, any REST EOL date, and whether custom apps must implement the
  three compliance webhooks / are bound by Level 1/2 obligations remain **officially
  unstated** — **not assumed absent**. Not re-checked this sprint (no new official page
  would resolve a question the RB-14 Part 2 adversarial cross-verify already confirmed
  is unanswered on every fetched page).
- **AR-005 (unchanged, carried from RB-14 Part 2):** `@idempotent` key-uniqueness scope,
  bulk-operation idempotency, and GID permanence/non-reuse remain officially unstated.

## How this evidence affects AR-002 / AR-003 / AR-005

- **AR-002:** unaffected by this sprint's fetches (no new Shopify page checked); DEC-004
  relies on the RB-14 Part 1/2 Shopify facts, dated 2026-07-01.
- **AR-003:** materially informs the **substrate recommendation** in DEC-005. The
  Odoo.sh "best effort" cron limitation reinforces that **no substrate choice removes
  the need for connector-owned per-record retry/backoff**; the `server_wide_modules`
  silence keeps OCA `queue_job` **feasibility-gated** (not excluded, not confirmed) —
  DEC-005 proposes it as an **optional, non-default** accelerator rather than the Phase
  1 default, precisely because Phase 1 must not depend on an unconfirmed hosting
  capability.
- **AR-005:** unaffected by this sprint's fetches (no new Odoo `ir.model.data`/GID page
  checked); DEC-006 relies on the RB-14 Part 2 source-code facts, dated 2026-07-01.

## No code and no implementation authorized

This file is evidence only. It makes no architecture decision, creates no code, and
authorizes no implementation. AR-002/AR-003/AR-005 status changes to **"Proposed for
ChatGPT review"** (not "Accepted") are recorded in
[`../05-qa/architecture-review-log.md`](../05-qa/architecture-review-log.md); the
decision content itself is in DEC-004/DEC-005/DEC-006, each explicitly **"Status:
Proposed for ChatGPT review."**
