# MORNING_REVIEW.md — overnight window 2026-06-11 → 2026-06-12

Single-file morning brief per the overnight governance change.
Sections: (1) queued consequence statements + revert commands,
(2) completed with evidence, (3) in progress, (4) decisions awaiting you,
(5) SSH/confirmation status.

## 5) SSH / Odoo.sh confirmation status — READ FIRST (changes the plan)

**SSH from session containers is impossible, permanently — not a policy
or key problem.** Evidence: (a) port 22 times out to ALL hosts
(adamsmen.dev.odoo.com AND github.com) while 443 to the same Odoo.sh
host connects instantly — so it's not Odoo.sh-side; (b) the official
docs (code.claude.com/docs/en/claude-code-on-the-web, "Security proxy")
state all outbound traffic passes through an HTTP/HTTPS proxy — raw TCP
like SSH is unsupported under every network access level, including
"Full". No environment setting changes this.

Also: `ODOO_SH_SSH_KEY` never reached this container — the session runs
in environment type `cloud_default` (the default), not a custom
environment, so even env-var changes you made to a custom environment
don't apply unless sessions are started IN that environment.

**What to change, step by step:**
1. Stop pursuing SSH from sessions. Remove the key from the environment
   config if you added it (no dedicated secrets store; env vars are
   visible to anyone who can edit the environment).
2. Odoo.sh confirmations stay touchpoint-1 (you relay). The 7 batched
   commands are in FINALIZE.md ("Batched Odoo.sh confirmation
   commands") — items 1, 2, 3a, 3b, 3c, 3d, 3e. Expected:
   0 failed/0 errors of 3 / 6 / 6 / 2 / 13 / 5 / 11.
3. GREEN BUILD Odoo.sh leg: from the Odoo.sh editor/web shell, run
   `grep -iE "error|warning" ~/logs/install.log` (or paste the build
   log page) — the local proxy already classified everything local
   (zero (a)-class; details in FINALIZE.md).
4. Optional, if you want sessions to reach Odoo.sh runtime some day:
   an HTTPS↔SSH bridge (e.g. `wstunnel`/`chisel` server on a VPS, or
   Cloudflare Tunnel in front of a jump host) would work through the
   proxy — your infra, your call; not assumed by any plan.
5. Recommended regardless: add an environment **setup script** (and
   select that environment when starting sessions) that rebuilds the
   local runtime — the container is ephemeral and this session spent
   ~25 min recreating it (exact recipe now in CLAUDE.md Environment,
   incl. two new quirks: `pip install cffi`, exclude
   `python-ldap`/`ofxparse`).

## 1) Queued consequence statements (in commit order)

(Queued as committed; each ends with the exact no-go revert command.)

### 3d — tax-fallback flavor filter + dropped-tax visibility (money path: taxes)

When no merchant mapping exists and we match an Odoo tax by rate, we now
only ever match PERCENT taxes — before, a fixed-amount tax of 10.0
(currency units) could silently satisfy a 10% lookup and book wrong tax
on every line. If nothing percent matches, the tax line is dropped as
before, but the merchant now SEES it: one warning activity per order
naming each unmapped tax and saying to create a mapping; the existing
total-check guard still keeps any mismatched auto-invoice in draft. Net
effect for merchants: strictly fewer wrong-tax postings and no new
silent states; orders import exactly as before in every case where the
fallback was already correct. Evidence: fail-before 4/0 of 5 →
pass-after 0/0 of 5 (TestTaxFallbackFlavor, strict1); full suites
strict1 0/0 of 557, strict_vat 2/0 of 557 (unchanged known AUD-001
pair).

**No-go revert:** `git revert 17a55bd b012e65` on
`claude/determined-cori-glvysk` (17a55bd = fix+docs, b012e65 = tests;
revert both to drop the now-failing tests with the fix, or only
17a55bd if you want the red tests kept).

### 3e — taxesIncluded / VAT-inclusive core (money path: taxes)

The importer now reads Shopify's `taxesIncluded` flag and reconciles it
with the Odoo tax it resolves. Concretely: when a store's prices and
the matched Odoo tax disagree about whether tax is inside the price
(e.g. any VAT-style tax-included Odoo company importing from a
standard exclusive-pricing store — the AUD-001 wrong-invoice bug), the
unit price is converted by the tax rate so the posted base, tax and
total equal exactly what the customer was charged, in both directions.
The rate fallback now also PREFERS a tax whose inclusion flavor
already matches the store, so conversion is the exception, not the
rule. Inclusive-pricing stores (EU/UK/AU) are now supported end to
end; legacy payloads without the flag behave exactly as before. Where
the arithmetic can't be made safe (mixed flavors, non-percent mapped
taxes) prices are left untouched and the permanent total-check guard
blocks any mismatch visibly. Evidence: fail-before 4/0 of 11 →
pass-after 0/0 of 11; full suites BOTH GREEN — strict_vat 0 failed,
0 errors of 562 (the 2 standing AUD-001 failures CLEARED; first
fully-green strict-VAT run), strict1 0 failed, 0 errors of 562.

**No-go revert:** `git revert 58af690 cd1bfd3` on
`claude/determined-cori-glvysk` (58af690 = fix+docs;
cd1bfd3 = fail-before tests).

### Item 4 — visibility batch (money-adjacent: refund/payout/payment visibility)

