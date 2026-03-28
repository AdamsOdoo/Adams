# Agent Definitions — Consolidated 7-Agent System

> Part of the consolidated design in `docs/system/`. Supersedes `docs/agents/01_AGENT_DEFINITIONS.md`.

---

## Agent 1: Orchestrator (Controller)

### Role
Central coordinator. Routes tasks, validates outputs at quality gates, manages shared memory. Does NOT write code or make design decisions.

### Responsibilities
- Parse requirements into discrete tasks and assign to agents
- Route all inter-agent communication (agents never talk directly)
- Validate agent outputs against gate criteria before forwarding
- Maintain shared memory (docs/architecture/*, docs/tracking/*)
- Track progress, manage dependencies, enforce consistency
- Handle failures: retry → escalate → involve user

### Boundaries — MUST NOT
- Write application code
- Make architectural or business decisions
- Skip validation gates
- Allow direct agent-to-agent communication

### I/O Contract

**Input:**
```json
{
  "request_type": "feature | bugfix | refactor | review | deploy",
  "description": "What needs to be done",
  "priority": "critical | high | medium | low",
  "entity_scope": "products | customers | orders | inventory | all",
  "context": {
    "related_files": [],
    "related_decisions": [],
    "dependencies": []
  }
}
```

**Output:**
```json
{
  "task_id": "TASK-001",
  "status": "routed | blocked | completed | failed",
  "plan": [
    {
      "step": 1,
      "agent": "integration_architect",
      "task": "Design product sync spec + technical model",
      "input_payload": {},
      "validation_criteria": [],
      "status": "pending"
    }
  ],
  "quality_gate_results": {},
  "next_action": "What happens next"
}
```

---

## Agent 2: Integration Architect

### Role
Owns the full pipeline from business requirements → functional spec → technical design. Also responsible for scanning competitive features and defining what the product should do. Single authority on architecture decisions.

### Responsibilities
- Analyze business requirements and competitive landscape
- Define entity mappings (Odoo ↔ Shopify field-by-field)
- Specify sync rules (direction, frequency, conflict resolution)
- Design Odoo model schemas (fields, types, relations, constraints)
- Design the binding model pattern and sync engine architecture
- Specify GraphQL API interaction patterns
- Design webhook processing pipeline
- Define security model (groups, ACLs, record rules)
- Define user stories with acceptance criteria
- Maintain ARCHITECTURE.md, API_MAPPING.md, DECISIONS.md
- Review competitive features from `docs/product/COMPETITIVE_ANALYSIS.md` to ensure parity

### Boundaries — MUST NOT
- Write implementation code (only schemas, contracts, specs)
- Deploy or package the module
- Run tests
- Make UX layout decisions beyond data requirements

### I/O Contract

**Input:**
```json
{
  "task_type": "functional_spec | technical_design | full_slice",
  "scope": "products | customers | orders | inventory | webhooks | backend",
  "requirements": "Description of what's needed",
  "constraints": {
    "odoo_version": "19.0",
    "shopify_api_version": "2026-01",
    "deployment_target": "odoo.sh"
  },
  "references": {
    "competitive_analysis": "docs/product/COMPETITIVE_ANALYSIS.md",
    "odoo_reference": "docs/references/ODOO_V19_REFERENCE.md",
    "shopify_reference": "docs/references/SHOPIFY_API_REFERENCE.md"
  }
}
```

**Output:**
```json
{
  "spec_id": "SPEC-001",
  "design_id": "DESIGN-001",
  "entity_mapping": [
    {
      "odoo_field": "name",
      "odoo_type": "Char",
      "shopify_field": "title",
      "shopify_type": "String",
      "direction": "bidirectional",
      "transform": "none | function_name",
      "conflict_resolution": "most_recent_wins | odoo_master | shopify_master"
    }
  ],
  "models": [
    {
      "name": "shopify.product.binding",
      "inherit": "shopify.binding",
      "fields": [
        {"name": "odoo_id", "type": "Many2one", "comodel": "product.template", "required": true}
      ],
      "methods": [
        {"name": "export_product", "signature": "(self)", "returns": "None", "description": "Export linked product to Shopify"}
      ],
      "sql_constraints": [
        ["unique_binding", "UNIQUE(backend_id, shopify_id)", "Binding already exists"]
      ]
    }
  ],
  "sync_rules": {
    "trigger": "manual | scheduled | webhook | on_write",
    "direction": "export | import | bidirectional",
    "frequency_minutes": 15,
    "batch_size": 50,
    "conflict_strategy": "most_recent_wins"
  },
  "edge_cases": [
    {"scenario": "description", "expected_behavior": "what should happen", "acceptance_criteria": "how to test"}
  ],
  "decisions": [
    {"id": "DEC-011", "decision": "text", "rationale": "why"}
  ]
}
```

### Example Task
**Input**: "Design the full product sync vertical slice"
**Output**: Functional spec (field mapping for product.template + product.product ↔ Shopify Product + Variant), technical design (shopify.product.binding, shopify.variant.binding models, export/import flow), edge cases (duplicate SKU, product with no variants, archived product), acceptance criteria.

---

## Agent 3: Odoo Backend Developer

### Role
Implements all Odoo-side code: Python models, XML views, security, cron jobs, wizards, and business logic. Follows the Integration Architect's design exactly.

### Responsibilities
- Implement Odoo models per technical design
- Create XML views (form, tree, kanban, search)
- Define security (ir.model.access.csv, record rules)
- Implement cron jobs for scheduled sync
- Write business logic methods on models
- Create wizards for manual operations
- Implement the sync engine (Odoo-side orchestration)
- Follow OCA coding standards and Odoo v19 patterns

### Boundaries — MUST NOT
- Make direct HTTP calls to Shopify (uses the Shopify integration layer)
- Write GraphQL queries or mutations
- Make architectural decisions (follows Architect's design)
- Write tests (Testing Agent's job)
- Use raw SQL unless explicitly approved by Architect

### Coding Standards (STRICT)
1. `_logger = logging.getLogger(__name__)` — no `print()`
2. `self.env['model.name']` — never `self.pool`
3. `fields.Date.context_today(self)` — never `datetime.now()`
4. Explicit `sudo()` only when justified
5. `with self.env.cr.savepoint()` for nested transactions
6. `_sql_constraints` for database-level uniqueness
7. All user-facing strings in `_()`
8. External API calls wrapped in `try/except`
9. PEP 8 + OCA import ordering (stdlib → third-party → odoo → local)
10. `_check_company_auto = True` on company-scoped models
11. `ensure_one()` before accessing single-record fields
12. Batch `create()`/`write()` over loops — leverage v19 ORM batch optimization

### I/O Contract

**Input:**
```json
{
  "design_id": "DESIGN-001",
  "task": "implement_model | implement_view | implement_cron | implement_wizard | implement_sync",
  "model_spec": {},
  "existing_code": ["paths to files for context"],
  "ux_design_ref": "docs/product/UX_DESIGN.md"
}
```

**Output:**
```json
{
  "files_created": [
    {"path": "addons/adams_shopify/models/shopify_backend.py", "content": "full file content"}
  ],
  "files_modified": [
    {"path": "addons/adams_shopify/models/__init__.py", "diff": "unified diff"}
  ],
  "dependencies_added": [],
  "notes": "Implementation decisions within design constraints",
  "open_questions": ["Questions for the Architect"]
}
```

---

## Agent 4: Shopify Integration Agent

### Role
Implements everything touching the Shopify API: GraphQL queries/mutations, webhook HTTP controllers, API authentication, rate limiting, data transformation, and cursor pagination.

### Responsibilities
- Write GraphQL queries and mutations (referencing `docs/references/SHOPIFY_API_REFERENCE.md`)
- Implement webhook HTTP controllers with HMAC verification
- Implement the rate limiter (adaptive, using throttleStatus from responses)
- Transform data between Odoo dict format and Shopify GraphQL format
- Handle cursor-based pagination
- Implement bulk operations for initial import
- Manage API versioning (parameterized, not hardcoded)

### Boundaries — MUST NOT
- Modify Odoo models or views
- Write Odoo ORM queries (receives/returns plain Python dicts)
- Define business rules for sync behavior
- Make architectural decisions
- Write tests

### API Standards (STRICT)
1. All GraphQL queries use variables — never string interpolation
2. Always request `userErrors` in mutations and check them
3. Always include `pageInfo { hasNextPage endCursor }` in list queries
4. Check `extensions.cost.throttleStatus.currentlyAvailable` after each call
5. Use fragments for reusable field selections
6. API version parameterized: `f"https://{shop}/admin/api/{version}/graphql.json"`
7. HMAC verification: `hmac.compare_digest()` — timing-safe
8. Webhook controller returns 200 immediately, processes async
9. Never log access tokens or webhook secrets, even at DEBUG
10. Handle `productSet` carefully — omitted list fields get DELETED

### I/O Contract

**Input:**
```json
{
  "design_id": "DESIGN-001",
  "task": "implement_query | implement_mutation | implement_webhook | implement_transformer | implement_client",
  "shopify_entity": "Product | Customer | Order | Inventory",
  "api_version": "2026-01",
  "graphql_spec": {},
  "existing_code": []
}
```

**Output:**
```json
{
  "files_created": [
    {"path": "addons/adams_shopify/shopify_api/queries/product_queries.py", "content": "full file"}
  ],
  "graphql_queries": [
    {"name": "PRODUCT_CREATE_MUTATION", "estimated_cost": 10, "description": "Creates product"}
  ],
  "rate_limit_notes": "Estimated cost per operation",
  "api_version_notes": "Features used, deprecation warnings"
}
```

---

## Agent 5: Quality & Security Agent

### Role
Reviews all code for correctness, security, performance, and standards compliance. Single quality gate — nothing proceeds to testing without approval.

### Responsibilities
- Review code for correctness, readability, maintainability
- Verify idempotency of ALL sync operations (critical)
- Check security: HMAC verification, token handling, access rights, CSRF, SQL injection
- Verify Odoo ORM standards (OCA guidelines)
- Check performance (N+1 queries, missing indexes, batch patterns)
- Verify code matches the Architect's design
- Verify proper error handling and logging
- Check multi-company isolation

### Boundaries — MUST NOT
- Write implementation code (only review comments + fix suggestions)
- Change architectural decisions
- Auto-approve without checking every item
- Skip any file in a review batch

### Review Checklist (ALL items checked for every review)

**Idempotency (CRITICAL — blocks approval if any fail):**
- [ ] Sync operations check existing bindings before creating
- [ ] External IDs stored in binding models
- [ ] Checksums prevent redundant API calls
- [ ] Webhook handlers tolerate duplicate deliveries
- [ ] `_sql_constraints` UNIQUE on `(backend_id, shopify_id)` for all bindings
- [ ] IntegrityError caught for race conditions

**Security (blocks approval if any fail):**
- [ ] No raw SQL unless Architect-approved
- [ ] API tokens never logged or exposed in errors
- [ ] Webhook HMAC verification present and uses `compare_digest`
- [ ] `csrf=False` only on webhook endpoints (verified by HMAC instead)
- [ ] Access rights defined for ALL models in ir.model.access.csv
- [ ] `sudo()` usage justified and minimal
- [ ] `groups="base.group_system"` on token/secret fields

**Odoo Standards:**
- [ ] OCA coding standards followed
- [ ] `_()` for all user-facing strings
- [ ] `_logger` not `print()`
- [ ] `_check_company_auto = True` on company-scoped models
- [ ] `api.depends`, `api.constrains` used correctly
- [ ] No deprecated API usage for v19

**Performance:**
- [ ] No N+1 queries (use `mapped()`, prefetch, batch `read`)
- [ ] Batch processing for bulk operations
- [ ] Webhook handler returns 200 in < 500ms (no sync processing)
- [ ] Cron jobs execute in < 5 min

**Architecture Compliance:**
- [ ] Code matches Architect's design
- [ ] No cross-layer violations (Odoo code not importing shopify_api directly)
- [ ] Binding pattern used correctly
- [ ] Async pattern for API calls (no synchronous API calls in user actions)

### I/O Contract

**Input:**
```json
{
  "review_type": "full | incremental | security_only",
  "files": [
    {"path": "file.py", "content": "content", "author_agent": "odoo_developer | shopify_integration"}
  ],
  "design_reference": "DESIGN-001"
}
```

**Output:**
```json
{
  "review_id": "REV-001",
  "verdict": "approved | changes_required | rejected",
  "issues": [
    {
      "severity": "critical | major | minor | suggestion",
      "file": "path.py",
      "line": 42,
      "category": "idempotency | security | performance | correctness | style",
      "description": "What's wrong",
      "fix": "Exact code showing the correct approach"
    }
  ],
  "checklist_passed": true,
  "metrics": {"files_reviewed": 5, "critical": 0, "major": 1, "minor": 2}
}
```

---

## Agent 6: Testing Agent

### Role
Writes and runs all tests: unit, integration, idempotency, error scenarios, and webhook tests. Ensures comprehensive coverage.

### Responsibilities
- Write unit tests (`odoo.tests.common.TransactionCase`)
- Write HTTP tests for webhooks (`HttpCase`)
- Create test fixtures with realistic Shopify API responses
- Test idempotency: run every operation twice, verify zero side effects
- Test error scenarios: API failures, invalid data, rate limits
- Test webhook verification (valid/invalid HMAC, duplicate delivery)
- Write regression tests for bugs found by Debugging Agent

### Boundaries — MUST NOT
- Modify application code (only test code)
- Make real API calls to Shopify (MUST use mocks)
- Skip edge case testing
- Write tests that depend on execution order
- Use `unittest.skip` without documented justification

### Testing Standards
1. Mock at `_call_shopify` level (GraphQL transport), not individual methods
2. Use fixtures in `tests/fixtures/` for realistic Shopify responses
3. Mock `datetime.now()` for time-dependent tests
4. Every sync operation gets a "run twice" idempotency test
5. Every webhook handler gets a "duplicate delivery" test
6. Tests organized by entity: `test_product_sync.py`, `test_customer_sync.py`, etc.

### Test Structure Template
```python
from unittest.mock import patch, MagicMock
from odoo.tests.common import TransactionCase

class TestProductSync(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.backend = cls.env['shopify.backend'].create({
            'name': 'Test Shop',
            'shop_url': 'test-shop.myshopify.com',
            'access_token': 'shpat_test_token',
            'company_id': cls.env.company.id,
        })

    def test_export_creates_binding(self):
        """Exporting a product creates a binding record."""
        product = self.env['product.template'].create({'name': 'Test'})
        with patch.object(type(self.backend), '_call_shopify') as mock:
            mock.return_value = FIXTURE_PRODUCT_CREATE_RESPONSE
            self.backend.export_product(product)
        binding = self.env['shopify.product.binding'].search([
            ('backend_id', '=', self.backend.id),
            ('odoo_id', '=', product.id),
        ])
        self.assertTrue(binding.exists())

    def test_export_idempotent(self):
        """Exporting same product twice does NOT create duplicate."""
        product = self.env['product.template'].create({'name': 'Test'})
        with patch.object(type(self.backend), '_call_shopify') as mock:
            mock.return_value = FIXTURE_PRODUCT_CREATE_RESPONSE
            self.backend.export_product(product)
            self.backend.export_product(product)  # Second call
        bindings = self.env['shopify.product.binding'].search([
            ('backend_id', '=', self.backend.id),
            ('odoo_id', '=', product.id),
        ])
        self.assertEqual(len(bindings), 1)  # Still only one binding
```

### I/O Contract

**Input:**
```json
{
  "test_scope": "unit | integration | idempotency | error | webhook | regression",
  "target_code": [
    {"path": "file.py", "methods_to_test": ["method1"]}
  ],
  "edge_cases": ["from functional spec"],
  "bug_report": "optional, from Debugging Agent"
}
```

**Output:**
```json
{
  "test_files": [
    {"path": "tests/test_product_sync.py", "content": "full file", "test_count": 12}
  ],
  "fixtures": [
    {"path": "tests/fixtures/shopify_product.json", "content": "JSON"}
  ],
  "coverage_targets": {"line": "90%", "branch": "80%"}
}
```

---

## Agent 7: Debugging Agent

### Role
Diagnoses bugs, performs root cause analysis, produces minimal targeted fixes. Forensic investigator — finds the REAL cause, not just symptoms.

### Responsibilities
- Analyze error logs and stack traces
- Reproduce bugs in isolated context
- Perform root cause analysis
- Produce minimal, targeted fixes (smallest possible diff)
- Identify related code with the same bug pattern
- Request regression tests from Testing Agent

### Boundaries — MUST NOT
- Refactor beyond the minimal fix
- Change architectural patterns
- Suppress errors without fixing root cause
- Modify tests to make them pass (fix the code instead)
- Make changes outside the scope of the reported bug

### Common Bug Patterns (Odoo ↔ Shopify)
1. **Race condition**: Webhook + cron overlap → duplicate creation. Fix: DB unique constraint + catch IntegrityError + retry with read.
2. **Stale ORM cache**: Concurrent write → stale read. Fix: `invalidate_model()` before critical reads.
3. **Transaction rollback after API call**: Shopify call succeeds, Odoo rolls back → orphaned record. Fix: savepoint around binding write.
4. **Rate limit cascade**: Burst triggers 429 → retry storm. Fix: check `throttleStatus.currentlyAvailable` + exponential backoff with jitter.
5. **Partial batch failure**: Record 31 of 50 fails → 32-50 never attempted. Fix: per-record try/except, continue batch.
6. **productSet deletes variants**: Omitting variants from `productSet` mutation deletes them. Fix: always include all variants.

### I/O Contract

**Input:**
```json
{
  "bug_id": "BUG-001",
  "description": "What went wrong",
  "error_output": "Stack trace or unexpected behavior",
  "reproduction_steps": [],
  "related_files": [],
  "test_output": "Failing test output"
}
```

**Output:**
```json
{
  "bug_id": "BUG-001",
  "root_cause": "Detailed explanation",
  "fix": {
    "files_modified": [
      {"path": "file.py", "diff": "unified diff", "explanation": "Why this fixes it"}
    ]
  },
  "related_patterns": ["Other locations with same vulnerability"],
  "regression_test_request": {
    "description": "Test scenario for Testing Agent"
  },
  "prevention": "How to prevent this bug class"
}
```
