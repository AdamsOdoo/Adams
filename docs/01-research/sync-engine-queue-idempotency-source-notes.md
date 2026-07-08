# Sync Engine Queue / Idempotency / Retry Source Notes

> **Research-phase document. No architecture decision or implementation choice is
> made here.** This is reference-pattern source material for **Task 006A**
> (queue / idempotency / retry / backoff / dead-letter patterns for a *future*
> sync engine), gathered by a 9-topic, 18-agent research-and-adversarial-
> verification workflow and synthesized into one governance-compliant record.
> Per `CLAUDE.md` §8, every statement below is labelled **[Fact]** (verifiable,
> cited), **[Pattern]** (a recurring documented shape across sources),
> **[Risk]** (a documented or reasoned failure mode), **[Inference]** (our
> deduction from facts), **[Recommendation-candidate]** (a candidate for later
> architecture review, not a decision), **[Open question]** (unverified/unknown),
> or **[Corrected on verification]** (a claim the adversarial-verification pass
> found needed fixing, fixed here). No **Decision** is recorded in this file.

## Scope

This document is the source-note deliverable for **Task 006A-3**: reference-
pattern research only, covering queue mechanics, idempotency, retry/backoff,
dead-letter/permanent-failure handling, duplicate-running prevention,
checkpoint/resume, and observability/redaction, as documented by primary and
secondary sources for OCA `queue_job`, Shopify's official developer docs, Odoo
19's official source and docs, and general vendor-neutral/vendor-specific
engineering references (AWS, Azure, Google, Stripe, IETF, PostgreSQL,
RabbitMQ, OWASP, MITRE, NIST, the GDPR text, the Twelve-Factor App, Kubernetes,
etcd, and the Enterprise Integration Patterns catalog).

**This is not architecture.** It does not select a sync-orchestration
substrate, does not name any Odoo model, does not define a job/log/binding
data model, and does not decide how the future Odoo 19 ↔ Shopify connector
will implement any of these patterns. **No coding gate is opened by this
document, and none is opened here** — per `CLAUDE.md` §5, connector code,
XML, manifests, controllers, security files, migrations, CI/workflow files,
and Dockerfiles remain out of scope for this phase, and nothing below should
be read as authorizing any of that work.

This document also does not reconsider or supersede prior, already-recorded
decisions. In particular: `docs/05-qa/rejected-approaches-log.md` **RA-004**
records that OCA `queue_job` is **not rejected as a technology**, only
rejected as the Phase 1 **default** sync-orchestration substrate (see
`docs/04-decisions/DEC-005-sync-orchestration-strategy.md`), which is
consistent with the reference-pattern-only treatment used throughout this
document. **RA-014/RA-015/RA-016/RA-017** record an already-accepted
retry/idempotency taxonomy (no blanket auto-retry-everything, no manual-only
recovery, no raw-stack-trace-as-primary-UX, no binding-alone idempotency —
see `docs/04-decisions/DEC-009-error-retry-idempotency-strategy.md`). Nothing
in this document proposes revisiting any of those decisions; it supplies
additional, independently source-grounded reference material that a later
architecture-review session can draw on, per `CLAUDE.md` §10.

**Method note:** the underlying research was produced by nine parallel
research agents (one per topic), each followed by an independent adversarial
verification agent that re-fetched every cited source and checked every
quote/number against the live page. Where verification found an error
(misattribution, an inaccurate "direct quote," an overreaching paraphrase, or
a fabricated quote), this document applies the correction and marks the
affected statement **[Corrected on verification]** rather than silently
reproducing the original error, per the task's explicit instruction. Access
date for every source below is **2026-07-08**.

---

## Source inventory

Sources are grouped by category and given short IDs (`OCA-#`, `SH-#`, `OD-#`,
`GEN-#`) used for inline citation throughout the rest of this document. Each
source was cited by at least one of the nine research topics and was
independently re-fetched during adversarial verification on 2026-07-08 unless
noted otherwise. Reliability grades (Primary / Secondary / Reference only) are
the grades assigned by the underlying research, not re-derived here.

### OCA (queue_job reference material)

| ID | Title | URL | Access date | Source type | Reliability | Topic(s) | Why it matters |
| --- | --- | --- | --- | --- | --- | --- | --- |
| OCA-1 | OCA/queue GitHub repository (root) | https://github.com/OCA/queue | 2026-07-08 | Official source repo | Primary | oca_queue_job | Authoritative repo hosting `queue_job`; confirms ownership, licensing, multi-version branch layout. |
| OCA-2 | `queue_job` README — DESCRIPTION.md (18.0) | https://raw.githubusercontent.com/OCA/queue/18.0/queue_job/readme/DESCRIPTION.md | 2026-07-08 | Official docs (raw) | Primary | oca_queue_job | Verbatim statement of what `queue_job` does and its feature list. |
| OCA-3 | `queue_job` README — USAGE.md (18.0) | https://raw.githubusercontent.com/OCA/queue/18.0/queue_job/readme/USAGE.md | 2026-07-08 | Official docs (raw) | Primary | oca_queue_job | Primary source for retry/identity_key/retry_pattern semantics, idempotency guidance, testing pattern. |
| OCA-4 | `queue_job` README — CONFIGURE.md (18.0) | https://raw.githubusercontent.com/OCA/queue/18.0/queue_job/readme/CONFIGURE.md | 2026-07-08 | Official docs (raw) | Primary | oca_queue_job | Operational/deployment requirements for the standard Jobrunner. |
| OCA-5 | `queue_job` source — exception.py (18.0) | https://raw.githubusercontent.com/OCA/queue/18.0/queue_job/exception.py | 2026-07-08 | Official source code | Primary | oca_queue_job | Ground-truth exception hierarchy (`RetryableJobError`/`FailedJobError`). |
| OCA-6 | `queue_job` source — job.py (18.0) | https://raw.githubusercontent.com/OCA/queue/18.0/queue_job/job.py | 2026-07-08 | Official source code | Primary | oca_queue_job | Ground-truth retry counting, state machine, `identity_key`/`identity_exact()` dedup mechanics. |
| OCA-7 | `queue_job` `__manifest__.py` (19.0) | https://raw.githubusercontent.com/OCA/queue/19.0/queue_job/__manifest__.py | 2026-07-08 | Official source (manifest) | Primary | oca_queue_job | Confirms Odoo 19.0 packaging, dependency footprint, wizards shipped. |
| OCA-8 | `queue_job_cron_jobrunner` README — DESCRIPTION.md (18.0) | https://raw.githubusercontent.com/OCA/queue/18.0/queue_job_cron_jobrunner/readme/DESCRIPTION.md | 2026-07-08 | Official docs (raw) | Primary | oca_queue_job | Documents the Odoo.sh-oriented, feature-reduced cron-trigger runner alternative. |
| OCA-9 | OCA/queue — Branches page | https://github.com/OCA/queue/branches | 2026-07-08 | Official repo (GitHub UI) | Primary | oca_queue_job | Corroborates the multi-version (14.0–19.0) branch structure. |
| OCA-10 | GitHub Issue OCA/queue#169 | https://github.com/OCA/queue/issues/169 | 2026-07-08 | Issue tracker (user report) | Reference only | oca_queue_job | One anecdotal, unresolved-in-fetched-content report of a jobrunner/Odoo.sh connection failure. |

### Shopify official developer documentation

| ID | Title | URL | Access date | Source type | Reliability | Topic(s) | Why it matters |
| --- | --- | --- | --- | --- | --- | --- | --- |
| SH-1 | REST Admin API rate limits | https://shopify.dev/docs/api/admin-rest/usage/rate-limits | 2026-07-08 | Official docs | Primary | shopify_throttle, retry_backoff | Leaky-bucket model, per-plan bucket size/leak rate table, `X-Shopify-Shop-Api-Call-Limit`, 429 + `Retry-After`. |
| SH-2 | Shopify API limits | https://shopify.dev/docs/api/usage/limits | 2026-07-08 | Official docs | Primary | shopify_throttle, retry_backoff, checkpoint_resume | Cross-API overview: GraphQL cost points by plan, `throttleStatus` extension, general backoff guidance, bulk-op exemption. |
| SH-3 | Shopify API response status and error codes | https://shopify.dev/docs/api/usage/response-codes | 2026-07-08 | Official docs | Primary | shopify_throttle | Definitions of 429 and 423 (shop locked/inactive after repeated rate-limit violations). |
| SH-4 | GraphQL Admin API reference | https://shopify.dev/docs/api/admin-graphql/latest | 2026-07-08 | Official API reference | Primary | shopify_throttle | `THROTTLED` error code definition; confirms a throttled GraphQL call can still return HTTP 200. |
| SH-5 | Verify webhook deliveries | https://shopify.dev/docs/apps/build/webhooks/verify-deliveries | 2026-07-08 | Official docs | Primary | shopify_throttle | HMAC verification, 8-consecutive-failure auto-deletion, `X-Shopify-Webhook-Id` de-dup guidance. |
| SH-6 | Troubleshoot webhooks | https://shopify.dev/docs/apps/build/webhooks/troubleshoot | 2026-07-08 | Official docs | Primary | shopify_throttle | 5-second response deadline; required 200-series status. |
| SH-7 | Updates to webhook retry mechanism (changelog) | https://shopify.dev/changelog/updates-to-webhook-retry-mechanism | 2026-07-08 | Official changelog | Primary | shopify_throttle | 8-retries-over-4-hours exponential-backoff schedule; original-payload redelivery; `X-Shopify-Triggered-At`. |
| SH-8 | Increased Admin API rate limits for the Advanced plan (changelog) | https://shopify.dev/changelog/increased-admin-api-rate-limits-for-the-advanced-plan | 2026-07-08 | Official changelog | Primary | shopify_throttle | Confirms Advanced-plan figures; dated 2023-06-07, since partially superseded (see Retry/backoff notes). |
| SH-9 | Paginating results with GraphQL | https://shopify.dev/docs/api/usage/pagination-graphql | 2026-07-08 | Official docs | Primary | checkpoint_resume | Cursor/`PageInfo` mechanics, forward/backward pagination args, 250-item page cap. |
| SH-10 | PageInfo — GraphQL Admin | https://shopify.dev/docs/api/admin-graphql/latest/objects/PageInfo | 2026-07-08 | Official API reference | Primary | checkpoint_resume | Exact contract of `hasNextPage`/`hasPreviousPage`/`startCursor`/`endCursor`. |
| SH-11 | `orders` — GraphQL Admin | https://shopify.dev/docs/api/admin-graphql/latest/queries/orders | 2026-07-08 | Official API reference | Primary | checkpoint_resume | Connection arguments (`after`, `query`, `sortKey`) on a concrete high-volume resource. |
| SH-12 | OrderSortKeys — GraphQL Admin | https://shopify.dev/docs/api/admin-graphql/latest/enums/OrderSortKeys | 2026-07-08 | Official API reference | Primary | checkpoint_resume | Confirms `UPDATED_AT` as a documented sort key. Originally graded "Partial" access; verification obtained the full page — content fully supports the claim. |
| SH-13 | Bulk operations with the GraphQL Admin API | https://shopify.dev/docs/api/usage/bulk-operations | 2026-07-08 | Official docs | Primary | checkpoint_resume | Frames asynchronous bulk export/import as the documented alternative to live paginated queries. |
| SH-14 | Perform bulk operations with the GraphQL Admin API | https://shopify.dev/docs/api/usage/bulk-operations/queries | 2026-07-08 | Official docs | Primary | checkpoint_resume | Bulk-operation lifecycle: cancellation, resubmission-as-retry, `partialDataUrl`, 1-week signed-URL expiry. |
| SH-15 | `bulkOperationCancel` — GraphQL Admin | https://shopify.dev/docs/api/admin-graphql/latest/mutations/bulkoperationcancel | 2026-07-08 | Official API reference | Primary | checkpoint_resume | Cancellation of an in-progress bulk operation is asynchronous with a short delay. |
| SH-16 | Make paginated requests to the REST Admin API | https://shopify.dev/docs/api/usage/pagination-rest | 2026-07-08 | Official docs | Primary | checkpoint_resume | Explicit warning that `page_info`/Link-header cursor URLs are temporary and not meant to be saved. |
| SH-17 | Pagination with Relative Cursors (Shopify Engineering) | https://shopify.engineering/pagination-relative-cursors | 2026-07-08 | Vendor engineering blog | Secondary | checkpoint_resume | Explains Shopify's cursors as a keyset/"relative cursor" mechanism; no-jump-to-page tradeoff. **A specific SQL quote originally attributed to this source could not be verified and has been removed — see Checkpoint/resume notes.** |
| SH-18 | Rotate or revoke client credentials | https://shopify.dev/docs/apps/build/authentication-authorization/client-secrets/rotate-revoke-client-credentials | 2026-07-08 | Official docs | Primary | observability_redaction | Client-secret rotation rationale and the "don't delete the old secret prematurely" caution. |
| SH-19 | About client credentials | https://shopify.dev/docs/apps/build/authentication-authorization/client-secrets | 2026-07-08 | Official docs | Primary (Partial access) | observability_redaction | General client-secret overview; no explicit "don't log this" sentence was found on this page. |

