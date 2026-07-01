# RB-14 Decision-Candidate Brief (AR-002 / AR-003 / AR-005)

> **RB-14 Architecture Preparation — Part 2.** A concise **decision-candidate brief** for
> **ChatGPT review**. It **narrows** the AR-002 / AR-003 / AR-005 candidate options using the
> Part 2 evidence resolution
> ([`rb14-part2-open-question-resolution.md`](./rb14-part2-open-question-resolution.md)) — but
> it **is not an ADR and not a decision**. Every narrowing is an **input** labelled
> `[Recommendation]` or `[Decision candidate]`; **no** REST/GraphQL, distribution,
> OAuth/token, queue-framework, binding/data-model, or module-boundary choice is made. AR-002
> / AR-003 / AR-005 remain **[Not decided] / Evidence pending** (`CLAUDE.md` §4–§5; RB-14).
>
> **Classification:** `[Official fact]` · `[Official limitation]` ·
> `[Official source-code fact]` · `[Competitor demonstrated]` · `[Competitor claim]` ·
> `[Inference]` · `[Recommendation]` · `[Decision candidate]` · `[Open question]` ·
> `[Decision — existing]` · `[Not decided]`. A **decision candidate** is an option we propose
> carrying forward; it is **not** a chosen option.

## Purpose

Give ChatGPT a review-ready, evidence-backed **narrowing** of the three framed AR rows so it
can decide the **next architecture-decision sprint** — **which options to carry forward, which
are weakened, what evidence is still required, and in what order to decide** — without
re-deriving the Part 1 framing or the Part 2 evidence. **This brief decides nothing.**

## Inputs used

- **[Decision — existing]** DEC-003 MVP scope
  ([`../04-decisions/DEC-003-mvp-scope.md`](../04-decisions/DEC-003-mvp-scope.md)):
  single-store / single-company, no App-Store packaging in MVP, controlled bidirectional
  product onboarding (with `productSet` delete-on-omit safety), layered sync + reconciliation,
  idempotency, per-record isolation, multi-store-safe keys.
- **[Official fact]/[Official source-code fact]** the Part 2 resolution (RQ-002-1/2/3,
  RQ-003-1/2/3, RQ-005-1/2/3/4) and the Part 1 refresh
  ([`rb14-official-source-refresh.md`](./rb14-official-source-refresh.md)).
- **[Competitor demonstrated]/[Competitor claim]** Sprint C/C2 evidence (as **inputs**, never
  promoted to fact) — carried in the AR framing docs.
- The three framing docs
  ([`ar-002-distribution-api-framing.md`](./ar-002-distribution-api-framing.md),
  [`ar-003-sync-orchestration-framing.md`](./ar-003-sync-orchestration-framing.md),
  [`ar-005-binding-dedup-framing.md`](./ar-005-binding-dedup-framing.md)) and the map
  ([`architecture-decision-framing.md`](./architecture-decision-framing.md)).

---

## AR-002 — Distribution / API / Auth (candidate narrowing)

### Candidate options still viable

- **[Decision candidate]** **Option B — custom/private app, offline token or OAuth,
  GraphQL-first.** Best fit for the DEC-003 single-store, no-App-Store MVP. Part 2
  strengthens it: `[Official fact]` custom apps have protected-customer-data access **"Always
  available"** (no App-Store review gate, no approval wait) and `[Official fact]` are **not
  categorically forbidden from REST** — so a GraphQL-first custom app is unconstrained by a
  prohibition yet future-proofed toward the "only supported long term" API.
- **[Decision candidate]** **Option A — public App-Store app** stays viable **only as a later
  path** (DEC-003 defers App-Store packaging); Part 2 makes its extra burden concrete (3
  compliance webhooks, protected-data **"Requires review"**, TLS, Billing API).

### Candidate options weakened

- **[Recommendation → weak candidate]** **Option C — GraphQL+REST hybrid** is weakened:
  `[Official limitation]` REST is legacy, `[Official fact]` GraphQL is the "only supported …
  over the long term," dual ID formats add GID↔numeric reconciliation cost (ties to AR-005),
  and a hybrid is a **dead-end for any future public-app path** (public = GraphQL-only).
