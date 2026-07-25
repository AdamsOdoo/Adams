# DEC-041: Evidence-First Process Reallocation — Fewer Artifacts, Unchanged Gates

- **Status:** Accepted by product-owner instruction, pending merge of this governance PR.
- **Date:** 2026-07-25
- **Deciders:** Product owner; ChatGPT strategic control room.
- **Scope:** MVP-program governance on or descending from `mvp/program-integration`.
- **Architecture impact:** None. The connector architecture is not redesigned.
- **Safety impact:** No gate is removed, combined, weakened, or bypassed.
- **Related:** DEC-032, DEC-039, DEC-040, issue #167, PR #189, PR #194, `CHATGPT.md`, `CLAUDE.md`, `GPT_SOL.md`.

## Decision summary

The program is not over-rigorous. Ceremony has been misallocated. Durable evidence, upstream-source checks, exact-SHA runtime, independent review, controlled Shopify mutations, security/data-integrity proof, checkpoint protection, and no self-acceptance remain mandatory. The correction reduces document chains and ruling churn while moving effort to earlier source verification, consolidated runtime/correction campaigns, CI, and truthful release trackers.

## Verified evidence

| ID | Verification | Result |
| --- | --- | --- |
| E1 | PR #189 history shows ruling [5069830526](https://github.com/AdamsOdoo/Adams/pull/189#issuecomment-5069830526), then commits [aa295ef](https://github.com/AdamsOdoo/Adams/commit/aa295efb1f4cd833e56160e07b770a4ffa73a710) and [25639f17](https://github.com/AdamsOdoo/Adams/commit/25639f17be14b30a52a8453f0813aa0b764de310) without the mandated immediate push record. The later control-room comment [5073570894](https://github.com/AdamsOdoo/Adams/pull/189#issuecomment-5073570894) repaired the push record. Odoo.sh then initially deployed the wrong parent `aa295ef`, a preserved historical process defect. Exact candidate `25639f17` was subsequently executed on Odoo.sh build `35422036`; the safely executable exact-SHA matrix is green in durable runtime comment [5074529652](https://github.com/AdamsOdoo/Adams/pull/189#issuecomment-5074529652), and independent evidence review [5077119326](https://github.com/AdamsOdoo/Adams/pull/189#issuecomment-5077119326) accepted it with zero candidate-owned failures. Gate D/CV-013 and record closure remain; PR #189 remains draft, unmerged, and not finally accepted. | Historical missing-immediate-push-record and wrong-parent-deployment defects remain recorded; exact-SHA runtime evidence is now independently accepted. |
| E2 | PR #189 comments [5067147430](https://github.com/AdamsOdoo/Adams/pull/189#issuecomment-5067147430), [5067208834](https://github.com/AdamsOdoo/Adams/pull/189#issuecomment-5067208834), and [5069830526](https://github.com/AdamsOdoo/Adams/pull/189#issuecomment-5069830526) superseded the same transfer sequence within about five hours. The first instruction assumed one workspace could both execute Odoo and publish to GitHub. | Confirmed. |
| E3 | [d3c157c](https://github.com/AdamsOdoo/Adams/commit/d3c157c1d4c369c1880fffc69ee6b4801ab9c05c) produced a findings synthesis and prompt; [ef991bf](https://github.com/AdamsOdoo/Adams/commit/ef991bf08ff55c4393fa2c0c971cd1dbef04ab2d) produced a decision lock and prompt normalization; ruling [5060656594](https://github.com/AdamsOdoo/Adams/pull/189#issuecomment-5060656594) then stopped the docs loop. | Confirmed. |
| E4 | PR #189 code/evidence records the invalid `sale.order.line.product_uom`, nonexistent `stock.stock_location_locations`, and latent `required_qty` KeyError. Odoo 19 source uses [`sale.order.line.product_uom_id`](https://github.com/odoo/odoo/blob/19.0/addons/sale_stock/models/sale_order_line.py#L548-L554), defines [stock location XML IDs](https://github.com/odoo/odoo/blob/19.0/addons/stock/data/stock_data.xml), and coerces a newly created move to `done` when its picking is already done in [`stock.move.create()`](https://github.com/odoo/odoo/blob/19.0/addons/stock/models/stock_move.py#L821-L834). | Confirmed. Earlier upstream-source inspection would have prevented or shortened all four families. |
| E5 | `.github/` is absent on the live integration branch, PR #189 branch, and PR #194 branch. All accepted green evidence is manually recorded Odoo.sh execution. | Confirmed for current release-relevant branches. |
| E6 | `mvp-acceptance-matrix.md` still described Wave 2 as draft/not green and inventory/fulfillment as unimplemented; `mvp-program-state.md` §1 still named PR #189 head `702d083`. | Confirmed. |
| E7 | `CHATGPT.md` named ChatGPT as control room while `CLAUDE.md` §13 and DEC-039/040 made Claude the default builder/reviewer; issue #167 retained the earlier Claude-control-room/Sol-primary model. | Confirmed. |

## D1–D10 adjudication

### D1 — Ground-truth-first rule: MODIFY and ACCEPT

Before authoring or changing any **framework-dependent behavior or fixture assumption**, the worker must read the governing source:

- Odoo-dependent behavior: the actual Odoo 19 source used by the target runtime, or the pinned authoritative `odoo/odoo@19.0` path and line range.
- Shopify-dependent behavior: current official Shopify documentation, recording API version, URL, and access date; source/schema when available.

The citation must appear in the change handoff and PR record. A code comment is required only where the dependency is non-obvious or future maintainers could reasonably regress it; citations are not sprayed onto framework-independent lines. This applies equally to production code and tests. If source cannot be accessed, stop or mark the assumption unproven—do not guess.

This supersedes any prompt/ruling that allowed Odoo/Shopify-dependent implementation to proceed on static inference alone, including the static-only assumptions preceding PR #189 runtime rulings 5062917634 and 5063368777.

### D2 — Push-completion record: ACCEPT

A push to an implementation branch is incomplete until one PR comment records:

- exact pushed SHA and sole parent (or all merge parents);
- changed-file list;
- evidence classification for every claimed check;
- runtime/build/database identity when applicable;
- remaining unproven gates.

This record is a permanent carve-out from “no documentation change” or “no PR metadata change” restrictions. No ruling may forbid its own compliance record. The record is not permission to broaden the code diff.

This supersedes the record-suppressing part of PR #189 ruling 5069830526 and any equivalent scope language.

### D3 — Runtime evidence preservation: MODIFY and ACCEPT

Runtime output must be converted to a sanitized durable GitHub record before the runtime environment or session is torn down. When Runtime Claude lacks GitHub write access, it returns the complete report in-session and the product owner/control room posts it verbatim or stores the attached artifact before ending the coordinated evidence handoff. Ephemeral `/tmp`, chat-only summaries, or untransferred tool output are not admissible as sole evidence.

This supersedes any handoff practice that treated ephemeral Odoo.sh files/tool outputs as sufficient, including the fragile transfer sequence replaced by ruling 5069830526.

### D4 — Environment-matched rulings: MODIFY and ACCEPT

Every executable ruling begins with a capability declaration for the addressed environment: repository checkout/read/write, GitHub auth/push, Odoo/PostgreSQL runtime, Shopify access/mutation authority, and durable-output path. Instructions outside those capabilities are invalid.

Every ruling supersession within 24 hours counts in the metric. Each event is classified separately as **preventable**, **justified by genuinely new external evidence**, **security-driven**, or **environment-capability-driven**. A justification changes the event's classification but never removes the event from the count; there is no exemption by which a real supersession disappears from measurement. “Refinement” alone is preventable.

This supersedes PR #189 ruling 5067147430 and any later prompt that combines incompatible Runtime Claude and GitHub-worker capabilities.

### D5 — No document-to-document production chain: MODIFY and ACCEPT

A findings review produces one durable correction contract. The next authored change must be implementation, or an explicit hard-stop record naming the missing decision/evidence. Do not create a synthesis → decision lock → prompt normalization → handoff chain.

Exceptions are durable governance instruments with direct recurring consumers (decision records, reusable templates, acceptance trackers) and legally/security-required records. The exception cannot be used to restate the same one-time correction contract.

This supersedes the Wave 4 sequence represented by d3c157c and ef991bf and is consistent with ruling 5060656594 (“STOP THE DOCS LOOP”).

### D6 — One correction batch per runtime campaign: ACCEPT

A runtime campaign collects every independent safely discoverable failure family. The next correction fixes the consolidated owned set in one coherent batch, followed by one exact-SHA rerun. Stop early only for identity/evidence contamination, destructive behavior, credential exposure, database corruption, or another safety hard stop.

This supersedes failure-by-failure correction instructions. It preserves the product-owner right to reject or defer an unsafe/out-of-scope family.

### D7 — Deterministic review tier: MODIFY and ACCEPT

Tier is computed from the diff’s paths **and semantics**, using the highest applicable tier:

| Deterministic trigger | Tier | Process |
| --- | --- | --- |
| Production or proof changes involving remote mutation, concurrency, transactions/locks, idempotency/reconciliation, security, credentials/PII, permissions, irreversible migration, or data-integrity invariants | 1 | Full independent review plus exact-SHA runtime and risk-specific proof |
| Domain contracts, architecture/module boundaries, manifests/dependency direction, job/state vocabulary, API shapes, or UI actions without new Tier-1 behavior | 2 | One normal independent review and at most one consolidated correction |
| Docs/wording/status/cross-reference changes; tests or fixtures that do not alter Tier-1/2 proof semantics | 3 | Fix in pass; no independent cycle and no runtime solely for this diff |

A test-only diff that changes whether a Tier-1 invariant is genuinely proved is Tier 1; file location must never downgrade proof risk. Mixed diffs use the highest tier for the risky portion without spreading Tier-1 ceremony to unrelated Tier-3 edits.

This supersedes DEC-040 only where tier selection was discretionary per session. DEC-040’s risk-tiering, independence, runtime, and no-self-acceptance safeguards otherwise remain.

### D8 — CI authorization: ACCEPT

Authorize a separate infrastructure task for a minimal install-and-run-suites workflow on push/PR. It must use no live Shopify credentials or mutations, use fixture-safe secrets handling, preserve Odoo.sh exact-SHA runtime as the Tier-1 acceptance authority until equivalence is proven, and publish durable logs/artifacts. CI is the automation path for acceptance-matrix row 21; it is not silently treated as green before implementation and execution.

This supersedes the “manual-only by default” operating assumption. It does not authorize CI implementation in this governance session.

### D9 — Present-tense PR body: ACCEPT

An implementation PR body is a short present-tense header: current SHA, parent/base, current changed scope, evidence status, blockers, and next gate. Historical narrative moves to the owning evidence document/comments.

Because this session may not modify PR #189 or PR #194 content, their body corrections are deferred to their next authorized closure/refresh batch. This decision supersedes the practice of accumulating wave history in PR bodies.

### D10 — Tracker truth as merge/continuation gate: MODIFY and ACCEPT

Before merge, both trackers must describe the exact candidate honestly: accepted evidence, remaining gates, and “merge pending”; they must not predict a merge SHA. Immediately after merge, a tracker-only closure record must add the actual merge SHA and post-merge state **before the next dependent implementation wave, Gate D/UAT continuation, or release claim**.

A stale tracker blocks merge closure and downstream continuation, not an already-running independent exact-SHA runtime session. This supersedes tracker handling that allowed PR #176/#182/#189 status to remain materially stale.

## Delivered inconsistency / A5 disposition

The current Delivered inconsistency is distinct from the historical validation-results **A5 KeyError** defect. It is not a PR #189 candidate defect and does not invalidate the accepted exact-SHA runtime record.

It may be deferred from the Wave 4 backend merge because no real Delivered backend seam currently exists. U1 must not claim, display, or offer **Delivered** as a supported state until a real backend seam exists and is independently proven. The next authorized refresh of PR #194 must remove or suppress that representation unless the missing backend seam is implemented under separate authorization. PR #194 is not modified by this decision correction.

## Gates explicitly unchanged

The following remain mandatory and are not reduced:

1. independent review;
2. no self-review or self-acceptance;
3. exact-SHA runtime evidence;
4. controlled Shopify reads/mutations and dev-store gates;
5. security, privacy, company-isolation, and data-integrity gates;
6. idempotency, concurrency, transaction, rollback, and residue proof;
7. GitHub as durable source of truth;
8. checkpoint, protected-branch, ready-mark, merge, and promotion protections;
9. product-owner final authority.

The correction reduces documents and rulings. It does **not** reduce gates.

## Per-wave metrics

| Metric | Target | Measurement rule |
| --- | ---: | --- |
| Correction rounds | ≤ 2 | Count consolidated post-review/runtime correction batches; safety resets are separately named |
| Documents authored per code commit | < 1 | Count one-time wave/correction artifacts, excluding required durable evidence appendices and recurring trackers |
| Rulings superseded within 24 h | 0 | Count every supersession event; classify each separately under D4. Justification changes classification, never the count. |
| Push to exact-SHA runtime record | Same day | Measure from GitHub push timestamp to durable exact-SHA runtime record; environment block is recorded, not hidden |
| Framework-dependent changes with upstream citation | 100% | Audit production and test assumptions under D1 |

## Consequences and follow-up

- PR #189 exact-SHA runtime at `25639f17` is complete and independently accepted through [runtime comment 5074529652](https://github.com/AdamsOdoo/Adams/pull/189#issuecomment-5074529652) and [review comment 5077119326](https://github.com/AdamsOdoo/Adams/pull/189#issuecomment-5077119326); no further code correction or runtime rerun is required. Gate D/CV-013 and record closure remain.
- PR #189/PR #194 bodies are not modified by this governance session.
- [SEC-2 #196](https://github.com/AdamsOdoo/Adams/issues/196), [SEC-3 #197](https://github.com/AdamsOdoo/Adams/issues/197), [inventory-test residue #198](https://github.com/AdamsOdoo/Adams/issues/198), [PERF-0 #199](https://github.com/AdamsOdoo/Adams/issues/199), and [Shopify dev-store provisioning #200](https://github.com/AdamsOdoo/Adams/issues/200) are now separate owned tasks; CI remains separately authorized by D8.
- This decision does not accept Wave 4, authorize Gate D, merge a PR, begin Wave 5 implementation, or authorize UAT.