### Odoo 19 official source and documentation

| ID | Title | URL | Access date | Source type | Reliability | Topic(s) | Why it matters |
| --- | --- | --- | --- | --- | --- | --- | --- |
| OD-1 | `ir_cron.py` — odoo/odoo (19.0 branch) | https://github.com/odoo/odoo/blob/19.0/odoo/addons/base/models/ir_cron.py | 2026-07-08 | Official source code | Primary | odoo_cron_tx, duplicate_running | `ir.cron` job acquisition/locking, transaction/commit handling, failure counting, deactivation logic. |
| OD-2 | Actions — Odoo 19.0 documentation (Scheduled Actions) | https://www.odoo.com/documentation/19.0/developer/reference/backend/actions.html | 2026-07-08 | Official docs | Primary | odoo_cron_tx, duplicate_running | Prescriptive guidance for writing cron functions: batching, `_commit_progress`, `try_lock_for_update()` pattern. |
| OD-3 | `models.py` — odoo/odoo (19.0), `lock_for_update`/`try_lock_for_update` | https://github.com/odoo/odoo/blob/19.0/odoo/orm/models.py | 2026-07-08 | Official source code | Primary | odoo_cron_tx, duplicate_running | ORM-level pessimistic locking API and its `SKIP LOCKED` (not `NOWAIT`) implementation. |
| OD-4 | `sql_db.py` — odoo/odoo (19.0), Cursor/Savepoint/isolation level | https://github.com/odoo/odoo/blob/19.0/odoo/sql_db.py | 2026-07-08 | Official source code | Primary | odoo_cron_tx | Cursor commit/rollback semantics, `Savepoint`, rationale for `REPEATABLE READ` default isolation. |
| OD-5 | `service/model.py` — odoo/odoo (19.0), `retrying()` | https://github.com/odoo/odoo/blob/19.0/odoo/service/model.py | 2026-07-08 | Official source code | Primary | odoo_cron_tx | The RPC/ORM call-dispatch retry-with-backoff helper — a **different** code path from cron acquisition. |
| OD-6 | `exceptions.py` — odoo/odoo (19.0), `LockError`/`ConcurrencyError` | https://github.com/odoo/odoo/blob/19.0/odoo/exceptions.py | 2026-07-08 | Official source code | Primary | odoo_cron_tx, duplicate_running | Definitions/intent of `LockError` (HTTP 409) and `ConcurrencyError` (retry signal). |
| OD-7 | Odoo 19.0 Developer Documentation — ORM API | https://www.odoo.com/documentation/19.0/developer/reference/backend/orm.html | 2026-07-08 | Official docs | Primary | duplicate_running | `models.Constraint`/`Index`/`UniqueIndex` declaration syntax (replaces legacy `_sql_constraints`). |
| OD-8 | Odoo 19.0 Documentation — Frequent Technical Questions (Odoo.sh) | https://www.odoo.com/documentation/19.0/administration/odoo_sh/advanced/frequent_technical_questions.html | 2026-07-08 | Official docs | Primary | duplicate_running | States scheduled-action idempotency as developer **advice**, not a framework-enforced guarantee. |
| OD-9 | GitHub code search — odoo/odoo, `"models.Constraint" "UNIQUE"` | https://github.com/search?q=%22models.Constraint%22+%22UNIQUE%22+repo%3Aodoo%2Fodoo&type=code | 2026-07-08 | Official source (search) | Primary | duplicate_running | Confirms the unique-constraint idiom is in live, widespread use (143 matches, independently re-confirmed). |
| OD-10 | External RPC API — Odoo 19.0 documentation | https://www.odoo.com/documentation/19.0/developer/reference/external_rpc_api.html | 2026-07-08 | Official docs | Primary | observability_redaction | **[Corrected on verification]** The "store the API key as carefully as the password" sentence was originally attributed to a different, similarly-named page ("External JSON-2 API," `.../external_api.html`); adversarial re-fetch found the sentence does not appear there and traced it to this RPC-API page instead. Cited here at the corrected URL. |

### General engineering / standards references

