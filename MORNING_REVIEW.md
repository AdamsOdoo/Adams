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
2. Odoo.sh confirmations stay touchpoint-1 (you relay). The 6 batched
   commands are in FINALIZE.md ("Batched Odoo.sh confirmation
   commands") — now items 1, 2, 3a, 3b, 3c (+3d once you say go).
   Expected: 0 failed/0 errors of 3 / 6 / 6 / 2 / 13 / 5.
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

**No-go revert:** `git revert <3d-fix-sha> <3d-test-sha>` on the working
branch (shas in section 2; revert both to drop the now-failing tests
with the fix, or only the fix sha if you want the red tests kept).

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

## 3) In progress

- (updated continuously — see STATUS.md "Resume here" for exact state)

## 4) Decisions awaiting you

- DEC-014 (keep base tombstone) made under standing approval —
  reversible, listed for visibility only.
