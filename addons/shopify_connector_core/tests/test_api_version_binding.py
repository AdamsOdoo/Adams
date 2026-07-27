"""TD-008: the stored API version may only ever be the connector constant.

The defect
----------
`shopify.connector.store.api_version` was a plain writable `Char`. The
store form marked it `readonly="1"`, which stops a person typing in it and
stops nothing else — an RPC call, a data import, a server action or any
`sudo()` write could set it to anything at all.

What made that misleading rather than merely untidy: the endpoint has never
been built from this column. `admin_graphql_endpoint` uses
`SHOPIFY_API_VERSION`, and every response is verified against that same
constant. So a store row saying `2025-01` could not send a single request
to 2025-01. It could only sit on the store looking authoritative while
every request went to 2026-07 — a field that lies about where requests go,
which is worse than a field that does nothing.

The correction
--------------
The column stays; no schema migration is performed. A default gives every
new store the constant without anyone passing it, and an `@api.constrains`
refuses any row that disagrees. `constrains` rather than a
`models.Constraint` because the acceptable value is a Python constant, not
a database-expressible one — and because it fires on `sudo()`, `load()`
and RPC, which are exactly the three paths the readonly attribute does not
cover.
"""

import uuid

from odoo.exceptions import ValidationError
from odoo.tests.common import TransactionCase, tagged

from odoo.addons.shopify_connector_core.tools.api_version import (
    SHOPIFY_API_VERSION,
    admin_graphql_endpoint,
)