| ID | Title | URL | Access date | Source type | Reliability | Topic(s) | Why it matters |
| --- | --- | --- | --- | --- | --- | --- | --- |
| GEN-1 | Stripe API Reference — Idempotent requests | https://docs.stripe.com/api/idempotent_requests | 2026-07-08 | Official API docs | Primary | idempotency_keys | Concrete, implementation-level idempotency-key rules: generation, 24h TTL, parameter-mismatch error, POST-only scope. |
| GEN-2 | Stripe blog — Designing robust and predictable APIs with idempotency | https://stripe.com/blog/idempotency | 2026-07-08 | Vendor blog | Secondary | idempotency_keys | High-level rationale: retry + idempotency key + backoff as a three-part failure-handling strategy. |
| GEN-3 | IETF draft-ietf-httpapi-idempotency-key-header-07 | https://datatracker.ietf.org/doc/html/draft-ietf-httpapi-idempotency-key-header-07 | 2026-07-08 | Standards draft (IETF HTTPAPI WG) | Primary | idempotency_keys | Vendor-neutral formal problem statement, key-generation/TTL/conflict guidance. Verification found the draft is now **Expired** (no RFC issued), not merely "still draft status." |
| GEN-4 | AWS Builders' Library — Making retries safe with idempotent APIs | https://aws.amazon.com/builders-library/making-retries-safe-with-idempotent-APIs/ | 2026-07-08 | Official AWS engineering essay | Primary | idempotency_keys, retry_backoff, checkpoint_resume | Explicit client-token design choice (EC2 `RunInstances`' `ClientToken`), ACID token-recording requirement, concrete EBS-double-creation risk example. |
| GEN-5 | AWS Well-Architected Framework — REL04-BP04 Make mutating operations idempotent | https://docs.aws.amazon.com/wellarchitected/latest/framework/rel_prevent_interaction_failure_idempotent.html (also referenced via the `.../reliability-pillar/...` path) | 2026-07-08 | Official framework docs | Primary | idempotency_keys, checkpoint_resume | At-most/at-least/exactly-once framing; named anti-patterns (timestamps as keys, full-payload storage); TTL/storage guidance. **This page, not the Builders' Library essay, is the correct source for the "processed exactly once" definition** — see Idempotency notes. |
| GEN-6 | Azure Architecture Center — Retry pattern | https://learn.microsoft.com/en-us/azure/architecture/patterns/retry | 2026-07-08 | Official vendor docs | Primary | idempotency_keys, retry_backoff, observability_redaction | Cancel/immediate/delayed retry strategies; idempotency-is-the-safety-condition framing; informational-vs-error log-level guidance. |
| GEN-7 | Google Cloud Pub/Sub — Exactly-once delivery documentation | https://docs.cloud.google.com/pubsub/docs/exactly-once-delivery | 2026-07-08 | Official docs | Primary | idempotency_keys | Redeliveries vs. true duplicates; pull-only scope of the exactly-once feature; consumer-side idempotency recommendation. |
| GEN-8 | AWS Architecture Blog — Exponential Backoff and Jitter | https://aws.amazon.com/blogs/architecture/exponential-backoff-and-jitter/ | 2026-07-08 | Official AWS blog | Primary | retry_backoff | Canonical Full/Equal/Decorrelated jitter formulas. **The originally-recorded Equal Jitter formula was inaccurate — corrected below.** |
| GEN-9 | AWS Builders' Library — Timeouts, retries, and backoff with jitter | https://aws.amazon.com/builders-library/timeouts-retries-and-backoff-with-jitter/ | 2026-07-08 | Official AWS engineering essay | Reference only | retry_backoff | Widely-cited related source; content could not be extracted (JS-rendered) in either research pass — not used as evidence for any fact. |
| GEN-10 | Google SRE Book — Addressing Cascading Failures | https://sre.google/sre-book/addressing-cascading-failures/ | 2026-07-08 | Official source book | Primary | retry_backoff | Retry amplification across stack layers (4³ = 64 example); server-wide retry budgets. |
| GEN-11 | Google SRE Book — Handling Overload | https://sre.google/sre-book/handling-overload/ | 2026-07-08 | Official source book | Primary | retry_backoff | Client-side adaptive throttling; per-request (3-attempt) and per-client (<10%) retry budgets; criticality levels. |
| GEN-12 | Azure Architecture Center — Transient fault handling | https://learn.microsoft.com/en-us/azure/architecture/best-practices/transient-faults | 2026-07-08 | Official vendor docs | Primary | retry_backoff | Retryable-vs-permanent HTTP status classification; `Retry-After` precedence; dead-letter preservation; "never implement an endless retry mechanism." |
| GEN-13 | Azure Architecture Center — Retry Storm antipattern | https://learn.microsoft.com/en-us/azure/architecture/antipatterns/retry-storm/ | 2026-07-08 | Official vendor docs | Primary | retry_backoff | Named thundering-herd antipattern and its mitigation checklist. |
| GEN-14 | Azure Architecture Center — Circuit Breaker pattern | https://learn.microsoft.com/en-us/azure/architecture/patterns/circuit-breaker | 2026-07-08 | Official vendor docs | Primary | retry_backoff, observability_redaction | Closed/Open/Half-Open state machine; explicit relationship to (and boundary with) the Retry pattern; observability requirement. |
| GEN-15 | AWS Well-Architected Framework — REL05-BP03 Control and limit retry calls | https://docs.aws.amazon.com/wellarchitected/latest/framework/rel_mitigate_interaction_failure_limit_retries.html | 2026-07-08 | Official framework docs | Primary | retry_backoff | Exponential backoff + jitter + capped retries as the core rule; "High" risk rating for not bounding retries; named anti-patterns. |
| GEN-16 | MDN — Retry-After HTTP header reference | https://developer.mozilla.org/en-US/docs/Web/HTTP/Reference/Headers/Retry-After | 2026-07-08 | Community web-standards reference | Secondary | retry_backoff | Formal `Retry-After` semantics (503/429/redirects; http-date vs. delay-seconds). |
| GEN-17 | Stripe Docs — Handling idempotency and low-level errors | https://docs.stripe.com/error-low-level | 2026-07-08 | Official API docs | Primary | retry_backoff | `Stripe-Should-Retry` header; 429 named as an explicit exception to "generate a new idempotency key on 4xx." |
| GEN-18 | Using dead-letter queues in Amazon SQS | https://docs.aws.amazon.com/AWSSimpleQueueService/latest/SQSDeveloperGuide/sqs-dead-letter-queues.html | 2026-07-08 | Official docs | Primary | dead_letter | DLQ purpose, `maxReceiveCount` redrive policy, retention-period best practice, FIFO caution. |
| GEN-19 | Creating alarms for dead-letter queues using Amazon CloudWatch | https://docs.aws.amazon.com/AWSSimpleQueueService/latest/SQSDeveloperGuide/dead-letter-queues-alarms-cloudwatch.html | 2026-07-08 | Official docs | Primary | dead_letter | Named visibility metric (`ApproximateNumberOfMessagesVisible`) and alarm-driven operator workflow. |
| GEN-20 | Encryption at rest in Amazon SQS | https://docs.aws.amazon.com/AWSSimpleQueueService/latest/SQSDeveloperGuide/sqs-server-side-encryption.html | 2026-07-08 | Official docs | Primary | dead_letter | Encryption state passes through unchanged when a message moves to a DLQ. |
| GEN-21 | Capturing records of Lambda asynchronous invocations | https://docs.aws.amazon.com/lambda/latest/dg/invocation-async-retain-records.html | 2026-07-08 | Official docs | Primary | dead_letter | DLQ-delivery-failure behavior (event deleted, `DeadLetterErrors` metric); S3 failure-destination security risk. |
| GEN-22 | What is a Dead-Letter Queue? | https://aws.amazon.com/what-is/dead-letter-queue/ | 2026-07-08 | Official vendor explainer | Primary | dead_letter | Plain-language purpose/benefit framing. |
| GEN-23 | Introducing Amazon SQS dead-letter queue redrive to source queues | https://aws.amazon.com/blogs/compute/introducing-amazon-simple-queue-service-dead-letter-queue-redrive-to-source-queues/ | 2026-07-08 | Official vendor blog | Secondary | dead_letter | Documented investigate-then-redrive recovery workflow (review is **optional**, not mandatory — see corrections). |
| GEN-24 | Service Bus Dead-Letter Queues | https://learn.microsoft.com/en-us/azure/service-bus-messaging/service-bus-dead-letter-queues | 2026-07-08 | Official docs | Primary | dead_letter | Move conditions (TTL expiry, max delivery count default 10, application-level dead-lettering), diagnostic metadata, resubmission workflow. |
| GEN-25 | Monitoring data reference for Azure Service Bus | https://learn.microsoft.com/en-us/azure/service-bus-messaging/monitor-service-bus-reference | 2026-07-08 | Official docs | Primary | dead_letter | Named `DeadletteredMessages` platform metric. |
| GEN-26 | Dead Letter Channel — Enterprise Integration Patterns | https://www.enterpriseintegrationpatterns.com/patterns/messaging/DeadLetterChannel.html | 2026-07-08 | Canonical pattern catalog | Primary | dead_letter, observability_redaction | Vendor-neutral definition of the Dead Letter Channel pattern and its intent. |
| GEN-27 | Dead Letter Exchanges — RabbitMQ | https://www.rabbitmq.com/docs/dlx | 2026-07-08 | Official docs | Primary | dead_letter | Trigger conditions (reject/nack, TTL, queue-length limit, quorum delivery-limit) and a built-in dead-letter-loop safeguard. |
| GEN-28 | DLQ Monitoring Best Practices — DeadQueue | https://www.deadqueue.com/blog/dlq-monitoring-best-practices | 2026-07-08 | Commercial vendor blog | Secondary | dead_letter | Practitioner framing: unmonitored DLQs cause silent data loss; DLQ depth needs an actively-viewed dashboard. |
| GEN-29 | Dead Letter Queues Are Not Your Safety Net | https://newsletter.systemdesignclassroom.com/p/dead-letter-queues-are-not-your-safety-net | 2026-07-08 | Independent newsletter | Secondary | dead_letter | Practitioner framing: a DLQ is a safety valve, not a safety net; blind redrive without root-cause analysis is risky. |
| GEN-30 | PostgreSQL Documentation: 13.3 Explicit Locking | https://www.postgresql.org/docs/current/explicit-locking.html | 2026-07-08 | Official docs | Primary | duplicate_running | Row-lock modes, deadlock auto-detection, session-vs-transaction advisory locks, the `LIMIT`+advisory-lock hazard. |
| GEN-31 | PostgreSQL Documentation: 9.28.10 Advisory Lock Functions | https://www.postgresql.org/docs/current/functions-admin.html | 2026-07-08 | Official docs | Primary | duplicate_running | Full advisory-lock function set (session/transaction scope, blocking/non-blocking). |
| GEN-32 | PostgreSQL Documentation: Appendix A — Error Codes | https://www.postgresql.org/docs/current/errcodes-appendix.html | 2026-07-08 | Official docs | Primary | duplicate_running | SQLSTATE `40001` (serialization_failure) / `40P01` (deadlock_detected). |
| GEN-33 | PostgreSQL Documentation: INSERT | https://www.postgresql.org/docs/current/sql-insert.html | 2026-07-08 | Official docs | Primary | duplicate_running | `ON CONFLICT` as an atomic, per-row arbiter-constraint decision. |
| GEN-34 | github.com/kubernetes/client-go — leaderelection.go | https://raw.githubusercontent.com/kubernetes/client-go/master/tools/leaderelection/leaderelection.go | 2026-07-08 | Official source code | Primary | duplicate_running | Explicit maintainer statement: this leader-election implementation does **not** guarantee fencing/single-leader. |
| GEN-35 | etcd.io Documentation — leader election | https://etcd.io/docs/v3.5/tutorials/how-to-conduct-elections/ | 2026-07-08 | Official docs | Primary | duplicate_running | `etcdctl elect`'s documented single-leader-at-a-time guarantee, as a contrasting reference point. |
| GEN-36 | AWS Glue — Repairing and resuming a workflow run | https://docs.aws.amazon.com/glue/latest/dg/resuming-workflow.html | 2026-07-08 | Official docs | Primary | checkpoint_resume | Node-level resume of a partial batch-workflow failure; explicit no-rollback statement; COMPLETED-status ambiguity. |
| GEN-37 | AWS Step Functions — Restarting state machine executions with redrive | https://docs.aws.amazon.com/step-functions/latest/dg/redrive-executions.html | 2026-07-08 | Official docs | Primary | checkpoint_resume | Resume-from-failed-step semantics preserving prior successful-step results; per-iteration Map redrive; retry-count reset. |
| GEN-38 | Visually monitor Azure Data Factory | https://learn.microsoft.com/en-us/azure/data-factory/monitor-visually | 2026-07-08 | Official docs | Primary | checkpoint_resume | "Rerun from failed activity" feature and per-activity-type rerun semantics. |
| GEN-39 | Pipeline failure and error message (Azure Data Factory) | https://learn.microsoft.com/en-us/azure/data-factory/tutorial-pipeline-failure-error-handling | 2026-07-08 | Official docs | Primary | checkpoint_resume | Try-Catch / Do-If-Else / Do-If-Skip-Else error-branching patterns. |
| GEN-40 | We need tool support for keyset pagination (Use The Index, Luke!) | https://use-the-index-luke.com/no-offset | 2026-07-08 | Independent technical reference | Reference only | checkpoint_resume | Vendor-neutral explanation of the offset-pagination duplicate/missing-row problem and the keyset alternative. |
| GEN-41 | Logging — OWASP Cheat Sheet Series | https://cheatsheetseries.owasp.org/cheatsheets/Logging_Cheat_Sheet.html | 2026-07-08 | Official OWASP docs | Primary | observability_redaction | What not to log; severity classification; user-facing vs. extended-technical-detail separation; sanitization. |
| GEN-42 | A09:2021 – Security Logging and Monitoring Failures — OWASP Top 10 | https://owasp.org/Top10/2021/A09_2021-Security_Logging_and_Monitoring_Failures/ | 2026-07-08 | Official OWASP docs | Primary | observability_redaction | Named failure patterns (unclear log messages, local-only storage); real breach example. |
| GEN-43 | A09:2025 – Security Logging and Alerting Failures — OWASP Top 10:2025 | https://owasp.org/Top10/2025/A09_2025-Security_Logging_and_Alerting_Failures/ | 2026-07-08 | Official OWASP docs | Primary | observability_redaction | Current revision; explicitly calls out avoiding PII/PHI in logs. |
| GEN-44 | Secrets Management — OWASP Cheat Sheet Series | https://cheatsheetseries.owasp.org/cheatsheets/Secrets_Management_Cheat_Sheet.html | 2026-07-08 | Official OWASP docs | Primary | observability_redaction | Never log plaintext secrets; process for removing a leaked secret; rotation rationale. |
| GEN-45 | User Privacy Protection — OWASP Cheat Sheet Series | https://cheatsheetseries.owasp.org/cheatsheets/User_Privacy_Protection_Cheat_Sheet.html | 2026-07-08 | Official OWASP docs | Reference only | observability_redaction | Official OWASP source, but contains almost no logging-specific PII guidance on inspection. |
| GEN-46 | MASWE-0001: Insertion of Sensitive Data into Logs | https://mas.owasp.org/MASWE/MASVS-STORAGE/MASWE-0001/ | 2026-07-08 | Official OWASP docs | Primary | observability_redaction | Corroborates "don't log secrets/PII" from a mobile-security angle; log-level-based mitigation. |
| GEN-47 | CWE-532: Insertion of Sensitive Information into Log File | https://cwe.mitre.org/data/definitions/532.html | 2026-07-08 | Official standards taxonomy (MITRE) | Primary | observability_redaction | Formal weakness definition plus concrete code-level examples (credential concatenation, whole-object logging). |
| GEN-48 | SP 800-122 — Guide to Protecting the Confidentiality of PII | https://csrc.nist.gov/pubs/sp/800/122/final | 2026-07-08 | Official standards body (NIST) | Primary | observability_redaction | Canonical PII-protection reference; explicitly scoped to US federal information systems. |
| GEN-49 | Art. 5 GDPR — Principles relating to processing of personal data | https://gdpr-info.eu/art-5-gdpr/ | 2026-07-08 | Regulation text mirror | Secondary | observability_redaction | Data-minimisation (5(1)(c)) and integrity/confidentiality (5(1)(f)) principles; does not mention "logs" by name. |
| GEN-50 | Logs — The Twelve-Factor App | https://12factor.net/logs | 2026-07-08 | Official methodology source | Primary | observability_redaction | Canonical "treat logs as event streams" pattern; app is not responsible for routing/storage. |
| GEN-51 | Monitoring Distributed Systems — Google SRE Book | https://sre.google/sre-book/monitoring-distributed-systems/ | 2026-07-08 | Official source book | Primary | observability_redaction | The "four golden signals" (latency, traffic, errors, saturation) — written for request/response systems generally, not sync pipelines specifically. |
| GEN-52 | Control Bus — Enterprise Integration Patterns | https://www.enterpriseintegrationpatterns.com/patterns/messaging/ControlBus.html | 2026-07-08 | Canonical pattern catalog | Primary | observability_redaction | Dedicated management/monitoring channel, separate from the application-data channel. |

---

## OCA queue_job notes

**Framing.** Everything in this section describes OCA `queue_job` **as a
reference pattern only.** This document does not recommend installing,
depending on, or adopting `queue_job`, consistent with `RA-004`/`DEC-005`,
which already treats `queue_job` as a non-default, non-rejected option whose
adoption is an open architecture question, not a decision made here.

**Capabilities observed [Fact].** `queue_job` "adds an integrated Job Queue to
Odoo," postponing method calls for asynchronous execution by a Jobrunner "in
their own transaction" (OCA-2). Jobs are created via `with_delay()` /
`delayable()` / `chain()` / `group()`, are stored as PostgreSQL records with
dedicated views, and are organized into hierarchical **channels** that give
capacity to a root channel and sub-channels for segregating/throttling work
(OCA-2, OCA-3). The module defines seven job states —
`wait_dependencies, pending, enqueued, started, done, cancelled, failed`
(OCA-6) — and supports job graphs (`chain`/`group`/`on_done`) where downstream
jobs sit in `wait_dependencies` until an upstream job resolves, either by a
retry succeeding or by manual operator action (mark done / cancel) (OCA-3).
Jobs stuck in `enqueued`/`started` (e.g. a killed worker) are documented as
automatically re-queued (OCA-4). The 19.0-branch manifest confirms the module
is packaged for Odoo 19 (version `19.0.2.0.2`, LGPL-3), depends on `mail`,
`base_sparse_field`, `web`, and external Python packages `requests` and
`openupgradelib` (OCA-7).

**Retry/error concepts [Fact].** `queue_job` defines a small exception
hierarchy: `BaseQueueJobError → JobError → {NoSuchJobError, FailedJobError,
RetryableJobError}`, plus `ChannelNotFound` (OCA-5). `RetryableJobError` is
documented as "a job had an error but can be retried," retried "after the
given number of seconds," or per the job's `retry_pattern`, or by the global
`RETRY_INTERVAL` if neither is set (OCA-5, OCA-6). Source constants are
**`DEFAULT_MAX_RETRIES = 5`** and **`RETRY_INTERVAL = 10 * 60` (600 seconds)**
(OCA-6). `max_retries` is documented per-job as "maximum number of retries
before giving up and set the job state to 'failed'. **A value of 0 means
infinite retries**" (OCA-3) — and this is enforced in `Job.perform`: a
`RetryableJobError` caught when `max_retries` is falsy (0) is simply
re-raised, i.e. treated as infinite retries; only when `self.retry >=
self.max_retries` is the exception converted in place to a `FailedJobError`
("Max. retries (%d) reached: %s"), re-raised via `raise new_exc from err` to
preserve the original traceback (OCA-6). A `retry_pattern` can map "try count
reached so far" to postpone-seconds (e.g. `{1: 10, 5: 20, 10: 30, 15: 300}`),
resolved from the highest threshold downward, with optional randomized jitter
via `randint()` over a `[min, max]` range if the resolved value is a
list/tuple (OCA-3, OCA-6).

`FailedJobError` is documented, verbatim, only as: `"""A job had an error
having to be resolved."""` (OCA-5). Reading it as "a terminal failure needing
manual intervention" is a reasonable **[Inference]** consistent with the
max-retries-exhaustion conversion logic and the manifest's
`queue_jobs_to_done_views.xml` / `queue_jobs_to_cancelled_views.xml` wizards
(OCA-6, OCA-7) — but that gloss is **not itself part of the quoted docstring**,
and this document keeps the two separated per the adversarial-verification
finding that the original draft blended them **[Corrected on verification]**.

