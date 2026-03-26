# 2) Optimized Agent Structure

## Final Balanced Agent List

## A1. Integration Architect Agent
**Role**: Own end-to-end technical blueprint and boundaries.

**Responsibilities**
- Define module boundaries (`shopify_core`, `shopify_webhook`, `shopify_sync`, etc.).
- Define sync strategy (event-driven + scheduled reconciliation).
- Define error taxonomy and retry policy boundaries.
- Approve contract changes between agents.

**Should NOT do**
- Implement low-level business mapping code.
- Write full test suites.
- Own deployment playbooks.

---

## A2. Odoo Domain Builder Agent
**Role**: Implement Odoo models/services/jobs/controllers following architecture contracts.

**Responsibilities**
- Build ORM models and service classes.
- Implement queue jobs / cron orchestration.
- Implement GraphQL client wrappers and business flows.
- Keep module coding conventions consistent.

**Should NOT do**
- Redefine architecture decisions ad hoc.
- Modify security policy without Security Agent sign-off.

---

## A3. Mapping & Idempotency Agent
**Role**: Own cross-system data contracts and duplicate-prevention logic.

**Responsibilities**
- Define field-level mapping specs (Shopify ↔ Odoo).
- Implement external ID strategy and upsert keys.
- Implement idempotent processing keys per webhook/event/order.
- Define conflict-resolution policy.

**Should NOT do**
- Own transport-level webhook signature validation.
- Own deployment/release execution.

---

## A4. QA & Performance Agent
**Role**: Guarantee correctness, non-regression, and throughput under realistic load.

**Responsibilities**
- Define and maintain test matrix (unit/integration/contract).
- Stress-test import/sync paths and query footprints.
- Detect ORM anti-patterns and N+1 issues.
- Validate retry and backoff behavior.

**Should NOT do**
- Introduce business logic changes except minimal testability refactor suggestions.

---

## A5. Security & Compliance Agent
**Role**: Own security controls and abuse/failure mode mitigation.

**Responsibilities**
- Webhook signature validation policy.
- Secrets handling policy for Odoo.sh.
- Least-privilege access and log redaction requirements.
- Input validation and replay attack protections.

**Should NOT do**
- Author primary business mapping logic.

---

## A6. Release & Operations Agent
**Role**: Productionization, observability, rollout safety.

**Responsibilities**
- Odoo.sh deployment flow and environment config checks.
- Structured logging, metrics, and alerting definition.
- Migration and rollback checklist ownership.
- Runbook maintenance.

**Should NOT do**
- Change data model semantics without architect review.

## Why this is optimal

- Covers all critical domains without duplicating ownership.
- Keeps only one agent per high-risk responsibility area.
- Avoids fragmentation into too many “micro-agents”.
