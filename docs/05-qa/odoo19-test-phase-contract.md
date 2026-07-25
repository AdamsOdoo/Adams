# Odoo 19 test-phase contract — required-column / module-load-order rule

> **Status:** `[Decision — implemented]` for the connector test suite on
> `sol/pre-wave-5-stabilization`. Closes the required correction recorded in
> [issue #193](https://github.com/AdamsOdoo/Adams/issues/193) and
> [issue #157](https://github.com/AdamsOdoo/Adams/issues/157).
> **Date:** 2026-07-25. **Scope:** connector test fixtures only. No production
> behaviour is changed by this contract.

## 1. The rule

**Any connector test class whose fixtures insert rows into an Odoo business
table that is extended with a required column by a module outside that test's
own module dependency closure MUST run in the `post_install` phase.**

Mechanically:

```python
@tagged('post_install', '-at_install')
class TestSomething(TransactionCase):
    ...
```

`-at_install` is required, not cosmetic. Odoo 19 unions `tagged` arguments onto
the inherited default tag set `{'standard', 'at_install'}`
([`BaseCase.__init_subclass__`](https://github.com/odoo/odoo/blob/19.0/odoo/tests/common.py)),
so omitting `-at_install` leaves the class carrying **both** phases and trips
the decorator's `at_install` XOR `post_install` warning.

## 2. Why — verified Odoo 19 mechanism

Classification: **Fact.** Verified against `odoo/odoo@19.0`, commit
`30bde9ff758834a4912c5ae55843d3a7dad849f1`, accessed 2026-07-25 (DEC-041 D1).

The three fields named in #193/#157 are all `required=True` and are contributed
by modules the connector does not depend on:

| Field | Contributing module | Odoo 19 source |
| --- | --- | --- |
| `res.partner.autopost_bills` | `account` | [`addons/account/models/partner.py` L608-L614](https://github.com/odoo/odoo/blob/19.0/addons/account/models/partner.py#L608-L614) — `required=True`, `default='ask'` |
| `product.template.tracking` | `stock` | [`addons/stock/models/product.py` L844-L850](https://github.com/odoo/odoo/blob/19.0/addons/stock/models/product.py#L844-L850) — `required=True`, `default='none'`, `compute='_compute_tracking'`, `store=True`, `precompute=True` |
| `res.users.notification_type` | `mail` | [`addons/mail/models/res_users.py` L29-L36](https://github.com/odoo/odoo/blob/19.0/addons/mail/models/res_users.py#L29-L36) — `required=True`, `default='email'`, `compute='_compute_notification_type'`, `store=True` |

The connector dependency closures do **not** cover those modules:

| Module | `depends` | Missing contributor |
| --- | --- | --- |
| `shopify_connector_core` | `base`, `web` | `account`, `mail` |
| `shopify_connector_product` | `shopify_connector_core`, `product` | `stock`, `account` |
| `shopify_connector_sale` | `shopify_connector_core`, `shopify_connector_product`, `sale` | `stock` |
| `shopify_connector_inventory` | `shopify_connector_core`, `shopify_connector_product`, `stock` | `account` |
| `shopify_connector_fulfillment` | `shopify_connector_core`, `shopify_connector_sale`, `stock_delivery`, `sale_stock` | — (closure covers both) |

The failure is a **phase**, not a value, problem:

1. On a **fresh install**, when the connector module's `at_install` tests run,
   the contributing module has not been installed yet, so the column does not
   exist in PostgreSQL either. The `INSERT` omits a column that is not there.
   No violation. This is why #193's exact-base fresh build was green.
2. On a **warm `-u` update**, the column already exists in PostgreSQL *with its
   `NOT NULL` constraint* from the previous install, but at `at_install` time
   the contributing module is not yet loaded into the registry, so the field is
   absent from `Model._fields`. `_add_missing_default_values`
   ([`odoo/orm/models.py` L1546-L1586](https://github.com/odoo/odoo/blob/19.0/odoo/orm/models.py#L1546-L1586))
   iterates `self._fields`, never sees the field, and never supplies its
   default. The `INSERT` omits the column and PostgreSQL raises
   `null value in column "..." violates not-null constraint`.
3. `post_install` runs after **every** module is loaded. The field is on the
   model, its default (or compute) applies normally, and the insert succeeds.

### 2.1 Why setting fixture values is *not* an available fix

At `at_install` time the field is not in the registry at all. Passing
`{'tracking': 'none'}` or `{'notification_type': 'email'}` in the fixture values
raises `ValueError: Invalid field ... on model ...` **before** the insert is
attempted. Fixture-value correction cannot solve this failure family; phase
placement is the only Odoo-19-compatible correction. This is why the correction
is expressed as a tag and not as fixture data.

### 2.2 Why this is test-only

`post_install` versus `at_install` selects *when the test runs*. It does not
change any model, field, default, constraint, view, or access rule. No
production business semantics are altered, which satisfies #193's requirement
that "the correction must preserve authoritative fresh-install behavior and must
not change production business semantics merely to satisfy warm-update tests."

## 3. Runtime evidence

Classification: **Fact — EXECUTED.** Environment recorded in full so the run is
reproducible and is not confused with Odoo.sh evidence.

| Item | Value |
| --- | --- |
| Odoo | `odoo/odoo@19.0` `30bde9ff758834a4912c5ae55843d3a7dad849f1` |
| PostgreSQL | 16.13 (local disposable cluster) |
| Python | 3.12.3, Odoo 19 Noble pin set (`urllib3==2.0.7`, `cryptography==42.0.8`, `pyopenssl==24.1.0`) |
| Installed | `shopify_connector_{core,product,sale,inventory,fulfillment}`, `account`, `stock` and closures |
| Fresh install | green — all five connector modules install cleanly |
| Warm command | `-u shopify_connector_core,shopify_connector_product --test-enable` on a template copy of the fresh database |

| Run | Result |
| --- | --- |
| Warm update **before** correction | `0 failed, 96 error(s) of 1270 tests` — 26 × `res_partner.autopost_bills` + 166 × `product_template.tracking` NOT NULL violations |
| Warm update **after** correction | recorded in the PR #203 push record for the exact SHA |

This local reproduction is a **faithful reproduction of the #193 signature**, not
a substitute for Odoo.sh. The Odoo.sh baseline recorded 97 errors of 909 tests on
a database with a different installed-module set; the local run sees 1270 tests
because a different module set is installed. The *signature* — zero failures,
all errors NOT NULL violations on exactly `autopost_bills` and `tracking`, fresh
install green — matches materially. The exact-SHA Odoo.sh confirmation remains
required and is listed in the consolidated runtime campaign.

## 4. Maintenance rule

New connector test classes default to `at_install` unless tagged. Because almost
every connector fixture eventually touches `res.users`, `res.partner`, or
`product.template` — directly or through the connector code under test — the
standing rule for this repository is:

> **Every connector test class carries `@tagged('post_install', '-at_install')`
> unless it has a specific, documented reason to run at install time.**

`addons/shopify_connector_core/tests/test_phase_contract.py` enforces this
mechanically, so a new untagged class fails the suite rather than silently
reintroducing the #193 family on the next warm update.

## 5. Open items

- Exact-SHA Odoo.sh warm-update confirmation on the stabilization head
  (consolidated runtime campaign, PR #203).
- Issues #193 and #157 stay open until that confirmation is recorded and an
  independent reviewer accepts it. Writing this correction does not close them.