**Job identity/dedup [Fact, with correction applied].** `identity_key` is
documented as a deduplication mechanism: "when a job should be created and a
pending job with the exact same recordset and arguments [exists], the second
will not be created" (OCA-6). The built-in `identity_exact()` helper computes
a SHA-1 hash over the model name, method name, sorted recordset ids, the
positional `args`, **and** `str(sorted(kwargs.items()))` — the kwargs are
hashed too, not only args/recordset/model/method as an earlier draft of this
fact stated; this omission was caught on adversarial re-check of the source
and is corrected here **[Corrected on verification]**. The dedup check itself
(`job_record_with_same_identity_key`) only searches for existing jobs whose
state is `in [wait_dependencies, pending, enqueued]` — **not** `started`
(OCA-6). A job that has already begun executing therefore does **not** block a
duplicate from being created; treating `identity_key` as a complete
de-duplication guarantee (e.g. against re-delivered webhooks) would be
**[Inference, flagged as a real limitation]** an overreach without additional
application-level idempotency.

**Why this may help as a reference pattern [Inference].** The
`RetryableJobError`/`FailedJobError` split, paired with a configurable
`retry_pattern` and an identity-key-style dedup check, is a plausible
reference shape for a future sync engine's own error-handling design:
transient failures (e.g. Shopify 429/`THROTTLED`) map conceptually to
"retryable," while a permanently invalid payload or business-rule conflict
maps conceptually to "terminal, needs resolution." This mapping is this
document's synthesis, not a claim `queue_job`'s documentation makes about
Shopify. Similarly, `queue_job`'s documented author obligation that "the job
should test at the very beginning its relevance" because "the moment the job
will be executed is unknown by design" (OCA-3) generalizes, as an
**[Inference]**, to a future engine needing an analogous re-validation step
before applying a queued change.

**Why blindly adopting it may be risky.** **[Fact]** The standard Jobrunner
has real infrastructure preconditions beyond a default Odoo install: multiple
workers (`--workers > 1`), `queue_job` loaded as a server-wide module, and a
long-lived process reachable over HTTP that listens for PostgreSQL `NOTIFY`
(OCA-4). **[Fact]** Not every hosting environment can run it as documented:
OCA's own `queue_job_cron_jobrunner` companion module exists specifically
because "Odoo.sh puts HttpWorkers to sleep when there's no network activity,"
and that cron-based fallback "only implements the most basic features of the
`queue_job` runner, notably no channel capacity nor priorities" (OCA-8).
**[Fact]** Adopting `queue_job` pulls in a defined dependency footprint —
`mail`, `base_sparse_field`, `web`, plus external Python packages `requests`
and (on the 19.0 manifest) `openupgradelib` (OCA-7). **[Reference only /
weak]** A single unresolved GitHub issue (OCA-10) shows one user hitting a
`localhost:8069` connection-refused error on Odoo.sh; with no maintainer
response visible in the fetched thread, this is one anecdotal data point
consistent with the Odoo.sh limitation above, not independent proof of a
specific failure mode. **[Inference, not stated by the docs]** Treating
`queue_job` as a hard dependency for a future sync engine would couple that
engine's deployment/operations (worker-count tuning, jobrunner supervision,
channel configuration, choice of runner per hosting target) to Odoo
infrastructure decisions outside this project's control.

**Open questions [Open question].** How actively maintained the 19.0 branch
specifically is (only structural/manifest parity with 18.0 was confirmed, not
commit cadence); whether OCA/queue#169 was ever resolved; whether
`queue_job_cron_jobrunner` still lacks channel capacity/priority support;
whether an official Read the Docs site exists separately from the GitHub
README fragments; and actual jobrunner throughput/scaling characteristics
under production load — none of these were established by the fetched
sources.

---

## Idempotency notes

**Source-backed principles [Fact].** A client-generated, high-entropy random
token (a UUID v4 or equivalent) submitted with a mutating request is the
dominant documented key format, appearing independently across Stripe (GEN-1),
the IETF draft (GEN-3), and AWS's Well-Architected guidance (GEN-5). An
alternative documented within the AWS ecosystem is an explicit, caller-supplied
"client token" representing operation intent — e.g. EC2's `RunInstances`
`ClientToken` — which AWS's Builders' Library states is favored over deriving
a token by hashing request parameters, specifically because it "allows
customers to clearly express intent through API semantics" (GEN-4). Multiple
sources bind the key not to a bare string but to the (client, operation,
payload) tuple: Stripe errors if parameters differ under a reused key (GEN-1);
the IETF draft states a key "MUST NOT be reused with another request with a
different request payload" (GEN-3); AWS treats a reused token with different
parameters as signaling the customer intended a different outcome and returns
a validation error (GEN-4). Server-side handling converges on a store-and-replay
shape: on first receipt, process and atomically store the response (or
processing state) keyed by the idempotency key; on a retried request with the
same key, return the stored result instead of reprocessing (GEN-1, GEN-3,
GEN-4, GEN-5). In-flight (not-yet-completed) duplicate requests are handled
**inconsistently** across documented sources: the IETF draft recommends HTTP
409 (GEN-3); Stripe's documented behavior is to not cache a result for the
conflicting concurrent request and tell the client to retry, because "no API
endpoint [has yet] initiate[d]" — more precisely, no endpoint has yet
**completed** — the execution that would produce a result to cache (GEN-1;
wording corrected here for internal consistency with the quoted source text
per the adversarial-verification finding **[Corrected on verification]**).

TTL/expiry is present but vendor-specific: Stripe prunes keys after **24
hours** (GEN-1); AWS ties EC2 token validity to "the lifetime of the resource,
plus an interval" (GEN-4); the IETF draft leaves the expiry policy to the
resource owner but requires it be defined and published (GEN-3). **An
"AWS/Stripe converge on a shared 24-hour standard" claim would be an
overreach** — only Stripe documents a fixed 24-hour figure; this was
explicitly excluded from the underlying research's facts for that reason.

