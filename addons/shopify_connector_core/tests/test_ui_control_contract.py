"""Fail-closed contract for every connector frontend control.

This suite inventories the installed connector's native Odoo views and its
Owl templates. It does not decide whether copy is beautiful; the driven
browser review does that. It prevents the objective regressions behind dead
buttons, empty routes, unlabeled fields and orphaned controls from shipping
again.
"""

import pathlib
import re

from lxml import etree

from odoo.tests.common import TransactionCase, tagged


ADDONS = pathlib.Path(__file__).resolve().parents[2]
CONNECTOR_MODULE = re.compile(r'^shopify_connector_')
HANDLER = re.compile(r'this\.([A-Za-z_$][\w$]*)')


@tagged('post_install', '-at_install', 'shopify_connector_ui_contract')
class TestUiControlContract(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.modules = cls.env['ir.module.module'].sudo().search([
            ('name', '=like', 'shopify_connector_%'),
            ('state', '=', 'installed'),
        ]).mapped('name')

    def _connector_data(self, model):
        return self.env['ir.model.data'].sudo().search([
            ('module', 'in', self.modules),
            ('model', '=', model),
        ])

    def test_every_native_field_and_button_resolves(self):
        """Every native field exists and every button has a real target."""
        failures = []
        action_model = self.env['ir.actions.actions'].sudo()
        for data in self._connector_data('ir.ui.view'):
            view = self.env['ir.ui.view'].sudo().browse(data.res_id).exists()
            if not view or not CONNECTOR_MODULE.match(data.module):
                continue
            try:
                arch = etree.fromstring(view.arch_db.encode())
            except (AttributeError, etree.XMLSyntaxError) as error:
                failures.append('%s: invalid view XML: %s' % (
                    data.complete_name, error,
                ))
                continue
            try:
                model = self.env[view.model]
            except KeyError:
                failures.append('%s: unknown model %s' % (
                    data.complete_name, view.model,
                ))
                continue
            for field in arch.xpath('.//field[@name]'):
                name = field.get('name')
                if name not in model._fields:
                    failures.append('%s: field %s.%s does not exist' % (
                        data.complete_name, view.model, name,
                    ))
            for button in arch.xpath('.//button'):
                label = button.get('string') or button.get('title')
                if not label:
                    failures.append('%s: button has no accessible name' %
                                    data.complete_name)
                if button.get('special') == 'cancel':
                    continue
                kind = button.get('type')
                name = button.get('name')
                if kind not in ('object', 'action') or not name:
                    failures.append(
                        '%s: %r has no object/action target' %
                        (data.complete_name, label)
                    )
                elif kind == 'object' and not hasattr(model, name):
                    failures.append('%s: %s.%s is not callable' % (
                        data.complete_name, view.model, name,
                    ))
                elif kind == 'action':
                    try:
                        action_id = int(name)
                    except (TypeError, ValueError):
                        failures.append('%s: action target %r did not resolve' % (
                            data.complete_name, name,
                        ))
                    else:
                        if not action_model.browse(action_id).exists():
                            failures.append('%s: action %s does not exist' % (
                                data.complete_name, action_id,
                            ))
        self.assertFalse(failures, '\n'.join(failures))

    def test_every_menu_is_a_destination_or_a_purposeful_branch(self):
        failures = []
        menus = []
        for data in self._connector_data('ir.ui.menu'):
            menu = self.env['ir.ui.menu'].sudo().browse(data.res_id).exists()
            if menu:
                menus.append(menu)
                if not menu.action and not menu.child_id:
                    failures.append('%s is a dead menu' % data.complete_name)
        self.assertFalse(failures, '\n'.join(failures))

        root = self.env.ref(
            'shopify_connector_core.menu_shopify_connector_root'
        )
        self.assertEqual(
            root.child_id.sorted('sequence').mapped('name'),
            ['Overview', 'Operations', 'Reporting', 'Configuration'],
        )
        for parent in menus:
            sequences = parent.child_id.mapped('sequence')
            self.assertEqual(
                len(sequences), len(set(sequences)),
                '%s has ambiguous sibling ordering: %s' %
                (parent.complete_name, sequences),
            )

    def test_operations_reporting_and_configuration_are_not_mixed(self):
        homes = {
            'operations': self.env.ref(
                'shopify_connector_core.menu_shopify_connector_operations'
            ),
            'reporting': self.env.ref(
                'shopify_connector_core.menu_shopify_connector_reporting'
            ),
            'configuration': self.env.ref(
                'shopify_connector_core.menu_shopify_connector_configuration'
            ),
        }
        expected = {
            'operations': [
                'shopify_connector_sale.menu_shopify_connector_orders',
                'shopify_connector_product.menu_shopify_connector_catalog',
                'shopify_connector_inventory.menu_shopify_connector_inventory',
                'shopify_connector_fulfillment.menu_shopify_connector_fulfillment',
                'shopify_connector_core.menu_shopify_connector_sync_center',
                'shopify_connector_core.menu_shopify_connector_error_center',
                'shopify_connector_product_export.menu_shopify_connector_product_export_backfill',
            ],
            'reporting': [
                'shopify_connector_core.menu_shopify_connector_sync_analysis',
                'shopify_connector_core.menu_shopify_connector_logs',
            ],
            'configuration': [
                'shopify_connector_core.menu_shopify_connector_stores',
                'shopify_connector_core.menu_shopify_connector_setup_wizard',
                'shopify_connector_core.menu_shopify_connector_store_settings',
                'shopify_connector_inventory.menu_shopify_connector_location_mapping',
                'shopify_connector_inventory.menu_shopify_connector_location_refresh',
                'shopify_connector_inventory.menu_shopify_connector_location_map',
                'shopify_connector_product_export.menu_shopify_connector_product_export_settings',
                'shopify_connector_fulfillment.menu_shopify_connector_fulfillment_settings',
                'shopify_connector_sale.menu_shopify_connector_tax_mapping',
            ],
        }
        for home_name, xmlids in expected.items():
            for xmlid in xmlids:
                menu = self.env.ref(xmlid, False)
                if not menu:
                    continue
                cursor = menu
                while cursor.parent_id and cursor.parent_id != homes[home_name]:
                    cursor = cursor.parent_id
                self.assertEqual(
                    cursor.parent_id, homes[home_name],
                    '%s is not grouped under %s' % (xmlid, home_name),
                )

    def test_list_destinations_explain_an_empty_result(self):
        failures = []
        for data in self._connector_data('ir.actions.act_window'):
            action = self.env['ir.actions.act_window'].sudo().browse(
                data.res_id
            ).exists()
            if action and 'list' in (action.view_mode or '').split(','):
                if not action.help:
                    failures.append(
                        '%s has no purposeful empty-state help' %
                        data.complete_name
                    )
        self.assertFalse(failures, '\n'.join(failures))

    def test_every_owl_control_is_named_labelled_and_wired(self):
        failures = []
        templates = sorted(
            ADDONS.glob('shopify_connector_*/static/src/xml/*.xml')
        )
        self.assertTrue(templates, 'No connector Owl templates found')
        for path in templates:
            root = etree.parse(str(path)).getroot()
            module_root = path.parents[3]
            javascript = '\n'.join(
                source.read_text()
                for source in module_root.glob('static/src/js/*.js')
            )
            label_for = {
                label.get('for')
                for label in root.xpath('.//label[@for]')
            }
            for control in root.xpath('.//input|.//select|.//textarea'):
                control_id = control.get('id')
                labelled = (
                    bool(control.xpath('ancestor::label'))
                    or bool(control_id and control_id in label_for)
                    or bool(control.get('aria-label'))
                    or bool(control.get('t-att-aria-label'))
                    or bool(control.get('aria-labelledby'))
                )
                if not labelled:
                    failures.append('%s: unlabeled <%s>' % (
                        path, control.tag,
                    ))
                if control.get('type') == 'radio' and not control.get('name'):
                    failures.append('%s: radio has no group name' % path)
            for button in root.xpath('.//button'):
                text = ' '.join(''.join(button.itertext()).split())
                dynamic_name = bool(button.xpath('.//*[@t-esc or @t-out]'))
                if not (text or dynamic_name or button.get('aria-label') or
                        button.get('t-att-aria-label')):
                    failures.append('%s: button has no accessible name' % path)
                handler = button.get('t-on-click')
                if not handler:
                    failures.append('%s: button has no click handler' % path)
                    continue
                for method in HANDLER.findall(handler):
                    if not re.search(
                        r'(?:async\s+)?%s\s*\(' % re.escape(method),
                        javascript,
                    ):
                        failures.append('%s: handler %s() does not exist' % (
                            path, method,
                        ))
            for phrase in (
                'coming soon', 'lorem ipsum', 'click here', 'start again',
                'confirm without the review screen',
            ):
                visible = ' '.join(root.itertext()).lower()
                if phrase in visible:
                    failures.append('%s: vague or obsolete copy %r' % (
                        path, phrase,
                    ))
        self.assertFalse(failures, '\n'.join(failures))
