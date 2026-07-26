# UI U3 — Operator Copy Deck (export, resilience, diagnostics)

> **Status: Delivered with the U3 implementation on `fable/wave-5-completion`.
> NOT accepted. NOT independently reviewed.** This deck records the copy that
> is *actually shipped* in the U3 surfaces at this head, not copy proposed for
> a later implementation. Every string below is quoted from the committed
> view, template or service — if a string here and the code disagree, the code
> is authoritative and this file is the defect.
>
> Required by `ui-implementation-phases-packet.md` §8.2 (`ALLOWED FILES:
> … docs/06-prompts/ui-u3-copy-deck.md`), which makes copy-deck finalization
> (MBQ-22 closure) part of the U3 polish pass.

---

## 1. The five rules this copy follows

`[Decision — applied throughout; derived from the U3 locked prompt's hard
constraints and the SEC-2 role model]`

1. **Say what will happen to the merchant's data, in the merchant's terms.**
   Not "productUpdate will be executed" — "Confirming removes 2 tag(s) from
   this product on Shopify".
2. **A refusal is a sentence about what the connector *will not do*, plus
   why.** Never a bare error code, never a raw `error_class`.
3. **Never show a credential, token, payload, header, stack trace, GraphQL
   document or PII.** Diagnostics screens included — especially diagnostics
   screens.
4. **Never promise a capability the backend does not have.** There is no
   "apply without preview", no "auto-apply", no "export all", because no
   such server path exists.
5. **Distinguish "nothing to do" from "something is wrong".** A product that
   already matches Shopify is a healthy result and reads as one.

---

## 2. Export review surface (S7 / S27) — the Owl diff

Source: `addons/shopify_connector_product_export/static/src/xml/shopify_connector_export_diff.xml`

| Slot | Shipped copy | Why this wording |
| --- | --- | --- |
| Loading | "Loading this export preview…" | A `role="status"` live region, so a screen reader announces the wait rather than silence. |
| Load failure | "We couldn't load this export preview" + the server message | Names the thing that failed. The server's own message is shown beneath rather than replaced by a generic one. |
| Path — create | "Creates a new Shopify product" | The consequence, not the mutation name. |
| Path — update | "Updates the bound Shopify product" | Says *bound*, so it is clear this is not a second product. |
| Stale preview | "This preview is no longer current" / "It aged out, or the product changed on one side since it was taken. Run a fresh preview — a stale confirmation can never authorise a write." | Both staleness directions in one sentence, and the reason the refusal exists. |
| **Tag removal (alert)** | "Confirming removes N tag(s) from this product on Shopify" + "Confirming this export replaces the product's COMPLETE Shopify tag list with the Odoo list. Tags are Odoo-owned; any tag added in Shopify and absent from Odoo is removed. Nothing else in this export removes anything from Shopify." | The single most important string in U3. It is the only place a confirmation *removes* remote data, and the removed tags are listed by name beneath it. |
| Diff table headers | "Field" / "On Shopify now" / "After this export" | "On Shopify now" rather than "Before" — a diff column labelled "before" invites the reading "before I made my Odoo edit". |
| Empty value | "(empty)" | A bare `false` renders as the word "false", which is a different claim than "this field is empty". |
| Images (on) | "Every image below is APPENDED. Existing Shopify media — including images this connector uploaded earlier — is never replaced, detached, reordered or deleted." | Append-only stated at the point of decision, not in a footnote. |
| Images (off) | "Media export is off for this store: media_source_of_truth is …, and export runs only under \"odoo\"." | A stated reason, never a silent omission. |
| Images (create path) | "Media is appended once the product exists on Shopify. Re-preview after the create completes." | Explains a sequencing fact rather than looking like a failure. |
| **Refusals heading** | "Refused differences" | Not "Warnings", not "Issues". The connector refused; that is the fact. |
| Refusals body | "These are differences this connector will **not** act on. They are not part of the plan below and cannot be confirmed. It never deletes a remote variant, product option, option value, collection membership, merchant metafield or image." | Enumerates what is protected, so "not listed" is never read as "not affected". |
| Untouched | "Collections — present, untouched" / "Merchant metafields — none on this product" | States both the presence and the disposition. "Untouched" alone does not tell an operator whether there was anything to touch. |
| Plan heading | "What will run, in order" | Order matters (create before media), and the heading says so. |
| Progress | "N of M steps complete" | Counted, next to a `role="progressbar"` carrying the same numbers. |
| Nothing to do | "This product already matches Shopify" / "There is nothing to export. That is a healthy result, not a problem." | Rule 5. An empty diff is not an error state. |
| Confirm | "Confirm this export" | The verb names the act, not "OK" or "Apply". |
| Confirm, in flight | "Confirming…" | The control disables itself, because two clicks must not become two apply jobs. |
| Confirm withheld | "Only a Shopify Connector Reviewer or Administrator can confirm an export, and only while the preview is still current." | Says *why* there is no button, rather than showing nothing. |

### Refusal labels

Source: `models/shopify_connector_product_export_ui.py::REFUSAL_LABELS`

