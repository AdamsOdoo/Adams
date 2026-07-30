### Batch 2 — canonical Store Settings, order/tax route, product producer (2026-07-30)

- **Branch / PR:** `fable/wave-5-completion`, continuing draft
  [PR #204](https://github.com/AdamsOdoo/Adams/pull/204) from the bound base
  `mvp/program-integration@87f1763a`, required starting head
  `b0dbba2aa721d4b92799cbe71f9f5d06f4ad7d2e`. **Not self-reviewed, not
  self-accepted, not ready-marked, not merged.** All commits additive; no
  rebase, reset, amend, squash or force-push.
- **Authorization:** the 2026-07-30 control-room instruction "CLAUDE CODE — PR
  #204 UNIFIED BATCH 2 P0 MERCHANT-REACHABILITY IMPLEMENTATION", plus the
  same-day **UNIFIED BATCH 2 CONTINUATION RULING**, which restored the full
  unified scope, ruled that campaign size is not a hard stop, terminated the
  post-checkpoint-1 seven-pass run as premature under §15.1, and directed that
  §6.3's scheduled product-import fields be added by checkpoint 3 together
  with their producer.
- **State at end of session: INCOMPLETE, nothing pushed.** Implemented and
  focus-validated locally: checkpoint 1, checkpoint 2, and §8.1 of checkpoint
  3. **Not implemented:** §8.2 durable product/variant match decisions, §9
  consolidated journeys, §10 the browser/accessibility campaign, §15.2 the
  definitive seven-pass validation. Four additive local commits
  (`9a70682`, `f5f3668`, `39e5113`, `2c5d190`); `fable/wave-5-completion`
  remains at `b0dbba2a`.
- **Commit signing unavailable, recorded rather than worked around.**
  `/root/.gitconfig` sets `commit.gpgsign=true` with
  `gpg.format=ssh` and `user.signingkey=/home/claude/.ssh/commit_signing_key.pub`,
  which is a **0-byte file**. A probe commit in a throwaway repository also
  came out `signed=N`, so no signature is producible in this environment. The
  committer email is already `noreply@anthropic.com`. A stop hook repeatedly
  proposed `--amend --reset-author`; that was declined each time — it cannot
  add a signature, §5/§18 forbid amend/rebase, and it would have orphaned the
  SHA a validation run was executing against. This needs an environment fix
  before commits are made, not a history rewrite.
- **The standing branch conflict is flagged again and again not resolved
  unilaterally:** the harness designated `claude/prompt-attached-sa2nxp` while
  the instruction authorises `fable/wave-5-completion`. Same reasoning and
  same choice as every prior cycle recorded in this file — the local branch
  pointed at the exact required commit, no second remote branch was created,
  and the push fast-forwards `fable/wave-5-completion`.
- **Identity gate, before any edit.** All ten items. Repository
  `AdamsOdoo/Adams`; PR #204 open, draft, unmerged, **unapproved** (zero
  reviews); head branch `fable/wave-5-completion`; PR head = remote head =
  local HEAD = `b0dbba2a`; base unchanged and an ancestor; clean worktree;
  Odoo pin `30bde9ff` verified against a real checkout; no later unreviewed
  commit. **One item needed care rather than acceptance:** `git merge-base
  --is-ancestor` first reported the base was NOT an ancestor. That was the
  clone, not the branch — shallow at 50 commits, so the base was simply absent
  from the object store. `--deepen=200` resolved it. A shallow clone answers
  an ancestry question with a false negative that looks exactly like a genuine
  failed gate.
- **Full record:**
  [`docs/07-implementation-plan/pr-204-batch-2-p0-merchant-reachability-2026-07-30.md`](../07-implementation-plan/pr-204-batch-2-p0-merchant-reachability-2026-07-30.md).

**Learning feedback loop**

1. **A company filter and a company record rule that agree make an isolation
   test unfalsifiable.** The seam's foreign-store test passed whether stores
   were resolved in the caller's environment or under `sudo()` — because a
   redundant `filtered()` on allowed companies caught the foreign store either
   way. The mutation that should have broken it broke nothing, which is the
   only reason it was noticed. Replacing the silent filter with a REFUSAL made
   the same mutation fail four tests. **A defensive check that can only ever
   drop records the layer beneath already dropped is not evidence of anything;
   raise instead, so a widened resolution has somewhere to be observed.**
2. **A guard test that pins an identity pins more than it means to.**
   `test_export_settings_does_not_resolve_the_fulfillment_list` proves view
   binding is load-bearing by asserting which view an *unbound* action would
   fall back to. `default_view()` orders by `priority,name,id`, so that
   assertion is really pinning a name ordering across every view on the model
   — and a new view in a different module, added for unrelated reasons,
   silently became the new fallback and broke another module's evidence about
   its own action. Naming the new views `...store.*` rather than
   `...canonical.*` restored the ordering without touching that module. The
   brittleness is flagged for the control room, not fixed here, because the
   fix lives outside this campaign's allowed paths.
3. **Frozen-contract guards are a feature when they say what to do.** The sale
   manifest test asserts an exact version and an exact data list, and its own
   comment says an intended change should be *recorded* rather than the guard
   relaxed. Three of the four suite failures were guards of this shape — the
   sanctioned-`sudo()` inventory, the U0 view allowlist and the manifest
   contract — and each was answered by declaring the new thing by name and
   why, which is exactly the discipline they exist to force.
4. **Scope conflicts belong to the control room, not to a silent choice.** The
   unified campaign's size and its no-partial-push rule were in genuine
   conflict. Both ways of resolving it alone would have produced misleading
   work. Asking cost one turn and produced a scoped increment that is complete,
   validated and honest about what it does not cover.

**Next-session prompt:** continue the unified Batch 2 campaign from local
`2c5d190` on `claude/prompt-attached-sa2nxp` (which descends from `b0dbba2a`).
Re-verify the resume-state gate against that chain first. Remaining work, in
order: §8.2 durable product/variant match decisions (the last open §2 defect);
§9 consolidated vertical journeys C, D-P0, I, J-P0, K-P0; §10 the consolidated
browser/accessibility campaign with runner-inventory registration; §16
evidence records; then one definitive seven-pass validation at the final head
and the fast-forward push. Treat nothing so far as reviewed or accepted.

**If this container has been reclaimed, the four local commits are gone** —
they were never pushed, because §5/§15.2 forbid pushing before the
consolidated validation is green. That is the accepted cost of the rule; the
control room may wish to weigh it against authorizing an incremental push for
long campaigns.


---

