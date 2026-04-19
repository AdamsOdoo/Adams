# Orchestration Workflow & Quality Gates

---

## Workflow: Vertical Slice Development

Each entity (products, customers, orders, inventory) is developed as a complete vertical slice. This means ALL layers (models, API, sync, views, tests) for one entity are completed before moving to the next.

### Slice Order
1. **Backend + Infrastructure** (shopify.backend, shopify.binding, GraphQL client, webhook controller)
2. **Products** (highest customer value, most complex mapping)
3. **Customers** (dependency for orders)
4. **Orders** (depends on products + customers)
5. **Inventory** (depends on products)
6. **Fulfillment** (depends on orders)

---

## Phase Flow per Slice

### Phase 1: Architecture (Integration Architect)
```
Input:  Feature requirement + entity scope
Action: Architect produces functional spec + technical design
Output: Entity mapping, model definitions, sync rules, edge cases
Gate 1: VALIDATE
  □ All fields have direction + transform defined
  □ Binding model has UNIQUE(backend_id, shopify_id)
  □ Idempotency mechanism specified (checksum + constraint)
  □ Retry policy defined
  □ Edge cases have acceptance criteria
  □ No conflicts with existing DECISIONS.md
FAIL → Return to Architect with specific gaps
PASS → Store in ARCHITECTURE.md + API_MAPPING.md, proceed
```

### Phase 2: Parallel Implementation (Odoo Developer + Shopify Agent)
```
Input:  Architect's technical design
Action: Two agents work IN PARALLEL:
  - Odoo Developer: models, views, security, cron, wizard
  - Shopify Agent: GraphQL queries, transformers, webhook handler
Output: Complete file contents for all created/modified files
Gate 2: VALIDATE (per agent, before merging)
  □ All files parse without syntax errors
  □ __init__.py chains complete
  □ All methods from design are implemented
  □ No cross-layer imports (models/ doesn't import shopify_api/)
  □ Odoo Developer didn't write GraphQL
  □ Shopify Agent didn't write ORM queries
FAIL → Return to specific developer with issues
PASS → Merge outputs, proceed to review
```

### Phase 3: Quality Review (Quality & Security Agent)
```
Input:  All code from both developers
Action: Full review against 30+ item checklist
Output: Review verdict + issue list
Gate 3: VALIDATE
  □ Zero CRITICAL issues
  □ Zero MAJOR issues
  □ Full checklist completed (no skipped items)
FAIL (changes_required) → Issues routed to relevant developer
  Developer fixes → re-review (max 3 iterations)
FAIL (rejected) → Escalate to Architect for design review
PASS → Proceed to testing
```

### Phase 4: Testing (Testing Agent)
```
Input:  Approved code + functional spec (for edge cases)
Action: Write + run all test categories
Output: Test files + fixtures + results
Gate 4: VALIDATE
  □ All tests pass
  □ Idempotency test exists for every sync operation
  □ Error scenario tests exist
  □ Webhook tests exist (HMAC valid/invalid, dedup)
  □ All API calls mocked (no real HTTP)
  □ Coverage meets targets (90% line, 80% branch)
FAIL (tests fail) → Route to Debug Loop (Phase 4a)
FAIL (missing coverage) → Return to Testing Agent
PASS → Mark slice as DONE in TASKS.md
```

### Phase 4a: Debug Loop
```
Input:  Failing test + code
Action: Debugging Agent analyzes root cause, produces fix
Flow:
  1. Debugging Agent → root cause + minimal fix
  2. Quality Agent → fast review (fix only)
  3. Testing Agent → adds regression test + re-runs all tests
  4. If still failing → loop (max 5 iterations, then escalate to user)
```

### Phase 5: Packaging (Release Agent — runs after milestone, not per slice)
```
Input:  All completed slices
Action: Update manifest, create migrations, validate structure
Output: Updated __manifest__.py, README.rst, migration scripts
Gate 5: VALIDATE
  □ Manifest has all required fields
  □ All data files in manifest exist
  □ Version number correct
  □ Module installs on fresh database
  □ No import errors
FAIL → Return to Release Agent or relevant developer
PASS → Milestone complete
```

---

## Communication Protocol

### Orchestrator → Agent
```json
{
  "to_agent": "odoo_developer",
  "task_id": "TASK-020",
  "task_type": "implement_model",
  "input": { "design_id": "DESIGN-001", "model_spec": {} },
  "context": {
    "architecture": "docs/architecture/ARCHITECTURE.md",
    "ux_design": "docs/product/UX_DESIGN.md",
    "existing_code": ["addons/adams_shopify/models/__init__.py"]
  },
  "constraints": {
    "must_follow_design": "DESIGN-001",
    "deadline_phase": "Phase 2"
  }
}
```

### Agent → Orchestrator
```json
{
  "from_agent": "odoo_developer",
  "task_id": "TASK-020",
  "status": "completed | failed | blocked | needs_input",
  "output": {},
  "warnings": ["Non-blocking concerns"],
  "open_questions": ["Questions requiring Architect input"]
}
```

---

## Failure Handling

### Retry Policy
| Failure Type | Max Retries | Action After Max |
|-------------|------------|-----------------|
| Developer code rejected by reviewer | 3 cycles | Escalate to Architect |
| Tests failing after debug fix | 5 iterations | Escalate to user |
| Validation gate failure | 2 re-attempts | Escalate to user |

### Escalation Format
When escalating to the user, provide:
1. What was attempted (all iterations)
2. Agent outputs from each attempt
3. Specific blocker description
4. Suggested manual intervention

### Conflict Resolution
When agents disagree:
- Architecture conflicts → Architect decides (final authority)
- Implementation approach → Quality Agent breaks the tie
- All resolutions logged in DECISIONS.md

### State Recovery
If workflow is interrupted:
1. Check TASKS.md for last completed step
2. Resume from last completed validation gate
3. Do not re-execute completed phases

---

## Mandatory Artifacts per PR / Merge

| Artifact | Required When | Owner |
|----------|--------------|-------|
| Updated API_MAPPING.md | Field mapping changed | Architect |
| Updated DECISIONS.md | Any design decision made | Architect |
| Updated TASKS.md | Task status changed | Orchestrator |
| Test evidence | Any code change | Testing Agent |
| Security checklist | Webhook/API changes | Quality Agent |
| Migration script | Schema changes | Release Agent |
| Updated UX_DESIGN.md | View/menu changes | Orchestrator |
