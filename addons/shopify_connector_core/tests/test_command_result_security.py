"""P15 command-result service authorization and tenant-bound replay tests."""

import uuid

from odoo.exceptions import AccessError, ValidationError
from odoo.tests.common import TransactionCase, new_test_user, tagged

from ..models.shopify_connector_command_result import (
    COMMAND_RESULT_SERVICE_CAPABILITY_CONTEXT,
    COMMAND_RESULT_SERVICE_CONTEXT,
    _COMMAND_RESULT_SERVICE_CAPABILITY,
)


@tagged("post_install", "-at_install", "shopify_connector_p15")
class TestCommandResultSecurity(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env.company
        cls.other_company = cls.env["res.company"].sudo().create({
            "name": "P15 command result other company %s" % uuid.uuid4().hex,
        })
        cls.store = cls.env["shopify.connector.store"].sudo().create({
            "name": "P15 command result store",
            "shop_domain": "p15-command-result-%s.myshopify.com" % uuid.uuid4().hex[:12],
            "api_version": "2026-07",
            "company_id": cls.company.id,
        })
        cls.other_store = cls.env["shopify.connector.store"].sudo().create({
            "name": "P15 command result other store",
            "shop_domain": "p15-command-result-other-%s.myshopify.com" % uuid.uuid4().hex[:12],
            "api_version": "2026-07",
            "company_id": cls.other_company.id,
        })
        cls.admin = new_test_user(
            cls.env,
            login="p15_command_result_admin_%s" % uuid.uuid4().hex[:8],
            groups="base.group_user,shopify_connector_core.group_shopify_connector_admin",
        )
        cls.operator = new_test_user(
            cls.env,
            login="p15_command_result_operator_%s" % uuid.uuid4().hex[:8],
            groups="base.group_user,shopify_connector_core.group_shopify_connector_operator",
        )
        cls.Result = cls.env["shopify.connector.command.result"]

    def _row(
        self, command_id=None, *, result_model=None, company=None, store=None,
    ):
        company = company or self.company
        store = store or self.store
        return (result_model or self.Result)._record_for_command(
            company_id=company.id,
            store_id=store.id,
            command_id=command_id or str(uuid.uuid4()),
            command_name="test_connection_v1",
            request_hash="a" * 64,
            result={"status": "accepted", "message": "bounded"},
            generation=0,
            service_capability=_COMMAND_RESULT_SERVICE_CAPABILITY,
        )

    def test_private_helpers_require_the_service_capability_for_every_role(self):
        row_model = self.Result
        for model in (
            row_model.with_user(self.operator),
            row_model.with_user(self.admin),
            row_model.sudo(),
        ):
            with self.assertRaises(AccessError):
                model._lock_scope(
                    self.company.id, self.store.id, "forged",
                )
            with self.assertRaises(AccessError):
                model._find_for_command(
                    company_id=self.company.id,
                    store_id=self.store.id,
                    command_id="forged",
                )
            with self.assertRaises(AccessError):
                model._record_for_command(
                    company_id=self.company.id,
                    store_id=self.store.id,
                    command_id="forged",
                    command_name="test_connection_v1",
                    request_hash="a" * 64,
                    result={"status": "accepted"},
                )

    def test_roles_have_no_direct_replay_read_or_delete_access(self):
        row = self._row()
        for user in (self.operator, self.admin):
            model = self.Result.with_user(user)
            with self.assertRaises(AccessError):
                model.search([])
            with self.assertRaises(AccessError):
                model.browse(row.id).read()
            with self.assertRaises(AccessError):
                model.browse(row.id).unlink()

    def test_sudo_and_forged_context_cannot_create_or_mutate_a_result(self):
        values = {
            "company_id": self.company.id,
            "store_id": self.store.id,
            "scope_key": "store:%d" % self.store.id,
            "command_id": str(uuid.uuid4()),
            "command_name": "test_connection_v1",
            "request_hash": "b" * 64,
            "status": "accepted",
            "generation": 0,
            "result_json": {"status": "accepted"},
        }
        for model in (
            self.Result.with_user(self.operator),
            self.Result.with_user(self.admin),
            self.Result.sudo(),
        ):
            with self.assertRaises(AccessError):
                model.create(values)
        forged = self.Result.with_user(self.admin).sudo().with_context(
            **{
                COMMAND_RESULT_SERVICE_CONTEXT: "copied-string",
                COMMAND_RESULT_SERVICE_CAPABILITY_CONTEXT: "copied-capability",
            }
        )
        with self.assertRaises(AccessError):
            forged.create(values)

        row = self._row()
        with self.assertRaises(AccessError):
            row.sudo().write({"message": "forged"})
        with self.assertRaises(AccessError):
            row.sudo().with_context(
                **{
                    COMMAND_RESULT_SERVICE_CONTEXT: "copied-string",
                    COMMAND_RESULT_SERVICE_CAPABILITY_CONTEXT: True,
                }
            ).write({"result_json": {"status": "forged"}})

    def test_capability_still_cannot_cross_the_active_company_or_store(self):
        with self.assertRaises(AccessError):
            self.Result._find_for_command(
                company_id=self.other_company.id,
                store_id=self.other_store.id,
                command_id="not-visible",
                service_capability=_COMMAND_RESULT_SERVICE_CAPABILITY,
            )
        with self.assertRaises(AccessError):
            self.Result._lock_scope(
                self.company.id,
                self.other_store.id,
                "cross-store",
                service_capability=_COMMAND_RESULT_SERVICE_CAPABILITY,
            )

    def test_record_is_bounded_and_replay_lookup_is_scoped(self):
        row = self._row()
        found = self.Result._find_for_command(
            company_id=self.company.id,
            store_id=self.store.id,
            command_id=row.command_id,
            service_capability=_COMMAND_RESULT_SERVICE_CAPABILITY,
        )
        self.assertEqual(found, row)
        with self.assertRaises(ValidationError):
            self.Result._record_for_command(
                company_id=self.company.id,
                store_id=self.store.id,
                command_id=str(uuid.uuid4()),
                command_name="test_connection_v1",
                request_hash="not-a-hash",
                result={"status": "accepted"},
                service_capability=_COMMAND_RESULT_SERVICE_CAPABILITY,
            )

    def test_admin_retention_is_active_company_scoped_but_sudo_is_global(self):
        local = self._row()
        other_model = self.Result.with_company(self.other_company)
        other = self._row(
            result_model=other_model,
            company=self.other_company,
            store=self.other_store,
        )
        self.env.cr.execute(
            "UPDATE shopify_connector_command_result "
            "SET created_at = %s WHERE id = ANY(%s)",
            ("2000-01-01 00:00:00", [local.id, other.id]),
        )
        deleted = self.Result.with_user(self.admin).run_retention()
        self.assertEqual(deleted, 1)
        self.assertFalse(self.Result.sudo().browse(local.id).exists())
        self.assertTrue(self.Result.sudo().browse(other.id).exists())

        deleted_global = self.Result.sudo().run_retention()
        self.assertEqual(deleted_global, 1)
        self.assertFalse(self.Result.sudo().browse(other.id).exists())
