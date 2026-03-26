# 4) Workflow Optimization

## Clean Execution Flow

1. **Architecture framing (A1)**
   - Produce/update integration decision log.
   - Confirm sync model, ownership boundaries, and data contracts.

2. **Slice planning (A1 + A2 + A3)**
   - Define vertical slice (e.g., product sync, order import, fulfillment updates).
   - Lock acceptance criteria and idempotency keys before coding.

3. **Implementation (A2 + A3)**
   - Build service/controller/job code.
   - Implement deterministic mapping + upsert keys.

4. **Security gate (A5)**
   - Validate webhook auth, secret usage, and replay defense before merge.

5. **Quality/performance gate (A4)**
   - Run test matrix and performance checks.
   - Block merge on idempotency or query regressions.

6. **Release readiness (A6)**
   - Verify environment variables, migration scripts, observability, and rollback.

7. **Deploy & monitor (A6)**
   - Deploy to Odoo.sh staging → prod with post-deploy checks.

## Friction Removed

- No duplicate approvals by multiple agents for the same concern.
- No “documentation-only” blocking steps.
- Security and performance are mandatory but lightweight gates.

## Mandatory Artifacts per PR

- Updated mapping contract (if fields changed).
- Test evidence for changed flow.
- Security checklist tick-off for webhook/API changes.
- Operational note (monitoring/rollback impact).