| Recorded kind | Operator-facing label |
| --- | --- |
| `too_many_options` | More Shopify options than Shopify allows |
| `too_many_variants` | More variants than one export job carries |
| `remote_option_divergence` | Shopify option structure differs |
| `variant_create_withheld` | New variants withheld |
| `bound_product_missing_remotely` | Bound Shopify product is gone |
| `bound_variant_missing_remotely` | A bound Shopify variant is gone |
| `unowned_remote_variant` | Shopify variant this connector does not own |
| `custom_id_already_bound_remotely` | Already exported to this store |
| `duplicate_sku_on_shopify` | SKU already exists on Shopify |

`[Fact]` An **unrecognised** kind renders as its raw kind string rather than as
a blank row, and a test pins that. A refusal nobody can see is the failure this
surface exists to prevent, so an unknown one must still be visible even at the
cost of showing an internal token.

### Plan-step labels

Source: `models/shopify_connector_product_export_ui.py::STEP_LABELS`

| Job type | Label |
| --- | --- |
| `product_export_binding_namespace` | Establish the connector binding id |
| `product_export_create` | Create the product on Shopify |
| `product_export_update` | Update product details |
| `product_export_variants_update` | Update variants |
| `product_export_variants_create` | Add new variants |
| `product_export_media_stage` | Append an image |

---

## 3. Reconnect and backfill (S25 / S26)

Source: `views/shopify_connector_product_export_diagnostics_views.xml`,
`views/shopify_connector_product_export_views.xml`

| Slot | Shipped copy |
| --- | --- |
| Store banner — degraded | "This store's API health is degraded. Exports stay reviewable, but a confirmation taken now may be refused at apply time. Open *Export > Reconnect and Backfill* to see what is waiting." |
| Store banner — not connected | "This store is not connected. No export can run, and every open preview was expired when the connection dropped — a stale confirmation can never authorise a write. Reconnect, then re-preview." |
| Reconnect control | "Expire Open Export Previews" |
| Reconnect confirmation | "Every open export preview for this store will be expired and must be reviewed again. Continue?" |
| Reconnect explanation | "Reconnecting a store expires every open export preview, so a confirmation taken before the reconnect can never authorise a write afterwards. The next preview is a fresh read by construction." |
| Backfill filters | "Needs a fresh preview" / "Catch-up in flight" / "Caught up" / "Stalled mid-apply" |
| Backfill empty state | "Nothing to catch up on" + the reconnect explanation |

`[Fact — and a deliberate limitation]` The catch-up progress is expressed as
**counts of previews by state**, not as a watermark timestamp. The export
domain keeps no watermark; inventing one for a progress bar would be a number
with nothing behind it. What an operator reads is the real backlog: how many
exported products still need a fresh preview after the reconnect.

---

## 4. Export diagnostics (S31)

| Slot | Shipped copy |
| --- | --- |
| Filters | "Needs a decision" / "Retrying by itself" / "Failed for good" / "Awaiting reconciliation" / "Still running" / "Unclassified failure" |
| Empty state | "Nothing needs your attention" + "No export job is blocked, retrying or failed. Clear the *Needs a decision* filter to see the full export history for this connector." |

`[Decision]` The three health dimensions are **never merged into one
"unhealthy" filter**. "Needs a decision", "will retry by itself" and "gave up"
are three different asks of an operator, and merging them makes the first
invisible inside the third.

`[Fact]` No column on this screen shows `preconditions_snapshot`,
`remote_mutation_intent`, a payload, a header or a token. A diagnostics screen
that shows a request body shows whatever was in it.

---

## 5. Product form and settings (S28 / S29 / S30)

| Slot | Shipped copy |
| --- | --- |
| Product opt-in help | "When set, this product may be previewed and exported to Shopify. Export still requires a reviewed, confirmed preview for every change." |
| Product allowlist disclosure | "Only these fields, the product's options and its variants are ever exported. Collections, merchant metafields, existing media and publication state are never touched. Every change needs a reviewed, confirmed preview." |
| Shopify status help | "The Shopify product status to export. New products are created DRAFT so they are not customer-visible before anyone intends them to be. Publication is a separate, explicit action and is never a side effect of export." |
| Tags help | "Comma-separated. Exported as the complete Shopify tag list for this product." |
| Settings disclosure | "Prices are exported only when this store declares Odoo as the price source of truth; otherwise price fields are omitted from the payload entirely. Media export runs only under an explicit \"Odoo\" media direction — unset blocks it rather than choosing for you." |
| Media direction help | "Which system owns product images. Media export runs only under \"odoo\"; the Task 010B image refresh runs only under \"shopify\". Unset blocks media export rather than choosing for you." |

---

## 6. Open copy items

`[Open question]` Not closed by this deck, and stated rather than omitted:

1. **Translation.** Every string above is source English. `_t` / `_` wrapping
   is in place in the JavaScript and the projection service; the XML template
   strings are not individually marked and rely on Odoo's QWeb extraction. No
   translation catalogue is produced or claimed.
2. **The tag-removal alert is the only removal copy in the product.** If a
   later wave adds any second path that removes remote state, it needs its own
   equally loud disclosure, and this rule should move into the design system
   rather than living only here.
3. **`ui-u2-copy-deck.md` does not exist.** The U2 surfaces ship their copy
   inline in their views without a deck. That is a genuine gap in the U2
   record, not something this U3 deck closes.