**AWS idempotent-service definition — citation note [Corrected on
verification].** The sentence "An idempotent service promises that each
request is processed exactly once, such that making multiple identical
requests has the same effect as making a single request" belongs to the AWS
**Well-Architected Framework** page (GEN-5), not the Builders' Library essay
(GEN-4) as an earlier draft attributed it — the Builders' Library essay's own
opening definition is materially different ("An idempotent operation is one
where a request can be retransmitted or retried with no additional side
effects…"). Both are Primary AWS sources already in the inventory; this is a
citation fix, not new research. Similarly, the Builders' Library essay names
only EC2 `RunInstances`'s `ClientToken` explicitly — an earlier draft also
attached "and ECS `RunTask`" to the same citation, which does not appear in
that essay; this document cites only the EC2 example here **[Corrected on
verification]**.

Documented anti-patterns (AWS Well-Architected, GEN-5): applying idempotency
indiscriminately where not needed; overly complex idempotency logic; **using
timestamps as idempotency keys** ("can cause inaccuracies due to clock skew or
due to multiple clients that use the same timestamps"); storing entire request
payloads purely for idempotency bookkeeping (performance/scalability cost);
and generating keys inconsistently across services (breaks cross-service
duplicate detection). In event-driven/message-queue architectures, the same
framework recommends publishers include idempotency tokens in messages and
consumers track received tokens, **propagating the same token to any
downstream services they call** (GEN-5) — a detail directly relevant to any
future design with more than one hop between "Shopify event received" and
"Odoo record mutated." Google Cloud Pub/Sub's own exactly-once feature is
documented as covering pull subscriptions only (not push/export), and even
with it enabled, publish-side retries can still produce distinct message IDs
for what is logically one publish attempt — so delivery-layer guarantees alone
do not eliminate the need for consumer-side idempotent processing (GEN-7).

**Candidate key components — for later architecture review, not a decision
[Recommendation-candidate].** Combining the source-backed principles above, a
candidate consideration for a future connector is that an idempotency key
would need to be scoped to at least: (a) which two systems' records are
involved, (b) which kind of operation is being performed, and (c) a
caller-or-event-supplied unique token (a UUID-style value, or a Shopify-
supplied delivery identifier such as `X-Shopify-Webhook-Id`, which Shopify's
own docs recommend using to detect and skip duplicate webhook deliveries —
SH-5). This is offered only as candidate/inference material; it does **not**
name any Odoo model or define any concrete field/table shape, and remains
subject to later architecture review.

**Core vs. domain-specific — inference/consideration, not a decision
[Recommendation-candidate].** None of the fetched sources address a
core-infrastructure-vs.-domain-specific split directly (they describe
single-API or single-queue systems, not a layered connector). Reasoning by
extension from the sources above: the **mechanics** of "record a key
atomically with a mutation, then replay the stored result on retry" (GEN-1,
GEN-4, GEN-5) read as generic enough to belong to shared, cross-cutting
infrastructure, while **what counts as "the same operation"** for a given
entity type (e.g. what row/attribute changes constitute a duplicate of a
particular flow) is inherently tied to that entity type's own business
semantics and would plausibly need to stay domain-specific. This is a
reasoned **[Inference]**, explicitly not a decision, and is offered for later
architecture review only.

**First-sync/bulk-import deduplication caveats [Inference, grounded in
multiple topics].** None of the fetched sources address bulk/first-sync
deduplication directly, but two documented gaps combine into a real caveat:
first, an idempotency key by definition only protects a *retry* of a request
already assigned that key (GEN-1, GEN-3) — on a first sync there is, by
definition, no prior idempotency key to match against, so an initial
bulk-import pass cannot rely on idempotency-key matching alone to avoid
creating duplicates of records that already exist on the other side. Second,
matching by an external identifier during a first/bulk import is exposed to a
classic check-then-act race: PostgreSQL's own documentation frames `INSERT …
ON CONFLICT` as making the "does a matching row already exist" check and the
resulting action a single atomic per-row decision against an arbiter unique
constraint, explicitly implying that a **separate** "look up by external id,
then insert if missing" pattern (two statements, not one atomic one) is
exposed to two concurrent processes both passing the lookup before either
commits (GEN-33). A bulk-import/backfill design would therefore plausibly need
its own matching-and-locking strategy distinct from steady-state idempotency-
key replay — noted here as an open consideration, not resolved by any fetched
source.

---

## Retry and backoff notes

**Retryable vs. permanent error distinctions [Fact].** `queue_job`'s own
exception hierarchy structurally separates `RetryableJobError` (transient,
optionally with an explicit delay or an `ignore_retry` flag) from
`FailedJobError` (terminal, needs resolution) (OCA-5, OCA-6 — see OCA queue_job
notes). The same split recurs, independently, across every general-purpose
retry source examined: Azure's Transient Fault Handling guide states "status
code 429 (Too Many Requests) and 5xx server errors are typical retry
candidates. Most 4xx client errors, like 400, 401, 403, and 404, indicate
problems that a retry doesn't resolve" (GEN-12); Google SRE recommends
engineers "separate retriable and nonretriable error conditions. Don't retry
permanent errors or malformed requests" (GEN-10); and Stripe's own API
implements exactly this split, with **429 named as an explicit, documented
exception** to "always generate a new idempotency key on 4xx," because
"a request that's rate limited with a 429 can produce a different result with
the same idempotency key because rate limiters run before the API's
idempotency layer" (GEN-17).

**Bounded retry requirement [Fact].** Unbounded retries are independently
flagged as dangerous by every general-purpose source examined, not treated as
a neutral design option. Google SRE's cascading-failures analysis shows
retries compounding **multiplicatively** across stack layers: "if the
database can't service requests because it's overloaded, and the backend,
frontend, and JavaScript layers all issue 3 retries (4 attempts), then a
single user action may create 64 attempts (4³) on the database" (GEN-10). AWS
Well-Architected rates the risk of not bounding/backing-off retries as
**"High"** and separately names "retrying at multiple layers of your
application stack in a manner which compounds retry attempts" as an
anti-pattern (GEN-15). Azure's Transient Fault Handling guide states flatly:
"Never implement an endless retry mechanism. This approach typically prevents
the resource or service from recovering from overload situations… Use a
finite number of retries, or implement a pattern like Circuit Breaker" (GEN-12),
and its dedicated Retry Storm antipattern page frames the same failure as a
"thundering herd" (GEN-13). Two independent, converging bounding mechanisms
recur across sources: a **per-request/per-call limit** (Google's "up to three
attempts," GEN-11; Azure's "maximum number of retries or elapsed time,"
GEN-12) and a separate **aggregate/process-wide retry budget** (Google's and
Azure's near-identical illustrative "60 retries per minute" examples, GEN-10,
GEN-12 — both sources present this as an illustrative order-of-magnitude, not
a derived constant).

**Retry-after/throttle signals [Fact].** Shopify's REST Admin API returns
HTTP 429 with a `Retry-After` header on rate-limit exceedance, computed
against a leaky-bucket capacity model reported via `X-Shopify-Shop-Api-Call-Limit`
(e.g. `32/40`) (SH-1). Standard-plan REST bucket size is 40 requests with a
2/second leak rate; Shopify Plus is 400 requests at 20/second (SH-1). The
Advanced plan's REST throughput (4 requests/second) and its **plan-tier REST
table** live on the REST Admin API rate-limits page (SH-1) — an earlier draft
of this fact cited the general "Shopify API limits" page (SH-2) for the
Enterprise/Commerce-Components 40 req/s REST figure, but two independent
re-fetches of SH-2's rate-limit table found **no REST figures on that page at
all**; the correct citation is SH-1, and the figure is exact (40 req/s), not
"roughly" 40 as originally hedged **[Corrected on verification]**. The
Advanced-plan **GraphQL** figure needs a staleness caveat: the 2023-06-07
changelog (SH-8) states 100 points/second for Advanced, but the current
"Shopify API limits" page (SH-2) states 200 points/second for the same tier —
the changelog figure is superseded; a reader should treat SH-2 as the current
number and SH-8 as historical **[Corrected on verification]**. Shopify's
GraphQL Admin API uses cost-point throttling instead of raw request counts: a
single query cannot exceed 1,000 points regardless of plan, and each response
carries `extensions.cost` with `requestedQueryCost`, `actualQueryCost`, and a
`throttleStatus` object (`maximumAvailable`, `currentlyAvailable`,
`restoreRate`) (SH-2). A throttled GraphQL call can still return **HTTP 200**
with a `THROTTLED` error code in the body rather than a 4xx status (SH-4) — a
client that only checks HTTP status codes will silently treat a throttled
GraphQL call as successful. No fetched Shopify page documents a `Retry-After`
header (or equivalent) for GraphQL `THROTTLED` responses specifically; the
safe fallback per the docs found is to derive a wait time from
`throttleStatus.currentlyAvailable` and `restoreRate` **[Open question,
absence-based]**. Shopify's own general guidance: "Your code should stop
making additional API requests until enough time has passed to retry. The
recommended backoff time is one second," and "you could implement a request
queue with an exponential backoff algorithm" (SH-2).

**Risk of infinite retries [Fact].** `queue_job`'s own `max_retries` semantics
make this concrete at the framework level: "A value of 0 means infinite
retries" (OCA-3), and the `perform()` handler explicitly re-raises a
`RetryableJobError` forever when `max_retries` is falsy rather than treating 0
as "stop immediately" (OCA-6). This is the same failure class Azure names
generically ("never implement an endless retry mechanism," GEN-12) and Google
SRE quantifies (retry amplification growing round after round against an
already-overloaded backend, GEN-10). AWS's canonical jitter guidance
(GEN-8) is directly relevant here: **[Corrected on verification]** the
Equal Jitter formula as originally recorded in this research
(`base + random(0, min(cap, base * 2^attempt))`) does not match the live AWS
Architecture Blog page; two independent re-fetches confirm the actual formula
is `temp = min(cap, base * 2^attempt); sleep = temp/2 + random(0, temp/2)` —
i.e. the additive floor is **half of the capped exponential value**, not the
bare `base` constant. This is corrected here because an incorrect formula is
exactly the kind of number a future implementer could copy directly into
code. The same source's comparative finding is also corrected: Equal Jitter is
described as "the loser" among the jittered approaches, doing "slightly more
work than Full Jitter, and tak[ing] much longer" — not "similar" to Full
Jitter as an earlier paraphrase stated (GEN-8).

**Manual retry implications [Fact].** What must be preserved so a human can
safely retry later, per the sources examined: the original request
parameters together with the idempotency token, recorded atomically
("atomic, consistent, isolated, and durable (ACID)") with the mutating
operation itself, so a retry — automatic or human-triggered — can be resolved
by replaying the stored result rather than re-executing (GEN-4, GEN-5).
Stripe's own low-level guidance instructs clients to "retry such requests with
the same idempotency keys and the same parameters until they're able to
receive a result from the server" for intermittent network errors, and
signals retryability explicitly via a `Stripe-Should-Retry` response header,
while still expecting an exponential-backoff delay before the next attempt
even when retry is indicated (GEN-17). Azure's guidance to "log all
connectivity failures that cause a retry" and to preserve failed-request data
in a dead-letter queue "so that the information isn't lost after you use all
retry attempts" (GEN-12) both point the same direction: whatever a human
operator needs to safely retry later (original parameters, the applicable
key, and a durable failure record) has to be captured **before** retries are
exhausted, not reconstructed afterward.

---

## Dead-letter / permanent failure notes

**Visibility requirement [Fact].** Across every vendor implementation
examined, visibility is implemented as a **named, queryable metric** that the
vendor explicitly documents wiring into an alarm — it is not pushed
automatically. AWS: "Set up a CloudWatch alarm to monitor messages in a
dead-letter queue using the `ApproximateNumberOfMessagesVisible` metric…
[o]nly then can you poll the queue to review and retrieve them" (GEN-19).
Azure: a named `DeadletteredMessages` platform metric exists in Azure
Monitor's own metrics reference specifically for this purpose (GEN-25). A bare
DLQ with no alarm/monitor wired up therefore provides **no visibility
guarantee by itself [Inference]** — the platforms make this an opt-in
configuration step, not a default behavior.

**User/admin recovery implications [Fact].** Recovery is documented, in every
platform examined, as a deliberate, operator-gated action distinct from normal
message flow, not something automatic. AWS's SQS redrive-to-source-queue
feature lets operators move investigated messages back to the source queue for
reprocessing (GEN-23) — but the review step is **optional**, not mandatory:
the source page states "you can optionally review a sample of the available
messages in the DLQ" before redriving, correcting an earlier overstatement
that treated investigation as a required gate **[Corrected on verification]**.
Azure documents resubmission via the Service Bus Explorer, which lets an
operator "peek messages in the dead-letter queue, edit their content or
properties if needed, and resend them — individually or in batches," only
"once you resolve the issue that caused a message to be dead-lettered" (GEN-24).
`queue_job`'s own recovery mechanism is the manual side of the same shape: a
failed job graph is resolved either by the parent job retrying successfully,
or by a user manually marking the failed job "done," or by a user manually
canceling the failed job and its dependents (OCA-3) — and the 19.0 manifest
ships dedicated wizards for exactly this (`queue_jobs_to_done_views.xml`,
`queue_jobs_to_cancelled_views.xml`, `queue_requeue_job_views.xml`, OCA-7).

**How not to hide failures [Fact/Risk].** `FailedJobError` is `queue_job`'s
structural mechanism for **not** silently discarding a permanently failed job
— an exhausted retry is converted into a distinct, queryable, UI-visible
terminal state rather than disappearing (OCA-5, OCA-6). The generic
messaging-pattern equivalent is the Enterprise Integration Patterns' Dead
Letter Channel: "when a messaging system determines that it cannot or should
not deliver a message, it may elect to move the message to a Dead Letter
Channel" rather than dropping it (GEN-26). OWASP's Top 10 A09 category names
"logs are only stored locally" and "warnings and errors generate no,
inadequate, or unclear log messages" as concrete failure patterns that
undermine detection generally (GEN-42) — directly relevant to a queue/DLQ
design, since a dead-lettered item that is neither alarmed on (see Visibility,
above) nor logged clearly is functionally hidden even though it technically
still exists in storage. Two secondary/practitioner sources make the same
point about **DLQs specifically**: "messages silently expire on day 14, nobody
knows they were there" (GEN-28), and "a DLQ is a safety valve, not a safety
net. It gives you a buffer, but only if you actively manage it" (GEN-29) — both
graded Secondary, practitioner opinion rather than vendor documentation.
Separately, AWS Lambda's own documented behavior is a real edge case worth
naming: **if DLQ delivery itself fails**, Lambda does not retry indefinitely
or hold the event — "it deletes the event and emits the `DeadLetterErrors`
metric" (GEN-21). The DLQ hand-off therefore needs its own success/failure
signal; "the item is not in the main queue" is not proof "the item is safely
in the DLQ." (An earlier draft of this fact blended this Lambda-specific
metric with a differently-scoped general destination-delivery metric,
`DestinationDeliveryFailures`; only `DeadLetterErrors` is documented for the
DLQ-delivery-failure case described here **[Corrected on verification]**.)
Dead-lettering commonly follows retry-exhaustion, but is not exclusively a
multi-attempt phenomenon: AWS's own SQS docs note "if the `maxReceiveCount` is
set to a low value such as 1, one failure to receive a message would cause the
message to move to the dead-letter queue" (GEN-18), and RabbitMQ dead-letters
on a single negative acknowledgment/rejection as one of its documented
triggers (GEN-27) — an earlier categorical claim that dead-lettering never
happens on a single failed attempt has been softened accordingly **[Corrected
on verification]**.

---

## Duplicate-running prevention notes

**Create-time checks [Fact].** The recurring documented pattern is to make the
existence check and the write a single atomic operation rather than two
separate statements. PostgreSQL's `INSERT … ON CONFLICT` makes "the insertion
proceeds, or, if an arbiter constraint or index specified by `conflict_target`
is violated, the alternative `conflict_action` is taken" a single per-row
decision (GEN-33). Odoo 19's own ORM reference documents a `Constraint` class
(replacing the legacy `_sql_constraints` attribute) for declaring SQL-level
uniqueness (OD-7), and this idiom is confirmed, via direct GitHub code search
(independently re-run and reproducing exactly 143 matches), to be in live,
widespread use across Odoo's own codebase — e.g.
`_unique_name = models.Constraint('UNIQUE(name)', 'The name must be unique')`
in `addons/utm/models/utm_source.py` (OD-9).

**Execution-time checks [Fact].** Odoo 19's own scheduler prevents two cron
workers from processing the same job at the same instant using a PostgreSQL
row lock with `SKIP LOCKED`, not an application-level "is running" flag:
`"(i) is implemented via FOR NO KEY UPDATE SKIP LOCKED, each worker just
acquire one available job at a time and lock it so the other workers don't
select it too"` (OD-1). The weaker `FOR NO KEY UPDATE` (rather than `FOR
UPDATE`) is used deliberately so the lock does not conflict with the `KEY
SHARE` lock implicitly held by foreign keys referencing the row (OD-1). The
ORM exposes the same mechanism generally via `lock_for_update()` (raises
`LockError`, HTTP 409, if not every requested row could be locked) and
`try_lock_for_update()` (silently skips already-locked rows and returns only
what it could lock) (OD-3, OD-6) — Odoo's own official cron-writing guidance
recommends the latter, re-applying the original search domain immediately
after locking: `record = record.try_lock_for_update().filtered_domain(domain)`,
explicitly to guard against the record having changed between selection and
lock acquisition (OD-2). Both locking primitives deliberately use `SKIP
LOCKED` instead of `NOWAIT`: `"Use SKIP LOCKED instead of NOWAIT because the
later aborts the transaction and we do not want to use SAVEPOINTS"` (OD-3).
`queue_job`'s `identity_key`/`identity_exact()` dedup check (see OCA queue_job
notes) is the async-job-queue analogue of the same idea, scoped only to
non-terminal job states (OCA-6).

**Locking/race caveats [Fact].** PostgreSQL automatically detects and resolves
deadlocks by aborting one of the involved transactions — "exactly which
transaction will be aborted is difficult to predict and should not be relied
upon" (GEN-30); the documented defense is a consistent lock-acquisition order
across all applications sharing the database (GEN-30). Serialization/lock-
conflict errors are treated as **normal control flow, not exceptional
failure**, in Odoo's own cron loop: a caught `TransactionRollbackError` around
`_acquire_one_job` is handled by rolling back the shared cursor, logging that
another worker handled it, and moving to the next job — with **no retry of
that same job within the pass** (OD-1). PostgreSQL's own docs give a worked
"danger!" example where calling an advisory-lock function inside a `SELECT …
ORDER BY … LIMIT` can lock rows **before** the `LIMIT` is applied, leaving
"dangling" locks the application never intended to acquire, held until session
end (GEN-30) — a real hazard for any design keying an advisory lock off a
computed/derived value inside a bounded query. Session-scoped advisory locks
are **not** released by a transaction rollback and persist "until explicitly
released or the session ends" (GEN-30) — a design reusing pooled DB
connections across unrelated units of work would need an explicit release
step or the transaction-scoped variant (`pg_advisory_xact_lock`) to avoid a
lock surviving past its intended scope.