- **[Recommendation → avoid-candidate, NOT rejected]** **Option D — REST-heavy** stays an
  avoid-candidate (legacy; 2048-variant product model degrades off the GraphQL product APIs;
  VT migrated away). **Not** formally rejected here (routes through ChatGPT/architecture review
  + `rejected-approaches-log.md`, `CLAUDE.md` §10).

### Why

`[Official fact]` the GraphQL-only **mandate** binds only *new public apps*; `[Official fact]`
custom apps may keep REST product APIs under 100 variants but GraphQL is signalled as the sole
long-term API with **no REST EOL date**. So the case for GraphQL-first is **direction +
longevity + product-model capability**, not a prohibition — a strong candidate, still an input.
`[Official fact]` the offline token model (non-expiring vs expiring + 90-day rotating refresh)
fits an unattended connector; **OAuth-vs-token stays open**.

### Decision criteria (recommendation, not a decision)

- **[Recommendation]** Decide **distribution first** (public vs custom) because it sets the API
  + obligation constraints; DEC-003 points to **custom** for MVP.
- **[Recommendation]** Prefer the option that **future-proofs toward GraphQL** without taking
  on the App-Store burden before distribution is decided.
- **[Recommendation]** Require any option to make the **`productSet` dry-run** and
  **`@idempotent` writes** cheap and mandatory (correctness > breadth).

### Remaining open questions (AR-002)

- `[Open question]` the **blanket** custom/private GraphQL-mandate scope + any **REST EOL date**;
  whether **custom apps must implement** the 3 compliance webhooks and whether **Level 1/2
  obligations bind** a custom deployment (Part 2 kept these open — **not** assumed absent);
  exact current dev-doc wording of "admin-created token installed on generation."

### Recommended decision-candidate direction

- **[Recommendation]** Carry **Option B (custom app + GraphQL-first + offline token, with an
  expiring-token/rotation path)** as the **lead MVP candidate**; keep **Option A** as an
  explicit **later** public-distribution path; treat **C** as weak and **D** as
  avoid-candidate. **This is a [Recommendation], not a [Decision].** AR-002 stays **[Not
  decided]**.

---

## AR-003 — Sync orchestration / queue / hosting (candidate narrowing)

### Hosting dependency (Part 2 resolves the core)

- **[Official limitation]** **"Odoo Online is incompatible with custom modules"** → the
  connector's custom module **cannot run on Odoo Online**; the substrate targets **Odoo.sh or
  on-premise**. This **removes** the Part 1 "must support Odoo Online" pressure that was the
  main disqualifier for a jobrunner-based option.
- **[Open question]** Whether **Odoo.sh / on-prem** permit **`server_wide_modules` + an
  external jobrunner** (required by OCA `queue_job`) is **still unconfirmed** from official
  docs — so a `queue_job` option remains **feasibility-gated**, just no longer excluded by
  Odoo Online.

### Candidate options still viable

- **[Decision candidate]** **Option 2 — webhook + `ir.cron` + an internal queue model (custom
  job records).** Portable across Odoo.sh/on-prem with **no non-core dependency**; matches the
  `[Competitor demonstrated]` TQ/EM cron-processed per-op queue. `[Official source-code fact]`
  cron's own failure model is coarse (deactivate only after **5 failures over ≥7 days**), so
  the connector **must** own per-record retry/backoff regardless — which this option builds in.
- **[Decision candidate]** **Option 3 — webhook + OCA `queue_job`.** **Strengthened relative
  to Part 1** now that the Odoo Online exclusion is moot; `[Competitor demonstrated]` VT proves
  it. Still carries the **jobrunner/`server_wide_modules` turnkey** open question and non-core
  dependency lifecycle.
- **[Decision candidate]** **Option 1 — `ir.cron`-only** remains viable **only as a floor
  with a queue model around it** (never `ir.cron`-as-a-queue, A-SYNC-3).

### Candidate options weakened

- **[Recommendation → weakened]** **Option 5 — hybrid substrate by hosting tier** is weakened:
  with **Odoo Online out of scope**, the tier spread that motivated a per-tier split (Online vs
  Odoo.sh/on-prem) largely **collapses** to Odoo.sh/on-prem, which are closer in capability —
  reducing the payoff of maintaining two substrates.
- **[Recommendation → weak candidate]** **Option 4 — external worker** stays heaviest to
  deploy/secure, no competitor demonstrates it, likely a **later-phase scale** option, not MVP.

