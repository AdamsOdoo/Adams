# Designing L-size changes

Use this for new flows, several interacting modules, or changes to existing data. Keep the design in the feature notes and make it only as long as the decisions need. A design is not evidence; the tests are.

## 1. Outcome and scope

- The business outcome in one or two sentences, and who benefits.
- In scope and explicitly out of scope.
- The facts you verified in the code, standard features you will reuse (with source paths), and assumptions awaiting confirmation.

## 2. Flow

| Step | Actor (role) | What they do | What the system does | Data changed | Errors and alternatives |
|---|---|---|---|---|---|

Cover the unhappy paths that matter: rejection, cancellation, duplicates, missing data, retries, and concurrent edits when two users can act on the same record.

## 3. Data model

New models and fields (type, required, company-dependent, stored or computed), the relations, and which standard models they extend. For each stored computed field, list its dependencies. Include the indexes and constraints you need.

## 4. Access

| Role (group) | Read | Create | Write | Delete | Record rule |
|---|---|---|---|---|---|

Also cover multi-company behaviour, and any `sudo()` with its justification.

## 5. Existing data and deployment

The version bump, migration scripts (pre, post), `noupdate` data affected, backfills and their cost on production volumes, anything the user must configure after deployment, and how to roll back.

## 6. Acceptance

Map each criterion to its proof:

| ID | Criterion | Test (file::class.method) or tour | Screen or report to check |
|---|---|---|---|

## 7. Open decisions

Only the decisions that block implementation, each with your recommendation, so the user can answer in one line.
