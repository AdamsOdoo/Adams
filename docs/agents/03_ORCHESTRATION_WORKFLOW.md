# Orchestration Workflow

## Step-by-Step: Idea → Production

### Phase 1: Requirements Analysis
```
Step 1.1: User submits a feature request to the Orchestrator
Step 1.2: Orchestrator parses request into structured task
Step 1.3: Orchestrator routes to Solution Architect
Step 1.4: Solution Architect produces functional specification
Step 1.5: Orchestrator VALIDATES:
         - All entity mappings have direction and transform rules
         - All sync rules specify conflict resolution
         - All edge cases have expected behavior defined
         - All user stories have acceptance criteria
Step 1.6: Orchestrator stores spec in shared memory (docs/architecture/API_MAPPING.md)
Step 1.7: Orchestrator appends decisions to DECISIONS.md
```

### Phase 2: Technical Design
```
Step 2.1: Orchestrator routes functional spec to Technical Architect
Step 2.2: Technical Architect produces technical design
Step 2.3: Orchestrator VALIDATES:
         - All models have field definitions with types
         - Binding models exist for every synced entity
         - Idempotency mechanism defined (checksum + unique constraint)
         - Retry policy specified
         - Security model defined (access rights + record rules)
         - Module dependencies declared
Step 2.4: Orchestrator stores design in shared memory (docs/architecture/ARCHITECTURE.md)
Step 2.5: Orchestrator creates subtasks for developer agents
```

### Phase 3: Parallel Development
```
Step 3.1: Orchestrator routes Odoo-side tasks to Odoo Backend Developer
Step 3.2: Orchestrator routes Shopify-side tasks to Shopify Integration Agent
         (Steps 3.1 and 3.2 run IN PARALLEL)
Step 3.3: Each developer produces code files
Step 3.4: Orchestrator VALIDATES per developer:
         - All files are syntactically valid
         - __init__.py chains are complete
         - No cross-layer violations detected
         - All methods from technical design are implemented
Step 3.5: Orchestrator merges outputs and checks for integration issues
```

### Phase 4: Code Review
```
Step 4.1: Orchestrator sends ALL code (both agents' output) to Code Reviewer
Step 4.2: Code Reviewer performs full review against checklist
Step 4.3: Orchestrator evaluates review verdict:
         - APPROVED → proceed to Phase 5
         - CHANGES_REQUIRED → route issues back to relevant developer (Phase 3 restart for specific files)
         - REJECTED → route to Technical Architect for design review
Step 4.4: If changes required, developer fixes → re-review (max 3 iterations)
Step 4.5: After 3 failed reviews, escalate to user
```

### Phase 5: Testing
```
Step 5.1: Orchestrator sends approved code + functional spec to Testing Agent
Step 5.2: Testing Agent writes tests (unit, integration, idempotency, error, webhook)
Step 5.3: Orchestrator VALIDATES test output:
         - All edge cases from spec have corresponding tests
         - Idempotency tests exist for every sync operation
         - Error scenarios tested
         - No real API calls (all mocked)
Step 5.4: Orchestrator runs tests (or delegates to Testing Agent to verify)
Step 5.5: If tests PASS → proceed to Phase 6
Step 5.6: If tests FAIL → route to Debugging Agent (Phase 5.5a)
```

### Phase 5.5a: Debug Loop
```
Step 5.5a.1: Orchestrator sends failing test + code to Debugging Agent
Step 5.5a.2: Debugging Agent produces root cause analysis + fix
Step 5.5a.3: Orchestrator routes fix to Code Reviewer (fast review — fix only)
Step 5.5a.4: Code Reviewer approves fix
Step 5.5a.5: Orchestrator routes regression test request to Testing Agent
Step 5.5a.6: Return to Phase 5, Step 5.4 (re-run tests)
Step 5.5a.7: Max 5 debug iterations, then escalate to user
```

### Phase 6: Packaging & Deployment Prep
```
Step 6.1: Orchestrator routes to DevOps/Packaging Agent
Step 6.2: DevOps Agent validates module structure
Step 6.3: DevOps Agent updates __manifest__.py, creates migration scripts if needed
Step 6.4: DevOps Agent produces deployment checklist
Step 6.5: Orchestrator VALIDATES:
         - Module installs on clean database (or simulates check)
         - All files referenced in manifest exist
         - Version number is correct
         - Dependencies are declared
Step 6.6: Orchestrator marks milestone as COMPLETE
```

### Phase 7: Integration Testing & Release
```
Step 7.1: Full regression test suite run
Step 7.2: Orchestrator compiles release notes from DECISIONS.md and TASKS.md
Step 7.3: DevOps Agent produces final package
Step 7.4: User reviews and approves for deployment
```