### Why

`[Official source-code fact]` `ir.cron` is the only core async primitive (`IrCron`/
`IrCronTrigger`/`IrCronProgress`; `_trigger`, `_commit_progress`, coarse deactivation); a true
queue is **community `queue_job`**. `[Official limitation]` webhooks are not guaranteed →
reconciliation mandatory. `[Official limitation]` Odoo.sh staging crons are disabled (a testing
constraint). The substrate is a real decision between **build-a-queue (Option 2)** and
**adopt-a-queue (Option 3)**, both now on Odoo.sh/on-prem.

### Decision criteria (recommendation, not a decision)

- **[Recommendation]** Require the **layered model** (webhooks + scheduled + manual +
  **first-class reconciliation**) regardless of substrate.
- **[Recommendation]** Decide the substrate against the **confirmed hosting target**
  (Odoo.sh/on-prem); if `queue_job` is chosen, make its jobrunner install **turnkey** (avoid
  VT's `odoo.conf` friction).
- **[Recommendation]** Require **per-record isolation + safe manual retry + idempotent writes**
  and a **command center + recovery-first error center** over whichever substrate is chosen.

### Remaining open questions (AR-003)

- `[Open question]` Odoo.sh/on-prem `server_wide_modules` + jobrunner support; MVP-scale
  throughput under `--max-cron-threads=2`; reconciliation cadence/scope (joint with AR-006);
  ordering guarantees (e.g. product-before-inventory).

### Recommended decision-candidate direction

- **[Recommendation]** Carry **Option 2 (internal cron-queue)** and **Option 3 (`queue_job`,
  turnkey)** forward as the two primary candidates, with **Option 1** as the floor; treat
  **Options 4 and 5 as weakened**. **This is a [Recommendation], not a [Decision].** AR-003
  stays **[Not decided]**.

---

## AR-005 — Binding / dedup / identity (candidate narrowing)

### Candidate options still viable

- **[Decision candidate]** **Option A — dedicated binding tables per domain (per-store)** and
  **[Decision candidate]** **Option E — hybrid (dedicated source-of-truth + selective
  convenience references).** Part 2 strengthens both: `[Official fact]` **GID permanence is not
  asserted** and `[Official fact]` **no general mutation idempotency** exists (only 17
  `@idempotent` mutations + **24h** dedup), so the binding record must be **authoritative over
  the key**, carry **connector-designed idempotency keys**, and handle **deleted/recreated**
  records — which a dedicated model with status/audit fields does cleanly.
- **[Decision candidate]** **Option B — generic single binding table** stays viable but must
  still carry per-location inventory identity (`inventory_item_id`+`location_id`) and a
  `store_id` dimension.

### Candidate options weakened

- **[Recommendation → weak / avoid-candidate, NOT rejected]** **Option C — reuse
  `ir.model.data`.** Part 2 gives the **facts**: `[Official source-code fact]` it **does** have
  `UniqueIndex('(module, name)')` and db-id-independence, and its docstring **explicitly**
  endorses third-party data integration/sync — so it is **not** the wrong tool *in principle*.
  **But** it has **no per-store/store-dimension column, no binding-status/audit fields**, its
  `module`/`noupdate` semantics are tied to **module-data lifecycle**, and
  `_allow_sudo_commands = False` — a **poor fit** for the DEC-003 **multi-store-safe +
  auditable** runtime binding store. **Weak/avoid-candidate, but formal rejection needs ChatGPT
  approval** (`CLAUDE.md` §10).
- **[Recommendation → weak candidate]** **Option D — Shopify-ID fields directly on Odoo
  records** is weak for **multi-store** (one record, many stores → many IDs), **audit**, and
  **deleted/recreated** handling; usable only as a convenience reference alongside a real
  binding model.

### Why

`[Official fact]` RQ-005-1 (no GID permanence) + RQ-005-2 (no general idempotency; 24h/17-list)
mean the **binding must not lean on GID stability or platform idempotency** — it must own
identity, idempotency keys, and stale/recreated handling. `[Official source-code fact]`
RQ-005-4: `sudo()` **crosses record-rule boundaries** (multi-company isolation named), so
**per-store isolation cannot rely on framework machinery under sudo** — a **dedicated model
with an explicit `store_id` + record rules** (Options A/E), used without gratuitous `sudo()`,
is the safer per-store-uniqueness path than `ir.model.data` (Option C) or ID-on-record (D).

### Multi-store and auditability implications

- **[Inference]** DEC-003 requires **multi-store-safe keys** and **auditability** even in the
  single-store MVP. A dedicated binding record can carry `store_id`, match key, source
  strategy, matched-by/at, and status — giving **per-store uniqueness** + **audit** natively.
  `ir.model.data` (no store column, no audit) and ID-on-record (no store dimension) do not.
- **[Official source-code fact]** because `sudo()` defeats record-rule isolation, **per-store
  record rules must be enforced without routing writes through `sudo()`** — a design
  constraint favouring an explicit store dimension over implicit framework isolation.

### Decision criteria (recommendation, not a decision)

- **[Recommendation]** Prefer a model with **explicit, documented, per-store-safe keys +
  auditability + safe deleted/recreated handling**, that **carries idempotency keys** and
  supports the **`productSet` dry-run diff** (AR-002/AR-006 hooks).
- **[Recommendation]** Keep **no name-only auto-matching**, **ambiguous → manual review**, and
  a **duplicate-prevention preview before create/bind** (DEC-003).

### Remaining open questions (AR-005)

- `[Open question]` `@idempotent` **key-uniqueness scope** (per-shop/app/global); **bulk-op
  idempotency**; **GID permanence/non-reuse**; the **per-store store-dimension** model
  (single table + `store_id` vs per-store scoping); **template-vs-variant** binding ownership
  + inventory identity shape; customer/order match-key sets.

### Recommended decision-candidate direction

- **[Recommendation]** Carry **Option A (dedicated per-domain)** and **Option E (hybrid)**
  forward as the primary candidates; keep **B** viable; treat **C** as weak/avoid-candidate and
  **D** as convenience-only. **This is a [Recommendation], not a [Decision].** AR-005 stays
  **[Not decided]**.

---

## Cross-dependencies

- **[Inference]** **AR-002 → AR-003 hosting.** RQ-003-1 ties the two: a **custom app** on
  **Odoo.sh/on-prem** (not Odoo Online) sets the substrate universe AR-003 chooses within.
- **[Inference]** **AR-002 → AR-005/AR-006 idempotency.** The GraphQL surface fixes the
  idempotency reality (17 `@idempotent` mutations, **24h** dedup, no general mechanism) that
  AR-005 binding keys and AR-006 retry taxonomy must build on.
- **[Inference]** **AR-002 ↔ AR-005.** `productSet` delete-on-omit makes a **reliable binding +
  dry-run** a correctness requirement, not a convenience.
- **[Inference]** **AR-005 ↔ AR-003 security.** `sudo()` crossing record-rule boundaries
  (RQ-005-4) couples the binding's per-store isolation to how orchestration runs jobs
  (credentials, store scoping).

## Candidate options to carry forward

| Row | Carry forward (decision candidates) | Keep as later/floor | Weak / avoid-candidate (not rejected) |
| --- | --- | --- | --- |
| **AR-002** | **B** (custom + GraphQL-first + offline token) | **A** (public, later path) | **C** (hybrid, weak); **D** (REST-heavy, avoid) |
| **AR-003** | **2** (internal cron-queue); **3** (`queue_job`, turnkey) | **1** (cron-only floor) | **4** (external worker); **5** (per-tier hybrid) |
| **AR-005** | **A** (dedicated per-domain); **E** (hybrid) | **B** (generic table) | **C** (`ir.model.data` reuse); **D** (ID-on-record alone) |

## Options that look weak / avoid-candidate (but NOT formally rejected)

- **AR-002 Option D (REST-heavy)** — avoid-candidate; **AR-002 Option C (hybrid)** — weak.
- **AR-003 Option 5 (per-tier hybrid)** — weakened by Odoo Online exclusion; **Option 4
  (external worker)** — weak for MVP.
- **AR-005 Option C (`ir.model.data` reuse)** — weak/avoid-candidate for a runtime binding
  store; **Option D (ID-on-record alone)** — weak for multi-store/audit.

> **None of these is entered in
> [`../05-qa/rejected-approaches-log.md`](../05-qa/rejected-approaches-log.md).** Formal
> rejection requires ChatGPT approval and routes through the architecture-review log
> (`CLAUDE.md` §10).

## Remaining evidence required before decision

- **AR-002:** custom/private blanket GraphQL scope + REST EOL; custom-app compliance-webhook /
  L1/L2 obligation applicability; dev-doc "token on generation" wording.
- **AR-003:** Odoo.sh/on-prem `server_wide_modules` + jobrunner support (gates Option 3);
  MVP-scale throughput under `--max-cron-threads=2`; reconciliation cadence (with AR-006).
- **AR-005:** `@idempotent` key-uniqueness scope; bulk-op idempotency; per-store store-dimension
  model; template-vs-variant ownership; customer/order match keys.

## Suggested next architecture-decision sprint sequence (recommendation, not a decision)

- **[Recommendation]** **RB-14 Part 3 — AR-002 decision sprint (distribution + API + auth)**
  first: it is the **most narrowed** (custom + GraphQL-first + offline token lead candidate)
  and it **constrains** AR-003 (hosting) and AR-005 (idempotency surface). **Only if ChatGPT
  accepts Part 2.**
- **[Recommendation]** Then **AR-003 and AR-005 in parallel** (both now have decision-ready
  inputs), then **AR-006/007/008**, with **AR-004 (module boundaries) last**.

## UX / operator implications

> UX reasoning aids only (ui-ux-pro-max / frontend-design used as reasoning aids, **not** as
> factual sources); grounded in
> [`../02-product/setup-ux-principles.md`](../02-product/setup-ux-principles.md) and
> [`../01-research/gaps-opportunities.md`](../01-research/gaps-opportunities.md). **No screens
> or wireframes are designed.**

- **Setup friction:** a **custom app** (AR-002 lead candidate) means a multi-step
  admin-token/scope wizard — but `[Official fact]` protected-data access is **"Always
  available"** for custom apps (no App-Store review wait), so the friction is **wizard steps,
  not approval latency**. The wizard must validate inline, mask secrets, run a **test
  connection**, and pre-empt known failures (EM trailing-slash). If an **expiring** offline
  token is used, the wizard/operator model must make **90-day refresh rotation** invisible and
  surface a clear "reconnect" path on refresh-token expiry.
- **Operator clarity (queue/orchestration):** with the substrate on **Odoo.sh/on-prem** and a
  cron/queue model (Option 2/3), the command center should show work as **queued/processing/
  done** with **honest freshness** ("last synced / last reconciled"), never expose raw
  `ir.cron` fields (A-UX-2), and never overstate "real-time."
- **Error recovery:** `[Official source-code fact]` cron auto-deactivates only after
  **5 failures over ≥7 days** — too coarse to be the user's safety net; the **recovery-first
  error center** must surface each failure's **record + reason + fix + safe retry**, with
  retries **safe by construction** (idempotency keys + binding), never email-only (A-LOG-1).
- **Command-center / log implications:** the **24-hour** idempotency window and
  **`X-Shopify-Webhook-Id`** dedup are the honest bounds to reflect — the log can show "deduped"
  / "already applied" states truthfully rather than implying infinite dedup.
- **First-sync confidence:** because `[Official fact]` **GID permanence is not asserted**, the
  matching UX must treat **deleted/recreated Shopify records as review items** (stale-binding /
  recreated-record surfaces), plus the DEC-003 **duplicate-prevention preview** (no blind
  create, no name-only auto-match) — so a non-developer trusts the first bidirectional sync.
- **Destructive-action safeguards:** `productSet` delete-on-omit (list fields) + a reliable
  binding demand a **dry-run diff before any full-state write**; and `[Official source-code
  fact]` because `sudo()` crosses record-rule (per-store) isolation, destructive apply must
  **never** be routed around store isolation via `sudo()` — the safeguard is both a UX diff and
  an architecture rule.

## No decisions made

This brief **decides nothing**. It narrows AR-002 / AR-003 / AR-005 into **decision candidates
and recommendations** for ChatGPT, records what is weakened and what evidence is still needed,
and suggests (does not set) the next sprint sequence. **AR-002 / AR-003 / AR-005 remain [Not
decided] / Evidence pending**; DEC-003 and MVP scope are unchanged; implementation stays
blocked (`CLAUDE.md` §4–§5; RB-14). Nothing here is entered as a decision, an ADR, or a
rejected approach.
