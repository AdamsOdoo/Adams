"""P15 backend command/read isolation tests.

The tests call the named application methods and the ordinary ORM as users;
menus and browser affordances are deliberately not involved.
"""

from datetime import datetime, timezone
from uuid import uuid4

from odoo.exceptions import AccessError, UserError, ValidationError
from odoo.tests.common import TransactionCase, new_test_user, tagged


@tagged("post_install", "-at_install", "shopify_connector_p15")
class TestP15StoreAdmin(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.Store = cls.env["shopify.connector.store"].sudo()
        cls.Settings = cls.env["shopify.connector.store.settings"].sudo()
        cls.Credential = cls.env["shopify.connector.store.credential"]
        cls.App = cls.env["shopify.connector.application.facade"]
        cls.admin = new_test_user(
            cls.env,
            login="p15_store_admin",
            groups="base.group_user,shopify_connector_core.group_shopify_connector_admin",
        )
        cls.operator = new_test_user(
            cls.env,
            login="p15_store_operator",
            groups="base.group_user,shopify_connector_core.group_shopify_connector_operator",
        )
        cls.company_b = cls.env["res.company"].create({
            "name": "P15 Company B",
        })
        cls.admin.sudo().write({"company_ids": [(4, cls.company_b.id)]})
        cls.operator.sudo().write({"company_ids": [(4, cls.company_b.id)]})
        cls._sequence = 0

    @classmethod
    def _store(cls, company=None):
        cls._sequence += 1
        store = cls.Store.create({
            "name": "P15 Store %d" % cls._sequence,
            "shop_domain": "p15-%d.myshopify.com" % cls._sequence,
            "api_version": "2026-07",
            "company_id": (company or cls.env.company).id,
        })
        cls.Settings._settings_service_create(
            "_canonical_settings", {"store_id": store.id},
        )
        return store

    @classmethod
    def _command(cls, user, company, store=None, payload=None, expected=0, name="save_setup_step_v1"):
        result = {
            "contract_version": 1,
            "command_id": str(uuid4()),
            "command_name": name,
            "company_id": company.id,
            "expected_generation": expected,
            "actor_uid": user.id,
            "trigger": "user",
            "requested_at": datetime.now(timezone.utc).isoformat(),
            "payload": payload or {},
        }
        if store is not None:
            result["store_id"] = store.id
        return result

    def test_ordinary_create_cannot_inject_state_or_duplicate_settings(self):
        store = self._store()
        Store = self.env["shopify.connector.store"].with_user(self.admin)
        Settings = self.env["shopify.connector.store.settings"].with_user(self.admin)
        with self.assertRaises(AccessError):
            Store.create({
                "name": "forged",
                "shop_domain": "p15-forged.myshopify.com",
                "state": "connected",
                "connection_generation": 99,
                "company_id": self.env.company.id,
            })
        with self.assertRaises(AccessError):
            Settings.create({
                "store_id": store.id,
                "setup_wizard_step_key": "review",
                "setup_wizard_step": 12,
            })
        with self.assertRaises(AccessError):
            Settings.browse(
                self.Settings.search([("store_id", "=", store.id)], limit=1).id,
            ).write({"fulfillment_switch_in_progress": True})
        self.assertEqual(
            self.Settings.search_count([("store_id", "=", store.id)]), 1,
        )

    def test_create_command_is_admin_only_and_uses_canonical_identity(self):
        company = self.env.company
        app = self.App.with_user(self.admin)
        command = self._command(
            self.admin,
            company,
            payload={
                "name": "P15 Created",
                "shop_domain": "  P15-Created.MYSHOPIFY.COM ",
            },
            name="create_store_v1",
        )
        result = app.create_store_v1(command)
        self.assertEqual(result["status"], "completed")
        store = self.Store.search(
            [("shop_domain", "=", "p15-created.myshopify.com")], limit=1,
        )
        self.assertTrue(store)
        self.assertEqual(store.state, "setup_incomplete")
        self.assertEqual(
            self.Settings.search_count([("store_id", "=", store.id)]), 1,
        )

        with self.assertRaises(AccessError):
            self.App.with_user(self.operator).create_store_v1(
                self._command(
                    self.operator,
                    company,
                    payload={
                        "name": "P15 Operator Create",
                        "shop_domain": "p15-operator.myshopify.com",
                    },
                    name="create_store_v1",
                )
            )

    def test_reads_and_commands_are_exact_active_company_scoped(self):
        local = self._store()
        foreign = self._store(self.company_b)
        app = self.App.with_user(self.admin).with_company(self.env.company)
        first = app.get_store_list_v1(
            company_ids=[self.env.company.id], limit=10,
        )
        ids = {item["store"]["id"] for item in first["data"]["stores"]}
        self.assertIn(local.id, ids)
        self.assertNotIn(foreign.id, ids)
        with self.assertRaises(AccessError):
            app.get_store_list_v1(company_ids=[self.company_b.id])
        with self.assertRaises(AccessError):
            app.get_store_list_v1(
                company_ids=[self.env.company.id, self.company_b.id],
            )
        with self.assertRaises(AccessError):
            app.get_store_admin_summary_v1(foreign.id)
        with self.assertRaises(AccessError):
            app.save_setup_step_v1(
                self._command(
                    self.admin,
                    self.env.company,
                    foreign,
                    {"step_key": "identity"},
                    name="save_setup_step_v1",
                )
            )

    def test_settings_generation_and_fingerprint_fence_stale_submit(self):
        store = self._store()
        app = self.App.with_user(self.admin)
        first = app.save_store_settings_group_v1(
            self._command(
                self.admin,
                self.env.company,
                store,
                {"group_key": "sync_domains", "values": {"product_domain_enabled": True}},
                name="save_store_settings_group_v1",
            )
        )
        self.assertEqual(first["status"], "completed")
        self.assertEqual(first["generation"], 1)
        stale = app.save_store_settings_group_v1(
            self._command(
                self.admin,
                self.env.company,
                store,
                {"group_key": "sync_domains", "values": {"sale_domain_enabled": True}},
                name="save_store_settings_group_v1",
            )
        )
        self.assertEqual(stale["status"], "conflict")
        self.assertEqual(stale["generation"], 1)
        with self.assertRaises(AccessError):
            app.save_store_settings_group_v1(
                self._command(
                    self.admin,
                    self.env.company,
                    store,
                    {
                        "group_key": "fulfillment",
                        "values": {"fulfillment_operating_mode": "mode2"},
                    },
                    expected=1,
                    name="save_store_settings_group_v1",
                )
            )

    def test_reused_command_id_cannot_cross_a_configuration_generation(self):
        store = self._store()
        app = self.App.with_user(self.admin)
        settings = self.Settings.search([("store_id", "=", store.id)], limit=1)
        self.env.cr.execute(
            "UPDATE shopify_connector_store_settings "
            "SET configuration_generation = 4 WHERE id = %s",
            (settings.id,),
        )
        settings.invalidate_recordset(["configuration_generation"])
        command_id = uuid4()
        payload = {
            "group_key": "sync_domains",
            "values": {"product_domain_enabled": True},
        }
        first_command = self._command(
            self.admin,
            self.env.company,
            store,
            payload,
            expected=4,
            name="save_store_settings_group_v1",
        )
        first_command["command_id"] = str(command_id)
        first = app.save_store_settings_group_v1(first_command)
        self.assertEqual(first["status"], "completed")
        self.assertEqual(first["generation"], 5)

        replay = app.save_store_settings_group_v1(dict(first_command))
        self.assertEqual(replay["status"], "duplicate")
        self.assertEqual(replay["original_status"], "completed")

        later_command = dict(first_command)
        later_command["expected_generation"] = 5
        with self.assertRaises(ValidationError):
            app.save_store_settings_group_v1(later_command)
        settings.invalidate_recordset(["configuration_generation"])
        self.assertEqual(settings.configuration_generation, 5)

    def test_noninteractive_or_spoofed_command_identity_is_rejected(self):
        store = self._store()
        app = self.App.with_user(self.admin)
        spoofed = self._command(
            self.admin,
            self.env.company,
            store,
            {"step_key": "identity"},
            name="save_setup_step_v1",
        )
        spoofed["actor_uid"] = self.operator.id
        with self.assertRaises(AccessError):
            app.save_setup_step_v1(spoofed)
        system = self._command(
            self.admin,
            self.env.company,
            store,
            {"step_key": "identity"},
            name="save_setup_step_v1",
        )
        system["trigger"] = "system"
        with self.assertRaises(AccessError):
            app.save_setup_step_v1(system)

    def test_pause_does_not_fabricate_a_reversible_legacy_state(self):
        store = self._store()
        result = self.App.with_user(self.admin).pause_store_v1(
            self._command(
                self.admin,
                self.env.company,
                store,
                name="pause_store_v1",
            )
        )
        self.assertEqual(result["status"], "blocked")
        store.invalidate_recordset(["state", "connection_generation"])
        self.assertEqual(store.state, "setup_incomplete")

    def test_admin_projection_never_contains_raw_credential(self):
        store = self._store()
        token = "shpat_p15_projection_must_not_escape"
        self.Credential.with_user(self.admin).action_set_token(store, token)
        projection = self.App.with_user(self.admin).get_store_admin_summary_v1(
            store.id,
        )
        rendered = repr(projection)
        self.assertNotIn(token, rendered)
        self.assertNotIn("access_token", rendered)
        self.assertNotIn("client_secret", rendered)
        self.assertTrue(projection["data"]["credentials"]["present"])

    def test_capacity_admission_rejects_the_eleventh_service_create(self):
        # Existing fixtures may have stores, so fill only the remaining slots
        # and exercise the same service seam the RPC create command uses.
        count = self.Store.search_count([])
        if count > 10:
            self.skipTest("database already exceeds the supported profile")
        for _index in range(10 - count):
            self._store()
        with self.assertRaises(UserError):
            self.App.with_user(self.admin).create_store_v1(
                self._command(
                    self.admin,
                    self.env.company,
                    payload={
                        "name": "P15 Eleventh",
                        "shop_domain": "p15-eleventh.myshopify.com",
                    },
                    name="create_store_v1",
                )
            )
