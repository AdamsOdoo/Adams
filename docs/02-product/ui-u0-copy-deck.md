# U0 Operator UI — Copy Deck

> Merchant-facing copy shipped in the U0 batch. Tone per
> `ui-ux-final-design-spec.md` §voice: calm, professional, concise,
> non-technical, action-oriented; verbs first; no exclamation marks in error
> states; "we/you" framing; **never claim encryption**; **never render a raw
> internal token on an action-path surface**. English only in U0 — final
> Arabic is a later pass (MBQ-22); the UI is RTL-ready.

## 1. Internal token → plain-language rendering (one rendering, reused)

These are the labels the U0 dashboard aggregate service emits. Native Odoo
lists additionally show the model's own selection labels (also human-readable,
never the raw snake_case token).

| Internal state / token | Plain-language rendering (U0 dashboard) |
| --- | --- |
| `succeeded` | Done |
| `queued` | Queued |
| `running` | Running |
| `retry_waiting` | Waiting to retry |
| `failed_retryable` | Needs a fix |
| `failed_final` | Failed |
| `blocked_manual_review` | Waiting on a decision |
| `skipped` | Skipped |
| `cancelled` | Cancelled |
| mutation attempt `uncertain` (unresolved) | Waiting on a decision |
| `mutation_domain` (raw) | Rendered as its business domain word; never shown raw on an action path |

The raw tokens `blocked_manual_review`, `failed_retryable`, `retry_waiting`,
`mutation_domain` never appear as primary operator copy.

## 2. Dashboard — lead band

| State | Lead text | Hint | Severity / icon |
| --- | --- | --- | --- |
| First-run / empty | Store setup is incomplete | Connect your store to begin syncing. | info / plug |
| Loading | Loading your dashboard… | (skeleton) | skeleton |
| Healthy | All systems normal | Everything that ran recently succeeded. | success / check |
| Warning | N items need your attention | Nothing has failed — these are working through on their own or need a quick check. | warning / clock |
| Degraded | N items need your attention | Review the items below to get things moving again. | danger / triangle |
| Manual review | N waiting on a decision | These are decisions for a reviewer — not a system failure. | danger / hand |
| Error (RPC) | We couldn't load the dashboard | (technical reason) | danger / triangle |

Affirmative empty line: **"All clear — nothing needs your attention right now."**

## 3. Dashboard — exceptions (title · why · owner)

| Exception | Title | Why | Owner |
| --- | --- | --- | --- |
| Blocked review | Jobs waiting on a review decision | A reviewer needs to decide how these proceed. | Reviewer |
| Uncertain mutation | Changes waiting on an administrator decision | An outcome could not be confirmed and needs an administrator judgement. | Administrator |
| Failed final | Jobs that stopped after repeated failures | These stopped retrying — review the reason to get them moving again. | Operator |
| Failed retryable | Jobs that need a fix before retrying | These are paused for a manual fix, then a retry. | Operator |
| Reconnect needed | Stores that need reconnecting | Shopify no longer accepts the saved credentials — reconnect to resume. | Administrator |

Chips: Stores ("N of M connected"), Queued, Running, Waiting to retry, To review.
Cadence line: "Automatic checks run on a schedule — last activity {relative}."

## 4. Stores

- Credential note (never claims encryption): **"The access token is stored with
  restricted access and is never shown here."**
- Disconnect confirm: **"Disconnecting stops all syncing and removes the stored
  credentials. History, matches, and logs are kept. You can reconnect anytime."**
- Empty state: **"No store connected yet — Connect your Shopify store to begin."**

## 5. Sync Center / Error & Review Center

- Sync Center empty: **"Nothing needs attention — Sync jobs appear here. When
  something needs a decision or a fix, it shows up first."**
- Error Center empty: **"No open errors — Everything that ran recently
  succeeded. Failures and items awaiting a decision appear here."**

## 6. Logs & mutation evidence

- Logs empty: **"No log activity yet — When syncing runs, every step is recorded
  here, read-only and redacted."**
- Audit-evidence section label: **"Immutable audit evidence (redacted)"** —
  "Recorded, redacted evidence kept for audit. It cannot be edited or deleted."
- Mutation evidence note: **"This is immutable audit evidence. Raw request and
  response contents are not shown."**

## 7. Wizards

- Cancel: field "Cancellation reason" — "A short, non-technical reason. It is
  recorded on the job's audit trail." Buttons: "Cancel this job" / "Keep job".
- Mutation resolution: warning — **"This records an administrator judgement
  about a change to Shopify. It is audited and cannot be undone. Base it on the
  evidence."** Disposition options: "Applied — the change did take effect in
  Shopify" / "Not applied — the change did not take effect". Confirm: "This
  decision is audited and cannot be undone. Continue?"
