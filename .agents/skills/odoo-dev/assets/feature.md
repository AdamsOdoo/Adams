# <ID> <Title>

Status: in progress | delivered · Size: S/M/L · Branch: · Modules (version): · Last tested commit:

## Requirement
<!-- The request in the user's words, then the goal in one or two sentences. -->

## Acceptance criteria
- A1 … → test `module/tests/test_x.py::TestX.test_a1`
- A2 … → …

## Design
<!-- S: one paragraph. M: rules, data model, access. L: see references/design.md. Mention standard features reused. -->

## Changes
<!-- Modules and main files; configuration or data the user must set. -->

## Verification
- Local: `oh test … --require …` → PASSED, n tests executed (record `.odoo-harness/evidence/test-….json`, matches commit …)
- Upgrade: `oh test … --upgrade-from origin/<prod>` → … (migrations run: …; `oh_upgrade` checks: …)
- Odoo.sh development build: … (status and link, or not run and why)
- Screens (English and Arabic, verified by `oh shot`): … (record `shot-….json`)
- Review: independent (odoo-reviewer, read-only enforced) | independent, not enforced | self-review; findings fixed: …

## Upgrade impact
<!-- Version bump, migration scripts, data changed, noupdate records, manual steps, rollback. "None" is a valid answer; say why. -->

## User guide (English)
<!-- Only for user-visible changes: where to click, what changes for whom. -->

## دليل المستخدم (العربية)
<!-- The same content in Arabic. -->

## Open items and assumptions