---

## Communication Protocol

### Message Format (Agent → Orchestrator)
```json
{
  "from_agent": "agent_name",
  "task_id": "TASK-001",
  "status": "completed | failed | blocked | needs_input",
  "output": {
    "// Agent-specific output per contract"
  },
  "metadata": {
    "tokens_used": 2500,
    "files_produced": 3,
    "confidence": "high | medium | low",
    "warnings": ["list of non-blocking concerns"]
  }
}
```

### Message Format (Orchestrator → Agent)
```json
{
  "to_agent": "agent_name",
  "task_id": "TASK-001",
  "task_type": "specific task type from agent contract",
  "input": {
    "// Agent-specific input per contract"
  },
  "context": {
    "architecture_ref": "docs/architecture/ARCHITECTURE.md",
    "decisions_ref": "docs/architecture/DECISIONS.md",
    "related_code": ["file paths"],
    "previous_output": "reference to prior agent output if iterating"
  },
  "constraints": {
    "max_files": 10,
    "must_follow_design": "DESIGN-001",
    "deadline_phase": "Phase 3"
  }
}
```

---

## Validation Gate Details

### Gate 1: Spec Validation (after Solution Architect)
| Check | Criteria | Fail Action |
|-------|----------|-------------|
| Completeness | All entities have field mappings | Return to Solution Architect |
| Consistency | No conflicting sync directions | Return to Solution Architect |
| Testability | All acceptance criteria are measurable | Return to Solution Architect |
| Feasibility | All Shopify API capabilities verified | Flag to Technical Architect |

### Gate 2: Design Validation (after Technical Architect)
| Check | Criteria | Fail Action |
|-------|----------|-------------|
| Spec Coverage | All spec entities have model designs | Return to Technical Architect |
| Idempotency | Binding + checksum defined for every synced entity | Return to Technical Architect |
| Security | Access rights defined for every model | Return to Technical Architect |
| Odoo Compat | No deprecated APIs, correct field types | Return to Technical Architect |
| Shopify Compat | API version supported, rate limits handled | Return to Technical Architect |

### Gate 3: Code Validation (after Developers)
| Check | Criteria | Fail Action |
|-------|----------|-------------|
| Syntax | All files parse without errors | Return to developer |
| Completeness | All design methods implemented | Return to developer |
| Imports | __init__.py chains complete | Return to developer |
| No Cross-Layer | Odoo code doesn't import shopify_api directly | Return to developer |

### Gate 4: Review Validation (after Code Reviewer)
| Check | Criteria | Fail Action |
|-------|----------|-------------|
| No Critical Issues | Zero critical severity findings | Return to developer |
| No Major Issues | Zero major severity findings | Return to developer |
| Checklist Complete | All checklist items checked | Return to Code Reviewer |

### Gate 5: Test Validation (after Testing Agent)
| Check | Criteria | Fail Action |
|-------|----------|-------------|
| Coverage | All sync operations have tests | Return to Testing Agent |
| Idempotency Tests | Every sync has run-twice test | Return to Testing Agent |
| All Pass | Zero test failures | Route to Debugging Agent |
| No Real Calls | All API calls mocked | Return to Testing Agent |

### Gate 6: Package Validation (after DevOps Agent)
| Check | Criteria | Fail Action |
|-------|----------|-------------|
| Manifest Valid | All required fields present | Return to DevOps Agent |
| Files Exist | All manifest-referenced files exist | Return to DevOps Agent |
| Version Correct | Follows Odoo version convention | Return to DevOps Agent |
| Install Clean | No import errors, no missing depends | Return to relevant developer |

---

## Failure Handling

### Retry Policy
- Developer tasks: max 3 review cycles, then escalate
- Debug tasks: max 5 iterations, then escalate
- Validation gates: max 2 re-attempts, then escalate

### Escalation Path
1. Agent fails → Orchestrator re-routes with additional context
2. Agent fails again → Orchestrator adds constraints/hints
3. Agent fails third time → Orchestrator escalates to user with:
   - Full context of what was attempted
   - Agent outputs from each attempt
   - Specific blocker description
   - Suggested manual intervention

### Conflict Resolution
When two agents produce conflicting outputs:
1. Orchestrator identifies the conflict
2. Higher-authority agent resolves (Architect > Developer > Reviewer for design conflicts)
3. Resolution logged in DECISIONS.md
4. Both agents updated with resolution

### State Recovery
If the workflow is interrupted at any point:
1. Check TASKS.md for last completed step
2. Check shared memory for latest valid state
3. Resume from the last completed validation gate
4. Do not re-execute successfully completed phases