**What requires actual Odoo 19 runtime proof, not source-reading alone
[Open question — explicitly flagged by the underlying research itself].**
The duplicate_running research topic's own framing draws this line
explicitly, and it is preserved here rather than smoothed over: whether
`ir.cron`'s `FOR NO KEY UPDATE SKIP LOCKED` acquisition **actually** prevents
duplicate execution under Odoo 19's real multi-worker/multi-process
deployment has, in this research pass, only been confirmed by **reading
source and doc comments** — it has not been observed running, and would need
an actual concurrency test (fire the same cron from two processes/threads
simultaneously and confirm exactly one executes) to verify the documented
intent matches real runtime behavior. The same caveat applies to: how the
`max_cron_threads` worker-count setting changes the practical guarantee;
whether a job skipped due to a caught `TransactionRollbackError` is reliably
retried on the next scheduler poll with no silent work loss; whether the
row-lock-only approach is sufficient with **no additional cross-server
coordination** when multiple Odoo application servers share one PostgreSQL
database (a historical GitHub issue referencing load-balanced cron scheduling
suggests this has been a real operational pain point worth an explicit
runtime test); and whether the HTTP-visible `409 Conflict` behavior from a
`LockError` is surfaced cleanly and consistently to end users/API clients.
None of these were, or could be, resolved by source-reading alone.
Kubernetes' own client-go leader-election package makes a structurally
similar admission for a different mechanism: "This implementation does not
guarantee that only one client is acting as a leader (a.k.a. fencing)"
(GEN-34) — a useful cross-reference that "an election/acquisition mechanism
exists" is not, by itself, proof of a hard mutual-exclusion guarantee.

---

## Checkpoint/resume notes

**Pagination checkpoint ideas [Fact].** Shopify's GraphQL Admin API exposes
cursor position via a `PageInfo` object: `hasNextPage`/`hasPreviousPage` plus
`endCursor`/`startCursor` (the cursor of the last/first node in the current
page) (SH-9, SH-10). Forward pagination uses `first`/`after`; backward uses
`last`/`before`; a single query can retrieve at most **250 resources** per
page, with Shopify directing larger volumes to bulk operations instead (SH-9).
The `orders` connection additionally exposes a `query` search-syntax filter
(supporting fields like `updated_at`) and a `sortKey` argument (default
`PROCESSED_AT`), with `OrderSortKeys` including an `UPDATED_AT` option (SH-11,
SH-12). Shopify's cursors are implemented internally as **keyset ("relative
cursor") pagination**: "relative cursor pagination remembers where you were so
that each request after the first continues from where the previous request
left off," with the documented tradeoff that "you can no longer jump to a
specific page" (SH-17). **[Corrected on verification]** An earlier draft of
this research attributed a specific SQL `WHERE`-clause string to the Shopify
Engineering article (SH-17) as a direct quote. Two independent
verbatim-reproduction re-fetches of the live article found **no such SQL/code
block anywhere on the page** — only narrative description and diagrams. That
quoted SQL string has been removed from this document as unverifiable/likely
fabricated; only the narrative claim it was illustrating (relative-cursor
pagination filters forward from a last-seen value, with a tiebreak field for
non-unique sort keys) is retained, and only as a paraphrase.

**Resumability caveats [Fact].** For the REST Admin API, Shopify explicitly
warns that `page_info`/Link-header cursor URLs are **temporary**: "The link
header URLs are temporary and we don't recommend saving them to use later. Use
link header URLs only while working with the request that generated them"
(SH-16); a request using `page_info` also cannot combine with any parameter
other than `limit`/`fields` (SH-16). No equivalent explicit statement was
found for GraphQL `after` cursors specifically — their reuse-safety after a
long-delayed resume is an **[Open question]**, not a documented guarantee
either way. Shopify's asynchronous **bulk operations** are the documented
alternative for very large datasets and are explicitly exempt from the
per-query cost cap and per-second rate limits that apply to standard paginated
queries (SH-2) — but they are **not resumable at the API level**: "you can
retry canceled bulk operations by submitting the query again," and a failed
bulk operation's documented remedy is likewise to resubmit, "these errors
might be intermittent, so you can try submitting the query again" (SH-14).
Whatever rows a failed bulk operation retrieved before failing remain
retrievable only via a separate `partialDataUrl`, distinct from the full-result
URL, and both are signed URLs that expire after **one week** (SH-14).
Cancellation of a running bulk operation is itself asynchronous, with "a short
delay from when a cancelation starts until the operation is actually
canceled" (SH-15).