Nine silent-failure branches now surface; no financial computation
changed anywhere. The merchant-visible effects: refund/payout cron
failures post a Sync Alert on the store's chatter instead of vanishing
(a dead token no longer means refunds silently never book); an order
webhook whose import crashes is retried and eventually dead-lettered
instead of being recorded as processed; a posted credit note or
invoice whose Shopify reverse-sync fails gets a warning activity
naming the manual fix (the two systems can no longer diverge
silently); reconcile/cancel failures during payment transitions and
unexpected registration errors get activities and ERROR-level
tracebacks. Risk is low: every change adds notification on an
existing failure path; the one behavioral change is AUD-005 (webhook
re-raise), where the retry machine was already built, tested, and
simply never reached. Evidence: fail-before 10/0 of 10 → pass-after
0/0 of 16; full suites (counts in §2).

**No-go revert:** `git revert <item4-fix-sha> 52a268c` on
`claude/determined-cori-glvysk` (52a268c = fail-before tests; fix sha
in §2 once committed).

### Item 5 — refund idempotency + over-refund guard (money path: refunds/credit notes)

Two protections around credit notes. First, booking a Shopify refund is
now atomic and double-entry-proof: the credit note and its tracking
record are created in one savepoint (a crash between them used to leave
a posted credit note that the next sync would post AGAIN), and every
connector credit note now carries the Shopify refund ID in a dedicated
field, so even if tracking records are lost the refund is recognized
and reused rather than re-booked. Second, a cumulative cap: when the
sum of connector credit notes plus the incoming refund would exceed the
posted invoice total (beyond 2× currency rounding), the credit note is
NOT created — the merchant gets a warning activity naming the amounts
and a retryable error-state binding. Legitimate partial refunds up to
exactly the invoiced total still post. Riders: a silently-dropped
non-product refund line is now logged, and shipping refund lines
resolve their income account like product lines instead of only the
journal default. Evidence: fail-before 2 failed + 1 error of 4 →
pass-after 0/0 of 11; full suites (counts in §2).

**No-go revert:** `git revert <item5-fix-sha> bd491b2` on
`claude/determined-cori-glvysk` (bd491b2 = fail-before tests; fix sha
in §2 once committed). Note: reverting removes the new
`shopify_refund_gid` column on the next upgrade; GID stamps on
already-created credit notes are lost on revert.

## 2) Completed with evidence

- **Environment rebuilt from scratch** (container was fresh: no Odoo
  checkout, no deps, empty PG cluster). Baselines reproduced EXACTLY on
  the rebuilt env, new core tip b4c7247f (was 07a333c8 — no drift):
  adams_strict1 **0 failed, 0 errors of 552**; adams_strict_vat
  **2 failed, 0 errors of 552** (the known AUD-001 pair). CLAUDE.md
  Environment section updated with the full verified recipe +
  corrections (`l10n_generic_coa` is not an Odoo 19 module; chart loads
  solely via `try_loading('generic_coa')`).
- **Item 3c session-boundary check: nothing lost.** Commit `7ff6e0f`
  (3c fix) + handoff `031f4d8` present on both
  `origin/claude/admiring-bell-e9g6qp` (previous session) and
  `origin/claude/determined-cori-glvysk` (this session's branch).
- **GREEN BUILD local proxy: zero (a)-class findings.** Fresh-install
  log (all 4 modules, warn level): only 2 docutils RST lines, proven to
  come from CORE `mail`'s manifest description (rendered every installed
  module's description; only `mail` errors) → class (c), not ours.
  Upgrade-path log (-u all 4): exit 0, zero lines. None of the explicit
  suspects fired (XML/ACL/deprecation/menu/manifest). DEC-014 records
  keeping `shopify_connector_pro_base` as a deprecation tombstone.
  Odoo.sh leg queued for your relay (see section 5).

- **Item 3e DONE and pushed** (commits cd1bfd3 tests, 58af690 fix+docs):
  taxesIncluded fetched + honored; flavor-preferring fallback; price
  alignment both directions on product and shipping lines; simulator
  emits the flag. Evidence: fail-before 4/0 of 11 → pass-after 0/0 of
  11; full suites strict_vat 0 failed, 0 errors of 562 (AUD-001 pair
  CLEARED — first fully-green strict-VAT run) and strict1 0 failed,
  0 errors of 562. PENDING RETROACTIVE GO (§1) + Odoo.sh confirmation
  (command 7 in the FINALIZE.md batch).
- **Item 3d DONE and pushed** (commits b012e65 tests, 17a55bd fix+docs,
  branch claude/determined-cori-glvysk): percent-only rate fallback
  (AUD-017), visible dropped-tax activity (AUD-016 remainder),
  deterministic ordering verified already guaranteed by core. Evidence:
  fail-before 4 failed/0 errors of 5 → pass-after 0/0 of 5
  (TestTaxFallbackFlavor, strict1); full suites strict1 0/0 of 557,
  strict_vat 2/0 of 557 (unchanged known AUD-001 pair). PENDING
  RETROACTIVE GO (statement in §1) + Odoo.sh confirmation (command 6 in
  the FINALIZE.md batch).

## 3) In progress

- (updated continuously — see STATUS.md "Resume here" for exact state)

## 4) Decisions awaiting you

- DEC-014 (keep base tombstone) made under standing approval —
  reversible, listed for visibility only.
