---
name: odoo-review
description: Review an Odoo 19 change (a diff, branch or pull request) for defects before it ships - correctness against acceptance criteria, security, multi-company, data safety on update, performance, translations and Odoo.sh build issues. Use when asked to review Odoo code, or as the independent review step of odoo-dev.
---

# Odoo change review

Review the change, not the whole codebase. Get the diff (`git diff <base>...HEAD`, plus uncommitted changes), the acceptance criteria, and the result records (`.odoo-harness/oh evidence`). Confirm a suspicion before reporting it: read the surrounding code, check standard behaviour with `.odoo-harness/oh src`, and run `.odoo-harness/oh test <module> --no-record` or a single test when that settles the question. Don't edit the code, the tests or the evidence records; report what should change.

## What to look for (most costly first)

1. **Wrong behaviour:** each acceptance criterion is implemented and demonstrated by a test. Edge cases: empty recordsets, multiple records (`self` holding many), cancelled or archived records, zero or negative amounts, other currencies.
2. **Security:** access rows for every new model; record rules (company rules on models with `company_id`); business checks enforced in methods, not only hidden in views; `sudo()` justified and narrow; controllers with the right `auth`, validated input, no SQL built from strings.
3. **Multi-company:** `check_company=True` on relations, `_check_company_auto`, `self.env.company` rather than a hard-coded company, figures limited to the allowed companies.
4. **Data safety on update:** version bumped for deployed modules; a migration for renamed or retyped fields and changed selections, with an `oh_upgrade` test that checks the migrated records; `noupdate` records that won't update; new required fields have values for existing rows; costly recomputes of stored fields on big tables.
5. **ORM correctness:** complete `@api.depends`, `@api.model_create_multi` with loops over `vals_list`, loops over `self` in computes and constraints, no ORM calls per record inside loops (N+1), flushing before raw SQL, and Odoo 19 APIs (see `odoo-dev/references/odoo19.md`: `models.Constraint`, `group_ids`, `check_access`, `_read_group`, `jsonrpc` routes).
6. **Figures:** a figure a standard report provides comes from that report, not a new calculation; a custom calculation has a written reason and explicit filters (states, dates, companies, currency, signs); the KPI and its drill-down share one domain (see `odoo-dev/references/reports.md`).
7. **Views and UI:** `list` not `tree`, no `attrs`/`states`, xpaths anchored on names, modifiers consistent with server rules, menus and actions reachable for the intended groups.
8. **Translations and right-to-left:** new strings translatable, `ar.po` updated with no empty entries, named placeholders, no concatenated translations, layouts that survive right-to-left.
9. **Odoo.sh build:** manifest `author` and `license` set; dependencies listed in `depends` and Python packages in `requirements.txt`; no warnings in the `oh test` output (they make builds "almost successful"); tests deterministic and independent of demo record IDs.
10. **Maintainability:** standard features reused rather than rebuilt, minimal overrides that call `super()`, no dead code or debugging leftovers.

## Report

Start with one line that binds the review to what you reviewed: `Reviewed <branch>@<commit> (+uncommitted changes, if any) digest <candidate digest from oh evidence> · <independent review, read-only enforced | independent review, read-only not enforced | self-review> · evidence: <record>: <status>, <intact and matching the commit | stale | problem | missing>`. Run `oh evidence` again at the end: if the candidate digest changed during the review, say so in that line, because the review no longer describes one fixed candidate.

Then findings only, most severe first. For each: `file:line`, what goes wrong in a concrete scenario, and the smallest fix. Then list the acceptance criteria that no test demonstrates, and any result record that is missing, stale or **not verified**. Don't include style preferences unless they cause defects. If nothing is wrong, say so in one line after the first line.