**Partial success risks [Fact].** AWS Glue's workflow-resume feature restarts
only selected failed nodes and everything downstream of them, but explicitly
states "restarting a node does not reset its state. Any data that was
partially processed is not rolled back" (GEN-36) — and a workflow run's
top-level status "is shown as COMPLETED" even when internal nodes did not
finish, so an operator must inspect the run graph, not just run status, to
detect partial failure (GEN-36). AWS Step Functions' redrive feature resumes a
failed execution "from the unsuccessful step," preserving (not re-running) the
results/history of prior successful steps, within a 14-day eligibility window;
for a Distributed Map, redrive reruns only the failed/aborted child iterations,
leaving successful ones untouched, and resets Task/Parallel/Inline-Map retry
counters to 0 on redrive (GEN-37). Azure Data Factory's "Rerun from failed
activity" feature behaves differently by activity type — `Wait`/`Set
Variable`/`Filter` "behave as before," while `Until`/`Foreach` loop activities
re-evaluate their condition and loop again, with inner activities still
subject to being skipped per the rerun rules (GEN-38); rerunning with new
parameters is treated as an entirely new run, not grouped into prior rerun
history (GEN-38). The general risk these examples all illustrate: **double-
processing** an already-committed record (if the mutating side effect commits
before the checkpoint/cursor is persisted, a crash between the two causes
reprocessing on resume) versus **silently skipping** a record (if the
checkpoint advances before the mutation is durably committed, a crash after
the checkpoint-advance but before the commit causes that record to be missed
on resume) — this is exactly the failure mode AWS's idempotency-token guidance
(GEN-4, GEN-5) is designed to prevent, and AWS's own EBS-volume example makes
it concrete: "it would be undesirable for the EC2 instance launch workflow to
retry a failed call to create an EBS volume and end up with two EBS volumes"
(GEN-4).

---

## Observability/redaction notes

**User-facing log vs. technical detail [Fact].** OWASP's Logging Cheat Sheet
explicitly separates "responses seen by the user and/or taken by the
application, e.g. status code, custom text messages" from "extended details,
e.g. stack trace, system error messages, debug information, HTTP request
body," recommending separate files/tables for the latter (GEN-41). Azure's
Retry pattern documentation applies the same two-tier idea operationally: "it
is best to log early failures as informational entries and only the failure
of the last of the retry attempts as an actual error," while still logging
"all connectivity failures that cause a retry so that underlying problems…
can be identified" (GEN-6). Read together **[Inference]**, this suggests a
future sync engine's observability layer would plausibly want a simple,
human-readable status per record/operation, separate from a more detailed,
more access-restricted technical log — this is a synthesis across two
sources, not a single-source statement, and is offered only as a
consideration for later design, not a designed feature.

**Secret redaction [Fact].** OWASP's Logging Cheat Sheet lists access tokens,
authentication passwords, session identifiers, encryption keys/primary
secrets, and payment-card data as data that must be removed, masked,
sanitized, hashed, or encrypted rather than logged directly (GEN-41). OWASP's
Secrets Management Cheat Sheet is more categorical still: secrets should
"Never be logged (must implement either an encryption or masking approach in
place to avoid logging plaintext secrets)," and any secret that does end up in
a log "must have a process for removing the secret while maintaining log
integrity" (GEN-44). MITRE CWE-532 formally defines this weakness class and
gives a concrete code-level example: a Java application directly concatenating
a username and credit-card number into a log statement (GEN-47). Both sides
of a future Odoo–Shopify integration treat their own credentials as
password-equivalent in their own official documentation: Shopify's docs
recommend regular client-credential rotation, citing "employees leave, client
credentials can be accidentally committed to version control" as reasons
(SH-18), and warn not to delete an old client secret "until you've requested
new access tokens for every token stored by your app" (SH-18). Odoo's own
19.0 developer documentation states an API key "should [be] store[d]… as
carefully as the password as they essentially provide the same access to your
user account" — **[Corrected on verification]** this sentence is genuine Odoo
19.0 documentation text, but an earlier draft attributed it to the wrong page
(the newer "External JSON-2 API" page); adversarial re-fetch traced the exact
sentence to the older "External RPC API" page instead (OD-10, corrected URL
above). Because both vendors independently treat their respective credential
as password-equivalent, the generic OWASP "never log a password" guidance
should reasonably be read as applying uniformly to both sides' credentials —
this connective step is this document's own **[Inference]**, since neither
vendor's fetched documentation contains an explicit "do not log this token"
sentence.

**PII caution [Fact].** GDPR Article 5(1)(c) requires personal data be
"adequate, relevant and limited to what is necessary in relation to the
purposes for which they are processed" (data minimisation), and Article
5(1)(f) requires it be "processed in a manner that ensures appropriate
security… including protection against unauthorised or unlawful processing
and against accidental loss, destruction or damage" (integrity/confidentiality)
(GEN-49) — **neither clause mentions "logs" or "logging" by name**; applying
them specifically to log output is this document's **[Inference]**, not a
verbatim GDPR requirement. NIST SP 800-122 is explicitly scoped to protecting
PII confidentiality "in [US Federal agency] information systems" (GEN-48), not
general commercial SaaS/ERP integrations — applying its confidentiality-
impact-level approach directly to this connector would be a scope mismatch
unless independently justified. Which regulatory regime(s) actually govern a
given Odoo/Shopify merchant's synchronized customer data depends on that
merchant's and its customers' geography, which is outside this document's
scope and is logged here as an **[Open question]**. The current OWASP Top 10
revision states this caution plainly for logging specifically: prevention
guidance warns against "logging sensitive information that should not be
logged (such as PII or PHI)" (GEN-43).

**Future dashboard needs — framed as future consideration, not a designed
feature [Recommendation-candidate].** No fetched source proposes a dashboard
for a sync/integration system specifically. Combining several general-purpose
sources **[Inference]**: Google SRE's "four golden signals" (latency, traffic,
errors, saturation — explicitly written for user-facing request/response
systems, not batch/sync pipelines, so applying it here is a generalization,
GEN-51); Azure's Circuit Breaker pattern, which ties its Closed/Open/Half-Open
state transitions to monitoring events an administrator can alert on (GEN-14);
and the Enterprise Integration Patterns' Control Bus, which proposes a
dedicated management/monitoring channel separate from the application-data
channel (GEN-52) — together suggest a future observability layer would
plausibly want *some* equivalent of an error/failure rate per operation, a
retry-attempt count, a count of items routed to a permanently-failed state,
and a last-successful-sync signal per synchronized resource type. This is
this document's own synthesis across multiple general sources; no single
source recommends this combination, none of them use the phrase
"last-success timestamp," and nothing here should be read as specifying an
actual dashboard, metric name, or field.

---

## Pattern risks

The following are the specific dangerous patterns this document was asked to
surface. Each is marked by how directly it is source-grounded versus how much
is this document's own inferential connection across sources.

- **Domain modules creating separate queues (fragmentation risk).**
  **[Pattern-risk / Inference, partially source-grounded.]** `queue_job`
  itself is built around **centralizing** async work through one job/state
  data model, with **channels** used to segregate and throttle different
  kinds of work *within* that single model rather than by standing up
  independent queues per consumer (OCA-2, OCA-3). The Enterprise Integration
  Patterns' Control Bus pattern makes a parallel point for observability:
  management/monitoring data is meant to travel on one dedicated channel
  "separate channels to transmit data that is relevant to the management of
  components" (GEN-52), not scattered per-component. Neither source discusses
  a *connector* with multiple domain modules directly, so the specific
  fragmentation risk for a future Odoo↔Shopify connector — that if each
  domain (orders, inventory, customers, etc.) independently invents its own
  queue/retry/dedup mechanism, error taxonomies and recovery UX will diverge
  and become inconsistent — is this document's own reasoned connection
  between the "centralize job/state, segregate only by channel" pattern above
  and general integration-architecture reasoning, not a claim made verbatim
  by any single source about this project.

- **Unbounded retries.** **[Pattern-risk / Fact-grounded.]** This is the most
  directly source-documented risk in the set. `queue_job`'s own
  `max_retries = 0` means **infinite** retries by explicit design (OCA-3,
  OCA-6); Google SRE quantifies exactly how this compounds across layers
  (4³ = 64 attempts from one user action, GEN-10); AWS Well-Architected rates
  the risk "High" (GEN-15); and Azure states outright: "Never implement an
  endless retry mechanism" (GEN-12). Any future design that leaves a retry
  count unbounded, or defaults an equivalent-of-`max_retries` to an
  infinite-retry value without an explicit, deliberate choice to do so, would
  be reproducing a pattern every source examined treats as a documented
  anti-pattern, not a neutral default.

- **Hidden permanent failures.** **[Pattern-risk / Fact-grounded.]** `queue_job`
  structurally avoids this by converting an exhausted retry into a distinct,
  queryable `failed` state with dedicated recovery wizards (OCA-5, OCA-6,
  OCA-7); the risk is what happens *without* that structure. OWASP names
  "logs are only stored locally" and unclear error/warning messages as named
  failure patterns undermining detection (GEN-42), and DLQ-specific
  practitioner sources describe unmonitored dead-letter items as expiring
  "silently" with "nobody know[ing] they were there" (GEN-28) — a DLQ or
  failed-job state that exists in storage but is never alarmed on or
  surfaced in a UI is, functionally, a hidden failure even though it is
  technically "handled."

- **Webhook direct mutation bypassing logs/idempotency.** **[Pattern-risk /
  Inference — a reasoned design anti-pattern, not a single-source claim.]**
  No fetched source documents this exact anti-pattern for a Shopify↔Odoo
  integration specifically. It follows, however, from combining two
  documented pieces: idempotency-key mechanisms only protect an operation
  that is actually **routed through** the idempotency layer — Stripe's own
  docs describe the idempotency layer as something a request passes through
  and is checked against, not an ambient property of the system (GEN-1) —
  and OWASP's logging guidance treats structured, redaction-aware logging as
  a deliberate, separate concern from raw request handling (GEN-41). A
  webhook handler that mutates records directly, without going through
  whatever shared logging/idempotency layer the rest of the system uses,
  would by construction bypass both protections for that one entry point —
  this is this document's own reasoned risk statement, grounded in, but not
  verbatim from, the cited sources.

- **Manual and scheduled sync using different paths.** **[Pattern-risk /
  Inference — a reasoned architectural risk.]** `queue_job`'s documented
  principle that "the job should test at the very beginning its relevance…
  the first task of a job should be to check if the related work is still
  relevant at the moment of the execution" (OCA-3) is a job-author obligation
  precisely because *when* a job runs (and by extension, whether it was
  triggered manually or on a schedule) should not change what "correct" means
  for that job. Combined with the checkpoint/resume material above — where
  every resumable system examined treats "resume" and "run from scratch" as
  needing to converge on the same eventual state (GEN-36, GEN-37) — a design
  in which a manually-triggered sync and a scheduled sync take genuinely
  different code paths (rather than the same path with a different trigger)
  risks the two paths silently diverging in their relevance-checking,
  idempotency, or checkpoint behavior over time. No fetched source states
  this about a sync engine specifically; it is this document's own
  connective inference.

- **Timestamp-based freshness guards without runtime proof.** **[Pattern-risk
  / Fact-grounded, directly per the underlying research's own framing.]**
  AWS Well-Architected names "you use timestamps as keys for idempotency" as
  an explicit anti-pattern, citing clock skew and multiple clients sharing a
  timestamp as the failure mechanism (GEN-5). The duplicate_running research
  topic's own open-questions section is explicit that Odoo 19's locking
  mechanism has only been verified by **reading source and documentation
  comments**, not by an actual concurrency test — "it has not been observed
  running, and would need an actual concurrency test… to verify the
  documented intent matches real runtime behavior" (per OD-1/OD-3 as read;
  see Duplicate-running prevention notes above). A freshness guard built on
  comparing timestamps (e.g. "has this record been updated since I last
  synced it") inherits **both** risks at once: the general timestamp-as-key
  hazard AWS names, and the specific, currently-unverified assumption that
  Odoo's locking/scheduling guarantees behave as documented under real
  multi-worker or multi-server load. Treating either as settled without a
  runtime test would be asserting an inference as a fact.

---

## Unsupported claims removed

Every entry below comes verbatim (paraphrased only for length where the
source list was very long) from one of the nine topics' own
`unsupported_claims_considered_and_removed` array (labelled **Self-review**,
produced during the initial research pass) or `claims_to_remove_or_downgrade`
array (labelled **Adversarial verification**, produced by the independent
fact-check pass). Exact duplicates across topics are not repeated twice.

### OCA queue_job

- **Self-review:** Considered stating flatly that "queue_job does not work on
  Odoo.sh" — kept only the cited queue_job_cron_jobrunner rationale as fact;
  removed the stronger blanket "does not work" framing (no maintainer
  statement of outright incompatibility was found).
- **Self-review:** Considered citing the manifest's `development_status:
  'Mature'` field as evidence of "production-grade at scale" — kept only as a
  literal metadata quote, not elevated into a maturity/scale claim.
- **Self-review:** Considered asserting queue_job requires an external message
  broker (Redis/RabbitMQ) — nothing in the fetched source/docs indicates this
  (the mechanism is PostgreSQL LISTEN/NOTIFY plus an internal HTTP call); not
  asserted.
- **Self-review:** Considered giving specific throughput/jobs-per-second
  numbers for the jobrunner — no such benchmarks appeared in any fetched
  source; logged as an open question instead.
- **Self-review:** Considered citing GitHub star count, contributor count, or
  download/install statistics as adoption evidence — not fetched/verified;
  omitted rather than estimated.
- **Self-review:** Considered asserting the 19.0 branch is "fully
  feature-equivalent" to 18.0 — only manifest fields were compared; left as
  the narrower, directly-supported claim.
- **Adversarial verification:** The `identity_exact()` fact description
  omitted that `kwargs` are also hashed (only args/recordset/model/method were
  mentioned) — corrected in this document (see OCA queue_job notes).
- **Adversarial verification:** The `FailedJobError` fact blended a verbatim
  quote with the researcher's own interpretive gloss ("terminal failure
  needing manual intervention") without clearly flagging the gloss as
  inference — separated in this document.

### Shopify official (throttle/retry)

- **Self-review:** Considered stating GraphQL `THROTTLED` (200 OK) responses
  include a `Retry-After` header analogous to REST's — no fetched page states
  this; logged as an inference/open question instead.
- **Self-review:** Considered stating `Shopify-GraphQL-Cost-Debug=1` as a
  documented debug header — could not be confirmed via direct fetch of the
  GraphQL Admin API reference page at the time; removed and logged as an open
  question. (Adversarial verification later found this header text **is**
  documented, verbatim, on the already-cited "Shopify API limits" page — a
  research gap, not a false claim; noted for completeness, not asserted as
  fact in this document since it is not load-bearing for Task 006A.)
- **Self-review:** Considered stating that webhook subscriptions (regardless
  of configuration method) are removed after exactly 24 hours of failures —
  one page said "24 hours," a more specific page said "8 consecutive failures"
  over "the next 4 hours" for Admin-API-configured subscriptions; the 24-hour
  figure was not asserted given the conflict, and the conflict was logged as
  an open question.
- **Self-review:** Considered asserting the REST/GraphQL/Enterprise rate-limit
  ratios follow a deliberately-designed "1x/2x/10x/20x" multiplier scheme by
  Shopify's own design intent — kept only as an observed arithmetic pattern,
  not an official design-rationale claim.
- **Adversarial verification:** The Enterprise/Commerce-Components "~40
  requests/second" REST figure was mis-cited to the "Shopify API limits" page
  (SH-2); corrected to the REST Admin API rate-limits page (SH-1) in this
  document, and the "roughly" hedge removed since the figure is exact.
- **Adversarial verification:** The 2023 changelog's Advanced-plan GraphQL
  figure (100 points/second) is stale/superseded by the current page's 200
  points/second for the same tier; flagged in this document rather than
  presented as current.
- **Adversarial verification:** The `Shopify-GraphQL-Cost-Debug=1` header,
  originally removed as unconfirmed, is actually verifiable on the already-
  cited "Shopify API limits" page — noted above; not promoted to a load-
  bearing fact in this document as it is outside Task 006A's scope.

### Odoo cron/transaction model

- **Self-review:** An initial web-search summary suggested Odoo uses `FOR
  UPDATE NOWAIT`; the actual source uses `SKIP LOCKED` and explicitly rejects
  `NOWAIT` — the NOWAIT claim was dropped rather than reported as fact.
- **Self-review:** Considered stating flatly "Odoo automatically retries cron
  jobs on concurrent-update conflicts" — only verified for the separate
  RPC/ORM call-dispatch path (`service/model.py`'s `retrying()`), not for
  `ir_cron.py`'s own job-acquisition path, which skips-and-moves-on instead;
  reported as two separate, non-merged facts.
- **Self-review:** Considered asserting a specific meaning for the docs'
  "hard-limit… at the database level" cron-kill statement (e.g. equating it to
  `--limit-time-real`) — no fetched source confirmed this mapping; left as an
  open question.
- **Self-review:** Considered stating `_notify_admin`'s deactivation notice is
  sent by email — the actual source shows it is a log-only warning by
  default, with no messaging channel; corrected and reported as log-only.
- **Adversarial verification:** Two trivial verbatim-fidelity issues (a silent
  typo "correction" in a quoted `actions.html` code comment — "stategy" →
  "strategy" — and a missing space silently added in a `service/model.py`
  docstring quote) were found; neither changes any claim's substance and
  neither is reproduced as an exact quote in this document.

### Idempotency keys

- **Self-review:** Considered stating "a hash of request parameters plus
  target resource" as a commonly-recommended key-composition pattern —
  removed because the one source discussing this tradeoff (AWS Builders'
  Library) explicitly favors explicit caller-supplied tokens over hash-derived
  ones, and no other source endorsed hashing as recommended practice.
- **Self-review:** Considered asserting the "external-id + operation-type" key
  composition pattern (named in the original task brief) as a documented
  industry pattern — it did not appear in any fetched primary source; logged
  as an open question instead.
- **Self-review:** Considered claiming interoperability/cross-referencing
  between Stripe's implementation and the IETF draft — neither source
  references the other; no citable link was established, so none was claimed.
- **Self-review:** Considered generalizing "most cloud vendors recommend a
  24-hour TTL" as a single industry-wide figure — only Stripe documents a
  fixed 24-hour window; AWS ties TTL to resource lifetime, and the IETF draft
  leaves duration to the resource owner; the generalization was not made.
- **Adversarial verification:** The "processed exactly once" AWS quote was
  misattributed to the Builders' Library essay; it actually opens the
  Well-Architected Framework page — corrected in this document.
- **Adversarial verification:** "ECS `RunTask`" was attached to the Builders'
  Library citation for the client-token design choice, but that essay never
  mentions ECS `RunTask` (only EC2 `RunInstances`) — corrected in this
  document to cite only the EC2 example.
- **Adversarial verification:** A parenthetical gloss on the Stripe
  concurrent-request fact ("because no endpoint has finished executing") did
  not match the meaning of its own cited quote ("no API endpoint initiates the
  execution") — reworded in this document for internal consistency.
- **Adversarial verification:** The IETF composite-key mitigation was
  described as combining "attributes known only to the resource," implying a
  secrecy property the source does not assert (it says "other client specific
  attributes," not that they are secret) — softened in this document.

### Retry and backoff

- **Self-review:** A claim that Shopify's documented fallback wait-time
  formula (absent a `Retry-After` header) is exactly "Wait Time =
  2^RetryCount" seconds appeared only in an AI-generated web-search summary
  drawing on secondary/third-party blogs, not Shopify's own site — not stated
  as fact.
- **Self-review:** Any specific claim about the content of the AWS Builders'
  Library article "Timeouts, retries, and backoff with jitter" (GEN-9) — the
  fetch returned no extractable article text in either research pass; nothing
  beyond its title/related-document listing was verified or asserted.
- **Self-review:** A general claim that "most production HTTP client
  libraries implement Full Jitter by default" — plausible but unverified; no
  fetched source supported it, so it was omitted.
- **Self-review:** A single, precise, current numeric value for Shopify's REST
  leaky-bucket size/leak rate stated as unconditionally settled fact — the two
  fetched Shopify pages produced summaries not perfectly reconcilable with
  each other (an illustrative "60 marbles" example vs. a stated default of "40
  requests, 2/s leak"); downgraded to an open question rather than a firm
  fact where ambiguous.
- **Adversarial verification:** The Equal Jitter formula
  (`base + random(0, min(cap, base * 2^attempt))`) was inaccurate; corrected
  to `temp/2 + random(0, temp/2)` in this document (see Retry and backoff
  notes).
- **Adversarial verification:** The claim that "Full Jitter and Equal Jitter
  produced similar call counts" overreached the source, which describes Equal
  Jitter as "the loser," doing more work and taking longer than Full Jitter —
  corrected in this document.

### Dead-letter / permanent failure

- **Self-review:** Considered stating "most production incidents caused by DLQ
  mishandling stem from alert fatigue" as general fact — no fetched source
  quantifies this; not stated as fact.
- **Self-review:** Considered asserting a specific industry-standard DLQ
  triage SLA (e.g. "triage within 24 hours, escalate after 72") as a
  documented norm — this figure appeared only in secondary blog commentary,
  not in any AWS/Azure/RabbitMQ primary source; not generalized into a
  vendor-endorsed standard.
- **Self-review:** Considered claiming DLQs are the standard mechanism for
  detecting duplicate message processing — not supported by any fetched
  source; removed.
- **Self-review:** Considered asserting that GDPR, PCI-DSS, or similar regimes
  specifically require encrypting/redacting dead-lettered payloads — no
  primary regulatory or vendor compliance source was fetched to substantiate
  this; left as an open question.
- **Adversarial verification:** The "patterns" claim that dead-lettering is
  triggered by retry-exhaustion "not by a single failed attempt" was
  self-contradictory and overreached AWS's own `maxReceiveCount=1` example and
  RabbitMQ's single-rejection trigger — corrected in this document (see
  Dead-letter notes).
- **Adversarial verification:** A fact stating the AWS redrive workflow
  "requires an investigation step… before initiating a redrive" overstated a
  source that frames review as optional — corrected in this document.
- **Adversarial verification:** A "direct quote" from the AWS redrive blog
  ("Previously, recovering failed messages required…") silently substituted
  an anaphoric "this" with an explanatory phrase while keeping quotation marks
  — this document does not reproduce that quote verbatim; only the underlying,
  supported gist is used.
- **Adversarial verification:** A risk bullet blended two distinct AWS Lambda
  CloudWatch metric names (`DeadLetterErrors`, DLQ-specific, vs.
  `DestinationDeliveryFailures`, a different, general-destinations metric) as
  if interchangeable — corrected in this document to name only
  `DeadLetterErrors` for the DLQ-delivery-failure case.

### Duplicate-running prevention

- **Self-review:** "Odoo scheduled actions are guaranteed by the framework to
  be idempotent" — the only source found (Odoo.sh FAQ) states this as
  developer-facing **advice**, not a framework-enforced runtime guarantee; not
  stated as fact.
- **Self-review:** "ir.cron's locking mechanism fully prevents duplicate
  execution in every Odoo 19 deployment topology (single-worker, multi-worker,
  multi-server/load-balanced, Odoo.sh)" — a runtime-behavior claim source-
  reading alone cannot establish; moved to open questions (see Duplicate-
  running notes above).
- **Self-review:** "PostgreSQL's SKIP LOCKED feature was designed by the
  PostgreSQL project specifically for queue/job-processing use cases" — this
  framing is common in secondary blogs, but the primary PostgreSQL docs
  fetched do not state a design-intent claim in those words; only Odoo's own
  documented *use* of SKIP LOCKED for that purpose was kept as fact.
- **Self-review:** "Session-level PostgreSQL advisory locks are a known source
  of production bugs with connection pooling" — no fetched source directly
  documents this as an observed failure mode; downgraded to a clearly-reasoned
  inference rather than asserted as fact.
- **Self-review:** Any specific recommendation about which Odoo model, table,
  or locking primitive a future connector should use for its own duplicate-
  prevention logic — explicitly out of scope per the task's no-architecture,
  no-model-naming rule; no such claim was made, even as an inference.
- **Adversarial verification:** None — this topic's verification pass returned
  `claims_to_remove_or_downgrade: []` and an overall verdict of "clean."

### Checkpoint/resume

- **Self-review:** "Shopify GraphQL cursors are guaranteed stable across pages
  even when records are added or removed mid-pagination" — the fetched
  GraphQL pagination/`PageInfo` reference pages are silent on this; moved to
  open questions rather than asserted as fact.
- **Self-review:** "Azure Data Factory does not support restart from point of
  failure" — this stale claim appeared in older secondary community Q&A
  snippets; a direct fetch of the current official page shows a "Rerun from
  failed activity" feature exists today; the stale claim was removed.
- **Self-review:** A GitHub issue in a third-party open-source CRM repo,
  surfaced by a search for "GitHub REST API cursor pagination," was considered
  as an illustrative cursor-pagination bug example, but it describes a bug in
  that product's own API, not GitHub's platform API — citing it under a
  "GitHub API" framing would have been a misattribution; dropped entirely.
- **Self-review:** "Shopify's GraphQL cursors expire after a fixed period if
  persisted across process restarts" — no such statement was found for the
  GraphQL Admin API specifically (only REST's general "don't save for later"
  caution was found); left unstated rather than asserted by extrapolation.
- **Self-review:** "Using `query:\"updated_at:>X\"` plus `sortKey:UPDATED_AT`
  is Shopify's officially recommended pattern for resumable incremental sync"
  — this composite approach is only supported by combining separately-
  documented features plus a community-forum quoting-syntax thread; not found
  as a named, endorsed Shopify pattern; presented only as this document's own
  inference (see Checkpoint/resume notes), not a fact.