@tagged('post_install', '-at_install')
class TestApiVersionBinding(TransactionCase):

    def _values(self, **extra):
        values = {
            'name': 'TD-008 store %s' % uuid.uuid4().hex[:6],
            'shop_domain': '%s.myshopify.com' % uuid.uuid4().hex[:10],
        }
        values.update(extra)
        return values

    # ------------------------------------------------------------------
    # Requirement 3: ordinary creation gets the centralized value
    # ------------------------------------------------------------------

    def test_a_new_store_receives_the_constant_without_being_told(self):
        store = self.env['shopify.connector.store'].create(self._values())
        self.assertEqual(store.api_version, SHOPIFY_API_VERSION)

    def test_creating_with_the_matching_value_is_accepted(self):
        """Requirement 4: existing/compatible records stay compatible."""
        store = self.env['shopify.connector.store'].create(
            self._values(api_version=SHOPIFY_API_VERSION)
        )
        self.assertEqual(store.api_version, SHOPIFY_API_VERSION)

    # ------------------------------------------------------------------
    # Requirement 2: a divergent value is refused before any request
    # ------------------------------------------------------------------

    def test_creating_with_a_divergent_version_is_refused(self):
        with self.assertRaises(ValidationError) as caught:
            self.env['shopify.connector.store'].create(
                self._values(api_version='2025-01')
            )
        self.assertIn(SHOPIFY_API_VERSION, str(caught.exception))
        self.assertIn('2025-01', str(caught.exception))

    def test_writing_a_divergent_version_is_refused(self):
        store = self.env['shopify.connector.store'].create(self._values())
        with self.assertRaises(ValidationError):
            store.write({'api_version': '2025-01'})
        store.invalidate_recordset()
        self.assertEqual(store.api_version, SHOPIFY_API_VERSION)

    def test_the_refusal_names_the_mismatch_accurately(self):
        """Requirement 7: the error has to be actionable.

        An operator hitting this needs to know which version the connector
        speaks and that it is not per-store configuration -- otherwise the
        obvious next move is to look for the setting that would let them
        change it.
        """
        store = self.env['shopify.connector.store'].create(self._values())
        with self.assertRaises(ValidationError) as caught:
            store.write({'api_version': '2099-01'})
        message = str(caught.exception)
        self.assertIn('2099-01', message)
        self.assertIn(SHOPIFY_API_VERSION, message)
        self.assertIn('cannot be reconfigured per store', message)

    # ------------------------------------------------------------------
    # Requirement 5: the elevated paths cannot slip past it
    # ------------------------------------------------------------------

    def test_sudo_cannot_set_a_divergent_version(self):
        """The path the `readonly` form attribute does not cover at all."""
        store = self.env['shopify.connector.store'].sudo().create(
            self._values()
        )
        with self.assertRaises(ValidationError):
            store.sudo().write({'api_version': '2025-04'})

    def test_an_rpc_equivalent_write_cannot_set_a_divergent_version(self):
        """`create`/`write` through the model as RPC reaches them."""
        Store = self.env['shopify.connector.store']
        with self.assertRaises(ValidationError):
            Store.create(self._values(api_version='2024-10'))
        store_id = Store.create(self._values()).id
        with self.assertRaises(ValidationError):
            Store.browse(store_id).write({'api_version': '2024-10'})

    def test_a_data_import_cannot_set_a_divergent_version(self):
        """`load()` is the import path, and it is an ORM write like any other."""
        result = self.env['shopify.connector.store'].load(
            ['name', 'shop_domain', 'api_version'],
            [['TD-008 imported', 'td008-import.myshopify.com', '2023-07']],
        )
        self.assertTrue(
            result.get('messages'),
            'the import reported no problem, so a divergent version was '
            'accepted through it',
        )
        self.assertFalse(
            self.env['shopify.connector.store'].search([
                ('shop_domain', '=', 'td008-import.myshopify.com'),
            ]),
            'a store with a divergent API version was created by import',
        )

    def test_an_import_of_the_matching_value_still_works(self):
        """The guard must not break a legitimate import."""
        result = self.env['shopify.connector.store'].load(
            ['name', 'shop_domain', 'api_version'],
            [['TD-008 imported ok', 'td008-import-ok.myshopify.com',
              SHOPIFY_API_VERSION]],
        )
        self.assertFalse(
            [m for m in result.get('messages') or []
             if m.get('type') == 'error'],
            'a legitimate import was refused: %s' % result.get('messages'),
        )
        self.assertTrue(result.get('ids'))

    # ------------------------------------------------------------------
    # Requirements 1 and 8: the constant is still the only authority
    # ------------------------------------------------------------------

    def test_the_endpoint_is_built_from_the_constant_not_the_column(self):
        store = self.env['shopify.connector.store'].create(self._values())
        self.assertIn(
            '/admin/api/%s/graphql.json' % SHOPIFY_API_VERSION,
            admin_graphql_endpoint(store.shop_domain),
        )

    def test_the_field_is_not_editable_in_the_ui(self):
        """Requirement 6: the form stays non-editable.

        Kept as an assertion rather than a comment, because the server
        guard and the form attribute answer different questions and a
        future edit could remove either one believing the other covers it.
        """
        view = self.env.ref(
            'shopify_connector_core.view_shopify_connector_store_form'
        )
        arch = view.arch_db or ''
        self.assertIn('name="api_version" readonly="1"', arch.replace('\n', ' '))

    def test_no_module_writes_a_version_that_is_not_the_constant(self):
        """Structural: nothing may hard-code a version anywhere.

        The existing per-module guard covers each addon's own sources; this
        one asserts the property that matters at the boundary -- that the
        only string any of them writes into `api_version` is the constant.
        """
        import pathlib
        import re

        addons = pathlib.Path(__file__).resolve().parents[2]
        offenders = []
        for path in sorted(addons.glob('shopify_connector_*/**/*.py')):
            if 'tests' in path.parts:
                continue
            for match in re.finditer(
                r"'api_version'\s*:\s*(.+)", path.read_text(),
            ):
                value = match.group(1).strip().rstrip(',')
                if 'SHOPIFY_API_VERSION' not in value:
                    offenders.append('%s: %s' % (path.name, value[:60]))
        self.assertFalse(offenders, (
            'these write an API version that is not the centralized '
            'constant: %s' % offenders
        ))