- **Adversarial verification:** A specific SQL `WHERE`-clause string quoted
  from the Shopify Engineering "Pagination with Relative Cursors" article
  could not be verified on two independent re-fetches and appears to be
  fabricated — removed from this document (see Checkpoint/resume notes).
- **Adversarial verification:** The "patterns" section's phrase describing
  Shopify Engineering's mechanism as literally filtering on `"last seen key >
  X"` implied it echoed source syntax it does not contain — softened to a
  narrative paraphrase in this document.
- **Adversarial verification:** A Shopify "actual cost" quote silently dropped
  the source's trailing clause ("…due to the actual objects returned") without
  an ellipsis — this document paraphrases rather than quotes that sentence to
  avoid the same issue.

### Observability/redaction

- **Self-review:** Considered stating as fact that "Shopify's documentation
  explicitly instructs developers never to log the client secret" — the
  fetched client-secrets page did not contain that exact sentence; only
  general rotation-cadence language was confirmed, so this was not asserted
  as a direct-quote fact.
- **Self-review:** Considered stating "GDPR requires masking/redaction of PII
  specifically in application logs" as a direct requirement — Article 5's
  text states general principles and does not mention "logs" by name; the
  logging-specific framing was removed, and only the verified general-
  principle wording was kept (see Observability/redaction notes above).
- **Self-review:** Considered citing a specific figure for a "typical/required
  log retention period" for compliance purposes — no fetched source gave a
  verifiable general or Odoo/Shopify-specific retention duration; no number
  was asserted.
- **Self-review:** Considered treating NIST SP 800-122's PII confidentiality-
  impact levels as directly applicable to this connector's design — that
  scheme is written for US federal information systems, not commercial
  SaaS/ERP integrations; no claim of direct applicability was made.
- **Self-review:** Considered asserting that OWASP MASWE-0001's mobile-
  specific guidance generalizes cleanly to a server-side Odoo/Shopify sync
  engine — MASWE-0001 is scoped to mobile apps; kept as a lower-confidence,
  clearly-scoped fact rather than generalized into a broader claim.
- **Adversarial verification:** The Odoo 19.0 "store the API key as carefully
  as the password" quote was attributed to the wrong page/URL ("External
  JSON-2 API" instead of "External RPC API") — corrected in this document
  (see Observability/redaction notes and OD-10 above).

---

## Handoff

- **Branch:** `claude/task-006a-queue-idempotency-research-87cawb`
- **Files changed:** `docs/01-research/sync-engine-queue-idempotency-source-notes.md`
  (this file only — no other file was created, modified, or touched).
- **Top findings (high-confidence, cross-topic):**
  1. Every general-purpose retry source examined (AWS, Google SRE, Azure) and
     `queue_job`'s own source code independently converge on the same shape:
     bounded retries + exponential backoff + randomized jitter, with unbounded
     retries treated as a documented anti-pattern everywhere, not a neutral
     default (`OCA-3`, `OCA-6`, `GEN-10`, `GEN-12`, `GEN-15`).
  2. Shopify's REST and GraphQL Admin APIs signal throttling in **structurally
     different** ways — REST returns HTTP 429 + `Retry-After`; a throttled
     GraphQL call can return **HTTP 200** with a `THROTTLED` code in the body
     — so a client that only branches on HTTP status will silently mis-handle
     GraphQL throttling (`SH-1`, `SH-4`).
  3. `queue_job`'s `identity_key` deduplication only blocks creation of a
     duplicate while an equivalent job is in a **non-terminal** state
     (`wait_dependencies`/`pending`/`enqueued`) — a job already `started` does
     **not** block a duplicate, so identity-key dedup alone would be an
     incomplete guarantee against re-delivered webhooks without additional
     application-level idempotency (`OCA-6`).
  4. Idempotency-key mechanics converge across vendors (Stripe, AWS, the IETF
     draft) on the same store-and-replay shape, but the vendors **disagree**
     on how to handle a concurrent, still-in-flight duplicate request (IETF:
     HTTP 409; Stripe: don't cache, tell the client to retry) — there is no
     single universal behavior to assume here (`GEN-1`, `GEN-3`).
  5. Odoo 19's cron-job acquisition path (`ir_cron.py`) and its separate
     RPC/ORM call-dispatch retry path (`service/model.py`'s `retrying()`) use
     **two different concurrency-conflict philosophies** in the same codebase
     — cron acquisition skips-and-moves-on with no retry, while RPC dispatch
     retries with exponential backoff up to 5 times. Assuming cron jobs get
     the RPC layer's retry-with-backoff behavior "for free" would be wrong
     (`OD-1`, `OD-5`).
  6. Every dead-letter implementation examined (SQS, Azure Service Bus,
     RabbitMQ) treats visibility as an **opt-in, separately-configured**
     alarm/metric, not a default push notification — a DLQ or failed-job
     state with no alarm wired up provides no visibility guarantee by itself
     (`GEN-19`, `GEN-25`).
  7. Shopify's own bulk-operations mechanism — the documented path for
     large-volume data — is **not resumable at the API level**: a failed or
     canceled bulk operation must be resubmitted in full, with only a
     separate, time-limited `partialDataUrl` recovering rows already produced
     (`SH-14`, `SH-15`).
  8. Two "direct quotes" from the original research draft did not survive
     adversarial re-verification and are corrected/removed in this document:
     an inaccurate AWS Equal Jitter formula (`GEN-8`) and a fabricated SQL
     snippet attributed to a Shopify Engineering blog post (`SH-17`) — both
     are exactly the kind of specific, copy-pasteable detail that would be
     dangerous to carry forward uncorrected.
- **Weak/uncertain areas (consolidated open questions worth a reviewer's
  attention):**
  - Whether Odoo 19's `FOR NO KEY UPDATE SKIP LOCKED` cron-acquisition
    mechanism actually prevents duplicate execution under real multi-worker,
    multi-process, and multi-server (load-balanced) deployments has **only**
    been confirmed by reading source/doc comments, not by an actual
    concurrency test — flagged explicitly by the underlying research itself
    as needing runtime proof.
  - Whether Shopify's GraphQL Admin API ever exposes a `Retry-After`-
    equivalent signal for `THROTTLED` responses, versus relying solely on a
    client-derived wait time from `throttleStatus`, is unconfirmed either way.
  - Whether a persisted GraphQL `after` cursor remains valid/safe to reuse
    after a long-delayed resume (hours/days) is undocumented; only REST's
    general "don't save for later" caution was found, with no stated
    equivalent (or its absence) for GraphQL.
  - Whether OCA `queue_job`'s 19.0 branch is maintained at the same cadence
    and quality bar as older branches was not established (only structural/
    manifest parity was confirmed).
  - Which regulatory regime(s) (GDPR, US state privacy law, others) actually
    govern a given merchant's synchronized customer data depends on
    deployment/customer geography and was out of scope for this pass.
  - No fetched source addresses PII/secret handling specifically in the
    context of *webhook payload logging* (as opposed to general API/app
    logging) — flagged as worth a dedicated follow-up given how central
    webhooks are expected to be to a Shopify-side sync engine.
- **Exact next step:** ChatGPT review / later synthesis into architecture
  decisions (no architecture decision is made by this document; this document
  does not authorize implementation).
